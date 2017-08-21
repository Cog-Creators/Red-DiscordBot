import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help, settings
from datetime import datetime
from collections import deque, defaultdict
from cogs.utils.chat_formatting import escape_mass_mentions, box, pagify
import os
import re
import logging
import asyncio


ACTIONS_REPR = {
    "BAN"     : ("Ban", "\N{HAMMER}"),
    "KICK"    : ("Kick", "\N{WOMANS BOOTS}"),
    "CMUTE"   : ("Channel mute", "\N{SPEAKER WITH CANCELLATION STROKE}"),
    "SMUTE"   : ("Server mute", "\N{SPEAKER WITH CANCELLATION STROKE}"),
    "SOFTBAN" : ("Softban", "\N{DASH SYMBOL} \N{HAMMER}"),
    "HACKBAN" : ("Preemptive ban", "\N{BUST IN SILHOUETTE} \N{HAMMER}"),
    "UNBAN"   : ("Unban", "\N{DOVE OF PEACE}")
}

ACTIONS_CASES = {
    "BAN"     : True,
    "KICK"    : True,
    "CMUTE"   : False,
    "SMUTE"   : True,
    "SOFTBAN" : True,
    "HACKBAN" : True,
    "UNBAN"   : True
}

default_settings = {
    "ban_mention_spam"  : False,
    "delete_repeats"    : False,
    "mod-log"           : None,
    "respect_hierarchy" : False
}


for act, enabled in ACTIONS_CASES.items():
    act = act.lower() + '_cases'
    default_settings[act] = enabled


class ModError(Exception):
    pass


class UnauthorizedCaseEdit(ModError):
    pass


class CaseMessageNotFound(ModError):
    pass


class NoModLogChannel(ModError):
    pass


class NoModLogAccess(ModError):
    pass


class TempCache:
    """
    This is how we avoid events such as ban and unban
    from triggering twice in the mod-log.
    Kinda hacky but functioning
    """
    def __init__(self, bot):
        self.bot = bot
        self._cache = []

    def add(self, user, server, action, seconds=1):
        tmp = (user.id, server.id, action)
        self._cache.append(tmp)

        async def delete_value():
            await asyncio.sleep(seconds)
            self._cache.remove(tmp)

        self.bot.loop.create_task(delete_value())

    def check(self, user, server, action):
        return (user.id, server.id, action) in self._cache


