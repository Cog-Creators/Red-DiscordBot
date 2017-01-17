import discord
from discord.ext import commands
from discord import utils
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *
import os
import re
import string

import datetime


class BotInfo:
    def __init__(self, bot):
        self.bot = bot
        self.welcome_messages = fileIO("data/botinfo/welcome.json", "load")

    def save_welcome(self):
        fileIO("data/botinfo/welcome.json", "save", self.welcome_messages)

    @property
    def prefixes(self):
        '''ret = "["
        middle = "|".join(self.bot.command_prefix)
        return ret+middle+"]"'''
        return self.bot.settings.get_prefixes(None)[0]

    @property
    def join_message(self):
        ret = bold("Hey there!") + "\n"
        ret += "I'm Squid and I just got asked to join this server.\n"
        ret += "If you don't want me here feel free to kick me.\n"
        ret += "Otherwise, my current prefixes are " + self.prefixes
        ret += " and you can see all of my commands by running "
        ret += inline(self.prefixes + "help")
        ret += "\n\n"
        ret += italics("If you want a custom plugin made:") + " "
        ret += inline("~contact [desc]")
        ret += " and it will be sent to my owner.\n"
        ret += "I can also do " + bold('Twitch Emotes') + "!\n"
        ret += "See " + inline(self.prefixes + "help Emotes")
        return ret

    @commands.command()
    async def servercount(self):
        '''General global server information'''
        servers = sorted([server.name for server in self.bot.servers])
        ret = "I am currently in "
        ret += bold(len(servers))
        ret += " servers with "
        ret += bold(len(set(self.bot.get_all_members())))
        ret += " members.\n"
        await self.bot.say(ret)

    @commands.command()
    async def support(self):
        """Support continued bot and cog development.
        """
        await self.bot.say("If you'd like to support continued bot and cog "
                           "development, I'd greatly appreciate that.\n\n"
                           "Patreon: https://www.patreon.com/tekulvw")

    @commands.command()
    async def info(self):
        """General bot information"""
        await self.bot.say("I'm Squid, a general, multi-purpose bot that is"
                           " always getting new features. You can access my"
                           " new support server here"
                           " (http://discord.me/Squid). All of my"
                           " help documentation can be found by using `~help`"
                           " so feel free to mess around with commands to"
                           " find what you like! If you'd like to support"
                           " continued development, check out `~support`")

    @commands.command()
    async def invite(self):
        """Invite me to a new server"""
        await self.bot.say("You must have manage server permissions in order"
                           " to add me to a new server. If you do, just click"
                           " the link below and select the server you wish for"
                           " me to join.\n\n"
                           "https://discordapp.com/oauth2/authorize?&"
                           "client_id=168417388663013376&scope=bot&"
                           "permissions=36826127")

    @commands.group(pass_context=True, no_pm=True)
    async def welcome(self, ctx):
        if not ctx.invoked_subcommand:
            await self.bot.send_cmd_help_help(ctx)

    @welcome.command(name="set", pass_context=True)
    async def _welcome_set(self, ctx, *, message):
        """You can use $user to mention the member who joins"""
        server = ctx.message.server.id
        channel_mentions = ctx.message.channel_mentions
        if server not in self.welcome_messages:
            self.welcome_messages[server] = {}
        if len(channel_mentions) == 0:
            channel = ctx.message.server.default_channel
        else:
            poss_mention = message.split(" ")[0]
            if not re.compile(r'<#([0-9]+)>').match(poss_mention):
                channel = ctx.message.server.default_channel
            else:
                channel = utils.get(channel_mentions, mention=poss_mention)
                message = message[len(channel.mention) + 1:]  # for the space

        self.welcome_messages[server][channel.id] = message
        fileIO("data/botinfo/welcome.json", "save", self.welcome_messages)

        await self.bot.say('Member join message on '
                           '{} set to:\n\n{}'.format(channel.mention, message))

    @welcome.command(name="remove", pass_context=True)
    async def _welcome_remove(self, ctx, channel):
        server = ctx.message.server.id
        channel_mentions = ctx.message.channel_mentions
        if server not in self.welcome_messages:
            return
        channel = utils.get(channel_mentions, mention=channel)
        if channel is None:
            await self.bot.say('Invalid channel.')
            return

        if channel.id in self.welcome_messages[server]:
            del self.welcome_messages[server][channel.id]
            self.save_welcome()

    async def serverjoin(self, server):
        channel = server.default_channel
        print('Joined {} at {}'.format(server.name, datetime.datetime.now()))
        try:
            await self.bot.send_message(channel, self.join_message)
        except discord.errors.Forbidden:
            pass

    async def memberjoin(self, member):
        server = member.server
        welcome = self.welcome_messages.copy()
        if server.id in welcome:
            for chan_id in welcome[server.id]:
                channel = server.get_channel(chan_id)
                if channel is None:
                    del self.welcome_messages[server.id][chan_id]
                    self.save_welcome()
                    continue
                template = welcome[server.id][chan_id]
                message = string.Template(template)
                message = message.safe_substitute(user=member.mention)
                await self.bot.send_message(channel, message)


def check_folders():
    if not os.path.exists("data/botinfo"):
        print("Creating default mentiontracker's welcome.json")
        os.mkdir("data/botinfo")


def check_files():
    f = "data/botinfo/welcome.json"
    if not fileIO(f, "check"):
        print("Creating default botinfo's welcome.json...")
        fileIO(f, "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = BotInfo(bot)
    bot.add_listener(n.serverjoin, "on_server_join")
    bot.add_listener(n.memberjoin, "on_member_join")
    bot.add_cog(n)
