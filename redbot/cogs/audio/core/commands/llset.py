import re
from pathlib import Path

import discord
from discord.ext.commands import BadArgument
from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ...utils import MAX_JAVA_RAM, DEFAULT_YAML_VALUES, DEFAULT_LAVALINK_SETTINGS

log = getLogger("red.cogs.Audio.cog.Commands.lavalink_setup")
_ = Translator("Audio", Path(__file__))

# TODO: Docstrings
# TODO: Add new configurable values to llset info


class LavalinkSetupCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="llsetup", aliases=["llset"])
    @commands.is_owner()
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
            await self.config.java_exc_path.set(str(exc_absolute))
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
                    "For it to take effect please reload Audio (`{prefix}reload audio`)."
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

    @command_llsetup.command(name="heapsize")
    async def command_llsetup_heapsize(self, ctx: commands.Context, *, size: int = MAX_JAVA_RAM):
        """Set the Lavalink max heap-size."""

        def validate_input(arg):
            match = re.match(r"(\d+)([MG])", arg, flags=re.IGNORECASE)
            if not match:
                raise BadArgument("Heap-size must be a valid measure of size, e.g. 256M, 256G")
            if (
                int(match.group(0)) * 1024 ** (2 if match.group(1).lower() == "m" else 3)
                < 64 * 1024 ** 2
            ):
                raise BadArgument(
                    "Heap-size must be at least 64M, however it is recommended to have it set to at least 1G"
                )

        validate_input(size)
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )
        await self.config.java.Xmx.set(size)
        footer = None
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node's heap-size set to {bytes}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(bytes=size, p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
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
    async def command_llsetup_host(
        self, ctx: commands.Context, host: str = DEFAULT_LAVALINK_SETTINGS["host"]
    ):
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

    @command_llsetup.command(name="password", aliases=["pass", "token"])
    async def command_llsetup_password(
        self, ctx: commands.Context, *, password: str = DEFAULT_LAVALINK_SETTINGS["password"]
    ):
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

    @command_llsetup.command(name="port")
    async def command_llsetup_wsport(
        self, ctx: commands.Context, port: int = DEFAULT_LAVALINK_SETTINGS["ws_port"]
    ):
        """Set the Lavalink websocket server port."""
        await self.config.ws_port.set(port)
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Websocket port set to {port}.").format(port=port),
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

    @command_llsetup.command(name="info", aliases=["settings"])
    async def command_llsetup_info(self, ctx: commands.Context):
        """Display Lavalink connection settings."""
        configs = await self.config.all()
        host = configs["host"]
        password = configs["password"]
        rest_port = configs["rest_port"]
        ws_port = configs["ws_port"]
        msg = "----" + _("Connection Settings") + "----        \n"
        msg += _("Host:             [{host}]\n").format(host=host)
        msg += _("WS Port:          [{port}]\n").format(port=ws_port)
        if ws_port != rest_port and rest_port != 2333:
            msg += _("Rest Port:        [{port}]\n").format(port=rest_port)
        msg += _("Password:         [{password}]\n").format(password=password)
        try:
            await self.send_embed_msg(ctx.author, description=box(msg, lang="ini"))
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you this info."))

    @command_llsetup.group(name="config", aliases=["conf", "yaml"])
    async def command_llsetup_config(self, ctx: commands.Context):
        """Configure the local node runtime options. """

    @command_llsetup_config.group(name="server")
    async def command_llsetup_config_server(self, ctx: commands.Context):
        """Configure the Server authorization and connection settings."""

    @command_llsetup_config_server.command(name="bind", aliases=["host", "address"])
    async def command_llsetup_config_server_host(
        self, ctx: commands.Context, *, host: str = DEFAULT_YAML_VALUES["yaml__server__address"]
    ):
        """Set the server host address.
        Default is: "0.0.0.0"
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        await self.config.yaml.server.address.set(set_to=host)
        host = await self.config.yaml.server.address()
        await self.send_embed_msg(
            ctx.author,
            title=_("Setting Changed"),
            description=_(
                "Managed node will now accept connection on {host}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(host=host, p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
        )

    @command_llsetup_config_server.command(name="token", aliases=["password", "pass"])
    async def command_llsetup_config_server_token(
        self,
        ctx: commands.Context,
        *,
        password: str = DEFAULT_YAML_VALUES["yaml__lavalink__server__password"],
    ):
        """Set the server authorization token.
        Default is: "youshallnotpass"
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        await self.config.yaml.server.lavalink.password.set(set_to=password)
        password = await self.config.yaml.server.lavalink.password()
        await self.send_embed_msg(
            ctx.author,
            title=_("Setting Changed"),
            description=_(
                "Managed node will now accept {password} as the authorization token.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                password=password,
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llsetup_config_server.command(name="port")
    async def command_llsetup_config_server_port(
        self, ctx: commands.Context, *, port: int = DEFAULT_YAML_VALUES["yaml__server__port"]
    ):
        """Set the server connection port.
        Default is: "2333"
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        if 1024 > port or port > 49151:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("The the port must be between 1024 and 49151."),
            )

        await self.config.yaml.server.port.set(set_to=port)
        port = await self.config.yaml.server.port()
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node will now accept connection on {port}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(port=port, p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
        )

    @command_llsetup_config.group(name="source")
    async def command_llsetup_config_source(self, ctx: commands.Context):
        """Toggle audio sources on/off."""

    @command_llsetup_config_source.command(name="http")
    async def command_llsetup_config_source_http(self, ctx: commands.Context):
        """Toggle HTTP direct URL usage on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.server.lavalink.sources.http()
        await self.config.yaml.server.lavalink.sources.http.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from direct URLs.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from direct URLs anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_source.command(name="bandcamp", aliases=["bc"])
    async def command_llsetup_config_source_bandcamp(self, ctx: commands.Context):
        """Toggle Bandcamp source on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.bandcamp.http()
        await self.config.yaml.server.lavalink.sources.bandcamp.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Bandcamp.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Bandcamp anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_source.command(name="local")
    async def command_llsetup_config_source_local(self, ctx: commands.Context):
        """Toggle local file usage on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.server.lavalink.sources.local()
        await self.config.yaml.server.lavalink.sources.local.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from local files.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from local files anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_source.command(name="soundcloud", aliases=["sc"])
    async def command_llsetup_config_source_soundcloud(self, ctx: commands.Context):
        """Toggle Soundcloud source on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.server.lavalink.sources.soundcloud()
        await self.config.yaml.server.lavalink.sources.soundcloud.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Soundcloud.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Soundcloud anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_source.command(name="youtube", aliases=["yt"])
    async def command_llsetup_config_source_youtube(self, ctx: commands.Context):
        """Toggle YouTube source on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.server.lavalink.sources.youtube()
        await self.config.yaml.server.lavalink.sources.youtube.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from YouTube.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from YouTube anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_source.command(name="twitch")
    async def command_llsetup_config_source_twitch(self, ctx: commands.Context):
        """Toggle Twitch source on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.server.lavalink.sources.twitch()
        await self.config.yaml.server.lavalink.sources.twitch.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Twitch.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Twitch anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_source.command(name="vimeo")
    async def command_llsetup_config_source_vimeo(self, ctx: commands.Context):
        """Toggle Vimeo source on or off."""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )

        state = await self.config.yaml.server.lavalink.sources.vimeo()
        await self.config.yaml.server.lavalink.sources.vimeo.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Vimeo.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Vimeo anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llsetup_config_server.command(name="framebuffer", aliases=["fb", "frame"])
    async def command_llsetup_config_server_framebuffer(
        self,
        ctx: commands.Context,
        *,
        milliseconds: int = DEFAULT_YAML_VALUES["yaml__lavalink__server__frameBufferDurationMs"],
    ):
        """Set the server framebuffer"""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )
        if milliseconds < 100:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("The lowest value the framebuffer may be is 100ms."),
            )
        await self.config.yaml.lavalink.frameBufferDurationMs.set(set_to=milliseconds)
        port = await self.config.yaml.server.lavalink.frameBufferDurationMs()
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node's bufferDurationMs set to {port}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(port=port, p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
        )

    @command_llsetup_config_server.command(name="buffer", aliases=["b"])
    async def command_llsetup_config_server_buffer(
        self,
        ctx: commands.Context,
        *,
        milliseconds: int = DEFAULT_YAML_VALUES["yaml__lavalink__server__bufferDurationMs"],
    ):
        """Set the server NAS buffer"""
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed node."),
            )
        if milliseconds < 100:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("The lowest value the buffer may be is 100ms."),
            )
        await self.config.yaml.lavalink.bufferDurationMs.set(set_to=milliseconds)
        port = await self.config.yaml.server.lavalink.bufferDurationMs()
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node's bufferDurationMs set to {port}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(port=port, p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
        )

    @command_llsetup.command(name="reset")
    async def command_llsetup_reset(self, ctx: commands.Context):
        """Reset all `llset` changes back to their default values."""

        async with await self.config.all() as global_data:
            global_data.update(DEFAULT_LAVALINK_SETTINGS)
            global_data.update(DEFAULT_YAML_VALUES)
            del global_data["java_exc_path"]
            global_data["use_external_lavalink"] = False

        try:
            if self.player_manager is not None:
                await self.player_manager.shutdown()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_(
                    "For it to take effect please reload Audio (`{prefix}reload audio`)."
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
