import logging
import asyncio
import contextlib

import discord
from redbot.core import commands, checks, i18n
from redbot.core.utils.chat_formatting import box
from .abc import MixinMeta

log = logging.getLogger("red.mod")
_ = i18n.Translator("Mod", __file__)


# TODO: Empty this to core red.
class MoveToCore(MixinMeta):
    """
    Mixin for things which should really not be in mod, but have not been moved out yet.
    """

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        await self._delete_delay(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # Every message which isn't a command but which
        # starts with a bot prefix is dispatched as a command error
        if not isinstance(error, commands.CommandNotFound):
            await self._delete_delay(ctx)

    async def _delete_delay(self, ctx: commands.Context):
        """Currently used for:
            * delete delay"""
        guild = ctx.guild
        if guild is None:
            return
        message = ctx.message
        delay = await self.settings.guild(guild).delete_delay()

        if delay == -1:
            return

        async def _delete_helper(m):
            with contextlib.suppress(discord.HTTPException):
                await m.delete()
                log.debug("Deleted command msg {}".format(m.id))

        await asyncio.sleep(delay)
        await _delete_helper(message)

    # When the below are moved to core, the global check in .modcore needs to be moved as well.
    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context):
        """Add servers or channels to the ignore list."""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.count_ignored())

    @ignore.command(name="channel")
    async def ignore_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Ignore commands in the channel.

        Defaults to the current channel.
        """
        if not channel:
            channel = ctx.channel
        if not await self.settings.channel(channel).ignored():
            await self.settings.channel(channel).ignored.set(True)
            await ctx.send(_("Channel added to ignore list."))
        else:
            await ctx.send(_("Channel already in ignore list."))

    @ignore.command(name="server", aliases=["guild"])
    @checks.admin_or_permissions(manage_guild=True)
    async def ignore_guild(self, ctx: commands.Context):
        """Ignore commands in this server."""
        guild = ctx.guild
        if not await self.settings.guild(guild).ignored():
            await self.settings.guild(guild).ignored.set(True)
            await ctx.send(_("This server has been added to the ignore list."))
        else:
            await ctx.send(_("This server is already being ignored."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx: commands.Context):
        """Remove servers or channels from the ignore list."""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.count_ignored())

    @unignore.command(name="channel")
    async def unignore_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Remove a channel from ignore the list.

        Defaults to the current channel.
        """
        if not channel:
            channel = ctx.channel

        if await self.settings.channel(channel).ignored():
            await self.settings.channel(channel).ignored.set(False)
            await ctx.send(_("Channel removed from ignore list."))
        else:
            await ctx.send(_("That channel is not in the ignore list."))

    @unignore.command(name="server", aliases=["guild"])
    @checks.admin_or_permissions(manage_guild=True)
    async def unignore_guild(self, ctx: commands.Context):
        """Remove this server from the ignore list."""
        guild = ctx.message.guild
        if await self.settings.guild(guild).ignored():
            await self.settings.guild(guild).ignored.set(False)
            await ctx.send(_("This server has been removed from the ignore list."))
        else:
            await ctx.send(_("This server is not in the ignore list."))

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
