import discord
from .utils import checks
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from __main__ import send_cmd_help
import os

class on_join:
    """Allows you to set your own server on_join message!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.derp = "data/on_join/wow.json"
        self.loveme = dataIO.load_json(self.derp)

    @checks.is_owner()
    @commands.group(pass_context=True)
    async def joinmsg(self, ctx):
        """Join Message - Allows you to set a message when the bot joined the server!"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
    
    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def toggle(self, ctx):
        """Turn JoinMsg on or off! It's up to you..."""
        
        if self.loveme["TOGGLE"] is False:
            self.loveme["TOGGLE"] = True
            dataIO.save_json(self.derp, self.loveme)
            await self.bot.say("The on_join have been turned on!")
        else:
            self.loveme["TOGGLE"] = False
            dataIO.save_json(self.derp, self.loveme)
            await self.bot.say("The on_join have been turned off!")

    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def embedmsg(self, ctx):
        """Do you want the welcome message to be embed?"""

        if self.loveme["EMB"] is False:
            self.loveme["EMB"] = True
            dataIO.save_json(self.derp, self.loveme)
            await self.bot.say("The on_join will now be embed!")
        else:
            self.loveme["EMB"] = False
            dataIO.save_json(self.derp, self.loveme)
            await self.bot.say("The on_join will not be embed!")
    
    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def embedauthor(self, ctx):
        """If you want to see the bot has an author in the embed."""

        if self.loveme["Emba"] is False:
            self.loveme["Emba"] = True
            dataIO.save_json(self.derp, self.loveme)
            await self.bot.say("The embed message will now display the bot as an author!")
        else:
            self.loveme["Emba"] = False
            dataIO.save_json(self.derp, self.loveme)
            await self.bot.say("The embed message will now not display the bot as an author!")

    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def message(self, ctx, *, msg):
        """You can set the way your on_join is set!


        {0} = The Joined Server
        {1} = The Bot
        {2} = The Bot Owner...

        Default Message: Hello, {0.name}! I am, {1.user.name}! I was created by {2}!
        """

        self.loveme["MESSAGE"] = msg
        dataIO.save_json(self.derp, self.loveme)
        await self.bot.say("Congrats, you have set your message to ```{}```".format(msg))

    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def setfooter(self, ctx, *, msg):
        """Allows you to set the footer message, if it's embed

        {0} = The Joined Server
        {1} = The Bot
        {2} = The Bot Owner...

        Default Message: This is your footer!
        """

        self.loveme["Embf"] = msg
        dataIO.save_json(self.derp, self.loveme)
        await self.bot.say("Congrats, you have set your embed footer to ```{}```".format(msg))

    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def setname(self, ctx, *, msg):
        """Allows you to set the embed name message, if it's embed

        {0} = The Joined Server
        {1} = The Bot
        {2} = The Bot Owner...

        Default Message: Welcome to {0.name}!
        """

        self.loveme["MESSAGE_TITLE"] = msg
        dataIO.save_json(self.derp, self.loveme)
        await self.bot.say("Congrats, you have set your embed message name to ```{}```".format(msg))
    
    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def settitle(self, ctx, *, msg):
        """Allows you to set the title message, if it's embed

        {0} = The Joined Server
        {1} = The Bot
        {2} = The Bot Owner...

        Default Message: This is your title!
        """

        self.loveme["Embt"] = msg
        dataIO.save_json(self.derp, self.loveme)
        await self.bot.say("Congrats, you have set your embed title name to ```{}```".format(msg))

    @checks.is_owner()
    @joinmsg.command(pass_context=True)
    async def setcolor(self, ctx, *, msg):
        """Allows you to set the embed color, if it's embed

        Needs to be a color code. Example: 0xFFFFFF 
        """
        self.loveme["Embc"] = msg
        dataIO.save_json(self.derp, self.loveme)
        await self.bot.say("Congrats, you have set your embed title name to ```{}```".format(msg))

    async def mowie(self, server):
        owner = discord.utils.get(self.bot.get_all_members(), id=self.bot.settings.owner)
        bota = self.bot
        msg = self.loveme["MESSAGE"]
        send = msg.format(server, bota, owner)
        channel = server.default_channel
        members = set(server.members)
        bots = filter(lambda m: m.bot, members)
        user = len(members) - len(bots)
        sketchy = len(bots) > len(members)
        em = discord.Embed(description="I've been added to **{}**! ^w^\nUsers: {}  Bots: {}".format(server.name, len(user), len(bots)), color=0x356a21)
        em.set_thumbnail(url=server.icon_url)
        em.set_footer(text="Current Server Count: {}".format(len(self.bot.servers)))
        if self.loveme["TOGGLE"] is True:
            await self.bot.send_message(discord.Object(id='433715765129248770'), embed=em)
            print("{} has joined {}!".format(bota.user.name, server.name))
            if self.loveme["EMB"]:
                try:
                    title = self.loveme["Embt"].format(server, bota, owner)
                    footer = self.loveme["Embf"].format(server, bota, owner)
                    auth = self.loveme["Emba"]
                    msgname = self.loveme["MESSAGE_TITLE"].format(server, bota, owner)
                    try:
                        color = int(self.loveme["Embc"], 16)
                    except:
                        color = 0x898a8b
                    wow=discord.Embed(title=title, color=color)
                    if auth:
                        wow.set_author(name=bota.user.name, url=bota.user.avatar_url)
                    wow.add_field(name=msgname, value=send)
                    wow.set_footer(text=footer)
                    await self.bot.send_message(channel, embed=wow)
                except discord.HTTPException:
                    await self.bot.send_message(channel, "The bot needs embed permissions")
            else:
                await self.bot.send_message(channel, send)


    async def on_server_join(self, server):
        await self.mowie(server)

def check_folders():
    if not os.path.exists("data/on_join"):
        print("Creating the on_join folder, so be patient...")
        os.makedirs("data/on_join")
        print("Finish!")

def check_files():
    twentysix = "data/on_join/wow.json"
    json = {
        "EMB" : False,
        "TOGGLE" : False,
        "MESSAGE" : "Hello, {0.name}! I am, {1.user.name}! I was created by {2.user.name}!",
        "Embc" : "0xFFFFFF",
        "Embf" : "This is your footer!",
        "Emba" : False,
        "Embt" : "This is your title!",
        "MESSAGE_TITLE" : "Welcome to {0.name}!"
    }

    if not dataIO.is_valid_json(twentysix):
        print("Derp Derp Derp...")
        dataIO.save_json(twentysix, json)
        print("Created wow.json!")

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(on_join(bot))
