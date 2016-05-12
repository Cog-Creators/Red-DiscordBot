import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *
from __main__ import send_cmd_help

import logging
import os
import asyncio
import time
from random import randint

log = logging.getLogger("red.scheduler")
log.setLevel(logging.DEBUG)


class Event:
    def __init__(self, data=None):
        self.name = data.pop('name')
        self.channel = data.pop('channel')
        self.server = data.pop('server')
        self.author = data.pop('author')
        self.command = data.pop('command')
        self.timedelta = data.pop('timedelta')
        self.repeat = data.pop('repeat')


class Scheduler:
    """Schedules commands to run every so often.

    Times are formed as follows: 1s, 2m, 3h, 5d, 1w
    """

    def __init__(self, bot):
        self.bot = bot
        self.events = fileIO('data/scheduler/events.json', 'load')
        self.queue = asyncio.PriorityQueue(loop=self.bot.loop)
        self.to_kill = []
        self._load_events()

    def save_events(self):
        fileIO('data/scheduler/events.json', 'save', self.events)
        log.debug('saved events:\n\t{}'.format(self.events))

    def _load_events(self):
        # for entry in the self.events make an Event
        for server in self.events:
            for name, event in self.events[server].items():
                ret = {}
                ret['server'] = server
                ret.update(event)
                e = Event(ret)
                self.bot.loop.create_task(self._put_event(e))

    async def _put_event(self, event, fut=None, offset=None):
        if fut is None:
            now = int(time.time())
            fut = now + event.timedelta
        if offset:
            fut += offset
        await self.queue.put((fut, event))
        log.debug('Added "{}" to the scheduler queue at {}'.format(event.name,
                                                                   fut))

    async def _add_event(self, name, command, dest_server, dest_channel,
                         author, time, repeat=False):
        if isinstance(dest_server, discord.Server):
            dest_server = dest_server.id
        if isinstance(dest_channel, discord.Channel):
            dest_channel = dest_channel.id
        if isinstance(author, discord.User):
            author = author.id

        if dest_server not in self.events:
            self.events[dest_server] = {}

        event_dict = {'name': name,
                      'channel': dest_channel,
                      'author': author,
                      'command': command,
                      'timedelta': time,
                      'repeat': repeat}

        log.debug('event dict:\n\t{}'.format(event_dict))

        if repeat:
            self.events[dest_server][name] = event_dict.copy()

        event_dict['server'] = dest_server
        e = Event(event_dict.copy())
        await self._put_event(e)

        self.save_events()

    @commands.group(no_pm=True, pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def scheduler(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @scheduler.command(pass_context=True, name="add")
    async def _scheduler_add(self, ctx, time_interval, *, command):
        """Add a command to run in [time_interval] seconds.

        Times are formed as follows: 1s, 2m, 3h, 5d, 1w
        """
        channel = ctx.message.channel
        server = ctx.message.server
        author = ctx.message.author
        name = str(time.time())
        try:
            s = self._parse_time(time_interval)
            log.debug('run command in {}s'.format(s))
        except:
            await send_cmd_help(ctx)
            return
        if s < 30:
            await self.bot.reply('yeah I can\'t do that, your time'
                                 ' interval is waaaay too short and I\'ll'
                                 ' likely get rate limited. Try going above'
                                 ' 30 seconds.')
            return
        log.debug('add {} "{}" to {} on {} in {}s'.format(
            name, command, channel.name, server.name, s))
        await self._add_event(name, command, server, channel, author, s)

    @scheduler.command(pass_context=True, name="repeat")
    async def _scheduler_repeat(self, ctx, name, time_interval, *, command):
        """Add a command to run every [time_interval] seconds.

        Times are formed as follows: 1s, 2m, 3h, 5d, 1w
        """
        channel = ctx.message.channel
        server = ctx.message.server
        author = ctx.message.author
        name = name.lower()
        try:
            s = self._parse_time(time_interval)
            log.debug('run command in {}s'.format(s))
        except:
            await send_cmd_help(ctx)
            return
        if s < 30:
            await self.bot.reply('yeah I can\'t do that, your time'
                                 ' interval is waaaay too short and I\'ll'
                                 ' likely get rate limited. Try going above'
                                 ' 30 seconds.')
            return
        log.debug('add {} "{}" to {} on {} every {}s'.format(
            name, command, channel.name, server.name, s))
        await self._add_event(name, command, server, channel, author, s, True)

    @scheduler.command(pass_context=True, name="remove")
    async def _scheduler_remove(self, ctx, name):
        """Removes scheduled command from running.
        """
        server = ctx.message.server
        name = name.lower()
        if server.id not in self.events:
            await self.bot.say('No events are scheduled for this server.')
            return
        if name not in self.events[server.id]:
            await self.bot.say('That event does not exist on this server.')
            return

        # self._remove_from_queue(name)
        del self.events[server.id][name]
        self.save_events()

    @scheduler.command(pass_context=True, name="list")
    async def _scheduler_list(self, ctx):
        """Lists all repeated commands
        """
        server = ctx.message.server
        if server.id not in self.events:
            await self.bot.say('No events scheduled for this server.')
            return
        mess = "Names:\n\t"
        mess += "\n\t".join(sorted(self.events[server.id].keys()))
        await self.bot.say(box(mess))

    def _parse_time(self, time):
        translate = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        timespec = time[-1]
        if timespec.lower() not in translate:
            raise ValueError
        timeint = int(time[:-1])
        return timeint * translate.get(timespec)

    def run_coro(self, event):
        data = {}
        data['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())
        data['id'] = randint(10**(17), (10**18) - 1)
        data['content'] = self.bot.command_prefix[0] + event.command
        data['channel'] = self.bot.get_channel(event.channel)
        data['author'] = {'id': event.author}
        data['nonce'] = randint(-2**32, (2**32) - 1)
        data['channel_id'] = event.channel
        fake_message = discord.Message(**data)
        coro = self.bot.process_commands(fake_message)
        self.bot.loop.create_task(coro)

    async def queue_manager(self):
        while self == self.bot.get_cog('Scheduler'):
            if self.queue.qsize() != 0:
                curr_time = int(time.time())
                next_tuple = await self.queue.get()
                next_time = next_tuple[0]
                next_event = next_tuple[1]
                diff = next_time - curr_time
                diff = diff if diff >= 0 else 0
                if diff < 30:
                    log.debug('scheduling call of "{}" in {}s'.format(
                        next_event.name, diff))
                    fut = self.bot.loop.call_later(diff, self.run_coro,
                                                   next_event)
                    self.to_kill.append(fut)
                    if next_event.repeat:
                        await self._put_event(next_event, next_time,
                                              next_event.timedelta)
                else:
                    log.debug('Will run {} "{}" in {}s'.format(
                        next_event.name, next_event.command, diff))
                    await self._put_event(next_event, next_time)
            await asyncio.sleep(15)
        log.debug('manager dying')
        while self.queue.qsize() != 0:
            await self.queue.get()
        while len(self.to_kill) != 0:
            curr = self.to_kill.pop()
            curr.cancel()


def check_folder():
    if not os.path.exists('data/scheduler'):
        os.mkdir('data/scheduler')


def check_files():
    f = 'data/scheduler/events.json'
    if not os.path.exists(f):
        fileIO(f, 'save', {})


def setup(bot):
    check_folder()
    check_files()
    n = Scheduler(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.queue_manager())
    bot.add_cog(n)
