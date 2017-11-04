import asyncio
from collections import deque, defaultdict

import discord
from discord.ext import commands

from redbot.core import checks, Config, modlog
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import box, escape
from .checks import mod_or_voice_permissions, admin_or_voice_permissions, bot_has_voice_permissions
from redbot.core.utils.mod import is_mod_or_superior, is_allowed_by_hierarchy, \
    get_audit_reason
from .log import log

_ = CogI18n("Mod", __file__)



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

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, 4961522000, force_registration=True)

        self.settings.register_guild(**self.default_guild_settings)
        self.settings.register_channel(**self.default_channel_settings)
        self.settings.register_member(**self.default_member_settings)
        self.settings.register_user(**self.default_user_settings)
        self.current_softban = {}
        self.ban_type = None
        self.cache = defaultdict(lambda: deque(maxlen=3))

        self.bot.loop.create_task(self._casetype_registration())

        self.last_case = defaultdict(dict)

    async def _casetype_registration(self):
        casetypes_to_register = [
            {
                "name": "ban",
                "default_setting": True,
                "image": ":hammer:",
                "case_str": "Ban",
                "audit_type": "ban"
            },
            {
                "name": "kick",
                "default_setting": True,
                "image": ":boot:",
                "case_str": "Kick",
                "audit_type": "kick"
            },
            {
                "name": "hackban",
                "default_setting": True,
                "image": ":bust_in_silhouette: :hammer:",
                "case_str": "Hackban",
                "audit_type": "ban"
            },
            {
                "name": "softban",
                "default_setting": True,
                "image": ":dash: :hammer:",
                "case_str": "Softban",
                "audit_type": "ban"
            },
            {
                "name": "unban",
                "default_setting": True,
                "image": ":dove:",
                "case_str": "Unban",
                "audit_type": "unban"
            },
            {
                "name": "voiceban",
                "default_setting": True,
                "image": ":mute:",
                "case_str": "Voice Ban",
                "audit_type": "member_update"
            },
            {
                "name": "voiceunban",
                "default_setting": True,
                "image": ":speaker:",
                "case_str": "Voice Unban",
                "audit_type": "member_update"
            },
            {
                "name": "vmute",
                "default_setting": False,
                "image": ":mute:",
                "case_str": "Voice Mute",
                "audit_type": "overwrite_update"
            },
            {
                "name": "cmute",
                "default_setting": False,
                "image": ":mute:",
                "case_str": "Channel Mute",
                "audit_type": "overwrite_update"
            },
            {
                "name": "smute",
                "default_setting": True,
                "image": ":mute:",
                "case_str": "Guild Mute",
                "audit_type": "overwrite_update"
            },
            {
                "name": "vunmute",
                "default_setting": False,
                "image": ":speaker:",
                "case_str": "Voice Unmute",
                "audit_type": "overwrite_update"
            },
            {
                "name": "cunmute",
                "default_setting": False,
                "image": ":speaker:",
                "case_str": "Channel Unmute",
                "audit_type": "overwrite_update"
            },
            {
                "name": "sunmute",
                "default_setting": True,
                "image": ":speaker:",
                "case_str": "Guild Unmute",
                "audit_type": "overwrite_update"
            }
        ]
        try:
            await modlog.register_casetypes(casetypes_to_register)
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def modset(self, ctx: commands.Context):
        """Manages guild administration settings."""
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            await self.bot.send_cmd_help(ctx)

            # Display current settings
            delete_repeats = await self.settings.guild(guild).delete_repeats()
            ban_mention_spam = await self.settings.guild(guild).ban_mention_spam()
            respect_hierarchy = await self.settings.guild(guild).respect_hierarchy()
            delete_delay = await self.settings.guild(guild).delete_delay()
            reinvite_on_unban = await self.settings.guild(guild).reinvite_on_unban()
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
        guild = ctx.guild
        toggled = await self.settings.guild(guild).respect_hierarchy()
        if not toggled:
            await self.settings.guild(guild).respect_hierarchy.set(True)
            await ctx.send(_("Role hierarchy will be checked when "
                             "moderation commands are issued."))
        else:
            await self.settings.guild(guild).respect_hierarchy.set(False)
            await ctx.send(_("Role hierarchy will be ignored when "
                             "moderation commands are issued."))

    @modset.command()
    @commands.guild_only()
    async def banmentionspam(self, ctx: commands.Context, max_mentions: int=False):
        """Enables auto ban for messages mentioning X different people

        Accepted values: 5 or superior"""
        guild = ctx.guild
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            await self.settings.guild(guild).ban_mention_spam.set(max_mentions)
            await ctx.send(
                _("Autoban for mention spam enabled. "
                  "Anyone mentioning {} or more different people "
                  "in a single message will be autobanned.").format(
                  max_mentions)
            )
        else:
            cur_setting = await self.settings.guild(guild).ban_mention_spam()
            if cur_setting is False:
                await self.bot.send_cmd_help(ctx)
                return
            await self.settings.guild(guild).ban_mention_spam.set(False)
            await ctx.send(_("Autoban for mention spam disabled."))

    @modset.command()
    @commands.guild_only()
    async def deleterepeats(self, ctx: commands.Context):
        """Enables auto deletion of repeated messages"""
        guild = ctx.guild
        cur_setting = await self.settings.guild(guild).delete_repeats()
        if not cur_setting:
            await self.settings.guild(guild).delete_repeats.set(True)
            await ctx.send(_("Messages repeated up to 3 times will "
                             "be deleted."))
        else:
            await self.settings.guild(guild).delete_repeats.set(False)
            await ctx.send(_("Repeated messages will be ignored."))

    @modset.command()
    @commands.guild_only()
    async def deletedelay(self, ctx: commands.Context, time: int=None):
        """Sets the delay until the bot removes the command message.
            Must be between -1 and 60.

        A delay of -1 means the bot will not remove the message."""
        guild = ctx.guild
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            await self.settings.guild(guild).delete_delay.set(time)
            if time == -1:
                await ctx.send(_("Command deleting disabled."))
            else:
                await ctx.send(
                    _("Delete delay set to {} seconds.").format(time)
                )
        else:
            delay = await self.settings.guild(guild).delete_delay()
            if delay != -1:
                await ctx.send(_("Bot will delete command messages after"
                                 " {} seconds. Set this value to -1 to"
                                 " stop deleting messages").format(delay))
            else:
                await ctx.send(_("I will not delete command messages."))

    @modset.command()
    @commands.guild_only()
    async def reinvite(self, ctx: commands.Context):
        """Toggles whether an invite will be sent when a user
        is unbanned via [p]unban. If this is True, the bot will
        attempt to create and send a single-use invite to the
        newly-unbanned user"""
        guild = ctx.guild
        cur_setting = await self.settings.guild(guild).reinvite_on_unban()
        if not cur_setting:
            await self.settings.guild(guild).reinvite_on_unban.set(True)
            await ctx.send(_("Users unbanned with {} will be reinvited.").format("[p]unban"))
        else:
            await self.settings.guild(guild).reinvite_on_unban.set(False)
            await ctx.send(_("Users unbanned with {} will not be reinvited.").format("[p]unban"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kicks user.
        If a reason is specified, it
        will be the reason that shows up
        in the audit log"""
        author = ctx.author
        guild = ctx.guild

        if author == user:
            await ctx.send(_("I cannot let you do that. Self-harm is "
                           "bad {}").format("\N{PENSIVE FACE}"))
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(_("I cannot let you do that. You are "
                             "not higher than the user in the role "
                             "hierarchy."))
            return
        audit_reason = get_audit_reason(author, reason)
        try:
            await guild.kick(user, reason=audit_reason)
            log.info("{}({}) kicked {}({})".format(
                author.name, author.id, user.name, user.id))
        except discord.errors.Forbidden:
            await ctx.send(_("I'm not allowed to do that."))
        except Exception as e:
            print(e)
        else:
            await ctx.send(_("Done. That felt good."))

        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "kick", user, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, days: str = None, *, reason: str = None):
        """Bans user and deletes last X days worth of messages.

        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.author
        guild = ctx.guild

        if author == user:
            await ctx.send(_("I cannot let you do that. Self-harm is "
                             "bad {}").format("\N{PENSIVE FACE}"))
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(_("I cannot let you do that. You are "
                             "not higher than the user in the role "
                             "hierarchy."))
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
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return

        try:
            await guild.ban(user, reason=audit_reason, delete_message_days=days)
            log.info("{}({}) banned {}({}), deleting {} days worth of messages".format(
                author.name, author.id, user.name, user.id, str(days)))
        except discord.Forbidden:
            await ctx.send(_("I'm not allowed to do that."))
        except Exception as e:
            print(e)
        else:
            await ctx.send(_("Done. It was about time."))

        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "ban", user, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def hackban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Preemptively bans user from the guild

        A user ID needs to be provided in order to ban
        using this command"""
        author = ctx.author
        guild = ctx.guild

        is_banned = False
        ban_list = await guild.bans()
        for entry in ban_list:
            if entry.user.id == user_id:
                is_banned = True
                break

        if is_banned:
            await ctx.send(_("User is already banned."))
            return

        user = guild.get_member(user_id)
        if user is None:
            user = discord.Object(id=user_id)  # User not in the guild, but

        audit_reason = get_audit_reason(author, reason)

        try:
            await guild.ban(user, reason=audit_reason)
            log.info("{}({}) hackbanned {}"
                     "".format(author.name, author.id, user_id))
        except discord.NotFound:
            await ctx.send(_("User not found. Have you provided the "
                             "correct user ID?"))
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to do this."))
        else:
            await ctx.send(_("Done. The user will not be able to join this "
                             "guild."))

        user_info = await self.bot.get_user_info(user_id)
        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "hackban", user_info, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kicks the user, deleting 1 day worth of messages."""
        guild = ctx.guild
        channel = ctx.channel
        can_ban = channel.permissions_for(guild.me).ban_members
        author = ctx.author

        if author == user:
            await ctx.send(_("I cannot let you do that. Self-harm is "
                             "bad {}").format("\N{PENSIVE FACE}"))
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(_("I cannot let you do that. You are "
                             "not higher than the user in the role "
                             "hierarchy."))
            return

        audit_reason = get_audit_reason(author, reason)

        invite = await self.get_invite_for_reinvite(ctx)
        if invite is None:
            invite = ""

        if can_ban:
            self.current_softban[str(guild.id)] = user
            try:  # We don't want blocked DMs preventing us from banning
                msg = await user.send(
                    _("You have been banned and "
                      "then unbanned as a quick way to delete your messages.\n"
                      "You can now join the guild again. {}").format(invite))
            except discord.HTTPException:
                msg = None
            try:
                await guild.ban(
                    user, reason=audit_reason, delete_message_days=1)
                await guild.unban(user)
            except discord.errors.Forbidden:
                await ctx.send(
                    _("My role is not high enough to softban that user."))
                if msg is not None:
                    await msg.delete()
                return
            except discord.HTTPException as e:
                print(e)
                return
            else:
                await ctx.send(_("Done. Enough chaos."))
                log.info("{}({}) softbanned {}({}), deleting 1 day worth "
                         "of messages".format(author.name, author.id,
                                              user.name, user.id))
                try:
                    await modlog.create_case(
                        guild,
                        ctx.message.created_at,
                        "softban",
                        user,
                        author,
                        reason,
                        until=None,
                        channel=None)
                except RuntimeError as e:
                    await ctx.send(e)
            finally:
                await asyncio.sleep(5)
                self.current_softban = None
        else:
            await ctx.send(_("I'm not allowed to do that."))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Unbans the target user. Requires specifying the target user's ID
        (which can be found in the mod log channel (if logging was enabled for
        the casetype associated with the command used to ban the user) or (if
        developer mode is enabled) by looking in Bans in guild settings,
        finding the user, right-clicking, and selecting 'Copy ID'"""
        guild = ctx.guild
        author = ctx.author
        user = self.bot.get_user_info(user_id)
        if not user:
            await ctx.send(_("Couldn't find a user with that ID!"))
            return
        reason = get_audit_reason(ctx.author, reason)
        bans = await guild.bans()
        bans = [be.user for be in bans]
        if user not in bans:
            await ctx.send(_("It seems that user isn't banned!"))
            return

        try:
            await guild.unban(user, reason=reason)
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to unban that user"))
            return
        else:
            await ctx.send(_("Unbanned that user from this guild"))

        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "unban", user, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

        if await self.settings.guild(guild).reinvite_on_unban():
            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    user.send(
                        _("You've been unbanned from {}.\n"
                          "Here is an invite for that guild: {}").format(guild.name, invite.url))
                except discord.Forbidden:
                    await ctx.send(
                        _("I failed to send an invite to that user. "
                          "Perhaps you may be able to send it for me?\n"
                          "Here's the invite link: {}").format(invite.url)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        _("Something went wrong when attempting to send that user"
                          "an invite. Here's the link so you can try: {}")
                        .format(invite.url))

    @staticmethod
    async def get_invite_for_reinvite(ctx: commands.Context):
        """Handles the reinvite logic for getting an invite
        to send the newly unbanned user
        :returns: :class:`Invite`"""
        guild = ctx.guild
        if "VANITY_URL" in guild.features and guild.me.permissions.manage_guild:
            # guild has a vanity url so use it as the one to send
            return await guild.vanity_invite()
        invites = await guild.invites()
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv
        else:  # No existing invite found that is valid
            channels_and_perms = zip(
                guild.text_channels,
                map(guild.me.permissions_in, guild.text_channels))
            channel = next((
                channel for channel, perms in channels_and_perms
                if perms.create_instant_invite), None)
            if channel is None:
                return
            try:
                # Create invite that expires after 1 day
                return await channel.create_invite(max_age=86400)
            except discord.HTTPException:
                return

    @commands.command()
    @commands.guild_only()
    @admin_or_voice_permissions(mute_members=True, deafen_members=True)
    @bot_has_voice_permissions(mute_members=True, deafen_members=True)
    async def voiceban(self, ctx: commands.Context, user: discord.Member, *, reason: str=None):
        """Bans the target user from speaking and listening in voice channels in the guild"""
        user_voice_state = user.voice
        if user_voice_state is None:
            await ctx.send(_("No voice state for that user!"))
            return
        needs_mute = True if user_voice_state.mute is False else False
        needs_deafen = True if user_voice_state.deaf is False else False
        audit_reason = get_audit_reason(ctx.author, reason)
        author = ctx.author
        guild = ctx.guild
        if needs_mute and needs_deafen:
            await user.edit(mute=True, deafen=True, reason=audit_reason)
        elif needs_mute:
            await user.edit(mute=True, reason=audit_reason)
        elif needs_deafen:
            await user.edit(deafen=True, reason=audit_reason)
        else:
            await ctx.send(_("That user is already muted and deafened guild-wide!"))
            return
        await ctx.send(
            _("User has been banned from speaking or "
              "listening in voice channels")
        )

        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "voiceban", user, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @admin_or_voice_permissions(mute_members=True, deafen_members=True)
    @bot_has_voice_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(self, ctx: commands.Context, user: discord.Member, *, reason: str=None):
        """Unbans the user from speaking/listening in the guild's voice channels"""
        user_voice_state = user.voice
        if user_voice_state is None:
            await ctx.send(_("No voice state for that user!"))
            return
        needs_unmute = True if user_voice_state.mute else False
        needs_undeafen = True if user_voice_state.deaf else False
        audit_reason = get_audit_reason(ctx.author, reason)
        if needs_unmute and needs_undeafen:
            await user.edit(mute=False, deafen=False, reason=audit_reason)
        elif needs_unmute:
            await user.edit(mute=False, reason=audit_reason)
        elif needs_undeafen:
            await user.edit(deafen=False, reason=audit_reason)
        else:
            await ctx.send(_("That user isn't muted or deafened by the guild!"))
            return
        await ctx.send(
            _("User is now allowed to speak and listen in voice channels")
        )
        guild = ctx.guild
        author = ctx.author
        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "voiceunban", user, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

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
            await ctx.send(_("I cannot do that, I lack the "
                             "'{}' permission.").format("Manage Nicknames"))

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def mute(self, ctx: commands.Context):
        """Mutes user in the channel/guild"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @mute.command(name="voice")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def voice_mute(self, ctx: commands.Context, user: discord.Member,
                         *, reason: str = None):
        """Mutes the user in a voice channel"""
        user_voice_state = user.voice
        guild = ctx.guild
        author = ctx.author
        if user_voice_state:
            channel = user_voice_state.channel
            if channel and channel.permissions_for(user).speak:
                overwrites = channel.overwrites_for(user)
                overwrites.speak = False
                audit_reason = get_audit_reason(ctx.author, reason)
                await channel.set_permissions(user, overwrite=overwrites, reason=audit_reason)
                await ctx.send(
                    _("Muted {}#{} in channel {}").format(
                        user.name, user.discriminator,
                        channel.name
                    )
                )
                try:
                    await modlog.create_case(
                        guild, ctx.message.created_at, "boicemute", user, author,
                        reason, until=None, channel=channel
                    )
                except RuntimeError as e:
                    await ctx.send(e)
                return
            elif channel.permissions_for(user).speak is False:
                await ctx.send(_("That user is already muted in {}!").format(channel.name))
                return
            else:
                await ctx.send(_("That user is not in a voice channel right now!"))
        else:
            await ctx.send(_("No voice state for the target!"))
            return

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="channel")
    @commands.guild_only()
    async def channel_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mutes user in the current channel"""
        author = ctx.message.author
        channel = ctx.message.channel
        guild = ctx.guild

        if reason is None:
            audit_reason = "Channel mute requested by {} (ID {})".format(author, author.id)
        else:
            audit_reason = "Channel mute requested by {} (ID {}). Reason: {}".format(author, author.id, reason)

        success, issue = await self.mute_user(guild, channel, author, user, audit_reason)

        if success:
            await channel.send(_("User has been muted in this channel."))
            try:
                await modlog.create_case(
                    guild, ctx.message.created_at, "cmute", user, author,
                    reason, until=None, channel=channel
                )
            except RuntimeError as e:
                await ctx.send(e)
        else:
            await channel.send(issue)

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="guild")
    @commands.guild_only()
    async def guild_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mutes user in the guild"""
        author = ctx.message.author
        guild = ctx.guild
        user_voice_state = user.voice
        if reason is None:
            audit_reason = "guild mute requested by {} (ID {})".format(author, author.id)
        else:
            audit_reason = "guild mute requested by {} (ID {}). Reason: {}".format(author, author.id, reason)

        mute_success = []
        for channel in guild.channels:
            if not isinstance(channel, discord.TextChannel):
                if channel.permissions_for(user).speak:
                    overwrites = channel.overwrites_for(user)
                    overwrites.speak = False
                    audit_reason = get_audit_reason(ctx.author, reason)
                    await channel.set_permissions(user, overwrite=overwrites, reason=audit_reason)
            else:
                success, issue = await self.mute_user(guild, channel, author, user, audit_reason)
                mute_success.append((success, issue))
            await asyncio.sleep(0.1)
        await ctx.send(_("User has been muted in this guild."))
        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "smute", user, author,
                reason, until=None, channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

    async def mute_user(self, guild: discord.Guild,
                        channel: discord.TextChannel,
                        author: discord.Member,
                        user: discord.Member, reason: str) -> (bool, str):
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)
        perms_cache = await self.settings.member(user).perms_cache()

        if overwrites.send_messages is False or permissions.send_messages is False:
            return False, mute_unmute_issues["already_muted"]

        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            return False, mute_unmute_issues["hierarchy_problem"]

        perms_cache[str(channel.id)] = overwrites.send_messages
        overwrites.send_messages = False
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, mute_unmute_issues["permissions_issue"]
        else:
            await self.settings.member(user).perms_cache.set(perms_cache)
            return True, None

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def unmute(self, ctx: commands.Context):
        """Unmutes user in the channel/guild

        Defaults to channel"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

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
                author = ctx.author
                guild = ctx.guild
                await ctx.send(
                    _("Unmuted {}#{} in channel {}").format(
                        user.name, user.discriminator, channel.name))
                try:
                    await modlog.create_case(
                        guild, ctx.message.created_at, "voiceunmute", user, author,
                        reason, until=None, channel=channel
                    )
                except RuntimeError as e:
                    await ctx.send(e)
            elif channel.permissions_for(user).speak:
                await ctx.send(_("That user is already unmuted in {}!").format(channel.name))
                return
            else:
                await ctx.send(_("That user is not in a voice channel right now!"))
        else:
            await ctx.send(_("No voice state for the target!"))
            return

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="channel")
    @commands.guild_only()
    async def channel_unmute(self, ctx: commands.Context, user: discord.Member, *, reason: str=None):
        """Unmutes user in the current channel"""
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild

        success, message = await self.unmute_user(guild, channel, author, user)

        if success:
            await ctx.send(_("User unmuted in this channel."))
            try:
                await modlog.create_case(
                    guild, ctx.message.created_at, "cunmute", user, author,
                    reason, until=None, channel=channel
                )
            except RuntimeError as e:
                await ctx.send(e)
        else:
            await ctx.send(_("Unmute failed. Reason: {}").format(message))

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="guild")
    @commands.guild_only()
    async def guild_unmute(self, ctx: commands.Context, user: discord.Member, *, reason: str=None):
        """Unmutes user in the guild"""
        guild = ctx.guild
        author = ctx.author
        channel = ctx.channel

        unmute_success = []
        for channel in guild.channels:
            if not isinstance(channel, discord.TextChannel):
                if channel.permissions_for(user).speak is False:
                    overwrites = channel.overwrites_for(user)
                    overwrites.speak = None
                    audit_reason = get_audit_reason(author, reason)
                    await channel.set_permissions(
                        user, overwrite=overwrites, reason=audit_reason)
            success, message = await self.unmute_user(guild, channel, author, user)
            unmute_success.append((success, message))
            await asyncio.sleep(0.1)
        await ctx.send(_("User has been unmuted in this guild."))
        try:
            await modlog.create_case(
                guild, ctx.message.created_at, "sunmute", user, author,
                reason, until=None, channel=channel
            )
        except RuntimeError as e:
            await ctx.send(e)

    async def unmute_user(self, guild: discord.Guild,
                          channel: discord.TextChannel,
                          author: discord.Member,
                          user: discord.Member) -> (bool, str):
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)
        perms_cache = await self.settings.member(user).perms_cache()

        if overwrites.send_messages or permissions.send_messages:
            return False, mute_unmute_issues["already_unmuted"]

        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
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
                await self.settings.member(user).perms_cache.set(perms_cache)
            return True, None

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context):
        """Adds guilds/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            await ctx.send(await self.count_ignored())

    @ignore.command(name="channel")
    async def ignore_channel(self, ctx: commands.Context, channel: discord.TextChannel=None):
        """Ignores channel

        Defaults to current one"""
        if not channel:
            channel = ctx.channel
        if not await self.settings.channel(channel).ignored():
            await self.settings.channel(channel).ignored.set(True)
            await ctx.send(_("Channel added to ignore list."))
        else:
            await ctx.send(_("Channel already in ignore list."))

    @ignore.command(name="guild", aliases=["server"])
    @commands.has_permissions(manage_guild=True)
    async def ignore_guild(self, ctx: commands.Context):
        """Ignores current guild"""
        guild = ctx.guild
        if not await self.settings.guild(guild).ignored():
            await self.settings.guild(guild).ignored.set(True)
            await ctx.send(_("This guild has been added to the ignore list."))
        else:
            await ctx.send(_("This guild is already being ignored."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx: commands.Context):
        """Removes guilds/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            await ctx.send(await self.count_ignored())

    @unignore.command(name="channel")
    async def unignore_channel(self, ctx: commands.Context, channel: discord.TextChannel=None):
        """Removes channel from ignore list

        Defaults to current one"""
        if not channel:
            channel = ctx.channel

        if await self.settings.channel(channel).ignored():
            await self.settings.channel(channel).ignored.set(False)
            await ctx.send(_("Channel removed from ignore list."))
        else:
            await ctx.send(_("That channel is not in the ignore list."))

    @unignore.command(name="guild", aliases=["server"])
    @commands.has_permissions(manage_guild=True)
    async def unignore_guild(self, ctx: commands.Context):
        """Removes current guild from ignore list"""
        guild = ctx.message.guild
        if await self.settings.guild(guild).ignored():
            await self.settings.guild(guild).ignored.set(False)
            await ctx.send(_("This guild has been removed from the ignore list."))
        else:
            await ctx.send(_("This guild is not in the ignore list."))

    async def count_ignored(self):
        ch_count = 0
        svr_count = 0
        for guild in self.bot.guilds:
            if not await self.settings.guild(guild).ignored():
                for channel in guild.text_channels:
                    if await self.settings.channel(channel).ignored():
                        ch_count += 1
            else:
                svr_count += 1
        msg = _("Currently ignoring:\n{} channels\n{} guilds\n").format(ch_count, svr_count)
        return box(msg)

    async def __global_check(self, ctx):
        """Global check to see if a channel or guild is ignored.

        Any users who have permission to use the `ignore` or `unignore` commands
        surpass the check."""
        perms = ctx.channel.permissions_for(ctx.author)
        surpass_ignore = (isinstance(ctx.channel, discord.abc.PrivateChannel) or
                          perms.manage_guild or
                          await ctx.bot.is_owner(ctx.author) or
                          await ctx.bot.is_admin(ctx.author))
        if surpass_ignore:
            return True
        guild_ignored = await self.settings.guild(ctx.guild).ignored()
        chann_ignored = await self.settings.channel(ctx.channel).ignored()
        return not (guild_ignored or
                    chann_ignored and not perms.manage_channels)

    @commands.command()
    async def names(self, ctx: commands.Context, user: discord.Member):
        """Show previous names/nicknames of a user"""
        names = await self.settings.user(user).past_names()
        nicks = await self.settings.member(user).past_nicks()
        msg = ""
        if names:
            names = [escape(name, mass_mentions=True) for name in names]
            msg += _("**Past 20 names**:")
            msg += "\n"
            msg += ", ".join(names)
        if nicks:
            nicks = [escape(nick, mass_mentions=True) for nick in nicks]
            if msg:
                msg += "\n\n"
            msg += _("**Past 20 nicknames**:")
            msg += "\n"
            msg += ", ".join(nicks)
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send(_("That user doesn't have any recorded name or "
                             "nickname change."))

    async def check_duplicates(self, message):
        guild = message.guild
        author = message.author

        if await self.settings.guild(guild).delete_repeats():
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
        guild = message.guild
        author = message.author

        if await self.settings.guild(guild).ban_mention_spam():
            max_mentions = await self.settings.guild(guild).ban_mention_spam()
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    await guild.ban(author, reason="Mention spam (Autoban)")
                except discord.HTTPException:
                    log.info("Failed to ban member for mention spam in "
                             "guild {}.".format(guild.id))
                else:
                    try:
                        case = await modlog.create_case(
                            guild, message.created_at, "ban", author, guild.me,
                            "Mention spam (Autoban)", until=None, channel=None
                        )
                    except RuntimeError as e:
                        print(e)
                        return False
                    return True
        return False

    async def on_command(self, ctx: commands.Context):
        """Currently used for:
            * delete delay"""
        guild = ctx.guild
        message = ctx.message
        delay = await self.settings.guild(guild).delete_delay()

        if delay == -1:
            return

        async def _delete_helper(m):
            try:
                await m.delete()
                log.debug("Deleted command msg {}".format(m.id))
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

    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        if str(guild.id) in self.current_softban and \
                self.current_softban[str(guild.id)] == member:
            return  # softban in progress, so a case will be created
        try:
            mod_ch = await modlog.get_modlog_channel(guild)
        except RuntimeError:
            return  # No modlog channel so no point in continuing
        audit_case = None
        permissions = guild.me.guild_permissions
        modlog_cases = await modlog.get_all_cases(guild, self.bot)
        if permissions.view_audit_log:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
                if entry.target == member:
                    audit_case = entry
                    break

            if audit_case:
                mod = audit_case.user
                reason = audit_case.reason
                for case in sorted(modlog_cases, key=lambda x: x.case_number, reverse=True):
                    if case.moderator == mod and case.user == member\
                            and case.action_type in ["ban", "hackban"]:
                        break
                else:  # no ban, softban, or hackban case with the mod and user combo
                    try:
                        await modlog.create_case(guild, audit_case.created_at, "ban",
                                                member, mod, reason if reason else None)
                    except RuntimeError as e:
                        print(e)
            else:
                return
        else:  # No permissions to view audit logs, so message the guild owner
            owner = guild.owner
            try:
                await owner.send(
                    _("Hi, I noticed that someone in your server "
                    "(the server named {}) banned {}#{} (user ID {}). "
                    "However, I don't have permissions to view audit logs, "
                    "so I could not determine if a mod log case was created "
                    "for that ban, meaning I could not create a case in "
                    "the mod log. If you want me to be able to add cases "
                    "to the mod log for bans done manually, I need the "
                    "`View Audit Logs` permission.").format(
                        guild.name,
                        member.name,
                        member.discriminator,
                        member.id
                    )
                )
            except discord.Forbidden:
                log.warning(
                    "I attempted to inform a guild owner of a lack of the "
                    "'View Audit Log' permission but I am unable to send "
                    "the guild owner the message!"
                )
            except discord.HTTPException:
                log.warning(
                    "Something else went wrong while attempting to "
                    "message a guild owner."
                )

    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        if str(guild.id) in self.current_softban and \
                self.current_softban[str(guild.id)] == user:
            return  # softban in progress, so a case will be created
        try:
            mod_ch = await modlog.get_modlog_channel(guild)
        except RuntimeError:
            return  # No modlog channel so no point in continuing
        audit_case = None
        permissions = guild.me.guild_permissions
        if permissions.view_audit_log:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.unban):
                if entry.target == user:
                    audit_case = entry
                    break
            else:
                return
            if audit_case:
                mod = audit_case.user
                reason = audit_case.reason

                cases = await modlog.get_all_cases(guild, self.bot)
                for case in sorted(cases, key=lambda x: x.case_number, reverse=True):
                    if case.moderator == mod and case.user == user\
                            and case.action_type == "unban": 
                        break
                else:
                    try:
                        await modlog.create_case(guild, audit_case.created_at, "unban",
                                                 user, mod, reason if reason else None)
                    except RuntimeError as e:
                        print(e)
        else:  # No permissions to view audit logs, so message the guild owner
            owner = guild.owner
            try:
                await owner.send(
                    _("Hi, I noticed that someone in your server "
                    "(the server named {}) unbanned {}#{} (user ID {}). "
                    "However, I don't have permissions to view audit logs, "
                    "so I could not determine if a mod log case was created "
                    "for that unban, meaning I could not create a case in "
                    "the mod log. If you want me to be able to add cases "
                    "to the mod log for unbans done manually, I need the "
                    "`View Audit Logs` permission.").format(
                        guild.name,
                        user.name,
                        user.discriminator,
                        user.id
                    )
                )
            except discord.Forbidden:
                log.warning(
                    "I attempted to inform a guild owner of a lack of the "
                    "'View Audit Log' permission but I am unable to send "
                    "the guild owner the message!"
                )
            except discord.HTTPException:
                log.warning(
                    "Something else went wrong while attempting to "
                    "message a guild owner."
                )

    async def on_member_update(self, before, after):
        if before.name != after.name:
            name_list = await self.settings.user(before).past_names()
            if after.name not in name_list:
                names = deque(name_list, maxlen=20)
                names.append(after.name)
                await self.settings.user(before).past_names.set(list(names))

        if before.nick != after.nick and after.nick is not None:
            nick_list = await self.settings.member(before).past_nicks()
            nicks = deque(nick_list, maxlen=20)
            if after.nick not in nicks:
                nicks.append(after.nick)
                await self.settings.member(before).past_nicks.set(list(nicks))

    @staticmethod
    def are_overwrites_empty(overwrites):
        """There is currently no cleaner way to check if a
        PermissionOverwrite object is empty"""
        return [p for p in iter(overwrites)] ==\
               [p for p in iter(discord.PermissionOverwrite())]


mute_unmute_issues = {
    "already_muted": "That user can't send messages in this channel.",
    "already_unmuted": "That user isn't muted in this channel!",
    "hierarchy_problem": "I cannot let you do that. You are not higher than "
                         "the user in the role hierarchy.",
    "permissions_issue": "Failed to mute user. I need the manage roles "
                         "permission and the user I'm muting must be "
                         "lower than myself in the role hierarchy."
}