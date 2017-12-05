import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils.chat_formatting import box
import os
import logging
import copy
import asyncio
import itertools

try:
    from tabulate import tabulate
except Exception as e:
    raise RuntimeError("You must run `pip3 install tabulate`.") from e

from __main__ import send_cmd_help, settings

log = logging.getLogger("red.permissions")


class PermissionsError(CommandNotFound):
    """
    Base exception for all others in this module
    """


class BadCommand(PermissionsError):
    """
    Thrown when we can't decipher a command from string into a command object.
    """
    pass


class RoleNotFound(PermissionsError):
    """
    Thrown when we can't get a valid role from a list and given name
    """
    pass


class SpaceNotation(BadCommand):
    """
    Throw when, with some certainty, we can say that a command was space
        notated, which would only occur when some idiot...fishy...tries to
        surround a command in quotes.
    """
    pass


class Check:
    """
    This is what we're going to stick into the checks for Command objects
    """

    def __init__(self, command):
        self.command = command

    def __call__(self, ctx):
        author = ctx.message.author
        perm_cog = ctx.bot.get_cog('Permissions')
        # Here we guarantee we're still loaded, if not, don't impede anything.
        if perm_cog is None or not hasattr(perm_cog, 'resolve_permission'):
            return True
        elif ctx.message.channel.is_private:
            return True

        has_perm = perm_cog.resolve_permission(ctx)

        if has_perm:
            log.debug("user {} allowed to execute {}"
                      " chid {}".format(ctx.message.author.name,
                                        ctx.command.qualified_name,
                                        ctx.message.channel.id))
        else:
            log.debug("user {} not allowed to execute {}"
                      " chid {}".format(ctx.message.author.name,
                                        ctx.command.qualified_name,
                                        ctx.message.channel.id))

        can_run = has_perm or author.id == self.owner_id

        return can_run

    @property
    def owner_id(self):
        return settings.owner


