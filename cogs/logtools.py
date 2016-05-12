import discord
from .utils import checks
from discord.ext import commands
from __main__ import send_cmd_help
from time import time
import os


class LogTools:
    def __init__(self, bot):
        self.bot = bot
        self.file = 'data/logtools/{}.log'

    @commands.group(pass_context=True, no_pm=True, aliases=['log'])
    async def logs(self, context):
        """Retrieve logs, the slowpoke way."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @logs.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def get(self, context, channel: discord.Channel, number: int):
        """[channel] [number]"""
        log = []
        async for message in self.bot.logs_from(channel, limit=number):
            author = message.author.name
            author_mention = message.author.id
            content = message.clean_content
            timestamp = str(message.timestamp)[:-7]
            log_msg = '[{}] {} ({}): {}'.format(timestamp, author, author_mention, content)
            log.append(log_msg)
        try:
            t = self.file.format(str(time()))
            with open(t, encoding='utf-8', mode="w") as f:
                for message in log[::-1]:
                    f.write(message+'\n')
            f.close()
            await self.bot.send_file(context.message.channel, t)
            os.remove(t)
        except Exception as error:
            print(error)

    @logs.command(pass_context=True, no_pm=True, aliases=['rp'])
    @checks.mod_or_permissions(manage_messages=True)
    async def roleplay(self, context, channel: discord.Channel, number: int):
        """[channel] [number]"""
        log = []
        async for message in self.bot.logs_from(channel, limit=number):
            author = message.author.name
            content = message.clean_content
            timestamp = str(message.timestamp)[:-7]
            log_msg = '[{}] {}: {}'.format(timestamp, author, content)
            log.append(log_msg)
        try:
            t = self.file.format(str(time()))
            with open(t, encoding='utf-8', mode="w") as f:
                for message in log[::-1]:
                    f.write(message+'\n')
            f.close()
            await self.bot.send_file(context.message.channel, t)
            os.remove(t)
        except Exception as error:
            print(error)


def check_folder():
    if not os.path.exists("data/logtools"):
        print("Creating data/logtools folder...")
        os.makedirs("data/logtools")


def setup(bot):
    check_folder()
    n = LogTools(bot)
    bot.add_cog(n)
