import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
import re

JSON = 'data/purgepins.json'

UNIT_TABLE = {'s': 1, 'm': 60, 'h': 60 * 60}


def _parse_time(time):
    if any(u in time for u in UNIT_TABLE.keys()):
        delim = '([0-9.]*[{}])'.format(''.join(UNIT_TABLE.keys()))
        time = re.split(delim, time)
        time = sum([_timespec_sec(t) for t in time if t != ''])
    return int(time)


def _timespec_sec(t):
    timespec = t[-1]
    if timespec.lower() not in UNIT_TABLE:
        raise ValueError('Unknown time unit "%c"' % timespec)
    timeint = float(t[:-1])
    return timeint * UNIT_TABLE[timespec]


class PurgePins:

    def __init__(self, bot):
        self.bot = bot
        self.handles = {}
        self.settings = dataIO.load_json(JSON)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def purgepins(self, ctx, wait: str = None):
        """Set delay for deletion of pin messages, or disable it.\n
        Accepted time units are s(econds), m(inutes), h(ours).
        Example: !purgepins 1h30m
        To disable purepins, run !purgepins off"""
        channel = ctx.message.channel
        if wait:
            if wait.strip().lower() in ['none', 'off']:
                wait = False
            else:
                try:
                    wait = _parse_time(wait)
                except ValueError:
                    await send_cmd_help(ctx)
                    return
            self.settings[channel.id] = wait

            dataIO.save_json(JSON, self.settings)
        else:
            wait = self.settings.get(channel.id, False)

        if wait is False:
            msg = ('Pin notifications in this channel are not set to be '
                   'automatically deleted.')
        else:
            msg = 'Pin notifications in this channel are set to be deleted '
            if wait > 0:
                msg += 'after %s seconds.' % wait
            else:
                msg += 'immediately.'

        if not channel.permissions_for(channel.server.me).manage_messages:
            msg += ("\n**Warning:** I don't have permissions to delete "
                    "messages in this channel!")

        await self.bot.say(msg)

    async def on_ready(self):
        pass

    async def on_message(self, message):
        channel = message.channel

        if not message.server:
            return
        if not channel.permissions_for(channel.server.me).manage_messages:
            return

        timeout = self.settings.get(channel.id, False)
        enabled = timeout is not False
        if enabled and message.type is discord.MessageType.pins_add:
            self.bot.loop.call_later(timeout, self._delete, message)

    async def on_message_delete(self, message):
        if message.id in self.handles:
            self.handles[message.id].cancel()
            del self.handles[message.id]

    def _delete(self, message):
        delf = self.bot.delete_message(message)
        self.bot.loop.create_task(delf)


def check_files(bot):
    if not dataIO.is_valid_json(JSON):
        print("Creating default purgepins json...")
        dataIO.save_json(JSON, {})


def setup(bot):
    check_files(bot)
    n = PurgePins(bot)
    bot.add_cog(n)
