import logging
from pathlib import Path

import discord

from redbot.core import commands
from redbot.core.i18n import Translator

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.lavalink_setup")
_ = Translator("Audio", Path(__file__))


class LavalinkSetupCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="llsetup", aliases=["llset"])
    @commands.is_owner()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_llsetup(self, ctx: commands.Context):
        """Lavalink server configuration options."""

    @command_llsetup.command(name="java")
    async def command_llsetup_java(self, ctx: commands.Context, *, java_path: str = None):
        """Change your Java executable path

        Enter nothing to reset to default.
        """
        external = await self.config.use_external_lavalink()
        if external:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "You cannot changed the Java executable path of "
                    "external Lavalink instances from the Audio Cog."
                ),
            )
        if java_path is None:
            await self.config.java_exc_path.clear()
            await self.send_embed_msg(
                ctx,
                title=_("Java Executable Reset"),
                description=_("Audio will now use `java` to run your Lavalink.jar"),
            )
        else:
            exc = Path(java_path)
            exc_absolute = exc.absolute()
            if not exc.exists() or not exc.is_file():
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Environment"),
                    description=_("`{java_path}` is not a valid executable").format(
                        java_path=exc_absolute
                    ),
                )
            await self.config.java_exc_path.set(exc_absolute)
            await self.send_embed_msg(
                ctx,
                title=_("Java Executable Changed"),
                description=_("Audio will now use `{exc}` to run your Lavalink.jar").format(
                    exc=exc_absolute
                ),
            )
        try:
            if self.player_manager is not None:
                await self.player_manager.shutdown()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_(
                    "For it to take effect please reload " "Audio (`{prefix}reload audio`)."
                ).format(
                    prefix=ctx.prefix,
                ),
            )
        else:
            try:
                self.lavalink_restart_connect()
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title=_("Failed To Shutdown Lavalink"),
                    description=_("Please reload Audio (`{prefix}reload audio`).").format(
                        prefix=ctx.prefix
                    ),
                )

    @command_llsetup.command(name="external")
    async def command_llsetup_external(self, ctx: commands.Context):
        """Toggle using external Lavalink servers."""
        external = await self.config.use_external_lavalink()
        await self.config.use_external_lavalink.set(not external)

        if external:
            embed = discord.Embed(
                title=_("Setting Changed"),
                description=_("External Lavalink server: {true_or_false}.").format(
                    true_or_false=_("Enabled") if not external else _("Disabled")
                ),
            )
            await self.send_embed_msg(ctx, embed=embed)
        else:
            try:
                if self.player_manager is not None:
                    await self.player_manager.shutdown()
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title=_("Failed To Shutdown Lavalink"),
                    description=_(
                        "External Lavalink server: {true_or_false}\n"
                        "For it to take effect please reload "
                        "Audio (`{prefix}reload audio`)."
                    ).format(
                        true_or_false=_("Enabled") if not external else _("Disabled"),
                        prefix=ctx.prefix,
                    ),
                )
            else:
                await self.send_embed_msg(
                    ctx,
                    title=_("Setting Changed"),
                    description=_("External Lavalink server: {true_or_false}.").format(
                        true_or_false=_("Enabled") if not external else _("Disabled")
                    ),
                )
        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_llsetup.command(name="host")
    async def command_llsetup_host(self, ctx: commands.Context, host: str):
        """Set the Lavalink server host."""
        await self.config.host.set(host)
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Host set to {host}.").format(host=host),
            footer=footer,
        )
        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_llsetup.command(name="password")
    async def command_llsetup_password(self, ctx: commands.Context, password: str):
        """Set the Lavalink server password."""
        await self.config.password.set(str(password))
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Server password set to {password}.").format(password=password),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_llsetup.command(name="restport")
    async def command_llsetup_restport(self, ctx: commands.Context, rest_port: int):
        """Set the Lavalink REST server port."""
        await self.config.rest_port.set(rest_port)
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("REST port set to {port}.").format(port=rest_port),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_llsetup.command(name="wsport")
    async def command_llsetup_wsport(self, ctx: commands.Context, ws_port: int):
        """Set the Lavalink websocket server port."""
        await self.config.ws_port.set(ws_port)
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Websocket port set to {port}.").format(port=ws_port),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )
