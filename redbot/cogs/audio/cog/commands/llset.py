import logging

import discord

from redbot.cogs.audio.cog import MixinMeta
from redbot.core import commands, checks

from ..utils import _

log = logging.getLogger("red.cogs.Audio.cog.commands.LavalinkSet")


class LavalinkSetCommands(MixinMeta):
    """
    All LavalinkSet commands.
    """

    @commands.group(aliases=["llset"])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @checks.is_owner()
    async def llsetup(self, ctx: commands.Context):
        """Lavalink server configuration options."""

    @llsetup.command()
    async def external(self, ctx: commands.Context):
        """Toggle using external lavalink servers."""
        external = await self.config.use_external_lavalink()
        await self.config.use_external_lavalink.set(not external)

        if external:
            embed = discord.Embed(
                title=_("Setting Changed"),
                description=_("External lavalink server: {true_or_false}.").format(
                    true_or_false=_("Enabled") if not external else _("Disabled")
                ),
            )
            await self._embed_msg(ctx, embed=embed)
        else:
            if self._manager is not None:
                await self._manager.shutdown()
            await self._embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("External lavalink server: {true_or_false}.").format(
                    true_or_false=_("Enabled") if not external else _("Disabled")
                ),
            )

        self._restart_connect()

    @llsetup.command()
    async def host(self, ctx: commands.Context, host: str):
        """Set the lavalink server host."""
        await self.config.host.set(host)
        footer = None
        if await self._check_external():
            footer = _("External lavalink server set to True.")
        await self._embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Host set to {host}.").format(host=host),
            footer=footer,
        )
        self._restart_connect()

    @llsetup.command()
    async def password(self, ctx: commands.Context, password: str):
        """Set the lavalink server password."""
        await self.config.password.set(str(password))
        footer = None
        if await self._check_external():
            footer = _("External lavalink server set to True.")
        await self._embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Server password set to {password}.").format(password=password),
            footer=footer,
        )

        self._restart_connect()

    @llsetup.command()
    async def restport(self, ctx: commands.Context, rest_port: int):
        """Set the lavalink REST server port."""
        await self.config.rest_port.set(rest_port)
        footer = None
        if await self._check_external():
            footer = _("External lavalink server set to True.")
        await self._embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("REST port set to {port}.").format(port=rest_port),
            footer=footer,
        )

        self._restart_connect()

    @llsetup.command()
    async def wsport(self, ctx: commands.Context, ws_port: int):
        """Set the lavalink websocket server port."""
        await self.config.ws_port.set(ws_port)
        footer = None
        if await self._check_external():
            footer = _("External lavalink server set to True.")
        await self._embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Websocket port set to {port}.").format(port=ws_port),
            footer=footer,
        )

        self._restart_connect()