class Mod:
    """Moderation tools."""

    def __init__(self, bot):
        self.bot = bot
        self.ignore_list = dataIO.load_json("data/mod/ignorelist.json")
        self.filter = dataIO.load_json("data/mod/filter.json")
        self.past_names = dataIO.load_json("data/mod/past_names.json")
        self.past_nicknames = dataIO.load_json("data/mod/past_nicknames.json")
        settings = dataIO.load_json("data/mod/settings.json")
        self.settings = defaultdict(lambda: default_settings.copy(), settings)
        self.cache = defaultdict(lambda: deque(maxlen=3))
        self.cases = dataIO.load_json("data/mod/modlog.json")
        self.last_case = defaultdict(dict)
        self.temp_cache = TempCache(bot)
        perms_cache = dataIO.load_json("data/mod/perms_cache.json")
        self._perms_cache = defaultdict(dict, perms_cache)

    @commands.group(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(administrator=True)
    async def modset(self, ctx):
        """Manages server administration settings."""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            await send_cmd_help(ctx)
            roles = settings.get_server(server).copy()
            _settings = {**self.settings[server.id], **roles}
            if "respect_hierarchy" not in _settings:
                _settings["respect_hierarchy"] = default_settings["respect_hierarchy"]
            if "delete_delay" not in _settings:
                _settings["delete_delay"] = "Disabled"

            msg = ("Admin role: {ADMIN_ROLE}\n"
                   "Mod role: {MOD_ROLE}\n"
                   "Mod-log: {mod-log}\n"
                   "Delete repeats: {delete_repeats}\n"
                   "Ban mention spam: {ban_mention_spam}\n"
                   "Delete delay: {delete_delay}\n"
                   "Respects hierarchy: {respect_hierarchy}"
                   "".format(**_settings))
            await self.bot.say(box(msg))

    @modset.command(name="adminrole", pass_context=True, no_pm=True, hidden=True)
    async def _modset_adminrole(self, ctx):
        """Use [p]set adminrole instead"""
        await self.bot.say("This command has been renamed "
                           "`{}set adminrole`".format(ctx.prefix))

    @modset.command(name="modrole", pass_context=True, no_pm=True, hidden=True)
    async def _modset_modrole(self, ctx):
        """Use [p]set modrole instead"""
        await self.bot.say("This command has been renamed "
                           "`{}set modrole`".format(ctx.prefix))

    @modset.command(pass_context=True, no_pm=True)
    async def modlog(self, ctx, channel : discord.Channel=None):
        """Sets a channel as mod log

        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["mod-log"] = channel.id
            await self.bot.say("Mod events will be sent to {}"
                               "".format(channel.mention))
        else:
            if self.settings[server.id]["mod-log"] is None:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["mod-log"] = None
            await self.bot.say("Mod log deactivated.")
        dataIO.save_json("data/mod/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def banmentionspam(self, ctx, max_mentions : int=False):
        """Enables auto ban for messages mentioning X different people

        Accepted values: 5 or superior"""
        server = ctx.message.server
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            self.settings[server.id]["ban_mention_spam"] = max_mentions
            await self.bot.say("Autoban for mention spam enabled. "
                               "Anyone mentioning {} or more different people "
                               "in a single message will be autobanned."
                               "".format(max_mentions))
        else:
            if self.settings[server.id]["ban_mention_spam"] is False:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["ban_mention_spam"] = False
            await self.bot.say("Autoban for mention spam disabled.")
        dataIO.save_json("data/mod/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def deleterepeats(self, ctx):
        """Enables auto deletion of repeated messages"""
        server = ctx.message.server
        if not self.settings[server.id]["delete_repeats"]:
            self.settings[server.id]["delete_repeats"] = True
            await self.bot.say("Messages repeated up to 3 times will "
                               "be deleted.")
        else:
            self.settings[server.id]["delete_repeats"] = False
            await self.bot.say("Repeated messages will be ignored.")
        dataIO.save_json("data/mod/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def resetcases(self, ctx):
        """Resets modlog's cases"""
        server = ctx.message.server
        self.cases[server.id] = {}
        dataIO.save_json("data/mod/modlog.json", self.cases)
        await self.bot.say("Cases have been reset.")

    @modset.command(pass_context=True, no_pm=True)
    async def deletedelay(self, ctx, time: int=None):
        """Sets the delay until the bot removes the command message.
            Must be between -1 and 60.

        A delay of -1 means the bot will not remove the message."""
        server = ctx.message.server
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            self.settings[server.id]["delete_delay"] = time
            if time == -1:
                await self.bot.say("Command deleting disabled.")
            else:
                await self.bot.say("Delete delay set to {}"
                                   " seconds.".format(time))
            dataIO.save_json("data/mod/settings.json", self.settings)
        else:
            try:
                delay = self.settings[server.id]["delete_delay"]
            except KeyError:
                await self.bot.say("Delete delay not yet set up on this"
                                   " server.")
            else:
                if delay != -1:
                    await self.bot.say("Bot will delete command messages after"
                                       " {} seconds. Set this value to -1 to"
                                       " stop deleting messages".format(delay))
                else:
                    await self.bot.say("I will not delete command messages.")

    @modset.command(pass_context=True, no_pm=True, name='cases')
    async def set_cases(self, ctx, action: str = None, enabled: bool = None):
        """Enables or disables case creation for each type of mod action

        Enabled can be 'on' or 'off'"""
        server = ctx.message.server

        if action == enabled:  # No args given
            await self.bot.send_cmd_help(ctx)
            msg = "Current settings:\n```py\n"
            maxlen = max(map(lambda x: len(x[0]), ACTIONS_REPR.values()))
            for action, name in ACTIONS_REPR.items():
                action = action.lower() + '_cases'
                value = self.settings[server.id].get(action,
                                                     default_settings[action])
                value = 'enabled' if value else 'disabled'
                msg += '%s : %s\n' % (name[0].ljust(maxlen), value)

            msg += '```'
            await self.bot.say(msg)

        elif action.upper() not in ACTIONS_CASES:
            msg = "That's not a valid action. Valid actions are: \n"
            msg += ', '.join(sorted(map(str.lower, ACTIONS_CASES)))
            await self.bot.say(msg)

        elif enabled == None:
            action = action.lower() + '_cases'
            value = self.settings[server.id].get(action,
                                                 default_settings[action])
            await self.bot.say('Case creation for %s is currently %s' %
                               (action, 'enabled' if value else 'disabled'))
        else:
            name = ACTIONS_REPR[action.upper()][0]
            action = action.lower() + '_cases'
            value = self.settings[server.id].get(action,
                                                 default_settings[action])
            if value != enabled:
                self.settings[server.id][action] = enabled
                dataIO.save_json("data/mod/settings.json", self.settings)
            msg = ('Case creation for %s actions %s %s.' %
                   (name.lower(),
                    'was already' if enabled == value else 'is now',
                    'enabled' if enabled else 'disabled')
                   )
            await self.bot.say(msg)

    @modset.command(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions()
    async def hierarchy(self, ctx):
        """Toggles role hierarchy check for mods / admins"""
        server = ctx.message.server
        toggled = self.settings[server.id].get("respect_hierarchy",
                                               default_settings["respect_hierarchy"])
        if not toggled:
            self.settings[server.id]["respect_hierarchy"] = True
            await self.bot.say("Role hierarchy will be checked when "
                               "moderation commands are issued.")
        else:
            self.settings[server.id]["respect_hierarchy"] = False
            await self.bot.say("Role hierarchy will be ignored when "
                               "moderation commands are issued.")
        dataIO.save_json("data/mod/settings.json", self.settings)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = None):
        """Kicks user."""
        author = ctx.message.author
        server = author.server

        if author == user:
            await self.bot.say("I cannot let you do that. Self-harm is "
                               "bad \N{PENSIVE FACE}")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        try:
            await self.bot.kick(user)
            logger.info("{}({}) kicked {}({})".format(
                author.name, author.id, user.name, user.id))
            await self.new_case(server,
                                action="KICK",
                                mod=author,
                                user=user,
                                reason=reason)
            await self.bot.say("Done. That felt good.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.Member, days: str = None, *, reason: str = None):
        """Bans user and deletes last X days worth of messages.

        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.message.author
        server = author.server

        if author == user:
            await self.bot.say("I cannot let you do that. Self-harm is "
                               "bad \N{PENSIVE FACE}")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        if days:
            if days.isdigit():
                days = int(days)
            else:
                if reason:
                    reason = days + ' ' + reason
                else:
                    reason = days
                days = 0
        else:
            days = 0

        if days < 0 or days > 7:
            await self.bot.say("Invalid days. Must be between 0 and 7.")
            return

        try:
            self.temp_cache.add(user, server, "BAN")
            await self.bot.ban(user, days)
            logger.info("{}({}) banned {}({}), deleting {} days worth of messages".format(
                author.name, author.id, user.name, user.id, str(days)))
            await self.new_case(server,
                                action="BAN",
                                mod=author,
                                user=user,
                                reason=reason)
            await self.bot.say("Done. It was about time.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def hackban(self, ctx, user_id: int, *, reason: str = None):
        """Preemptively bans user from the server

        A user ID needs to be provided
        If the user is present in the server a normal ban will be
        issued instead"""
        user_id = str(user_id)
        author = ctx.message.author
        server = author.server

        ban_list = await self.bot.get_bans(server)
        is_banned = discord.utils.get(ban_list, id=user_id)

        if is_banned:
            await self.bot.say("User is already banned.")
            return

        user = server.get_member(user_id)
        if user is not None:
            await ctx.invoke(self.ban, user=user, reason=reason)
            return

        try:
            await self.bot.http.ban(user_id, server.id, 0)
        except discord.NotFound:
            await self.bot.say("User not found. Have you provided the "
                               "correct user ID?")
        except discord.Forbidden:
            await self.bot.say("I lack the permissions to do this.")
        else:
            logger.info("{}({}) hackbanned {}"
                        "".format(author.name, author.id, user_id))
            user = await self.bot.get_user_info(user_id)
            await self.new_case(server,
                                action="HACKBAN",
                                mod=author,
                                user=user,
                                reason=reason)
            await self.bot.say("Done. The user will not be able to join this "
                               "server.")

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def softban(self, ctx, user: discord.Member, *, reason: str = None):
        """Kicks the user, deleting 1 day worth of messages."""
        server = ctx.message.server
        channel = ctx.message.channel
        can_ban = channel.permissions_for(server.me).ban_members
        author = ctx.message.author

        if author == user:
            await self.bot.say("I cannot let you do that. Self-harm is "
                               "bad \N{PENSIVE FACE}")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        try:
            invite = await self.bot.create_invite(server, max_age=3600*24)
            invite = "\nInvite: " + invite
        except:
            invite = ""
        if can_ban:
            try:
                try:  # We don't want blocked DMs preventing us from banning
                    msg = await self.bot.send_message(user, "You have been banned and "
                              "then unbanned as a quick way to delete your messages.\n"
                              "You can now join the server again.{}".format(invite))
                except:
                    pass
                self.temp_cache.add(user, server, "BAN")
                await self.bot.ban(user, 1)
                logger.info("{}({}) softbanned {}({}), deleting 1 day worth "
                    "of messages".format(author.name, author.id, user.name,
                     user.id))
                await self.new_case(server,
                                    action="SOFTBAN",
                                    mod=author,
                                    user=user,
                                    reason=reason)
                self.temp_cache.add(user, server, "UNBAN")
                await self.bot.unban(server, user)
                await self.bot.say("Done. Enough chaos.")
            except discord.errors.Forbidden:
                await self.bot.say("My role is not high enough to softban that user.")
                await self.bot.delete_message(msg)
            except Exception as e:
                print(e)
        else:
            await self.bot.say("I'm not allowed to do that.")

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx, user : discord.Member, *, nickname=""):
        """Changes user's nickname

        Leaving the nickname empty will remove it."""
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(user, nickname)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                               "\"Manage Nicknames\" permission.")

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.mod_or_permissions(administrator=True)
    async def mute(self, ctx, user : discord.Member, *, reason: str = None):
        """Mutes user in the channel/server

        Defaults to channel"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.channel_mute, user=user, reason=reason)

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="channel", pass_context=True, no_pm=True)
    async def channel_mute(self, ctx, user : discord.Member, *, reason: str = None):
        """Mutes user in the current channel"""
        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server
        overwrites = channel.overwrites_for(user)

        if overwrites.send_messages is False:
            await self.bot.say("That user can't send messages in this "
                               "channel.")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        self._perms_cache[user.id][channel.id] = overwrites.send_messages
        overwrites.send_messages = False
        try:
            await self.bot.edit_channel_permissions(channel, user, overwrites)
        except discord.Forbidden:
            await self.bot.say("Failed to mute user. I need the manage roles "
                               "permission and the user I'm muting must be "
                               "lower than myself in the role hierarchy.")
        else:
            dataIO.save_json("data/mod/perms_cache.json", self._perms_cache)
            await self.new_case(server,
                                action="CMUTE",
                                channel=channel,
                                mod=author,
                                user=user,
                                reason=reason)
            await self.bot.say("User has been muted in this channel.")

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="server", pass_context=True, no_pm=True)
    async def server_mute(self, ctx, user : discord.Member, *, reason: str = None):
        """Mutes user in the server"""
        author = ctx.message.author
        server = ctx.message.server

        if not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        register = {}
        for channel in server.channels:
            if channel.type != discord.ChannelType.text:
                continue
            overwrites = channel.overwrites_for(user)
            if overwrites.send_messages is False:
                continue
            register[channel.id] = overwrites.send_messages
            overwrites.send_messages = False
            try:
                await self.bot.edit_channel_permissions(channel, user,
                                                        overwrites)
            except discord.Forbidden:
                await self.bot.say("Failed to mute user. I need the manage roles "
                                   "permission and the user I'm muting must be "
                                   "lower than myself in the role hierarchy.")
                return
            else:
                await asyncio.sleep(0.1)
        if not register:
            await self.bot.say("That user is already muted in all channels.")
            return
        self._perms_cache[user.id] = register
        dataIO.save_json("data/mod/perms_cache.json", self._perms_cache)
        await self.new_case(server,
                            action="SMUTE",
                            mod=author,
                            user=user,
                            reason=reason)
        await self.bot.say("User has been muted in this server.")

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.mod_or_permissions(administrator=True)
    async def unmute(self, ctx, user : discord.Member):
        """Unmutes user in the channel/server

        Defaults to channel"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.channel_unmute, user=user)

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="channel", pass_context=True, no_pm=True)
    async def channel_unmute(self, ctx, user : discord.Member):
        """Unmutes user in the current channel"""
        channel = ctx.message.channel
        author = ctx.message.author
        server = ctx.message.server
        overwrites = channel.overwrites_for(user)

        if overwrites.send_messages:
            await self.bot.say("That user doesn't seem to be muted "
                               "in this channel.")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        if user.id in self._perms_cache:
            old_value = self._perms_cache[user.id].get(channel.id)
        else:
            old_value = None
        overwrites.send_messages = old_value
        is_empty = self.are_overwrites_empty(overwrites)
        try:
            if not is_empty:
                await self.bot.edit_channel_permissions(channel, user,
                                                        overwrites)
            else:
                await self.bot.delete_channel_permissions(channel, user)
        except discord.Forbidden:
            await self.bot.say("Failed to unmute user. I need the manage roles"
                               " permission and the user I'm unmuting must be "
                               "lower than myself in the role hierarchy.")
        else:
            try:
                del self._perms_cache[user.id][channel.id]
            except KeyError:
                pass
            if user.id in self._perms_cache and not self._perms_cache[user.id]:
                del self._perms_cache[user.id]  # cleanup
            dataIO.save_json("data/mod/perms_cache.json", self._perms_cache)
            await self.bot.say("User has been unmuted in this channel.")

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="server", pass_context=True, no_pm=True)
    async def server_unmute(self, ctx, user : discord.Member):
        """Unmutes user in the server"""
        server = ctx.message.server
        author = ctx.message.author

        if user.id not in self._perms_cache:
            await self.bot.say("That user doesn't seem to have been muted with {0}mute commands. "
                               "Unmute them in the channels you want with `{0}unmute <user>`"
                               "".format(ctx.prefix))
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return

        for channel in server.channels:
            if channel.type != discord.ChannelType.text:
                continue
            if channel.id not in self._perms_cache[user.id]:
                continue
            value = self._perms_cache[user.id].get(channel.id)
            overwrites = channel.overwrites_for(user)
            if overwrites.send_messages is False:
                overwrites.send_messages = value
                is_empty = self.are_overwrites_empty(overwrites)
                try:
                    if not is_empty:
                        await self.bot.edit_channel_permissions(channel, user,
                                                                overwrites)
                    else:
                        await self.bot.delete_channel_permissions(channel, user)
                except discord.Forbidden:
                    await self.bot.say("Failed to unmute user. I need the manage roles"
                                       " permission and the user I'm unmuting must be "
                                       "lower than myself in the role hierarchy.")
                    return
                else:
                    del self._perms_cache[user.id][channel.id]
                    await asyncio.sleep(0.1)
        if user.id in self._perms_cache and not self._perms_cache[user.id]:
            del self._perms_cache[user.id]  # cleanup
        dataIO.save_json("data/mod/perms_cache.json", self._perms_cache)
        await self.bot.say("User has been unmuted in this server.")

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def cleanup(self, ctx):
        """Deletes messages."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @cleanup.command(pass_context=True, no_pm=True)
    async def text(self, ctx, text: str, number: int):
        """Deletes last X messages matching the specified text.

        Example:
        cleanup text \"test\" 5

        Remember to use double quotes."""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        def check(m):
            if text in m.content:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        logger.info("{}({}) deleted {} messages "
                    " containing '{}' in channel {}".format(author.name,
                    author.id, len(to_delete), text, channel.id))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, no_pm=True)
    async def user(self, ctx, user: discord.Member, number: int):
        """Deletes last X messages from specified user.

        Examples:
        cleanup user @\u200bTwentysix 2
        cleanup user Red 6"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages
        self_delete = user == self.bot.user

        def check(m):
            if m.author == user:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        if not has_permissions and not self_delete:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        logger.info("{}({}) deleted {} messages "
                    " made by {}({}) in channel {}"
                    "".format(author.name, author.id, len(to_delete),
                              user.name, user.id, channel.name))

        if is_bot and not self_delete:
            # For whatever reason the purge endpoint requires manage_messages
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, no_pm=True)
    async def after(self, ctx, message_id : int):
        """Deletes all messages after specified message

        To get a message id, enable developer mode in Discord's
        settings, 'appearance' tab. Then right click a message
        and copy its id.

        This command only works on bots running as bot accounts.
        """

        channel = ctx.message.channel
        author = ctx.message.author
        server = channel.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        if not is_bot:
            await self.bot.say("This command can only be used on bots with "
                               "bot accounts.")
            return

        to_delete = []

        after = await self.bot.get_message(channel, message_id)

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return
        elif not after:
            await self.bot.say("Message not found.")
            return

        async for message in self.bot.logs_from(channel, limit=2000,
                                                after=after):
            to_delete.append(message)

        logger.info("{}({}) deleted {} messages in channel {}"
                    "".format(author.name, author.id,
                              len(to_delete), channel.name))

        await self.mass_purge(to_delete)

    @cleanup.command(pass_context=True, no_pm=True)
    async def messages(self, ctx, number: int):
        """Deletes last X messages.

        Example:
        cleanup messages 26"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        to_delete = []

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        async for message in self.bot.logs_from(channel, limit=number+1):
            to_delete.append(message)

        logger.info("{}({}) deleted {} messages in channel {}"
                    "".format(author.name, author.id,
                              number, channel.name))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, no_pm=True, name='bot')
    async def cleanup_bot(self, ctx, number: int):
        """Cleans up command messages and messages from the bot"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = channel.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        prefixes = self.bot.command_prefix
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        elif callable(prefixes):
            if asyncio.iscoroutine(prefixes):
                await self.bot.say('Coroutine prefixes not yet implemented.')
                return
            prefixes = prefixes(self.bot, ctx.message)

        # In case some idiot sets a null prefix
        if '' in prefixes:
            prefixes.pop('')

        def check(m):
            if m.author.id == self.bot.user.id:
                return True
            elif m == ctx.message:
                return True
            p = discord.utils.find(m.content.startswith, prefixes)
            if p and len(p) > 0:
                return m.content[len(p):].startswith(tuple(self.bot.commands))
            return False

        to_delete = [ctx.message]

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        logger.info("{}({}) deleted {} "
                    " command messages in channel {}"
                    "".format(author.name, author.id, len(to_delete),
                              channel.name))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, name='self')
    async def cleanup_self(self, ctx, number: int, match_pattern: str = None):
        """Cleans up messages owned by the bot.

        By default, all messages are cleaned. If a third argument is specified,
        it is used for pattern matching: If it begins with r( and ends with ),
        then it is interpreted as a regex, and messages that match it are
        deleted. Otherwise, it is used in a simple substring test.

        Some helpful regex flags to include in your pattern:
        Dots match newlines: (?s); Ignore case: (?i); Both: (?si)
        """
        channel = ctx.message.channel
        author = ctx.message.author
        is_bot = self.bot.user.bot

        # You can always delete your own messages, this is needed to purge
        can_mass_purge = False
        if type(author) is discord.Member:
            me = channel.server.me
            can_mass_purge = channel.permissions_for(me).manage_messages

        use_re = (match_pattern and match_pattern.startswith('r(') and
                  match_pattern.endswith(')'))

        if use_re:
            match_pattern = match_pattern[1:]  # strip 'r'
            match_re = re.compile(match_pattern)

            def content_match(c):
                return bool(match_re.match(c))
        elif match_pattern:
            def content_match(c):
                return match_pattern in c
        else:
            def content_match(_):
                return True

        def check(m):
            if m.author.id != self.bot.user.id:
                return False
            elif content_match(m.content):
                return True
            return False

        to_delete = []
        # Selfbot convenience, delete trigger message
        if author == self.bot.user:
            to_delete.append(ctx.message)
            number += 1

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        if channel.name:
            channel_name = 'channel ' + channel.name
        else:
            channel_name = str(channel)

        logger.info("{}({}) deleted {} messages "
                    "sent by the bot in {}"
                    "".format(author.name, author.id, len(to_delete),
                              channel_name))

        if is_bot and can_mass_purge:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def reason(self, ctx, case, *, reason : str=""):
        """Lets you specify a reason for mod-log's cases

        Defaults to last case assigned to yourself, if available."""
        author = ctx.message.author
        server = author.server
        try:
            case = int(case)
            if not reason:
                await send_cmd_help(ctx)
                return
        except:
            if reason:
                reason = "{} {}".format(case, reason)
            else:
                reason = case
            case = self.last_case[server.id].get(author.id)
            if case is None:
                await send_cmd_help(ctx)
                return
        try:
            await self.update_case(server, case=case, mod=author,
                                   reason=reason)
        except UnauthorizedCaseEdit:
            await self.bot.say("That case is not yours.")
        except KeyError:
            await self.bot.say("That case doesn't exist.")
        except NoModLogChannel:
            await self.bot.say("There's no mod-log channel set.")
        except CaseMessageNotFound:
            await self.bot.say("I couldn't find the case's message.")
        except NoModLogAccess:
            await self.bot.say("I'm not allowed to access the mod-log "
                               "channel (or its message history)")
        else:
            await self.bot.say("Case #{} updated.".format(case))

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx):
        """Adds servers/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

    @ignore.command(name="channel", pass_context=True)
    async def ignore_channel(self, ctx, channel: discord.Channel=None):
        """Ignores channel

        Defaults to current one"""
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(current_ch.id)
                dataIO.save_json("data/mod/ignorelist.json", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")
        else:
            if channel.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(channel.id)
                dataIO.save_json("data/mod/ignorelist.json", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")

    @ignore.command(name="server", pass_context=True)
    async def ignore_server(self, ctx):
        """Ignores current server"""
        server = ctx.message.server
        if server.id not in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].append(server.id)
            dataIO.save_json("data/mod/ignorelist.json", self.ignore_list)
            await self.bot.say("This server has been added to the ignore list.")
        else:
            await self.bot.say("This server is already being ignored.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx):
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

    @unignore.command(name="channel", pass_context=True)
    async def unignore_channel(self, ctx, channel: discord.Channel=None):
        """Removes channel from ignore list

        Defaults to current one"""
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(current_ch.id)
                dataIO.save_json("data/mod/ignorelist.json", self.ignore_list)
                await self.bot.say("This channel has been removed from the ignore list.")
            else:
                await self.bot.say("This channel is not in the ignore list.")
        else:
            if channel.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(channel.id)
                dataIO.save_json("data/mod/ignorelist.json", self.ignore_list)
                await self.bot.say("Channel removed from ignore list.")
            else:
                await self.bot.say("That channel is not in the ignore list.")

    @unignore.command(name="server", pass_context=True)
    async def unignore_server(self, ctx):
        """Removes current server from ignore list"""
        server = ctx.message.server
        if server.id in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].remove(server.id)
            dataIO.save_json("data/mod/ignorelist.json", self.ignore_list)
            await self.bot.say("This server has been removed from the ignore list.")
        else:
            await self.bot.say("This server is not in the ignore list.")

    def count_ignored(self):
        msg = "```Currently ignoring:\n"
        msg += str(len(self.ignore_list["CHANNELS"])) + " channels\n"
        msg += str(len(self.ignore_list["SERVERS"])) + " servers\n```\n"
        return msg

    @commands.group(name="filter", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def _filter(self, ctx):
        """Adds/removes words from filter

        Use double quotes to add/remove sentences
        Using this command with no subcommands will send
        the list of the server's filtered words."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            server = ctx.message.server
            author = ctx.message.author
            if server.id in self.filter:
                if self.filter[server.id]:
                    words = ", ".join(self.filter[server.id])
                    words = "Filtered in this server:\n\n" + words
                    try:
                        for page in pagify(words, delims=[" ", "\n"], shorten_by=8):
                            await self.bot.send_message(author, page)
                    except discord.Forbidden:
                        await self.bot.say("I can't send direct messages to you.")

    @_filter.command(name="add", pass_context=True)
    async def filter_add(self, ctx, *words: str):
        """Adds words to the filter

        Use double quotes to add sentences
        Examples:
        filter add word1 word2 word3
        filter add \"This is a sentence\""""
        if words == ():
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        added = 0
        if server.id not in self.filter.keys():
            self.filter[server.id] = []
        for w in words:
            if w.lower() not in self.filter[server.id] and w != "":
                self.filter[server.id].append(w.lower())
                added += 1
        if added:
            dataIO.save_json("data/mod/filter.json", self.filter)
            await self.bot.say("Words added to filter.")
        else:
            await self.bot.say("Words already in the filter.")

    @_filter.command(name="remove", pass_context=True)
    async def filter_remove(self, ctx, *words: str):
        """Remove words from the filter

        Use double quotes to remove sentences
        Examples:
        filter remove word1 word2 word3
        filter remove \"This is a sentence\""""
        if words == ():
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        removed = 0
        if server.id not in self.filter.keys():
            await self.bot.say("There are no filtered words in this server.")
            return
        for w in words:
            if w.lower() in self.filter[server.id]:
                self.filter[server.id].remove(w.lower())
                removed += 1
        if removed:
            dataIO.save_json("data/mod/filter.json", self.filter)
            await self.bot.say("Words removed from filter.")
        else:
            await self.bot.say("Those words weren't in the filter.")

    @commands.group(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx):
        """Edits roles settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @editrole.command(aliases=["color"], pass_context=True)
    async def colour(self, ctx, role: discord.Role, value: discord.Colour):
        """Edits a role's colour

        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        \"http://www.w3schools.com/colors/colors_picker.asp\"
        Examples:
        !editrole colour \"The Transistor\" #ff0000
        !editrole colour Test #ff9900"""
        author = ctx.message.author
        try:
            await self.bot.edit_role(ctx.message.server, role, color=value)
            logger.info("{}({}) changed the colour of role '{}'".format(
                author.name, author.id, role.name))
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I need permissions to manage roles first.")
        except Exception as e:
            print(e)
            await self.bot.say("Something went wrong.")

    @editrole.command(name="name", pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def edit_role_name(self, ctx, role: discord.Role, name: str):
        """Edits a role's name

        Use double quotes if the role or the name contain spaces.
        Examples:
        !editrole name \"The Transistor\" Test"""
        if name == "":
            await self.bot.say("Name cannot be empty.")
            return
        try:
            author = ctx.message.author
            old_name = role.name  # probably not necessary?
            await self.bot.edit_role(ctx.message.server, role, name=name)
            logger.info("{}({}) changed the name of role '{}' to '{}'".format(
                author.name, author.id, old_name, name))
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I need permissions to manage roles first.")
        except Exception as e:
            print(e)
            await self.bot.say("Something went wrong.")

    @commands.command()
    async def names(self, user : discord.Member):
        """Show previous names/nicknames of a user"""
        server = user.server
        names = self.past_names[user.id] if user.id in self.past_names else None
        try:
            nicks = self.past_nicknames[server.id][user.id]
            nicks = [escape_mass_mentions(nick) for nick in nicks]
        except:
            nicks = None
        msg = ""
        if names:
            names = [escape_mass_mentions(name) for name in names]
            msg += "**Past 20 names**:\n"
            msg += ", ".join(names)
        if nicks:
            if msg:
                msg += "\n\n"
            msg += "**Past 20 nicknames**:\n"
            msg += ", ".join(nicks)
        if msg:
            await self.bot.say(msg)
        else:
            await self.bot.say("That user doesn't have any recorded name or "
                               "nickname change.")

    async def mass_purge(self, messages):
        while messages:
            if len(messages) > 1:
                await self.bot.delete_messages(messages[:100])
                messages = messages[100:]
            else:
                await self.bot.delete_message(messages[0])
                messages = []
            await asyncio.sleep(1.5)

    async def slow_deletion(self, messages):
        for message in messages:
            try:
                await self.bot.delete_message(message)
            except:
                pass

    def is_admin_or_superior(self, obj):
        if isinstance(obj, discord.Message):
            user = obj.author
        elif isinstance(obj, discord.Member):
            user = obj
        elif isinstance(obj, discord.Role):
            pass
        else:
            raise TypeError('Only messages, members or roles may be passed')

        server = obj.server
        admin_role = settings.get_server_admin(server)

        if isinstance(obj, discord.Role):
            return obj.name == admin_role

        if user.id == settings.owner:
            return True
        elif discord.utils.get(user.roles, name=admin_role):
            return True
        else:
            return False

    def is_mod_or_superior(self, obj):
        if isinstance(obj, discord.Message):
            user = obj.author
        elif isinstance(obj, discord.Member):
            user = obj
        elif isinstance(obj, discord.Role):
            pass
        else:
            raise TypeError('Only messages, members or roles may be passed')

        server = obj.server
        admin_role = settings.get_server_admin(server)
        mod_role = settings.get_server_mod(server)

        if isinstance(obj, discord.Role):
            return obj.name in [admin_role, mod_role]

        if user.id == settings.owner:
            return True
        elif discord.utils.get(user.roles, name=admin_role):
            return True
        elif discord.utils.get(user.roles, name=mod_role):
            return True
        else:
            return False

    def is_allowed_by_hierarchy(self, server, mod, user):
        toggled = self.settings[server.id].get("respect_hierarchy",
                                               default_settings["respect_hierarchy"])
        is_special = mod == server.owner or mod.id == self.bot.settings.owner

        if not toggled:
            return True
        else:
            return mod.top_role.position > user.top_role.position or is_special

    async def new_case(self, server, *, action, mod=None, user, reason=None, until=None, channel=None):
        action_type = action.lower() + "_cases"
        if not self.settings[server.id].get(action_type, default_settings[action_type]):
            return

        mod_channel = server.get_channel(self.settings[server.id]["mod-log"])
        if mod_channel is None:
            return

        if server.id not in self.cases:
            self.cases[server.id] = {}

        case_n = len(self.cases[server.id]) + 1

        case = {
            "case"         : case_n,
            "created"      : datetime.utcnow().timestamp(),
            "modified"     : None,
            "action"       : action,
            "channel"      : channel.id if channel else None,
            "user"         : str(user),
            "user_id"      : user.id,
            "reason"       : reason,
            "moderator"    : str(mod) if mod is not None else None,
            "moderator_id" : mod.id if mod is not None else None,
            "amended_by"   : None,
            "amended_id"   : None,
            "message"      : None,
            "until"        : None,
        }

        case_msg = self.format_case_msg(case)

        try:
            msg = await self.bot.send_message(mod_channel, case_msg)
            case["message"] = msg.id
        except:
            pass

        self.cases[server.id][str(case_n)] = case

        if mod:
            self.last_case[server.id][mod.id] = case_n

        dataIO.save_json("data/mod/modlog.json", self.cases)

    async def update_case(self, server, *, case, mod=None, reason=None,
                          until=False):
        channel = server.get_channel(self.settings[server.id]["mod-log"])
        if channel is None:
            raise NoModLogChannel()

        case = str(case)
        case = self.cases[server.id][case]

        if case["moderator_id"] is not None:
            if case["moderator_id"] != mod.id:
                if self.is_admin_or_superior(mod):
                    case["amended_by"] = str(mod)
                    case["amended_id"] = mod.id
                else:
                    raise UnauthorizedCaseEdit()
        else:
            case["moderator"] = str(mod)
            case["moderator_id"] = mod.id

        if case["reason"]:  # Existing reason
            case["modified"] = datetime.utcnow().timestamp()
        case["reason"] = reason

        if until is not False:
            case["until"] = until

        case_msg = self.format_case_msg(case)

        dataIO.save_json("data/mod/modlog.json", self.cases)

        if case["message"] is None:  # The case's message was never sent
            raise CaseMessageNotFound()

        try:
            msg = await self.bot.get_message(channel, case["message"])
        except discord.NotFound:
            raise CaseMessageNotFound()
        except discord.Forbidden:
            raise NoModLogAccess()
        else:
            await self.bot.edit_message(msg, case_msg)


    def format_case_msg(self, case):
        tmp = case.copy()
        if case["reason"] is None:
            tmp["reason"] = "Type [p]reason %i <reason> to add it" % tmp["case"]
        if case["moderator"] is None:
            tmp["moderator"] = "Unknown"
            tmp["moderator_id"] = "Nobody has claimed responsibility yet"
        if case["action"] in ACTIONS_REPR:
            tmp["action"] = ' '.join(ACTIONS_REPR[tmp["action"]])

        channel = case.get("channel")
        if channel:
            channel = self.bot.get_channel(channel)
            tmp["action"] += ' in ' + channel.mention

        case_msg = (
            "**Case #{case}** | {action}\n"
            "**User:** {user} ({user_id})\n"
            "**Moderator:** {moderator} ({moderator_id})\n"
        ).format(**tmp)

        created = case.get('created')
        until = case.get('until')
        if created and until:
            start = datetime.fromtimestamp(created)
            end = datetime.fromtimestamp(until)
            end_fmt = end.strftime('%Y-%m-%d %H:%M:%S UTC')
            duration = end - start
            dur_fmt = strfdelta(duration)
            case_msg += ("**Until:** {}\n"
                         "**Duration:** {}\n").format(end_fmt, dur_fmt)

        amended = case.get('amended_by')
        if amended:
            amended_id = case.get('amended_id')
            case_msg += "**Amended by:** %s (%s)\n" % (amended, amended_id)

        modified = case.get('modified')
        if modified:
            modified = datetime.fromtimestamp(modified)
            modified_fmt = modified.strftime('%Y-%m-%d %H:%M:%S UTC')
            case_msg += "**Last modified:** %s\n" % modified_fmt

        case_msg += "**Reason:** %s\n" % tmp["reason"]

        return case_msg

    async def check_filter(self, message):
        server = message.server
        if server.id in self.filter.keys():
            for w in self.filter[server.id]:
                if w in message.content.lower():
                    try:
                        await self.bot.delete_message(message)
                        logger.info("Message deleted in server {}."
                                    "Filtered: {}"
                                    "".format(server.id, w))
                        return True
                    except:
                        pass
        return False

    async def check_duplicates(self, message):
        server = message.server
        author = message.author
        if server.id not in self.settings:
            return False
        if self.settings[server.id]["delete_repeats"]:
            if not message.content:
                return False
            self.cache[author].append(message)
            msgs = self.cache[author]
            if len(msgs) == 3 and \
                    msgs[0].content == msgs[1].content == msgs[2].content:
                try:
                    await self.bot.delete_message(message)
                    return True
                except:
                    pass
        return False

    async def check_mention_spam(self, message):
        server = message.server
        author = message.author
        if server.id not in self.settings:
            return False
        if self.settings[server.id]["ban_mention_spam"]:
            max_mentions = self.settings[server.id]["ban_mention_spam"]
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    self.temp_cache.add(author, server, "BAN")
                    await self.bot.ban(author, 1)
                except:
                    logger.info("Failed to ban member for mention spam in "
                                "server {}".format(server.id))
                else:
                    await self.new_case(server,
                                        action="BAN",
                                        mod=server.me,
                                        user=author,
                                        reason="Mention spam (Autoban)")
                    return True
        return False

    async def on_command(self, command, ctx):
        """Currently used for:
            * delete delay"""
        server = ctx.message.server
        message = ctx.message
        try:
            delay = self.settings[server.id]["delete_delay"]
        except KeyError:
            # We have no delay set
            return
        except AttributeError:
            # DM
            return

        if delay == -1:
            return

        async def _delete_helper(bot, message):
            try:
                await bot.delete_message(message)
                logger.debug("Deleted command msg {}".format(message.id))
            except:
                pass  # We don't really care if it fails or not

        await asyncio.sleep(delay)
        await _delete_helper(self.bot, message)

    async def on_message(self, message):
        author = message.author
        if message.server is None or self.bot.user == author:
            return

        valid_user = isinstance(author, discord.Member) and not author.bot

        #  Bots and mods or superior are ignored from the filter
        if not valid_user or self.is_mod_or_superior(message):
            return

        deleted = await self.check_filter(message)
        if not deleted:
            deleted = await self.check_duplicates(message)
        if not deleted:
            deleted = await self.check_mention_spam(message)

    async def on_message_edit(self, _, message):
        author = message.author
        if message.server is None or self.bot.user == author:
            return

        valid_user = isinstance(author, discord.Member) and not author.bot

        if not valid_user or self.is_mod_or_superior(message):
            return

        await self.check_filter(message)

    async def on_member_ban(self, member):
        server = member.server
        if not self.temp_cache.check(member, server, "BAN"):
            await self.new_case(server,
                                user=member,
                                action="BAN")

    async def on_member_unban(self, server, user):
        if not self.temp_cache.check(user, server, "UNBAN"):
            await self.new_case(server,
                                user=user,
                                action="UNBAN")

    async def check_names(self, before, after):
        if before.name != after.name:
            if before.id not in self.past_names:
                self.past_names[before.id] = [after.name]
            else:
                if after.name not in self.past_names[before.id]:
                    names = deque(self.past_names[before.id], maxlen=20)
                    names.append(after.name)
                    self.past_names[before.id] = list(names)
            dataIO.save_json("data/mod/past_names.json", self.past_names)

        if before.nick != after.nick and after.nick is not None:
            server = before.server
            if server.id not in self.past_nicknames:
                self.past_nicknames[server.id] = {}
            if before.id in self.past_nicknames[server.id]:
                nicks = deque(self.past_nicknames[server.id][before.id],
                              maxlen=20)
            else:
                nicks = []
            if after.nick not in nicks:
                nicks.append(after.nick)
                self.past_nicknames[server.id][before.id] = list(nicks)
                dataIO.save_json("data/mod/past_nicknames.json",
                                 self.past_nicknames)

    def are_overwrites_empty(self, overwrites):
        """There is currently no cleaner way to check if a
        PermissionOverwrite object is empty"""
        original = [p for p in iter(overwrites)]
        empty = [p for p in iter(discord.PermissionOverwrite())]
        return original == empty


def strfdelta(delta):
    s = []
    if delta.days:
        ds = '%i day' % delta.days
        if delta.days > 1:
            ds += 's'
        s.append(ds)
    hrs, rem = divmod(delta.seconds, 60*60)
    if hrs:
        hs = '%i hr' % hrs
        if hrs > 1:
            hs += 's'
        s.append(hs)
    mins, secs = divmod(rem, 60)
    if mins:
        s.append('%i min' % mins)
    if secs:
        s.append('%i sec' % secs)
    return ' '.join(s)


def check_folders():
    folders = ("data", "data/mod/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    ignore_list = {"SERVERS": [], "CHANNELS": []}

    files = {
        "ignorelist.json"     : ignore_list,
        "filter.json"         : {},
        "past_names.json"     : {},
        "past_nicknames.json" : {},
        "settings.json"       : {},
        "modlog.json"         : {},
        "perms_cache.json"    : {}
    }

    for filename, value in files.items():
        if not os.path.isfile("data/mod/{}".format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json("data/mod/{}".format(filename), value)


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("mod")
    # Prevents the logger from being loaded again in case of module reload
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename='data/mod/mod.log', encoding='utf-8', mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = Mod(bot)
    bot.add_listener(n.check_names, "on_member_update")
    bot.add_cog(n)
