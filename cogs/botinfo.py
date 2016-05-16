import discord
from discord.ext import commands
from discord import utils
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *
from __main__ import settings, send_cmd_help
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
        return self.bot.command_prefix[0]

    @property
    def join_message(self):
        ret = bold("Hey there!") + "\n"
        ret += "I'm a bot made by the ***MonsterLyrics Team*** and I just got asked to join this server.\n"
        ret += "If you don't want me here feel free to kick me.\n"
        ret += "Otherwise, my current prefixes are " + self.prefixes
        ret += " and you can see all of my commands by running "
        ret += inline("!help")
        ret += "\n\n"
        ret += italics("If you need help, or something goes wrong:") + " "
        ret += inline("!contact [message]")
        ret += " and it will be sent to my owner.\n"
        ret += "I can also do " + bold('Twitch Emotes') + "!\n"
        ret += "See " + inline("!help Emotes")
        return ret

    # @commands.command()
    # async def servers(self):
    #     '''General global server information'''
    #     servers = sorted([server.name for server in self.bot.servers])
    #     ret = "I am currently in "
    #     ret += bold(len(servers))
    #     ret += " servers with "
    #     ret += bold(len([m for m in self.bot.get_all_members()]))
    #     ret += " members.\n"
    #     await self.bot.say(ret)

    @commands.command(pass_context=True)
    async def contact(self, ctx, *, message: str):
        """Send a message to my owner"""
        author = ctx.message.author.name
        server = ctx.message.server.name
        owner = utils.find(lambda mem: str(mem.id) == settings.owner,
                           self.bot.get_all_members())
        message = "A message from {} on {}:\n\t```{}```".format(
            author, server, message)
        if owner is not None:
            await self.bot.send_message(owner, message)
        else:
            await self.bot.say("Sorry, my owner is offline, try again later?")

    @commands.command(pass_context=True)
    async def botinfo(self):
        """Displays stuff about ME!"""
        msg = "Hey there! I'm a _fully modular_ bot made by Twentysix and modified by the ***MonsterLyrics Team***.\n"
        msg += "Some stuff about me:\n"
        msg += "\n"
        msg += "**Language:** Python/discord.py\n"
        msg += "**Owner:** <@!116079569349378049>\n"
        msg += "**Scrutinise my code:** <http://github.fishyfing.xyz>\n"
        msg += "**Need more help? Drop me an email!** support@bot.fishyfing.xyz"
        msg += "**Want me on your server? Use this link:** <http://invite.fishyfing.xyz>"
        await self.bot.say(msg)

    # @commands.group(pass_context=True, no_pm=True)
    # async def welcome(self, ctx):
    #     if not ctx.invoked_subcommand:
    #         await send_cmd_help(ctx)

    # @welcome.command(name="set", pass_context=True)
    # async def _welcome_set(self, ctx, *, message):
    #     """You can use $user to mention the member who joins"""
    #     server = ctx.message.server.id
    #     channel_mentions = ctx.message.channel_mentions
    #     if server not in self.welcome_messages:
    #         self.welcome_messages[server] = {}
    #     if len(channel_mentions) == 0:
    #         channel = ctx.message.server.default_channel
    #     else:
    #         poss_mention = message.split(" ")[0]
    #         if not re.compile(r'<#([0-9]+)>').match(poss_mention):
    #             channel = ctx.message.server.default_channel
    #         else:
    #             channel = utils.get(channel_mentions, mention=poss_mention)
    #             message = message[len(channel.mention) + 1:]  # for the space

        # self.welcome_messages[server][channel.id] = message
        # fileIO("data/botinfo/welcome.json", "save", self.welcome_messages)

        # await self.bot.say('Member join message on '
        #                    '{} set to:\n\n{}'.format(channel.mention, message))

    # @welcome.command(name="remove", pass_context=True)
    # async def _welcome_remove(self, ctx, channel):
    #     server = ctx.message.server.id
    #     channel_mentions = ctx.message.channel_mentions
    #     if server not in self.welcome_messages:
    #         return
    #     channel = utils.get(channel_mentions, mention=channel)
    #     if channel is None:
    #         await self.bot.say('Invalid channel.')
    #         return

    #     if channel.id in self.welcome_messages[server]:
    #         del self.welcome_messages[server][channel.id]
    #         self.save_welcome()

    async def serverjoin(self, server):
        channel = server.default_channel
        print('Joined {} at {}'.format(server.name, datetime.datetime.now()))
        try:
            await self.bot.send_message(channel, self.join_message)
        except discord.errors.Forbidden:
            pass

    # async def memberjoin(self, member):
    #     server = member.server
    #     welcome = self.welcome_messages.copy()
    #     if server.id in welcome:
    #         for chan_id in welcome[server.id]:
    #             channel = server.get_channel(chan_id)
    #             if channel is None:
    #                 del self.welcome_messages[server.id][chan_id]
    #                 self.save_welcome()
    #                 continue
    #             template = welcome[server.id][chan_id]
    #             message = string.Template(template)
    #             message = message.safe_substitute(user=member.mention)
    #             await self.bot.send_message(channel, message)


# def check_folders():
#     if not os.path.exists("data/botinfo"):
#         print("Creating default mentiontracker's welcome.json")
#         os.mkdir("data/botinfo")


# def check_files():
#     f = "data/botinfo/welcome.json"
#     if not fileIO(f, "check"):
#         print("Creating default botinfo's welcome.json...")
#         fileIO(f, "save", {})


def setup(bot):
    #check_folders()
    #check_files()
    n = BotInfo(bot)
    bot.add_listener(n.serverjoin, "on_server_join")
    #bot.add_listener(n.memberjoin, "on_member_join")
    bot.add_cog(n)
