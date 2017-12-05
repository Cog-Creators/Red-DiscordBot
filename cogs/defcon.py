import os

import discord
from discord.ext import commands

from .utils import checks
from .utils.dataIO import dataIO


class Defcon:

    """Server DEFCON Levels"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/defcon/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.valid_defcons = ['1', '2', '3', '4', '5']

    @commands.command(name="defcon", no_pm=True, pass_context=True)
    async def defcon(self, ctx):
        """Reports the server DEFCON level."""
        server = ctx.message.server
        nick = self.settings.get(server.id, {}).get("authority", "none")
        level = self.settings.get(server.id, {}).get("defcon", 5)
        await self.post_defcon(ctx, str(level), nick)

    @commands.command(name="defcon+", no_pm=True, pass_context=True)
    async def defconplus(self, ctx):
        """Elevates the server DEFCON level."""
        server = ctx.message.server
        nick = ctx.message.author.display_name
        level = self.settings.get(server.id, {}).get("defcon", 5)
        if level == 1:
            await self.bot.say("We are already at DEFCON 1! Oh no!")
        else:
            level -= 1

        self.settings.setdefault(server.id, {}).update(defcon=level, authority=nick)
        dataIO.save_json(self.settings_path, self.settings)
        await self.post_defcon(ctx, str(level), nick)

    @commands.command(name="defcon-", no_pm=True, pass_context=True)
    async def defconminus(self, ctx):
        """Lowers the server DEFCON level."""
        server = ctx.message.server
        nick = ctx.message.author.display_name
        level = self.settings.get(server.id, {}).get("defcon", 5)
        if level == 5:
            await self.bot.say("We are already at DEFCON 5! Relax!")
        else:
            level += 1

        self.settings.setdefault(server.id, {}).update(defcon=level, authority=nick)
        dataIO.save_json(self.settings_path, self.settings)
        await self.post_defcon(ctx, str(level), nick)

    @commands.command(name="setdefcon", no_pm=True, pass_context=True)
    async def setdefcon(self, ctx, level: int):
        """Manually set the server DEFCON level in case of emergency."""
        server = ctx.message.server
        nick = ctx.message.author.display_name
        if str(level) in self.valid_defcons:
            self.settings.setdefault(server.id, {}).update(defcon=level, authority=nick)
            dataIO.save_json(self.settings_path, self.settings)
            await self.post_defcon(ctx, str(level), nick)
        else:
            await self.bot.say("Not a valid DEFCON level. Haven't "
                               "you seen War Games?")

    @commands.command(name="defconchan", no_pm=True, pass_context=True)
    @checks.mod()
    async def defconchan(self, ctx, channel: discord.Channel=None):
        """Constrain defcon alerts to a specific channel.
        Omit the channel argument to clear the setting."""
        me = ctx.message.server.me
        author = ctx.message.author
        server = ctx.message.server
        if channel is None:
            self.settings.setdefault(server.id, {}).update(channel=None)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("DEFCON channel setting cleared.")
            return

        if channel.type != discord.ChannelType.text:
            await self.bot.say("Channel must be a text channel")
            return
        elif not channel.permissions_for(author).send_messages:
            await self.bot.say("You're not allowed to send messages in that channel.")
            return
        elif not channel.permissions_for(me).send_messages:
            await self.bot.say("I'm not allowed to send messaages in that channel.")
            return

        self.settings.setdefault(server.id, {}).update(channel=channel.id)
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Defcon channel set to **{}**.".format(channel.name))

    async def post_defcon(self, ctx, level, nick):

        icon_url = 'http://i.imgur.com/MfDcOEU.gif'

        if level == '5':
            color = 0x0080ff
            thumbnail_url = 'https://i.imgur.com/ynitQlf.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = ("No known threats to your self esteem "
                        "exist at this time.")
            instructions = ("- Partipaction in online games is encouraged\n"
                            "- Remain vigilant of insider threats\n"
                            "- Report all suspicious activity")
        elif level == '4':
            color = 0x00ff00
            thumbnail_url = 'https://i.imgur.com/sRhQekI.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Trace amounts of sodium have been detected.'
            instructions = ("- Inhale deeply through your nose and "
                            "count to 5\n"
                            "- Take short breaks between games\n"
                            "- Do not encourage trolls")
        elif level == '3':
            color = 0xffff00
            thumbnail_url = 'https://i.imgur.com/xY9SkkA.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Sodium levels may exceed OSHA exposure limits.'
            instructions = ("- Use extreme caution when playing ranked games\n"
                            "- Log off non-essential communication channels\n"
                            "- Put on your big boy pants")
        elif level == '2':
            color = 0xff0000
            thumbnail_url = 'https://i.imgur.com/cSzezRE.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Sodium levels are approaching critical mass'
            instructions = ("- Avoid ranked game modes at all costs\n"
                            "- Mute all hostile voice channels\n"
                            "- Queue up some relaxing jazz music")
        elif level == '1':
            color = 0xffffff
            thumbnail_url = 'https://i.imgur.com/NVB1AFA.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Total destruction is IMMINENT.'
            instructions = ("- Do not participate in any online games\n"
                            "- Log off all social media immediately\n"
                            "- Take shelter outdoors until the "
                            "all-clear is given")

        embed = discord.Embed(title="\u2063", color=color)
        embed.set_author(name=author, icon_url=icon_url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name=subtitle, value=instructions, inline=False)
        embed.set_footer(text="Authority: {}".format(nick))

        server = ctx.message.server
        channel = self.bot.get_channel(self.settings.get(server.id, {}).get("channel", None))
        if channel is None:
            await self.bot.say(embed=embed)
        else:
            if channel != ctx.message.channel:
                await self.bot.say("Done.")
            await self.bot.send_message(channel, embed=embed)


def check_folders():
    folder = "data/defcon"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {}
    if not dataIO.is_valid_json("data/defcon/settings.json"):
        print("Creating default defcon settings.json...")
        dataIO.save_json("data/defcon/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    n = Defcon(bot)
    bot.add_cog(n)
