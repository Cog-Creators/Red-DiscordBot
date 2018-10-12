# needs a lot more work + upgrades.
import discord
import asyncio
from typing import cast

from redbot.core import commands, checks, modlog
from .checks import mod_or_voice_permissions, bot_has_voice_permissions
from redbot.core.i18n import Translator

_ = T_ = Translator("Mod", __file__)


class MuteMixin:
    """
    Handles mute related things for mod cog
    """

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def mute(self, ctx: commands.Context):
        """Mute users."""
        pass

    @mute.command(name="voice")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def voice_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mute a user in their current voice channel."""
        user_voice_state = user.voice
        guild = ctx.guild
        author = ctx.author
        if user_voice_state:
            channel = user_voice_state.channel
            if channel:
                audit_reason = self.get_audit_reason(author, reason)

                success, issue = await self.mute_user(guild, channel, author, user, audit_reason)

                if success:
                    await ctx.send(
                        _("Muted {user} in channel {channel.name}").format(
                            user=user, channel=channel
                        )
                    )
                    try:
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
                    except RuntimeError as e:
                        await ctx.send(e)
                else:
                    await channel.send(issue)
            else:
                await ctx.send(_("That user is not in a voice channel right now!"))
        else:
            await ctx.send(_("No voice state for the target!"))
            return

    @mute.command(name="channel")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(administrator=True)
    async def channel_mute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Mute a user in the current text channel."""
        author = ctx.message.author
        channel = ctx.message.channel
        guild = ctx.guild
        audit_reason = self.get_audit_reason(author, reason)

        success, issue = await self.mute_user(guild, channel, author, user, audit_reason)

        if success:
            await channel.send(_("User has been muted in this channel."))
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
        else:
            await channel.send(issue)

    @mute.command(name="server", aliases=["guild"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(administrator=True)
    async def guild_mute(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Mutes user in the server"""
        author = ctx.message.author
        guild = ctx.guild
        audit_reason = self.get_audit_reason(author, reason)

        mute_success = []
        for channel in guild.channels:
            success, issue = await self.mute_user(guild, channel, author, user, audit_reason)
            mute_success.append((success, issue))
            await asyncio.sleep(0.1)
        await ctx.send(_("User has been muted in this server."))
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
            return False, T_(mute_unmute_issues["is_admin"])

        new_overs = {}
        if not isinstance(channel, discord.TextChannel):
            new_overs.update(speak=False)
        if not isinstance(channel, discord.VoiceChannel):
            new_overs.update(send_messages=False, add_reactions=False)

        if all(getattr(permissions, p) is False for p in new_overs.keys()):
            return False, T_(mute_unmute_issues["already_muted"])

        elif not await self.is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            return False, T_(mute_unmute_issues["hierarchy_problem"])

        old_overs = {k: getattr(overwrites, k) for k in new_overs}
        overwrites.update(**new_overs)
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, T_(mute_unmute_issues["permissions_issue"])
        else:
            await self.settings.member(user).set_raw(
                "perms_cache", str(channel.id), value=old_overs
            )
            return True, None

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(manage_channel=True)
    async def unmute(self, ctx: commands.Context):
        """Unmute users."""
        pass

    @unmute.command(name="voice")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def unmute_voice(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmute a user in their current voice channel."""
        user_voice_state = user.voice
        guild = ctx.guild
        author = ctx.author
        if user_voice_state:
            channel = user_voice_state.channel
            if channel:
                audit_reason = self.get_audit_reason(author, reason)

                success, message = await self.unmute_user(
                    guild, channel, author, user, audit_reason
                )

                if success:
                    await ctx.send(
                        _("Unmuted {user} in channel {channel.name}").format(
                            user=user, channel=channel
                        )
                    )
                    try:
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
                    except RuntimeError as e:
                        await ctx.send(e)
                else:
                    await ctx.send(_("Unmute failed. Reason: {}").format(message))
            else:
                await ctx.send(_("That user is not in a voice channel right now!"))
        else:
            await ctx.send(_("No voice state for the target!"))
            return

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="channel")
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute_channel(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmute a user in this channel."""
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        audit_reason = self.get_audit_reason(author, reason)

        success, message = await self.unmute_user(guild, channel, author, user, audit_reason)

        if success:
            await ctx.send(_("User unmuted in this channel."))
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
        else:
            await ctx.send(_("Unmute failed. Reason: {}").format(message))

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="server", aliases=["guild"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute_guild(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmute a user in this server."""
        guild = ctx.guild
        author = ctx.author
        audit_reason = self.get_audit_reason(author, reason)

        unmute_success = []
        for channel in guild.channels:
            success, message = await self.unmute_user(guild, channel, author, user, audit_reason)
            unmute_success.append((success, message))
            await asyncio.sleep(0.1)
        await ctx.send(_("User has been unmuted in this server."))
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
            )
        except RuntimeError as e:
            await ctx.send(e)

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
            return False, T_(mute_unmute_issues["already_unmuted"])

        elif not await self.is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            return False, T_(mute_unmute_issues["hierarchy_problem"])

        overwrites.update(**old_values)
        try:
            if overwrites.is_empty():
                await channel.set_permissions(
                    user, overwrite=cast(discord.PermissionOverwrite, None), reason=reason
                )
            else:
                await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, T_(mute_unmute_issues["permissions_issue"])
        else:
            await self.settings.member(user).clear_raw("perms_cache", str(channel.id))
            return True, None


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
