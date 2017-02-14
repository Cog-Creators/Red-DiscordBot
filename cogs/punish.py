import discord
from discord.ext import commands
from .utils import checks
import logging
from cogs.utils.dataIO import dataIO
import os
import time
import re

try:
    from tabulate import tabulate
except Exception as e:
    raise RuntimeError("You must run `pip3 install tabulate`.") from e

UserInputError = commands.UserInputError

log = logging.getLogger('red.punish')

UNIT_TABLE = {'s': 1, 'm': 60, 'h': 60 * 60, 'd': 60 * 60 * 24}
UNIT_SUF_TABLE = {'sec': (1, ''),
                  'min': (60, ''),
                  'hr': (60 * 60, 's'),
                  'day': (60 * 60 * 24, 's')
                  }
DEFAULT_TIMEOUT = '30m'
PURGE_MESSAGES = 1  # for cpunish


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


def _generate_timespec(sec):
    timespec = []

    def sort_key(kt):
        k, t = kt
        return t[0]
    for unit, kt in sorted(UNIT_SUF_TABLE.items(), key=sort_key, reverse=True):
        secs, suf = kt
        q = sec // secs
        if q:
            if q <= 1:
                suf = ''
            timespec.append('%02.d%s%s' % (q, unit, suf))
        sec = sec % secs
    return ', '.join(timespec)


