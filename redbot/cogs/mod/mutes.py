import asyncio
import logging
from typing import cast, Optional, Union

import discord
from redbot.core import commands, checks, i18n, modlog
from redbot.core.utils.chat_formatting import format_perms_list
from redbot.core.utils.mod import get_audit_reason, is_allowed_by_hierarchy
from .abc import MixinMeta

log = logging.getLogger("red.mod.mutes")

T_ = i18n.Translator("Mod", __file__)

_ = lambda s: s
mute_unmute_issues = {
    "already_muted": _("That user can't send messages in this channel."),
    "already_unmuted": _("That user isn't muted in this channel."),
    "hierarchy_problem": _(
        "I cannot let you do that. You are not higher than the user in the role hierarchy."
    ),
    "is_admin": _("That user cannot be muted, as they have the Administrator permission."),
    "permissions_issue": _(
        "Failed to mute user. I need the manage roles "
        "permission and the user I'm muting must be "
        "lower than myself in the role hierarchy."
    ),
}
_ = T_


class MuteMixin(MixinMeta):
    """
    Stuff for mutes goes here
    """

    @staticmethod
    async def _voice_perm_check(
        ctx: commands.Context, user_voice_state: Optional[discord.VoiceState], **perms: bool
    ) -> bool:
        """Check if the bot and user have sufficient permissions for voicebans.

        This also verifies that the user's voice state and connected
        channel are not ``None``.

        Returns
        -------
        bool
            ``True`` if the permissions are sufficient and the user has
            a valid voice state.

        """
        if user_voice_state is None or user_voice_state.channel is None:
            await ctx.send(_("That user is not in a voice channel."))
            return False
        voice_channel: discord.VoiceChannel = user_voice_state.channel
        required_perms = discord.Permissions()
        required_perms.update(**perms)
        if not voice_channel.permissions_for(ctx.me) >= required_perms:
            await ctx.send(
                _("I require the {perms} permission(s) in that user's channel to do that.").format(
                    perms=format_perms_list(required_perms)
                )
            )
            return False
        if (
            ctx.permission_state is commands.PermState.NORMAL
            and not voice_channel.permissions_for(ctx.author) >= required_perms
        ):
            await ctx.send(
                _(
                    "You must have the {perms} permission(s) in that user's channel to use this "
                    "command."
                ).format(perms=format_perms_list(required_perms))
            )
            return False
        return True

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Unban a user from speaking and listening in the server's voice channels."""
        user_voice_state = user.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
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
            await ctx.send(_("That user isn't muted or deafened by the server!"))
            return

        guild = ctx.guild
        author = ctx.author
        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "voiceunban",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)
        await ctx.send(_("User is now allowed to speak and listen in voice channels"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(mute_members=True, deafen_members=True)
    async def voiceban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Ban a user from speaking and listening in the server's voice channels."""
        user_voice_state: discord.VoiceState = user.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
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
            await ctx.send(_("That user is already muted and deafened server-wide!"))
            return

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "voiceban",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)
        await ctx.send(_("User has been banned from speaking or listening in voice channels"))

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def mute(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
        *,
        reason: str = None,
    ):
        """Mute users."""
        if not ctx.invoked_subcommand:
            if isinstance(channel, discord.CategoryChannel):
                command = self.category_mute
            else:
                command = self.channel_mute
            await ctx.invoke(command, user=user, channel=channel, reason=reason)

    @mute.command(name="channel")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(administrator=True)
    async def channel_mute(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: Optional[discord.TextChannel] = None,
        *,
        reason: str = None,
    ):
        """Mute a user in the current text channel."""
        author = ctx.message.author
        channel = channel or ctx.message.channel
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)

        success, issue = await self.mute_user(guild, channel, author, user, audit_reason)

        if success:
            try:
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at,
                    "cmute",
                    user,
                    author,
                    reason,
                    until=None,
                    channel=channel,
                )
            except RuntimeError as e:
                await ctx.send(e)
            await channel.send(
                _("{user} has been muted in channel {channel}").format(user=user, channel=channel)
            )
        else:
            await channel.send(issue)

    @mute.command(name="category")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(administrator=True)
    async def category_mute(
        self,
        ctx: commands.Context,
        user: discord.Member,
        category: Optional[discord.CategoryChannel] = None,
        *,
        reason: str = None,
    ):
        """Mutes user in the server"""
        author = ctx.message.author
        category = category or ctx.message.category
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)

        if not category:
            channels = (c for c in guild.channels if not c.category and c not in guild.categories)
        else:
            channels = category.channels

        mute_success = {}
        for channel in channels:
            mute_success[channel] = await self.mute_user(
                guild, channel, author, user, audit_reason
            )
            await asyncio.sleep(0.1)

        to_log = "\n".join(
            f"{k.name} ({k.id}): {v[1]}" for k, v in mute_success.items() if not v[0]
        )
        if to_log:
            log.info(to_log)

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "catmute",
                user,
                author,
                reason,
                until=None,
                channel=category,
            )
        except RuntimeError as e:
            await ctx.send(e)

        await ctx.send(
            _(
                "{user} has been muted in {success} / {total} channels in category {category}."
            ).format(
                user=user,
                success=sum(1 for v in mute_success.values() if v[0]),
                total=len(mute_success),
                category=category,
            )
        )

    @mute.command(name="server", aliases=["guild"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(administrator=True)
    async def guild_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mutes user in the server"""
        author = ctx.message.author
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)

        # try categories first, to reduce API calls for synced channels
        channels = guild.categories
        channels += [c for c in guild.channels if c not in guild.categories]

        mute_success = {}
        for channel in guild.categories + guild.channels:
            mute_success[channel] = await self.mute_user(
                guild, channel, author, user, audit_reason
            )
            await asyncio.sleep(0.1)

        to_log = "\n".join(
            f"{k.name} ({k.id}): {v[1]}" for k, v in mute_success.items() if not v[0]
        )
        if to_log:
            log.info(to_log)

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "smute",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

        await ctx.send(
            _(
                "{user} has been muted in {success} / {total} channels in this server."
            ).format(
                user=user,
                success=sum(1 for v in mute_success.values() if v[0]),
                total=len(mute_success),
            )
        )

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(administrator=True)
    async def unmute(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: Union[discord.TextChannel, discord.CategoryChannel, None] = None,
        *,
        reason: str = None,
    ):
        """
        Unmutes user in the channel/server

        Defaults to channel
        """
        if not ctx.invoked_subcommand:
            if isinstance(channel, discord.CategoryChannel):
                command = self.category_unmute
            else:
                command = self.channel_unmute
            await ctx.invoke(command, user=user, channel=channel, reason=reason)

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="channel")
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def channel_unmute(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: Optional[discord.TextChannel] = None,
        *,
        reason: str = None,
    ):
        """Unmute a user in this channel."""
        channel = channel or ctx.channel
        author = ctx.author
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)

        success, issue = await self.unmute_user(guild, channel, author, user, audit_reason)

        if success:
            try:
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at,
                    "cunmute",
                    user,
                    author,
                    reason,
                    until=None,
                    channel=channel,
                )
            except RuntimeError as e:
                await ctx.send(e)
            await ctx.send(_("{user} has been unmuted in channel {channel}.").format(user=user, channel=channel))
        else:
            await ctx.send(issue)

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="category")
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def category_unmute(
        self, ctx: commands.Context, user: discord.Member, category: Optional[discord.CategoryChannel] = None, *, reason: str = None
    ):
        """Unmute a user in this server."""
        guild = ctx.guild
        category = category or ctx.message.category
        author = ctx.author
        audit_reason = get_audit_reason(author, reason)

        if not category:
            channels = (c for c in guild.channels if not c.category and c not in guild.categories)
        else:
            channels = category.channels

        unmute_success = {}
        for channel in channels:
            unmute_success[channel] = await self.unmute_user(guild, channel, author, user, audit_reason)
            await asyncio.sleep(0.1)

        to_log = "\n".join(
            f"{k.name} ({k.id}): {v[1]}" for k, v in unmute_success.items() if not v[0]
        )
        if to_log:
            log.info(to_log)

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "sunmute",
                user,
                author,
                reason,
                until=None,
                channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

        await ctx.send(
            _(
                "{user} has been muted in {success} / {total} channels in category {category}."
            ).format(
                user=user,
                success=sum(1 for v in unmute_success.values() if v[0]),
                total=len(unmute_success),
                category=category,
            )
        )

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="server", aliases=["guild"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def guild_unmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmute a user in this server."""
        guild = ctx.guild
        author = ctx.author
        audit_reason = get_audit_reason(author, reason)

        # try categories first, to reduce API calls for synced channels
        channels = guild.categories
        channels += [c for c in guild.channels if c not in guild.categories]

        unmute_success = {}
        for channel in guild.channels:
            unmute_success[channel] = await self.unmute_user(guild, channel, author, user, audit_reason)
            await asyncio.sleep(0.1)

        to_log = "\n".join(
            f"{k.name} ({k.id}): {v[1]}" for k, v in unmute_success.items() if not v[0]
        )
        if to_log:
            log.info(to_log)

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "sunmute",
                user,
                author,
                reason,
                until=None,
                channel=None
            )
        except RuntimeError as e:
            await ctx.send(e)

        await ctx.send(
            _(
                "{user} has been muted in {success} / {total} channels in this server."
            ).format(
                user=user,
                success=sum(1 for v in unmute_success.values() if v[0]),
                total=len(unmute_success),
            )
        )

    async def mute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        reason: str,
    ) -> (bool, str):
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)

        if permissions.administrator:
            return False, _(mute_unmute_issues["is_admin"])

        new_overs = {}
        if not isinstance(channel, discord.TextChannel):
            new_overs.update(speak=False)
        if not isinstance(channel, discord.VoiceChannel):
            new_overs.update(send_messages=False, add_reactions=False)

        if all(getattr(permissions, p) is False for p in new_overs.keys()):
            return False, _(mute_unmute_issues["already_muted"])

        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            return False, _(mute_unmute_issues["hierarchy_problem"])

        old_overs = {k: getattr(overwrites, k) for k in new_overs}
        overwrites.update(**new_overs)
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, _(mute_unmute_issues["permissions_issue"])
        else:
            await self.settings.member(user).set_raw(
                "perms_cache", str(channel.id), value=old_overs
            )
            return True, None

    async def unmute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        reason: str,
    ) -> (bool, str):
        overwrites = channel.overwrites_for(user)
        perms_cache = await self.settings.member(user).perms_cache()

        if channel.id in perms_cache:
            old_values = perms_cache[channel.id]
        else:
            old_values = {"send_messages": None, "add_reactions": None, "speak": None}

        if all(getattr(overwrites, k) == v for k, v in old_values.items()):
            return False, _(mute_unmute_issues["already_unmuted"])

        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            return False, _(mute_unmute_issues["hierarchy_problem"])

        overwrites.update(**old_values)
        try:
            if overwrites.is_empty():
                await channel.set_permissions(
                    user, overwrite=cast(discord.PermissionOverwrite, None), reason=reason
                )
            else:
                await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, _(mute_unmute_issues["permissions_issue"])
        else:
            await self.settings.member(user).clear_raw("perms_cache", str(channel.id))
            return True, None
