import re
from io import BytesIO
from pathlib import Path

import discord
import yaml
from discord.ext.commands import BadArgument
from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ...utils import MAX_JAVA_RAM, DEFAULT_YAML_VALUES, DEFAULT_LAVALINK_SETTINGS

log = getLogger("red.cogs.Audio.cog.Commands.lavalink_setup")
_ = Translator("Audio", Path(__file__))


class LavalinkSetupCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="llsetup", aliases=["llset"])
    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    async def command_llsetup(self, ctx: commands.Context):
        """**[Dangerous commands]** Manage Lavalink node configuration settings.

        This command block holds all commands to manage an external or managed Lavalink node.

        You should not mess with any command in here unless you have a valid reason to,
        i.e. been told by someone in support to do so. All the commands in here have the potential to break the Audio Cog.
        """

    @command_llsetup.command(name="java")
    async def command_llsetup_java(self, ctx: commands.Context, *, java_path: str = "java"):
        """Change your Java executable path - Only applicable if using a managed Lavalink instance.

        This command shouldn't need to be used most of the time, and is only useful if the host machine has conflicting Java versions.

        If changing this make sure that the java you set is supported by Audio.
        The current supported version is Java 11.

        Enter nothing or "java" to reset it back to default.
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
        if java_path == "java":
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

    @command_llsetup.command(name="heapsize", aliases=["hs"])
    async def command_llsetup_heapsize(self, ctx: commands.Context, *, size: int = MAX_JAVA_RAM):
        """Set the Lavalink max heap-size - Only applicable if using a managed Lavalink instance.

        By default, this value is 50% of available RAM in the host machine represented by [1-1024][M|G] (256M, 256G for example)

        This value only represents the maximum amount of RAM allowed to be used at any given point, and does not mean that the managed Lavalink instance will use this value ever.

        To reset this value to the default, run the command without any input.
        """

        def validate_input(arg):
            match = re.match(r"(\d+)([MG])", arg, flags=re.IGNORECASE)
            if not match:
                raise BadArgument("Heap-size must be a valid measure of size, e.g. 256M, 256G")
            if (
                int(match.group(0)) * 1024 ** (2 if match.group(1).lower() == "m" else 3)
                < 64 * 1024 ** 2
            ):
                raise BadArgument(
                    "Heap-size must be at least 64M, however it is recommended to have it set to at least 1G."
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
        """Toggle using external Lavalink servers - Requires an existing external Lavalink server for Audio to work, if enabled.

        This command disables the managed Lavalink server, if you do not have an external Lavalink server you will be unable to use Audio while this is enabled.
        """
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
        """Set the Lavalink server host - Only applicable for external Lavalink nodes.

        This command sets the connection host which Audio will use to connect to an **external** Lavalink server.
        """
        if not (await self.config.use_external_lavalink()):
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are an external node."),
            )

        await self.config.host.set(host)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("External Lavalink node host set to {host}.").format(host=host),
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
        """Set the Lavalink server password - Only applicable for external Lavalink nodes.

        This command sets the connection password which Audio will use to connect to an **external** Lavalink server.
        """

        if not (await self.config.use_external_lavalink()):
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are using an external Lavalink node."),
            )
        await self.config.password.set(str(password))
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("External Lavalink node password set to {password}.").format(
                password=password
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

    @command_llsetup.command(name="port")
    async def command_llsetup_wsport(
        self, ctx: commands.Context, port: int = DEFAULT_LAVALINK_SETTINGS["ws_port"]
    ):
        """Set the Lavalink server port - Only applicable for external Lavalink nodes.

        This command sets the connection port which Audio will use to connect to an **external** Lavalink server.
        """
        if not (await self.config.use_external_lavalink()):
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are using an external Lavalink node."),
            )
        await self.config.ws_port.set(port)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("External Lavalink node port set to {port}.").format(port=port),
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
        msg = "----" + _("Connection Settings") + "----        \n"
        if configs["use_external_lavalink"]:
            msg += _("Host:             [{host}]\n").format(host=configs["host"])
            msg += _("Port:             [{port}]\n").format(port=configs["ws_port"])
            msg += _("Password:         [{password}]\n").format(password=configs["password"])
        if not configs["use_external_lavalink"]:
            msg += _("Host:             [{host}]\n").format(
                host=configs["yaml"]["server"]["address"]
            )
            msg += _("Port:             [{port}]\n").format(port=configs["yaml"]["server"]["port"])
            msg += _("Password:         [{password}]\n").format(
                password=configs["yaml"]["server"]["lavalink"]["password"]
            )
            msg += _("Xms:              [{xms}]\n").format(xms=configs["java"]["Xms"])
            msg += _("Xmx:              [{xmx}]\n").format(xmx=configs["java"]["Xmx"])
            msg += _("Java exec:        [{java_exc_path}]\n").format(
                java_exc_path=configs["java_exc_path"]
            )

        try:
            await self.send_embed_msg(ctx.author, description=box(msg, lang="ini"))
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you this info."))

    @command_llsetup.command(name="yaml", aliases=["yml"])
    async def command_llsetup_yaml(self, ctx: commands.Context):
        """Uploads a copy of the application.yml file used by the managed Lavalink node."""
        configs = await self.config.yaml.all()
        data = yaml.safe_dump(configs)
        playlist_data = data.encode("utf-8")
        to_write = BytesIO()
        to_write.write(playlist_data)
        to_write.seek(0)
        try:
            datapath = cog_data_path(raw_name="Audio")
            temp_file = datapath / f"application.dump.yaml"
            with temp_file.open("wb") as application_file:
                application_file.write(to_write.read())
            await self.send_embed_msg(ctx.author, description=box(data, lang="yaml"))
            await ctx.author.send(
                content=_("Playlist is too large, here is the compressed version."),
                file=discord.File(str(temp_file)),
            )
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you this info."))
        finally:
            temp_file.unlink()

    @command_llsetup.group(name="config", aliases=["conf"])
    async def command_llsetup_config(self, ctx: commands.Context):
        """Configure the managed Lavalink node runtime options - Only applicable if using a managed Lavalink instance.

        All settings under this group will likely cause Audio to malfunction if changed from their defaults, only change settings here if you been advised to by support.
        """

    @command_llsetup_config.group(name="server")
    async def command_llsetup_config_server(self, ctx: commands.Context):
        """Configure the managed node authorization and connection settings."""

    @command_llsetup_config_server.command(name="bind", aliases=["host", "address"])
    async def command_llsetup_config_server_host(
        self, ctx: commands.Context, *, host: str = DEFAULT_YAML_VALUES["yaml__server__address"]
    ):
        """**[Dangerous command]** Set the managed Lavalink node's binding IP address.

        This value by default is `0.0.0.0` which will allow the server to bind to all interfaces by default, changing this will likely break the webserver if you don't know what you are doing.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
            )

        await self.config.yaml.server.address.set(set_to=host)
        host = await self.config.yaml.server.address()
        await self.send_embed_msg(
            ctx,
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
        """Set the managed Lavalink node's connection password.

        This is the password required for Audio to connect to the managed Lavalink node.
        The value by default is `youshallnotpass`.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
            )

        await self.config.yaml.server.lavalink.password.set(set_to=password)
        password = await self.config.yaml.server.lavalink.password()
        await self.send_embed_msg(
            ctx,
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
        """**[Dangerous command]** Set the managed Lavalink node's connection port.

        This port is the port the webserver binds to, you should only change this if there is a conflict with the default port because you already have an application using port 2333 on this device.

        The value by default is `2333`.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
                "Managed node will now accept connections on {port}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(port=port, p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
        )

    @command_llsetup_config.group(name="source")
    async def command_llsetup_config_source(self, ctx: commands.Context):
        """**[Dangerous command]** Toggle audio sources on/off.

        By default, all sources are enabled, you should only use commands here to disable a specific source if you have been advised to, disabling sources without background knowledge can cause Audio to break.
        """

    @command_llsetup_config_source.command(name="http")
    async def command_llsetup_config_source_http(self, ctx: commands.Context):
        """Toggle HTTP direct URL usage on or off.

        This source is used to allow playback from direct http streams (This does not affect direct url playback for the other sources)
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
        """Toggle Bandcamp source on or off.

        This toggle controls the playback of all Bandcamp related content.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
        """Toggle local file usage on or off.

        This toggle controls the playback of all local track content, usually found inside the `localtracks` folder.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
        """Toggle Soundcloud source on or off.

        This toggle controls the playback of all Soundcloud related content.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
        """**[Dangerous command]** Toggle YouTube source on or off (this includes Spotify).

        This toggle controls the playback of all YouTube and Spotify related content.
        """
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
        """Toggle Twitch source on or off.

        This toggle controls the playback of all Twitch related content.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
        """Toggle Vimeo source on or off.

        This toggle controls the playback of all Vimeo related content.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
        """**[Dangerous command]** Set the managed Lavalink node framebuffer size.

        Only change this if you have been directly advised to, changing it can cause significant playback issues.
        """
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
                description=_("The lowest value the framebuffer can be set to is 100ms."),
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
        """**[Dangerous command]**  Set the managed Lavalink node NAS buffer size.

        Only change this if you have been directly advised to, changing it can cause significant playback issues.
        """
        if await self.config.use_external_lavalink():
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("You are only able to set this if you are running a managed Lavalink node."),
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