class Punish:
    """Adds the ability to punish users."""

    # --- Format
    # {
    # serverid : {
    #   memberid : {
    #       until : timestamp
    #       by : memberid
    #       reason: str
    #       }
    #    }
    # }
    # ---

    def __init__(self, bot):
        self.bot = bot
        self.location = 'data/punish/settings.json'
        self.json = compat_load(self.location)
        self.handles = {}
        self.role_name = 'Punished'
        bot.loop.create_task(self.on_load())

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def cpunish(self, ctx, user: discord.Member, duration: str=None, *, reason: str=None):
        """Same as punish but cleans up after itself and the target"""
        server = ctx.message.server

        if ctx.message.author.top_role <= user.top_role:
            await self.bot.say('Permission denied.')
            return

        role = await self.setup_role(server, quiet=True)
        if not role:
            return

        if server.id not in self.json:
            self.json[server.id] = {}

        if not duration:
            duration = _parse_time(DEFAULT_TIMEOUT)
            timestamp = time.time() + duration
        elif duration.lower() in ['forever', 'inf', 'infinite']:
            duration = None
            timestamp = None
        else:
            duration = _parse_time(duration)
            timestamp = time.time() + duration

        if server.id not in self.json:
            self.json[server.id] = {}

        self.json[server.id][user.id] = {
            'until': timestamp,
            'by': ctx.message.author.id,
            'reason': reason
        }

        await self.bot.add_roles(user, role)
        dataIO.save_json(self.location, self.json)

        # schedule callback for role removal
        if duration:
            self.schedule_unpunish(duration, user, reason)

        def is_user(m):
            return m == ctx.message or m.author == user

        try:
            await self.bot.purge_from(ctx.message.channel, limit=PURGE_MESSAGES + 1, check=is_user)
            await self.bot.delete_message(ctx.message)
        except discord.errors.Forbidden:
            await self.bot.send_message(ctx.message.channel, "Punishment set, but I need"
                                        "permissions to manage messages to clean up.")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def punish(self, ctx, user: discord.Member, duration: str=None, *, reason: str=None):
        """Puts a user into timeout for a specified time period, with an optional reason.
        Time specification is any combination of number with the units s,m,h,d.
        Example: !punish @idiot 1.1h10m Enough bitching already!"""

        server = ctx.message.server

        if ctx.message.author.top_role <= user.top_role:
            await self.bot.say('Permission denied.')
            return

        role = await self.setup_role(server)
        if role is None:
            return

        if server.id not in self.json:
            self.json[server.id] = {}

        if user.id in self.json[server.id]:
            msg = 'User was already punished; resetting their timer...'
        elif role in user.roles:
            msg = 'User was punished but had no timer, adding it now...'
        else:
            msg = 'Done.'

        if not duration:
            msg += ' Using default duration of ' + DEFAULT_TIMEOUT
            duration = _parse_time(DEFAULT_TIMEOUT)
            timestamp = time.time() + duration
        elif duration.lower() in ['forever', 'inf', 'infinite']:
            duration = None
            timestamp = None
        else:
            duration = _parse_time(duration)
            timestamp = time.time() + duration

        if server.id not in self.json:
            self.json[server.id] = {}

        self.json[server.id][user.id] = {
            'until': timestamp,
            'by': ctx.message.author.id,
            'reason': reason
        }

        await self.bot.add_roles(user, role)
        dataIO.save_json(self.location, self.json)

        # schedule callback for role removal
        if duration:
            self.schedule_unpunish(duration, user, reason)

        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True, name='lspunish')
    @checks.mod_or_permissions(manage_messages=True)
    async def list_punished(self, ctx):
        """Shows a table of punished users with time, mod and reason.

        Displays punished users, time remaining, responsible moderator and
        the reason for punishment, if any."""
        server = ctx.message.server
        server_id = server.id
        if not (server_id in self.json and self.json[server_id]):
            await self.bot.say("No users are currently punished.")
            return

        def getmname(mid):
            member = discord.utils.get(server.members, id=mid)
            if member:
                if member.nick:
                    return '%s (%s)' % (member.nick, member)
                else:
                    return str(member)
            else:
                return '(member not present, id #%d)'

        headers = ['Member', 'Remaining', 'Punished by', 'Reason']
        table = []
        disp_table = []
        now = time.time()
        for member_id, data in self.json[server_id].items():
            member_name = getmname(member_id)
            punisher_name = getmname(data['by'])
            reason = data['reason']
            t = data['until']
            sort = t if t else float("inf")
            table.append((sort, member_name, t, punisher_name, reason))

        for _, name, rem, mod, reason in sorted(table, key=lambda x: x[0]):
            remaining = _generate_timespec(rem - now) if rem else 'forever'
            if not reason:
                reason = 'n/a'
            disp_table.append((name, remaining, mod, reason))

        msg = '```\n%s\n```' % tabulate(disp_table, headers)
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason: str=None):
        """Warns a user with boilerplate about the rules."""
        msg = ['Hey %s, ' % user.mention]
        msg.append("you're doing something that might get you muted if you keep "
                   "doing it.")
        if reason:
            msg.append(" Specifically, %s." % reason)
        msg.append("Be sure to review the server rules.")
        await self.bot.say(' '.join(msg))

    async def setup_role(self, server, quiet=False):
        role = discord.utils.get(server.roles, name=self.role_name)
        if not role:
            if not (any(r.permissions.manage_roles for r in server.me.roles) and
                    any(r.permissions.manage_channels for r in server.me.roles)):
                await self.bot.say("The Manage Roles and Manage Channels permissions are required to use this command.")
                return None
            else:
                msg = "The %s role doesn't exist; Creating it now... " % self.role_name
                if not quiet:
                    msgobj = await self.bot.reply(msg)
                log.debug('Creating punish role')
                perms = discord.Permissions.none()
                role = await self.bot.create_role(server, name=self.role_name, permissions=perms)
                if not quiet:
                    msgobj = await self.bot.edit_message(msgobj, msgobj.content + 'configuring channels... ')
                for c in server.channels:
                    await self.on_channel_create(c, role)
                if not quiet:
                    await self.bot.edit_message(msgobj, msgobj.content + 'done.')
        return role

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def unpunish(self, ctx, user: discord.Member):
        """Removes punishment from a user. Same as removing the role directly"""
        role = discord.utils.get(user.server.roles, name=self.role_name)
        sid = user.server.id
        if role and role in user.roles:
            reason = 'Punishment manually ended early by %s. ' % ctx.message.author
            if self.json[sid][user.id]['reason']:
                reason += self.json[sid][user.id]['reason']
            await self._unpunish(user, reason)
            await self.bot.say('Done.')
        else:
            await self.bot.say("That user wasn't punished.")

    async def on_load(self):
        """Called when bot is ready and each time cog is (re)loaded"""
        await self.bot.wait_until_ready()
        # copy so we can delete stuff from the original
        for serverid, members in self.json.copy().items():
            server = discord.utils.get(self.bot.servers, id=serverid)
            if not server:
                del(self.json[serverid])
                continue
            role = discord.utils.get(server.roles, name=self.role_name)
            for member_id, data in members.items():
                until = data['until']
                if until:
                    duration = until - time.time()
                member = discord.utils.get(server.members, id=member_id)
                if until and duration < 0:
                    if member:
                        reason = 'Punishment removal overdue, maybe bot was offline. '
                        if self.json[server.id][member_id]['reason']:
                            reason += self.json[server.id][member_id]['reason']
                        await self._unpunish(member, reason)
                    else:  # member disappeared
                        del(self.json[server.id][member.id])
                elif member:
                    await self.bot.add_roles(member, role)
                    if until:
                        self.schedule_unpunish(duration, member)
        dataIO.save_json(self.location, self.json)

    # Functions related to unpunishing

    def schedule_unpunish(self, delay, member, reason=None):
        """Schedules role removal, canceling and removing existing tasks if present"""
        handle = self.bot.loop.call_later(delay, self._unpunish_cb, member, reason)
        sid = member.server.id
        if sid not in self.handles:
            self.handles[sid] = {}
        if member.id in self.handles[sid]:
            self.handles[sid][member.id].cancel()
        self.handles[sid][member.id] = handle

    def _unpunish_cb(self, member, reason=None):
        """Regular function to be used as unpunish callback"""
        def wrap(member, reason):
            return self._unpunish(member, reason)
        self.bot.loop.create_task(wrap(member, reason))

    async def _unpunish(self, member, reason):
        """Remove punish role, delete record and task handle"""
        role = discord.utils.get(member.server.roles, name=self.role_name)
        if role:
            # Has to be done first to prevent triggering on_member_update listener
            self._unpunish_data(member)
            await self.bot.remove_roles(member, role)
            msg = 'Your punishiment in %s has ended.' % member.server.name
            if reason:
                msg += "\nReason was: %s" % reason
            await self.bot.send_message(member, msg)

    def _unpunish_data(self, member):
        """Removes punish data entry and cancels any present callback"""
        sid = member.server.id
        if sid in self.json and member.id in self.json[sid]:
            del(self.json[member.server.id][member.id])
            dataIO.save_json(self.location, self.json)

        if sid in self.handles and member.id in self.handles[sid]:
            self.handles[sid][member.id].cancel()
            del(self.handles[member.server.id][member.id])

    # Listeners

    async def on_channel_create(self, c, role=None):
        """Run when new channels are created and set up role permissions"""
        if c.is_private:
            return
        perms = discord.PermissionOverwrite()
        if c.type == discord.ChannelType.text:
            perms.send_messages = False
            perms.send_tts_messages = False
        elif c.type == discord.ChannelType.voice:
            perms.speak = False
        if not role:
            role = discord.utils.get(c.server.roles, name=self.role_name)
        await self.bot.edit_channel_permissions(c, role, overwrite=perms)

    async def on_member_update(self, before, after):
        """Remove scheduled unpunish when manually removed"""
        sid = before.server.id
        role = discord.utils.get(before.server.roles, name=self.role_name)
        if not (sid in self.json and before.id in self.json[sid]):
            return
        if role and role in before.roles and role not in after.roles:
            msg = 'Your punishiment in %s was ended early by a moderator/admin.' % before.server.name
            if self.json[sid][before.id]['reason']:
                msg += '\nReason was: ' + self.json[sid][before.id]['reason']
            await self.bot.send_message(after, msg)
            self._unpunish_data(after)

    async def on_member_join(self, member):
        """Restore punishment if punished user leaves/rejoins"""
        sid = member.server.id
        role = discord.utils.get(member.server.roles, name=self.role_name)
        if role:
            if not (sid in self.json and member.id in self.json[sid]):
                return
            duration = self.json[sid][member.id]['until'] - time.time()
            if duration > 0:
                await self.bot.add_roles(member, role)
                reason = 'punishment re-added on rejoin. '
                if self.json[sid][member.id]['reason']:
                    reason += self.json[sid][member.id]['reason']
                if member.id not in self.handles[sid]:
                    self.schedule_unpunish(duration, member, reason)


def compat_load(path):
    data = dataIO.load_json(path)
    for server, punishments in data.items():
        for user, pdata in punishments.items():
            by = pdata.pop('givenby', None)  # able to read Kownlin json
            by = by if by else pdata.pop('by', None)
            pdata['by'] = by
            pdata['until'] = pdata.pop('until', None)
            pdata['reason'] = pdata.pop('reason', None)
    return data


def check_folder():
    if not os.path.exists('data/punish'):
        log.debug('Creating folder: data/punish')
        os.makedirs('data/punish')


def check_file():
    f = 'data/punish/settings.json'
    if dataIO.is_valid_json(f) is False:
        log.debug('Creating json: settings.json')
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = Punish(bot)
    bot.add_cog(n)
