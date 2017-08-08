import asyncio
import logging
from collections import deque, defaultdict

import discord
from discord.ext import commands

from cogs.mod.casetypes import BanCase, KickCase, SoftbanCase, HackbanCase, CMuteCase, SMuteCase, UnbanCase
from cogs.mod.common import is_mod_or_superior, is_allowed_by_hierarchy,\
    mute_unmute_issues, get_audit_reason
from .checks import mod_or_voice_permissions, admin_or_voice_permissions, bot_has_voice_permissions
from core import checks, Config
from core.bot import Red
from core.utils.chat_formatting import box, escape
from cogs.modlog.modlog import ModLog


class Mod:
    """Moderation tools."""

    default_guild_settings = {
        "ban_mention_spam": False,
        "delete_repeats": False,
        "ignored": False,
        "respect_hierarchy": True,
        "delete_delay": -1,
        "reinvite_on_unban": False
    }

    default_channel_settings = {
        "ignored": False
    }

    default_member_settings = {
        "past_nicks": [],
        "perms_cache": {},
        "banned_until": False
    }

    default_user_settings = {
        "past_names": []
    }

    def __init__(self, bot: Red, modlog: ModLog):
        self.bot = bot
        self.settings = Config.get_conf(self, 4961522000, force_registration=True)

        self.settings.register_guild(**self.default_guild_settings)
        self.settings.register_channel(**self.default_channel_settings)
        self.settings.register_member(**self.default_member_settings)
        self.settings.register_user(**self.default_user_settings)
        self.current_softban = {}
        self.ban_type = None
        self.cache = defaultdict(lambda: deque(maxlen=3))
        self.modlog = modlog

        casetypes_to_register = [
            (BanCase, True),
            (KickCase, True),
            (SoftbanCase, True),
            (HackbanCase, True),
            (UnbanCase, True),
            (CMuteCase, False),
            (SMuteCase, True)
        ]

        self.bot.loop.create_task(self.modlog.register_casetypes(casetypes_to_register))

        self.last_case = defaultdict(dict)
        global logger
        logger = logging.getLogger("mod")
        # Prevents the logger from being loaded again in case of module reload
        if logger.level == 0:
            logger.setLevel(logging.INFO)
            handler = logging.FileHandler(
                filename='cogs/.data/Mod/mod.log', encoding='utf-8', mode='a')
            handler.setFormatter(
                logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
            logger.addHandler(handler)

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def modset(self, ctx: commands.Context):
        """Manages server administration settings."""
        if ctx.invoked_subcommand is None:
            server = ctx.guild
            await self.bot.send_cmd_help(ctx)

            # Display current settings
            delete_repeats = self.settings.guild(server).delete_repeats()
            ban_mention_spam = self.settings.guild(server).ban_mention_spam()
            respect_hierarchy = self.settings.guild(server).respect_hierarchy()
            delete_delay = self.settings.guild(server).delete_delay()
            reinvite_on_unban = self.settings.guild(server).reinvite_on_unban()
            msg = ""
            msg += "Delete repeats: {}\n".format("Yes" if delete_repeats else "No")
            msg += "Ban mention spam: {}\n".format(
                "{} mentions".format(ban_mention_spam) if isinstance(ban_mention_spam, int) else "No"
            )
            msg += "Respects hierarchy: {}\n".format("Yes" if respect_hierarchy else "No")
            msg += "Delete delay: {}\n".format(
                "{} seconds".format(delete_delay) if delete_delay != -1 else "None"
            )
            msg += "Reinvite on unban: {}".format("Yes" if reinvite_on_unban else "No")
            await ctx.send(box(msg))

    @modset.command()
    @commands.guild_only()
    async def hierarchy(self, ctx: commands.Context):
        """Toggles role hierarchy check for mods / admins"""
        server = ctx.guild
        toggled = self.settings.guild(server).respect_hierarchy()
        if not toggled:
            await self.settings.guild(server).set("respect_hierarchy", True)
            await ctx.send("Role hierarchy will be checked when "
                           "moderation commands are issued.")
        else:
            await self.settings.guild(server).set("respect_hierarchy", False)
            await ctx.send("Role hierarchy will be ignored when "
                           "moderation commands are issued.")

    @modset.command()
    @commands.guild_only()
    async def banmentionspam(self, ctx: commands.Context, max_mentions: int=False):
        """Enables auto ban for messages mentioning X different people

        Accepted values: 5 or superior"""
        server = ctx.guild
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            await self.settings.guild(server).set("ban_mention_spam", max_mentions)
            await ctx.send("Autoban for mention spam enabled. "
                           "Anyone mentioning {} or more different people "
                           "in a single message will be autobanned."
                           "".format(max_mentions))
        else:
            cur_setting = self.settings.guild(server).ban_mention_spam()
            if cur_setting is False:
                await self.bot.send_cmd_help(ctx)
                return
            await self.settings.guild(server).set("ban_mention_spam", False)
            await ctx.send("Autoban for mention spam disabled.")

    @modset.command()
    @commands.guild_only()
    async def deleterepeats(self, ctx: commands.Context):
        """Enables auto deletion of repeated messages"""
        server = ctx.guild
        cur_setting = self.settings.guild(server).delete_repeats()
        if not cur_setting:
            await self.settings.guild(server).set("delete_repeats", True)
            await ctx.send("Messages repeated up to 3 times will "
                           "be deleted.")
        else:
            await self.settings.guild(server).set("delete_repeats", False)
            await ctx.send("Repeated messages will be ignored.")

    @modset.command()
    @commands.guild_only()
    async def deletedelay(self, ctx: commands.Context, time: int=None):
        """Sets the delay until the bot removes the command message.
            Must be between -1 and 60.

        A delay of -1 means the bot will not remove the message."""
        server = ctx.guild
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            await self.settings.guild(server).set("delete_delay", time)
            if time == -1:
                await ctx.send("Command deleting disabled.")
            else:
                await ctx.send("Delete delay set to {}"
                               " seconds.".format(time))
        else:
            delay = self.settings.guild(server).delete_delay()
            if delay != -1:
                await ctx.send("Bot will delete command messages after"
                               " {} seconds. Set this value to -1 to"
                               " stop deleting messages".format(delay))
            else:
                await ctx.send("I will not delete command messages.")

    @modset.command()
    @commands.guild_only()
    async def reinvite(self, ctx: commands.Context):
        """Toggles whether an invite will be sent when a user
        is unbanned via [p]unban. If this is True, the bot will
        attempt to create and send a single-use invite to the
        newly-unbanned user"""
        server = ctx.guild
        cur_setting = self.settings.guild(server).reinvite_on_unban()
        if not cur_setting:
            await self.settings.guild(server).set("reinvite_on_unban", True)
            await ctx.send("Users unbanned with [p]unban will be reinvited.")
        else:
            await self.settings.guild(server).set("reinvite_on_unban", False)
            await ctx.send("Users unbanned with [p]unban will not be reinvited.")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kicks user.
        If a reason is specified, it
        will be the reason that shows up
        in the audit log"""
        author = ctx.author
        server = ctx.guild

        if author == user:
            await ctx.send("I cannot let you do that. Self-harm is "
                           "bad \N{PENSIVE FACE}")
            return
        elif not is_allowed_by_hierarchy(self.bot, self.settings, server, author, user):
            await ctx.send("I cannot let you do that. You are "
                           "not higher than the user in the role "
                           "hierarchy.")
            return
        audit_reason = get_audit_reason(author, reason)
        try:
            await server.kick(user, reason=audit_reason)
            logger.info("{}({}) kicked {}({})".format(
                author.name, author.id, user.name, user.id))
            await self.modlog.new_case(server,
                                       action=KickCase,
                                       mod=author,
                                       user=user,
                                       reason=reason)
            await ctx.send("Done. That felt good.")
        except discord.errors.Forbidden:
            await ctx.send("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, days: str = None, *, reason: str = None):
        """Bans user and deletes last X days worth of messages.

        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.author
        server = ctx.guild

        if author == user:
            await ctx.send("I cannot let you do that. Self-harm is "
                           "bad \N{PENSIVE FACE}")
            return
        elif not is_allowed_by_hierarchy(self.bot, self.settings, server, author, user):
            await ctx.send("I cannot let you do that. You are "
                           "not higher than the user in the role "
                           "hierarchy.")
            return

        if days:
            if days.isdigit():
                days = int(days)
            else:
                days = 0
        else:
            days = 0

        audit_reason = get_audit_reason(author, reason)

        if days < 0 or days > 7:
            await ctx.send("Invalid days. Must be between 0 and 7.")
            return
        self.ban_type = BanCase
        try:
            await server.ban(user, reason=audit_reason, delete_message_days=days)
            logger.info("{}({}) banned {}({}), deleting {} days worth of messages".format(
                author.name, author.id, user.name, user.id, str(days)))
            await self.modlog.new_case(server,
                                       action=BanCase,
                                       mod=author,
                                       user=user,
                                       reason=reason)
            await ctx.send("Done. It was about time.")
        except discord.Forbidden:
            await ctx.send("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def hackban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Preemptively bans user from the server

        A user ID needs to be provided in order to ban
        using this command"""
        author = ctx.author
        server = ctx.guild

        ban_list = await server.bans()
        is_banned = discord.utils.get(ban_list, id=user_id)

        if is_banned:
            await ctx.send("User is already banned.")
            return

        user = server.get_member(user_id)
        if user is None:
            user = discord.Object(id=user_id)  # User not in the server, but

        audit_reason = get_audit_reason(author, reason)

        try:
            await server.ban(user, reason=audit_reason)
        except discord.NotFound:
            await ctx.send("User not found. Have you provided the "
                           "correct user ID?")
        except discord.Forbidden:
            await ctx.send("I lack the permissions to do this.")
        else:
            logger.info("{}({}) hackbanned {}"
                        "".format(author.name, author.id, user_id))
            user_info = await self.bot.get_user_info(user_id)
            await self.modlog.new_case(server,
                                       action=HackbanCase,
                                       mod=author,
                                       user=user_info,
                                       reason=reason)
            await ctx.send("Done. The user will not be able to join this "
                           "server.")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kicks the user, deleting 1 day worth of messages."""
        server = ctx.guild
        channel = ctx.channel
        can_ban = channel.permissions_for(server.me).ban_members
        author = ctx.author

        if author == user:
            await ctx.send("I cannot let you do that. Self-harm is "
                           "bad \N{PENSIVE FACE}")
            return
        elif not is_allowed_by_hierarchy(self.bot, self.settings, server, author, user):
            await ctx.send("I cannot let you do that. You are "
                           "not higher than the user in the role "
                           "hierarchy.")
            return

        audit_reason = get_audit_reason(author, reason)

        invite = await self.get_invite_for_reinvite(ctx)
        if invite is None:
            invite = ""

        if can_ban:
            msg = None
            try:
                try:  # We don't want blocked DMs preventing us from banning
                    msg = await user.send(
                        "You have been banned and "
                        "then unbanned as a quick way to delete your messages.\n"
                        "You can now join the server again.{}".format(invite)
                    )
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass
                self.current_softban["user"] = user
                await server.ban(user, reason=audit_reason, delete_message_days=1)
                logger.info(
                    "{}({}) softbanned {}({}), deleting 1 day worth "
                    "of messages".format(
                        author.name, author.id, user.name, user.id
                    )
                )
                await self.modlog.new_case(server,
                                           action=SoftbanCase,
                                           mod=author,
                                           user=user,
                                           reason=reason)
                await server.unban(user)
                await ctx.send("Done. Enough chaos.")
                asyncio.sleep(5)
                self.current_softban = {}
            except discord.errors.Forbidden:
                await ctx.send("My role is not high enough to softban that user.")
                if msg:
                    await msg.delete()
            except Exception as e:
                print(e)
        else:
            await ctx.send("I'm not allowed to do that.")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Unbans the target user. Requires specifying the target user's ID
        (which can be found in the mod log channel (if logging was enabled for
        the casetype associated with the command used to ban the user) or (if
        developer mode is enabled) by looking in Bans in server settings,
        finding the user, right-clicking, and selecting 'Copy ID'"""
        server = ctx.guild
        user = await self.bot.get_user(user_id)
        if not user:
            await ctx.send("Couldn't find a user with that ID!")
            return
        reason = get_audit_reason(ctx.author, reason)
        bans = await server.bans()
        bans = [be.user for be in bans]
        if user not in bans:
            await ctx.send("It seems that user isn't banned!")
            return

        try:
            await server.unban(user, reason=reason)
        except discord.HTTPException:
            await ctx.send("Something went wrong while attempting to unban that user")
            return
        if self.settings.guild(server).reinvite_on_unban():
            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    user.send(
                        "You've been unbanned from {}.\n"
                        "Here is an invite for that server: {}".format(server.name, invite.url))
                except discord.Forbidden:
                    await ctx.send(
                        "I failed to send an invite to that user. "
                        "Perhaps you may be able to send it for me?\n"
                        "Here's the invite link: {}".format(invite.url)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        "Something went wrong when attempting to send that user"
                        "an invite. Here's the link so you can try: {}".format(invite.url)
                    )
        await ctx.send("Unbanned that user from this server")

    @staticmethod
    async def get_invite_for_reinvite(ctx: commands.Context):
        """Handles the reinvite logic for getting an invite
        to send the newly unbanned user
        :returns: :class:`Invite`"""
        server = ctx.guild
        permissions = server.default_channel.permissions_for(server.me)
        if not permissions.create_instant_invite and not permissions.manage_guild:
            return None
        if "VANITY_URL" in server.features:  # Server has a vanity url so use it as the one to send
            return await server.vanity_invite()
        invites = await server.invites()
        for inv in invites:  # Loop through the invites for the server
            if inv.channel == server.default_channel \
                    and not inv.max_uses and not inv.max_age \
                    and not inv.temporary:
                # Invite is for the server's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv
        else:  # No existing invite found that is valid
            try:
                # Create invite that expires after 1 day
                return await server.create_invite(max_age=86400)
            except discord.HTTPException:
                return None

    @commands.command()
    @commands.guild_only()
    @admin_or_voice_permissions(mute_members=True, deafen_members=True)
    @bot_has_voice_permissions(mute_members=True, deafen_members=True)
    async def voiceban(self, ctx: commands.Context, user: discord.Member, *, reason: str=None):
        """Bans the target user from speaking and listening in voice channels in the server"""
        user_voice_state = user.voice
        if user_voice_state is None:
            await ctx.send("No voice state for that user!")
            return
        needs_mute = True if user_voice_state.mute is False else False
        needs_deafen = True if user_voice_state.deaf is False else False
        audit_reason = get_audit_reason(ctx.author, reason)
        if needs_mute and needs_deafen:
            await user.edit(mute=True, deafen=True, reason=audit_reason)
            await ctx.send("User has been muted and deafened server-wide")
        elif needs_mute:
            await user.edit(mute=True, reason=audit_reason)
            await ctx.send("User has been muted server-wide")
        elif needs_deafen:
            await user.edit(deafen=True, reason=audit_reason)
            await ctx.send("User has been deafened server-wide")
        else:
            await ctx.send("That user is already muted and deafened server-wide!")

    @commands.command()
    @commands.guild_only()
    @admin_or_voice_permissions(mute_members=True, deafen_members=True)
    @bot_has_voice_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(self, ctx: commands.Context, user: discord.Member, *, reason: str=None):
        """Unbans the user from speaking/listening in the server's voice channels"""
        user_voice_state = user.voice
        needs_unmute = True if user_voice_state.mute else False
        needs_undeafen = True if user_voice_state.deaf else False
        audit_reason = get_audit_reason(ctx.author, reason)
        if needs_unmute and needs_undeafen:
            await user.edit(mute=False, deafen=False, reason=audit_reason)
            await ctx.send("User can now speak and listen in voice channels")
        elif needs_unmute:
            await user.edit(mute=False, reason=audit_reason)
            await ctx.send("User can now speak in voice channels")
        elif needs_undeafen:
            await user.edit(deafen=False, reason=audit_reason)
            await ctx.send("User can now listen in voice channels")
        else:
            await ctx.send("That user isn't muted or deafened by the guild!")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx: commands.Context, user: discord.Member, *, nickname=""):
        """Changes user's nickname

        Leaving the nickname empty will remove it."""
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await user.edit(
                reason=get_audit_reason(ctx.author, None),
                nick=nickname
            )
            await ctx.send("Done.")
        except discord.Forbidden:
            await ctx.send("I cannot do that, I lack the "
                           "\"Manage Nicknames\" permission.")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def mute(self, ctx: commands.Context, user : discord.Member, *, reason: str = None):
        """Mutes user in the channel/server

        Defaults to channel"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.channel_mute, user=user, reason=reason)

    @mute.command(name="voice")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def voice_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mutes the user in a voice channel"""
        user_voice_state = user.voice
        if user_voice_state:
            channel = user_voice_state.channel
            if channel and channel.permissions_for(user).speak:
                overwrites = channel.overwrites_for(user)
                overwrites.speak = False
                audit_reason = get_audit_reason(ctx.author, reason)
                await channel.set_permissions(user, overwrite=overwrites, reason=audit_reason)
                await ctx.send(
                    "Muted {}#{} in channel {}".format(
                        user.name, user.discriminator,
                        channel.name
                    )
                )
                return
            elif channel.permissions_for(user).speak is False:
                await ctx.send("That user is already muted in {}!".format(channel.name))
                return
            else:
                await ctx.send("That user is not in a voice channel right now!")
        else:
            await ctx.send("No voice state for the target!")
            return

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="channel")
    @commands.guild_only()
    async def channel_mute(self, ctx: commands.Context, user : discord.Member, *, reason: str = None):
        """Mutes user in the current channel"""
        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.guild

        if reason is None:
            audit_reason = "Channel mute requested by {} (ID {})".format(author, author.id)
        else:
            audit_reason = "Channel mute requested by {} (ID {}). Reason: {}".format(author, author.id, reason)

        success, issue = await self.mute_user(server, channel, author, user, audit_reason)

        if success:
            await self.modlog.new_case(server,
                                       action="CMUTE",
                                       channel=channel,
                                       mod=author,
                                       user=user,
                                       reason=reason)
            await channel.send("User has been muted in this channel.")
        else:
            await channel.send(issue)

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="server")
    @commands.guild_only()
    async def server_mute(self, ctx: commands.Context, user : discord.Member, *, reason: str = None):
        """Mutes user in the server"""
        author = ctx.message.author
        server = ctx.guild

        if reason is None:
            audit_reason = "Server mute requested by {} (ID {})".format(author, author.id)
        else:
            audit_reason = "Server mute requested by {} (ID {}). Reason: {}".format(author, author.id, reason)

        mute_success = []
        for channel in server.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
            success, issue = await self.mute_user(server, channel, author, user, audit_reason)
            mute_success.append((success, issue))
            await asyncio.sleep(0.1)

        success_count = 0
        already_muted_count = 0
        not_higher_than_target_count = 0
        permissions_error_count = 0

        for attempt in mute_success:
            if attempt[0]:
                success_count += 1
            else:
                if attempt[1] == mute_unmute_issues["already_muted"]:
                    already_muted_count += 1
                elif attempt[1] == mute_unmute_issues["hierarchy_problem"]:
                    not_higher_than_target_count += 1
                elif attempt[1] == mute_unmute_issues["permissions_issue"]:
                    permissions_error_count += 1
        if already_muted_count == len(server.channels):
            await ctx.send("That user can't send messages in this server!")
            return
        elif not_higher_than_target_count == len(server.channels):
            await ctx.send(mute_unmute_issues["hierarchy_problem"])
            return
        elif permissions_error_count == len(server.channels):
            await ctx.send(mute_unmute_issues["permissions_issue"])
        elif success_count > 0:
            await ctx.send(
                "Server mute results:\n"
                "Success: {}\n"
                "Already muted in: {}\n"
                "Permissions error count: {}\n"
                "".format(success_count, already_muted_count, permissions_error_count)
            )
            await self.modlog.new_case(server,
                                       action=SMuteCase,
                                       mod=author,
                                       user=user,
                                       reason=reason)

    async def mute_user(self, server: discord.Guild,
                        channel: discord.TextChannel,
                        author: discord.Member,
                        user: discord.Member, reason: str) -> (bool, str):
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)
        perms_cache = self.settings.member(user).perms_cache()

        if overwrites.send_messages is False or permissions.send_messages is False:
            return False, mute_unmute_issues["already_muted"]

        elif not is_allowed_by_hierarchy(self.bot, self.settings, server, author, user):
            return False, mute_unmute_issues["hierarchy_problem"]

        perms_cache[str(channel.id)] = overwrites.send_messages
        overwrites.send_messages = False
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, mute_unmute_issues["permissions_issue"]
        else:
            await self.settings.member(user).set("perms_cache", perms_cache)
            return True, None

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def unmute(self, ctx: commands.Context, user : discord.Member):
        """Unmutes user in the channel/server

        Defaults to channel"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.channel_unmute, user=user)

    @unmute.command(name="voice")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def voice_unmute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Unmutes the user in a voice channel"""
        user_voice_state = user.voice
        if user_voice_state:
            channel = user_voice_state.channel
            if channel and channel.permissions_for(user).speak is False:
                overwrites = channel.overwrites_for(user)
                overwrites.speak = None
                audit_reason = get_audit_reason(ctx.author, reason)
                await channel.set_permissions(user, overwrite=overwrites, reason=audit_reason)
                await ctx.send(
                    "Unmuted {}#{} in channel {}".format(
                        user.name, user.discriminator,
                        channel.name
                    )
                )
                return
            elif channel.permissions_for(user).speak:
                await ctx.send("That user is already unmuted in {}!".format(channel.name))
                return
            else:
                await ctx.send("That user is not in a voice channel right now!")
        else:
            await ctx.send("No voice state for the target!")
            return

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="channel")
    @commands.guild_only()
    async def channel_unmute(self, ctx: commands.Context, user : discord.Member):
        """Unmutes user in the current channel"""
        channel = ctx.channel
        author = ctx.author
        server = ctx.guild

        success, message = await self.unmute_user(server, channel, author, user)

        if success:
            await ctx.send("User unmuted in this channel.")
        else:
            await ctx.send("Unmute failed. Reason: {}".format(message))

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="server")
    @commands.guild_only()
    async def server_unmute(self, ctx: commands.Context, user: discord.Member):
        """Unmutes user in the server"""
        server = ctx.guild
        author = ctx.author
        channel = ctx.channel
        perms_cache = self.settings.member(user).get("perms_cache")

        unmute_success = []
        for channel in server.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
            if str(channel.id) not in perms_cache:
                continue
            success, message = await self.unmute_user(server, channel, author, user)
            unmute_success.append((success, message))
            await asyncio.sleep(0.1)

        success_count = 0
        already_unmuted_count = 0
        not_higher_than_target_count = 0
        permissions_error_count = 0

        for attempt in unmute_success:
            if attempt[0]:
                success_count += 1
            elif attempt[1] == mute_unmute_issues["already_muted"]:
                already_unmuted_count += 1
            elif attempt[1] == mute_unmute_issues["hierarchy_problem"]:
                not_higher_than_target_count += 1
            elif attempt[1] == mute_unmute_issues["permissions_issue"]:
                permissions_error_count += 1
        if already_unmuted_count == len(server.channels):
            await ctx.send("That user can't send messages in this server!")
            return
        elif not_higher_than_target_count == len(server.channels):
            await ctx.send(mute_unmute_issues["hierarchy_problem"])
            return
        elif permissions_error_count == len(server.channels):
            await ctx.send(mute_unmute_issues["permissions_issue"])
        elif success_count > 0:
            await ctx.send(
                "Server unmute results:\n"
                "Success: {}\n"
                "Already unmuted in: {}\n"
                "Permissions error count: {}\n"
                "".format(success_count, already_unmuted_count, permissions_error_count)
            )
            await ctx.send("User has been unmuted in this server.")

    async def unmute_user(self, server: discord.Guild,
                          channel: discord.TextChannel,
                          author: discord.Member,
                          user: discord.Member) -> (bool, str):
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)
        perms_cache = self.settings.member(user).perms_cache()

        if overwrites.send_messages or permissions.send_messages:
            return False, mute_unmute_issues["already_unmuted"]

        elif not is_allowed_by_hierarchy(self.bot, self.settings, server, author, user):
            return False, mute_unmute_issues["hierarchy_problem"]
        
        if channel.id in perms_cache:
            old_value = perms_cache[channel.id]
        else:
            old_value = None
        overwrites.send_messages = old_value
        is_empty = self.are_overwrites_empty(overwrites)
        
        try:
            if not is_empty:
                await channel.set_permissions(user, overwrite=overwrites)
            else:
                await channel.set_permissions(user, overwrite=None)
        except discord.Forbidden:
            return False, mute_unmute_issues["permissions_issue"]
        else:
            try:
                del perms_cache[channel.id]
            except KeyError:
                pass
            else:
                await self.settings.member(user).set("perms_cache", perms_cache)
            return True, None

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context):
        """Adds servers/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            await ctx.send(self.count_ignored())

    @ignore.command(name="channel")
    async def ignore_channel(self, ctx: commands.Context, channel: discord.TextChannel=None):
        """Ignores channel

        Defaults to current one"""
        if not channel:
            channel = ctx.channel
        if not self.settings.channel(channel).ignored():
            await self.settings.channel(channel).set("ignored", True)
            await ctx.send("Channel added to ignore list.")
        else:
            await ctx.send("Channel already in ignore list.")

    @ignore.command(name="server")
    async def ignore_server(self, ctx: commands.Context):
        """Ignores current server"""
        server = ctx.guild
        if not self.settings.guild(server).ignored():
            await self.settings.guild(server).set("ignored", True)
            await ctx.send("This server has been added to the ignore list.")
        else:
            await ctx.send("This server is already being ignored.")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx: commands.Context):
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            await ctx.send(self.count_ignored())

    @unignore.command(name="channel")
    async def unignore_channel(self, ctx: commands.Context, channel: discord.TextChannel=None):
        """Removes channel from ignore list

        Defaults to current one"""
        if not channel:
            channel = ctx.channel

        if self.settings.channel(channel).ignored():
            await self.settings.channel(channel).set("ignored", False)
            await ctx.send("Channel removed from ignore list.")
        else:
            await ctx.send("That channel is not in the ignore list.")

    @unignore.command(name="server")
    async def unignore_server(self, ctx: commands.Context):
        """Removes current server from ignore list"""
        server = ctx.message.server
        if self.settings.guild(server).ignored():
            await self.settings.guild(server).set("ignored", False)
            await ctx.send("This server has been removed from the ignore list.")
        else:
            await ctx.send("This server is not in the ignore list.")

    def count_ignored(self):
        msg = "```Currently ignoring:\n"
        ch_count = 0
        svr_count = 0
        for server in self.bot.guilds:
            if not self.settings.guild(server).ignored():
                for channel in server.text_channels:
                    if self.settings.channel(channel).ignored():
                        ch_count += 1
            else:
                svr_count += 1

        msg += str(ch_count) + " channels\n"
        msg += str(svr_count) + " servers\n```\n"
        return msg

    @commands.command()
    async def names(self, ctx: commands.Context, user : discord.Member):
        """Show previous names/nicknames of a user"""
        names = self.settings.user(user).past_names()
        nicks = self.settings.member(user).past_nicks()
        msg = ""
        if names:
            names = [escape(name, mass_mentions=True) for name in names]
            msg += "**Past 20 names**:\n"
            msg += ", ".join(names)
        if nicks:
            nicks = [escape(nick, mass_mentions=True) for nick in nicks]
            if msg:
                msg += "\n\n"
            msg += "**Past 20 nicknames**:\n"
            msg += ", ".join(nicks)
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send("That user doesn't have any recorded name or "
                           "nickname change.")

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
                    await message.delete()
                    return True
                except discord.HTTPException:
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
                    await server.ban(author, reason="Mention spam (Autoban)")
                except discord.HTTPException:
                    logger.info("Failed to ban member for mention spam in "
                                "server {}.".format(server.id))
                else:
                    await self.modlog.new_case(server,
                                               action=BanCase,
                                               mod=server.me,
                                               user=author,
                                               reason="Mention spam (Autoban)")
                    return True
        return False

    async def on_command(self, command, ctx: commands.Context):
        """Currently used for:
            * delete delay"""
        server = ctx.guild
        message = ctx.message
        delay = self.settings.guild(server).delete_delay()

        if delay == -1:
            return

        async def _delete_helper(m):
            try:
                await m.delete()
                logger.debug("Deleted command msg {}".format(m.id))
            except:
                pass  # We don't really care if it fails or not

        await asyncio.sleep(delay)
        await _delete_helper(message)

    async def on_message(self, message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return
        valid_user = isinstance(author, discord.Member) and not author.bot

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if not valid_user or mod_or_superior:
            return
        deleted = await self.check_duplicates(message)
        if not deleted:
            deleted = await self.check_mention_spam(message)

    async def on_member_ban(self, server: discord.Guild, member: discord.Member):
        if self.current_softban:
            return
        audit_case = None
        async for entry in server.audit_logs(action=discord.AuditLogAction.ban):
            if entry.target == member:
                audit_case = entry
                break

        if audit_case:
            mod = audit_case.user if audit_case.user != server.me else None
            reason = audit_case.reason
            if not mod:
                if "Reason:" in reason:  # Would be the case if event is triggered by a command
                    tmp_reason = reason.split("Reason:")
                    reason = tmp_reason[1]
                    tmp_reason = tmp_reason[0].split()
                    mod = [m for m in server.members if m.id == tmp_reason[-1][:-2]][0]

            await self.modlog.new_case(server,
                                       mod=mod if mod else None,
                                       user=member,
                                       reason=reason if reason else None,
                                       action=BanCase)
        else:
            await self.modlog.new_case(server, user=member, action=BanCase)

    async def on_member_unban(self, server: discord.Guild, user: discord.User):
        if self.current_softban:
            return
        audit_case = None
        async for entry in server.audit_logs(action=discord.AuditLogAction.unban):
            if entry.target == user:
                audit_case = entry
                break
        if audit_case:
            mod = audit_case.user if audit_case.user != server.me else None
            reason = audit_case.reason
            if not mod:
                if "Reason:" in reason:  # Would be the case if event is triggered by a command
                    tmp_reason = reason.split("Reason:")
                    reason = tmp_reason[1]
                    tmp_reason = tmp_reason[0].split()
                    mod = [m for m in server.members if m.id == tmp_reason[-1][:-2]][0]

            await self.modlog.new_case(server,
                                       mod=mod if mod else None,
                                       user=user,
                                       reason=reason if reason else None,
                                       action=UnbanCase)
        else:
            await self.modlog.new_case(server, user=user, action=UnbanCase)

    async def on_member_update(self, before, after):
        if before.name != after.name:
            name_list = self.settings.user(before).past_names()
            if after.name not in name_list:
                names = deque(name_list, maxlen=20)
                names.append(after.name)
                await self.settings.user(before).set("past_names", list(names))

        if before.nick != after.nick and after.nick is not None:
            nick_list = self.settings.member(before).past_nicks()
            nicks = deque(nick_list, maxlen=20)
            if after.nick not in nicks:
                nicks.append(after.nick)
                self.settings.member(before).set("past_nicks", list(nicks))

    @staticmethod
    def are_overwrites_empty(overwrites):
        """There is currently no cleaner way to check if a
        PermissionOverwrite object is empty"""
        return [p for p in iter(overwrites)] ==\
               [p for p in iter(discord.PermissionOverwrite())]
