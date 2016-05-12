import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os


default_greeting = "Welcome {0.name} to {1.name}!"
default_settings = {"GREETING": default_greeting, "ON": False, "CHANNEL": None}

class Welcome:
    """Welcomes new members to the server in the default channel"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/welcome/settings.json", "load")


    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def welcomeset(self, ctx):
        """Sets welcome module settings"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO("data/welcome/settings.json","save",self.settings)
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            msg += "GREETING: {}\n".format(self.settings[server.id]["GREETING"])
            msg += "CHANNEL: #{}\n".format(self.get_welcome_channel(server)) 
            msg += "ON: {}\n".format(self.settings[server.id]["ON"]) 
            msg += "```"
            await self.bot.say(msg)

    @welcomeset.command(pass_context=True)
    async def greeting(self, ctx, *, format_msg):
        """Sets the welcome message format for the server.

        {0} is user
        {1} is server
        Default is set to: 
            Welcome {0.name} to {1.name}!

        Example formats:
            {0.mention}.. What are you doing here?
            {1.name} has a new member! {0.name}#{0.discriminator} - {0.id}
            Someone new joined! Who is it?! D: IS HE HERE TO HURT US?!
        """
        server = ctx.message.server
        self.settings[server.id]["GREETING"] = format_msg
        fileIO("data/welcome/settings.json","save",self.settings)
        await self.bot.say("Welcome message set for the server.")
        await self.send_testing_msg(ctx)

    @welcomeset.command(pass_context=True)
    async def toggle(self, ctx):
        """Turns on/off welcoming new users to the server"""
        server = ctx.message.server
        self.settings[server.id]["ON"] = not self.settings[server.id]["ON"]
        if self.settings[server.id]["ON"]:
            await self.bot.say("I will now welcome new users to the server.")
            await self.send_testing_msg(ctx)
        else:
            await self.bot.say("I will no longer welcome new users.")
        fileIO("data/welcome/settings.json", "save", self.settings)

    @welcomeset.command(pass_context=True)
    async def channel(self, ctx, channel : discord.Channel=None): 
        """Sets the channel to send the welcome message

        If channel isn't specified, the server's default channel will be used"""
        server = ctx.message.server
        if channel == None:
            channel = ctx.message.server.default_channel
        if not server.get_member(self.bot.user.id).permissions_in(channel).send_messages:
            await self.bot.say("I do not have permissions to send messages to {0.mention}".format(channel))
            return
        self.settings[server.id]["CHANNEL"] = channel.id
        fileIO("data/welcome/settings.json", "save", self.settings)
        channel = self.get_welcome_channel(server)
        await self.bot.send_message(channel,"I will now send welcome messages to {0.mention}".format(channel))
        await self.send_testing_msg(ctx)


    async def member_join(self, member):
        server = member.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO("data/welcome/settings.json","save",self.settings)
        if not self.settings[server.id]["ON"]:
            return
        if server == None:
            print("Server is None. Private Message or some new fangled Discord thing?.. Anyways there be an error, the user was {}".format(member.name))
            return
        channel = self.get_welcome_channel(server)
        if self.speak_permissions(server):
            await self.bot.send_message(channel, self.settings[server.id]["GREETING"].format(member, server))
        else:
            print("Permissions Error. User that joined: {0.name}".format(member))
            print("Bot doesn't have permissions to send messages to {0.name}'s #{1.name} channel".format(server,channel))


    def get_welcome_channel(self, server):
        return server.get_channel(self.settings[server.id]["CHANNEL"])

    def speak_permissions(self, server):
        channel = self.get_welcome_channel(server)
        return server.get_member(self.bot.user.id).permissions_in(channel).send_messages

    async def send_testing_msg(self, ctx):
        server = ctx.message.server
        channel = self.get_welcome_channel(server)
        await self.bot.send_message(ctx.message.channel, "`Sending a testing message to `{0.mention}".format(channel))
        if self.speak_permissions(server):
            await self.bot.send_message(channel, self.settings[server.id]["GREETING"].format(ctx.message.author,server))
        else: 
            await self.bot.send_message(ctx.message.channel,"I do not have permissions to send messages to {0.mention}".format(channel))
        

def check_folders():
    if not os.path.exists("data/welcome"):
        print("Creating data/welcome folder...")
        os.makedirs("data/welcome")

def check_files():
    f = "data/welcome/settings.json"
    if not fileIO(f, "check"):
        print("Creating welcome settings.json...")
        fileIO(f, "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Welcome(bot)
    bot.add_listener(n.member_join,"on_member_join")
    bot.add_cog(n)
