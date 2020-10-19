from typing import Optional
from .abc import MixinMeta

import discord
from redbot.core import commands, checks, i18n, modlog
from redbot.core.utils.chat_formatting import format_perms_list
from redbot.core.utils.mod import get_audit_reason

_ = i18n.Translator("Mutes", __file__)


class VoiceMutes(MixinMeta):
    """
    This handles all voice channel related muting
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
            await ctx.send(_("That user isn't muted or deafened by the server."))
            return

        guild = ctx.guild
        author = ctx.author
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
        await ctx.send(_("User is now allowed to speak and listen in voice channels."))

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
            await ctx.send(_("That user is already muted and deafened server-wide."))
            return

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
        await ctx.send(_("User has been banned from speaking or listening in voice channels."))

    @commands.command(name="voicemute")
    @commands.guild_only()
    async def voice_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mute a user in their current voice channel."""
        user_voice_state = user.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, mute_members=True, manage_channels=True
            )
            is False
        ):
            return
        guild = ctx.guild
        author = ctx.author
        channel = user_voice_state.channel
        audit_reason = get_audit_reason(author, reason)

        success, issue = await self.mute_user(guild, channel, author, user, audit_reason)

        if success["success"]:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "vmute",
                user,
                author,
                reason,
                until=None,
                channel=channel,
            )
            await ctx.send(
                _("Muted {user} in channel {channel.name}").format(user=user, channel=channel)
            )
            try:
                if channel.permissions_for(ctx.me).move_members:
                    await user.move_to(channel)
                else:
                    raise RuntimeError
            except (discord.Forbidden, RuntimeError):
                await ctx.send(
                    _(
                        "Because I don't have the Move Members permission, this will take into effect when the user rejoins."
                    )
                )
        else:
            await ctx.send(issue)

    @commands.command(name="voiceunmute")
    @commands.guild_only()
    async def unmute_voice(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmute a user in their current voice channel."""
        user_voice_state = user.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, mute_members=True, manage_channels=True
            )
            is False
        ):
            return
        guild = ctx.guild
        author = ctx.author
        channel = user_voice_state.channel
        audit_reason = get_audit_reason(author, reason)

        success, message = await self.unmute_user(guild, channel, author, user, audit_reason)

        if success:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "vunmute",
                user,
                author,
                reason,
                until=None,
                channel=channel,
            )
            await ctx.send(
                _("Unmuted {user} in channel {channel.name}").format(user=user, channel=channel)
            )
            try:
                if channel.permissions_for(ctx.me).move_members:
                    await user.move_to(channel)
                else:
                    raise RuntimeError
            except (discord.Forbidden, RuntimeError):
                await ctx.send(
                    _(
                        "Because I don't have the Move Members permission, this will take into effect when the user rejoins."
                    )
                )
        else:
            await ctx.send(_("Unmute failed. Reason: {}").format(message))