class Permissions:
    """
    The VERY important thing to note about this cog is that every command will
    be interpreted in dot notation instead of space notation (e.g how you call
    them from within Discord)
    """

    def __init__(self, bot):
        self.bot = bot

        # All the saved permission levels with role ID's
        self.perms_we_want = self._load_perms()
        self.perm_lock = asyncio.Lock()

        self.check_adder = bot.loop.create_task(self.add_checks_to_all())

    def __unload(self):
        if self.check_adder:
            self.check_adder.cancel()

        for cmd_dot in self.perms_we_want:
            try:
                cmd = self._get_command(cmd_dot)
            except BadCommand:
                # Just means the command couldn't be found which is okay
                #   because we're unloading anyways.
                pass
            else:
                keepers = [c for c in cmd.checks if not isinstance(c, Check)]
                cmd.checks = keepers

    async def _check_perm_entry(self, command, server):
        await self.perm_lock.acquire()
        if command not in self.perms_we_want:
            self.perms_we_want[command] = {"LOCKS": {"GLOBAL": False,
                                                     "SERVERS": {},
                                                     "CHANNELS": {}}}

        if server.id not in self.perms_we_want[command]:
            self.perms_we_want[command][server.id] = {"CHANNELS": {},
                                                      "ROLES": {}}

        if "LOCKS" not in self.perms_we_want[command]:
            self.perms_we_want[command]["LOCKS"] = {"GLOBAL": False,
                                                    "COGS": [],
                                                    "SERVERS": {},
                                                    "CHANNELS": {}}

        if "COGS" not in self.perms_we_want[command]["LOCKS"]:
            self.perms_we_want[command]["LOCKS"]["COGS"] = []
        self.perm_lock.release()

    def _error_raise(exc):
        def deco(func):
            def pred(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    raise exc from e
            return pred
        return deco

    async def _error_responses(self, error, ctx):
        original = error.__cause__
        if isinstance(original, SpaceNotation):
            await self.bot.send_message(
                ctx.message.channel, "You just tried space notation, how about"
                                     " you replace those spaces with dots and"
                                     " try again?")
        elif isinstance(original, BadCommand):
            await self.bot.send_message(ctx.message.channel,
                                        "Command not found. Make sure you're"
                                        " using dots and not spaces (e.g."
                                        " playlist.add instead of \"playlist"
                                        " add\")")
        elif isinstance(original, RoleNotFound):
            await self.bot.send_message(ctx.message.channel,
                                        "Role not found. Make sure you're"
                                        " using dots and not spaces (e.g."
                                        " playlist.add instead of \"playlist"
                                        " add\")")

    @_error_raise(BadCommand)
    def _get_command(self, cmd_string):
        cmd = cmd_string.split('.')
        ret = self.bot.commands[cmd.pop(0)]
        while len(cmd) > 0:
            ret = ret.commands[cmd.pop(0)]
        return ret

    async def _get_info(self, server, command):
        await self.perm_lock.acquire()
        command = command.qualified_name.replace(' ', '.')

        per_server = self.perms_we_want[command][server.id]
        ret = {"CHANNELS": [], "ROLES": []}
        for chanid, status in per_server["CHANNELS"].items():
            chan = self.bot.get_channel(chanid)
            if chan:
                allowed = self._is_allow(status)
                allow_str = "Allowed" if allowed else "Denied"
                ret["CHANNELS"].append((chan.name, allow_str))

        for roleid, status in per_server["ROLES"].items():
            role = self._get_role_from_id(server, roleid)
            if role:
                allowed = self._is_allow(status)
                allow_str = "Allowed" if allowed else "Denied"
                ret["ROLES"].append((role.name, allow_str))

        chan_sort = sorted(ret["CHANNELS"], key=lambda r: r[0])
        ret["CHANNELS"] = chan_sort

        role_sort = sorted(ret["ROLES"], key=lambda r: r[0])
        ret["ROLES"] = role_sort
        self.perm_lock.release()

        return ret

    def _get_ordered_role_list(self, server=None, roles=None):
        """
        First item in ordered list is @\u200Beveryone, e.g. the highest role
            in the Discord role heirarchy is last in this list.
        """
        if server is None and roles is None:
            raise PermissionsError("Must supply either server or role.")

        if server:
            roles = server.roles
        else:
            server = roles[0].server

        ordered_roles = sorted(roles, key=lambda r: r.position)

        log.debug("Ordered roles for sid {}:\n\t{}".format(server.id,
                                                           ordered_roles))

        return sorted(roles, key=lambda r: r.position)

    def _get_role(self, roles, role_string):
        if role_string.lower() == "everyone":
            role_string = "@everyone"

        role = discord.utils.find(
            lambda r: r.name.lower() == role_string.lower(), roles)

        if role is None:
            raise RoleNotFound(roles[0].server, role_string)

        return role

    def _get_role_from_id(self, server, roleid):
        try:
            roles = server.roles
        except AttributeError:
            server = self._get_server_from_id(server)
            try:
                roles = server.roles
            except AttributeError:
                raise RoleNotFound(server, roleid)

        role = discord.utils.get(roles, id=roleid)
        if role is None:
            raise RoleNotFound(server, roleid)
        return role

    def _get_server_from_id(self, serverid):
        return discord.utils.get(self.bot.servers, id=serverid)

    def _has_higher_role(self, member, role):
        server = member.server
        roles = self._get_ordered_role_list(server=server)
        try:
            role_index = roles.index(role)
        except ValueError:
            # Role isn't in the ordered role list
            return False

        higher_roles = roles[role_index + 1:]

        if any([r in higher_roles for r in member.roles]):
            return True
        return False

    def _is_allow(self, permission):
        if permission.startswith("+"):
            return True
        return False

    def _is_locked(self, command, server, channel):
        locks = self.perms_we_want[command].get("LOCKS", None)

        if locks is None:
            return False

        global_lock = locks["GLOBAL"]
        server_lock = locks["SERVERS"].get(server.id, False)
        channel_lock = locks["CHANNELS"].get(channel.id, False)

        cog_name = self._get_command(command).cog_name
        cog_lock = cog_name in locks.get("COGS", set())

        return global_lock or cog_lock or server_lock or channel_lock

    def _load_perms(self):
        try:
            ret = dataIO.load_json("data/permissions/perms.json")
        except:
            ret = {}
            if not os.path.exists("data/permissions"):
                os.mkdir("data/permissions")
            dataIO.save_json("data/permissions/perms.json", ret)
        return ret

    async def _lock_channel(self, command, channel, lock=True):
        await self._check_perm_entry(command, channel.server)

        with (await self.perm_lock):
            self.perms_we_want[command]["LOCKS"]["CHANNELS"][channel.id] = lock

        self._save_perms()

    async def _lock_cog(self, server, cogname, lock=True):
        cmds = list(filter(lambda c: c.cog_name == cogname,
                           self.bot.commands.values()))
        for cmd_name in cmds:
            command = cmd_name.qualified_name.replace(" ", ".")
            await self._check_perm_entry(command, server)
            await self.perm_lock.acquire()
            if lock:
                if cogname not in \
                        self.perms_we_want[command]["LOCKS"]["COGS"]:
                    self.perms_we_want[command]["LOCKS"]["COGS"].append(
                        cogname)
            else:
                try:
                    self.perms_we_want[command]["LOCKS"]["COGS"].remove(
                        cogname)
                except Exception:
                    # Cog wasn't locked
                    pass
            self.perm_lock.release()

        self._save_perms()

    async def _lock_global(self, command, server, lock=True):
        await self._check_perm_entry(command, server)

        with (await self.perm_lock):
            self.perms_we_want[command]["LOCKS"]["GLOBAL"] = lock

        self._save_perms()

    async def _lock_server(self, command, server, lock=True):
        await self._check_perm_entry(command, server)

        with (await self.perm_lock):
            self.perms_we_want[command]["LOCKS"]["SERVERS"][server.id] = lock

        self._save_perms()

    async def _reset(self, server):
        await self.perm_lock.acquire()
        for cmd in self.perms_we_want:
            try:
                del self.perms_we_want[cmd][server.id]
            except KeyError:
                pass

            for chan in server.channels:
                try:
                    del self.perms_we_want[cmd]["LOCKS"]["CHANNELS"][chan.id]
                except KeyError:
                    pass
        self.perm_lock.release()
        self._save_perms()

    async def _reset_channel(self, command, server, channel):
        try:
            command = command.qualified_name.replace(' ', '.')
        except AttributeError:
            # If we pass a cog name in as command
            cmds = list(filter(lambda c: c.cog_name == command,
                               self.bot.commands.values()))
            for cmd in cmds:
                await self._reset_channel(cmd, server, channel)
            return
        if command not in self.perms_we_want:
            return

        await self.perm_lock.acquire()
        cmd_perms = self.perms_we_want[command]
        if server.id not in cmd_perms:
            return

        try:
            del self.perms_we_want[command][server.id]["CHANNELS"][channel.id]
        except KeyError:
            pass

        self.perm_lock.release()
        self._save_perms()

    async def _reset_permission(self, command, server, channel=None,
                                role=None):
        if channel:
            await self._reset_channel(command, server, channel)
        else:
            await self._reset_role(command, server, role)

    async def _reset_role(self, command, server, role):
        try:
            command = command.qualified_name.replace(' ', '.')
        except AttributeError:
            # If we pass a cog name in as command
            cmds = list(filter(lambda c: c.cog_name == command,
                               self.bot.commands.values()))
            for cmd in cmds:
                self._reset_role(cmd, server, role)
            return

        await self.perm_lock.acquire()
        if command not in self.perms_we_want:
            return

        cmd_perms = self.perms_we_want[command]
        if server.id not in cmd_perms:
            return

        try:
            del self.perms_we_want[command][server.id]["ROLES"][role.id]
        except KeyError:
            pass
        self.perm_lock.release()

        self._save_perms()

    def resolve_permission(self, ctx):
        command = ctx.command.qualified_name.replace(' ', '.')
        server = ctx.message.server
        channel = ctx.message.channel
        roles = reversed(self._get_ordered_role_list(
            roles=ctx.message.author.roles))

        try:
            per_command = self.perms_we_want[command]
        except KeyError:
            log.debug("{} not in perms_we_want".format(command))
            return True

        try:
            per_server = per_command[server.id]
        except KeyError:
            # In this case the server is not in the perms we want to check
            #   therefore we're just gonna assume the default "allow"
            log.debug("sid {} not found for command {}".format(server.id,
                                                               command))
            return True

        channel_perm_dict = per_server["CHANNELS"]
        role_perm_dict = per_server["ROLES"]

        if channel.id not in channel_perm_dict:
            # Again, assume default "allow"
            log.debug("chanid {} not found, chan_perm = True".format(
                channel.id))
            channel_perm = True
        else:
            # We know that an admin has set permission on this channel
            if self._is_allow(channel_perm_dict[channel.id]):
                log.debug("chanid {} found and allowed".format(channel.id))
                channel_perm = True
            else:
                log.debug("chanid {} found and denied".format(channel.id))
                channel_perm = False

        for role in roles:
            if role.id in role_perm_dict:
                if self._is_allow(role_perm_dict[role.id]):
                    log.debug("role {} found and allowed".format(role.id))
                    role_perm = True
                    break
                else:
                    log.debug("role {} found and denied".format(role.id))
                    role_perm = False
                    break
        else:
            # By doing this we let the channel perm override in the case of
            #   no role perms being set.
            log.debug("role not found, ignoring roles")
            role_perm = None

        is_locked = self._is_locked(command, server, channel)

        has_perm = ((role_perm is None and channel_perm) or
                    (role_perm is True)) and not is_locked
        log.debug("uid {} has perm: {}".format(ctx.message.author.id,
                                               has_perm))
        return has_perm

    def _save_perms(self):
        dataIO.save_json('data/permissions/perms.json', self.perms_we_want)

    async def _set_channel(self, command, server, channel, allow):
        try:
            cmd_dot_name = command.qualified_name.replace(" ", ".")
        except AttributeError:
            # If we pass a cog name in as command
            cmds = list(filter(lambda c: c.cog_name == command,
                               self.bot.commands.values()))
            for cmd in cmds:
                await self._set_channel(cmd, server, channel, allow)
            return

        if allow:
            allow = "+"
        else:
            allow = "-"

        await self.perm_lock.acquire()
        if cmd_dot_name not in self.perms_we_want:
            self.perms_we_want[cmd_dot_name] = {}
        if server.id not in self.perms_we_want[cmd_dot_name]:
            self.perms_we_want[cmd_dot_name][server.id] = \
                {"CHANNELS": {}, "ROLES": {}}
        self.perms_we_want[cmd_dot_name][server.id]["CHANNELS"][channel.id] = \
            "{}{}".format(allow, cmd_dot_name)
        self.perm_lock.release()
        self._save_perms()

    async def _set_permission(self, command, server, channel=None, role=None,
                              allow=True):
        """Command can be a command object or cog name (string)"""
        if channel:
            await self._set_channel(command, server, channel, allow)
        else:
            await self._set_role(command, server, role, allow)

    async def _set_role(self, command, server, role, allow):
        """Command can be a command object or cog name (string)"""
        try:
            cmd_dot_name = command.qualified_name.replace(" ", ".")
        except AttributeError:
            # If we pass a cog name in as command
            cmds = list(filter(lambda c: c.cog_name == command,
                               self.bot.commands.values()))
            for cmd in cmds:
                await self._set_role(cmd, server, role, allow)
        else:
            if allow:
                allow = "+"
            else:
                allow = "-"
            await self.perm_lock.acquire()
            if cmd_dot_name not in self.perms_we_want:
                self.perms_we_want[cmd_dot_name] = {}
            if server.id not in self.perms_we_want[cmd_dot_name]:
                self.perms_we_want[cmd_dot_name][server.id] = \
                    {"CHANNELS": {}, "ROLES": {}}
            self.perms_we_want[cmd_dot_name][server.id]["ROLES"][role.id] = \
                "{}{}".format(allow, cmd_dot_name)
            self.perm_lock.release()
            self._save_perms()

    @commands.group(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(manage_roles=True)
    async def p(self, ctx):
        """Permissions manager"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @p.group(pass_context=True)
    async def channel(self, ctx):
        """Channel based permissions

        Will be overridden by role based permissions."""
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)

    @channel.command(pass_context=True, name="allow", hidden=True)
    async def channel_allow(self, ctx, command, channel: discord.Channel=None):
        """Explicitly allows [command/cog] to be used in [channel].

        Not really useful because role perm overrides channel perm"""
        server = ctx.message.server
        try:
            command_obj = self._get_command(command)
        except BadCommand as e:
            try:
                self.bot.cogs[command]
                command_obj = command
            except KeyError:
                raise e
        if channel is None:
            channel = ctx.message.channel
        await self._set_permission(command_obj, server, channel=channel)

        await self.bot.say("Channel {} allowed use of {}.".format(
            channel.mention, command))

    @channel.command(pass_context=True, name="deny")
    async def channel_deny(self, ctx, command, channel: discord.Channel=None):
        """Explicitly denies [command/cog] usage in [channel]

        Overridden by role based permissions"""
        server = ctx.message.server
        try:
            command_obj = self._get_command(command)
        except BadCommand as e:
            try:
                self.bot.cogs[command]
                command_obj = command
            except KeyError:
                raise e
        if channel is None:
            channel = ctx.message.channel
        await self._set_permission(command_obj, server, channel=channel,
                                   allow=False)

        await self.bot.say("Channel {} denied use of {}.".format(
            channel.mention, command))

    @channel.command(pass_context=True, name="reset")
    async def channel_reset(self, ctx, command, channel: discord.Channel=None):
        """Resets permissions of [command/cog] on [channel] to the default"""
        server = ctx.message.server
        try:
            command_obj = self._get_command(command)
        except BadCommand as e:
            try:
                self.bot.cogs[command]
                command_obj = command
            except KeyError:
                raise e
        if channel is None:
            channel = ctx.message.channel
        await self._reset_permission(command_obj, server, channel=channel)

        await self.bot.say("Channel {} permissions for {} reset.".format(
            channel.mention, command))

    @p.command(pass_context=True)
    async def info(self, ctx, command):
        """Gives current info about permissions on your server"""
        server = ctx.message.server
        channel = ctx.message.channel
        if command not in self.perms_we_want:
            await self.bot.say("No permissions have been set up for that"
                               " command")
            return
        elif server.id not in self.perms_we_want[command]:
            await self.bot.say("No permissions have been set up for this"
                               " server.")
            return
        cmd_obj = self._get_command(command)
        perm_info = await self._get_info(server, cmd_obj)
        headers = ["Channel", "Status", "Role", "Status", "Locked Here"]

        partial = itertools.zip_longest(perm_info["CHANNELS"],
                                        perm_info["ROLES"], fillvalue=("", ""))
        partial = list(partial)

        if len(partial) == 0:
            partial = ((("", ""), ("", "")), )  # For compat below
        data = []
        for i, row in enumerate(partial):
            if i == 0:
                locked = (str(self._is_locked(command, server, channel)), )
            else:
                locked = tuple()
            data.append(row[0] + row[1] + locked)

        msg = tabulate(data, headers=headers, tablefmt='psql')
        await self.bot.say(box(msg))

    @p.group(pass_context=True, invoke_without_command=True)
    async def lock(self, ctx, command):
        """Globally locks a command from being used by anyone but owner

        Can call `lock server` or `lock channel` as well."""
        author = ctx.message.author
        if author.id != self.bot.settings.owner:
            return

        cmd_obj = self._get_command(command)
        server = ctx.message.server
        if cmd_obj is None:
            await self.bot.say("Invalid command")

        await self._lock_global(command, server)
        await self.bot.say("Globally locked {}".format(command))

    @lock.command(pass_context=True, name="channel")
    async def lock_channel(self, ctx, command):
        """Locks a command on this channel from being used by anyone but""" + \
            """ owner"""
        channel = ctx.message.channel
        cmd_obj = self._get_command(command)
        if cmd_obj is None:
            await self.bot.say("Invalid command")

        await self._lock_channel(command, channel)
        await self.bot.say("Channel locked {}".format(command))

    @lock.command(pass_context=True, name="cog")
    async def lock_cog(self, ctx, cog_name):
        """Locks all commands in a cog"""
        author = ctx.message.author
        if author.id != self.bot.settings.owner:
            return

        if ctx.bot.get_cog(cog_name) is None:
            await self.bot.say("No cog by that name found, make sure your"
                               " capitalization is correct.")
            return

        server = ctx.message.server

        await self._lock_cog(server, cog_name)

        await self.bot.say('Commands from cog {} locked.'.format(cog_name))

    @lock.command(pass_context=True, name="server")
    async def lock_server(self, ctx, command):
        """Locks a command on this server from being used by anyone but""" + \
            """ owner"""
        server = ctx.message.server
        cmd_obj = self._get_command(command)
        if cmd_obj is None:
            await self.bot.say("Invalid command")

        await self._lock_server(command, server)
        await self.bot.say("Server locked {}".format(command))

    @p.command(pass_context=True, name="reset")
    async def p_reset(self, ctx):
        """Resets ALL permissions on this server"""
        server = ctx.message.server

        await self._reset(server)

        await self.bot.say("Permissions reset.")

    @p.group(pass_context=True)
    async def role(self, ctx):
        """Role based permissions

        Overrides channel based permissions"""
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)

    @role.command(pass_context=True, name="allow")
    async def role_allow(self, ctx, command, *, role):
        """Explicitly allows [command/cog] to be used by [role] server wide

        This OVERRIDES channel based permissions"""
        server = ctx.message.server
        try:
            command_obj = self._get_command(command)
        except BadCommand as e:
            try:
                self.bot.cogs[command]
                command_obj = command
            except KeyError:
                raise e
        role = self._get_role(server.roles, role)
        await self._set_permission(command_obj, server, role=role)

        await self.bot.say("Role {} allowed use of {}.".format(role.name,
                                                               command))

    @role.command(pass_context=True, name="deny")
    async def role_deny(self, ctx, command, *, role):
        """Explicitly denies [command/cog] usage by [role] server wide

        This OVERRIDES channel based permissions"""
        server = ctx.message.server
        try:
            command_obj = self._get_command(command)
        except BadCommand as e:
            try:
                self.bot.cogs[command]
                command_obj = command
            except KeyError:
                raise e
        role = self._get_role(server.roles, role)
        await self._set_permission(command_obj, server, role=role, allow=False)

        await self.bot.say("Role {} denied use of {}.".format(role.name,
                                                              command))

    @role.command(pass_context=True, name="reset")
    async def role_reset(self, ctx, command, *, role):
        """Reset permissions of [role] on [command/cog] to the default"""
        server = ctx.message.server
        try:
            command_obj = self._get_command(command)
        except BadCommand as e:
            try:
                self.bot.cogs[command]
                command_obj = command
            except KeyError:
                raise e
        role = self._get_role(server.roles, role)
        await self._reset_permission(command_obj, server, role=role)

        await self.bot.say("{} permission reset.".format(role.name))

    @p.group(pass_context=True, invoke_without_command=True)
    async def unlock(self, ctx, command):
        """Globally unlocks a command from being used by anyone but owner

        Can call `unlock server` or `unlock channel` as well."""
        author = ctx.message.author
        if author.id != self.bot.settings.owner:
            return
        cmd_obj = self._get_command(command)
        server = ctx.message.server
        if cmd_obj is None:
            await self.bot.say("Invalid command")

        await self._lock_global(command, server, False)
        await self.bot.say("Globally unlocked {}".format(command))

    @unlock.command(pass_context=True, name="channel")
    async def unlock_channel(self, ctx, command):
        """Unocks a command on this channel from being used by anyone but"""
        """ owner"""
        channel = ctx.message.channel
        cmd_obj = self._get_command(command)
        if cmd_obj is None:
            await self.bot.say("Invalid command")

        await self._lock_channel(command, channel, False)
        await self.bot.say("Channel unlocked {}".format(command))

    @unlock.command(pass_context=True, name="cog")
    async def unlock_cog(self, ctx, cog_name):
        """Unlocks all commands in a cog"""
        author = ctx.message.author
        if author.id != self.bot.settings.owner:
            return
        if ctx.bot.get_cog(cog_name) is None:
            await self.bot.say("No cog by that name found, make sure your"
                               " capitalization is correct.")
            return

        server = ctx.message.server

        await self._lock_cog(server, cog_name, False)

        await self.bot.say("Commands from cog {} unlocked.".format(cog_name))

    @unlock.command(pass_context=True, name="server")
    async def unlock_server(self, ctx, command):
        """Unocks a command on this server from being used by anyone but"""
        """ owner"""
        server = ctx.message.server
        cmd_obj = self._get_command(command)
        if cmd_obj is None:
            await self.bot.say("Invalid command")

        await self._lock_server(command, server, False)
        await self.bot.say("Server unlocked {}".format(command))

    async def command_error(self, error, ctx):
        cmd = ctx.command
        if cmd and cmd.qualified_name.split(" ")[0] == "p":
            await self._error_responses(error, ctx)

    async def add_checks_to_all(self):
        while self == self.bot.get_cog('Permissions'):
            perms_we_want = copy.copy(self.perms_we_want)
            for cmd_dot in perms_we_want:
                try:
                    cmd_obj = self._get_command(cmd_dot)
                    check_obj = discord.utils.find(
                        lambda c: type(c).__name__ == "Check", cmd_obj.checks)
                except BadCommand:
                    # Command is no longer loaded/found
                    pass
                except AttributeError:
                    # cmd_obj got to be None somehow so we'll assume it's not
                    #   loaded
                    pass
                else:
                    if check_obj is None:
                        log.debug("Check object not found in {},"
                                  " adding".format(cmd_dot))
                        cmd_obj.checks.append(Check(cmd_dot))
            await asyncio.sleep(0.5)


def setup(bot):
    n = Permissions(bot)
    bot.add_cog(n)
    bot.add_listener(n.command_error, "on_command_error")
