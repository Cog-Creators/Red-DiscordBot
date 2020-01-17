import asyncio
import datetime
import json
import logging
import time
from typing import cast

import discord
import lavalink

from redbot.cogs.audio.apis.interface import AudioAPIInterface
from redbot.cogs.audio.apis.playlist_interface import get_all_playlist_for_migration23
from redbot.cogs.audio.audio_globals import update_audio_globals
from redbot.cogs.audio.cog import MixinMeta
from redbot.cogs.audio.cog.utils import CompositeMetaClass, _SCHEMA_VERSION
from redbot.cogs.audio.errors import LavalinkDownloadFailed
from redbot.cogs.audio.manager import ServerManager
from redbot.cogs.audio.utils import PlaylistScope

log = logging.getLogger("red.cogs.Audio.cog.Tasks")


class Tasks(MixinMeta, metaclass=CompositeMetaClass):
    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        # Unlike most cases, we want the cache to exit before migration.
        try:
            (
                _black_hole,
                _black_hole,
                _black_hole,
                _black_hole,
                _playlist_api,
            ) = await update_audio_globals(self.config, self.bot, await self.config.localpath())
            self.api_interface = AudioAPIInterface(self.session)
            await self.api_interface.initialize()
            await self._migrate_config(
                from_version=await self.config.schema_version(), to_version=_SCHEMA_VERSION
            )
            if _playlist_api:
                await _playlist_api.delete_scheduled()
            self._restart_connect()
            self._disconnect_task = self.bot.loop.create_task(self.disconnect_timer())
            lavalink.register_event_listener(self.event_handler)
        except Exception as err:
            log.exception("Audio failed to start up, please report this issue.", exc_info=err)
            raise err

        self._ready_event.set()

    async def _migrate_config(self, from_version: int, to_version: int) -> None:
        database_entries = []
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if from_version == to_version:
            return
        if from_version < 2 <= to_version:
            all_guild_data = await self.config.all_guilds()
            all_playlist = {}
            for (guild_id, guild_data) in all_guild_data.items():
                temp_guild_playlist = guild_data.pop("playlists", None)
                if temp_guild_playlist:
                    guild_playlist = {}
                    for (count, (name, data)) in enumerate(temp_guild_playlist.items(), 1):
                        if not data or not name:
                            continue
                        playlist = {"id": count, "name": name, "guild": int(guild_id)}
                        playlist.update(data)
                        guild_playlist[str(count)] = playlist

                        tracks_in_playlist = data.get("tracks", []) or []
                        for t in tracks_in_playlist:
                            uri = t.get("info", {}).get("uri")
                            if uri:
                                t = {"loadType": "V2_COMPAT", "tracks": [t], "query": uri}
                                data = json.dumps(t)
                                if all(
                                    k in data
                                    for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]
                                ):
                                    database_entries.append(
                                        {
                                            "query": uri,
                                            "data": data,
                                            "last_updated": time_now,
                                            "last_fetched": time_now,
                                        }
                                    )
                        await asyncio.sleep(0)
                    if guild_playlist:
                        all_playlist[str(guild_id)] = guild_playlist
                await asyncio.sleep(0)
            await self.config.custom(PlaylistScope.GUILD.value).set(all_playlist)
            # new schema is now in place
            await self.config.schema_version.set(_SCHEMA_VERSION)

            # migration done, now let's delete all the old stuff
            for guild_id in all_guild_data:
                await self.config.guild(
                    cast(discord.Guild, discord.Object(id=guild_id))
                ).clear_raw("playlists")
        if from_version < 3 <= to_version:
            for scope in PlaylistScope.list():
                scope_playlist = await get_all_playlist_for_migration23(scope)
                for p in scope_playlist:
                    await p.save()
                await self.config.custom(scope).clear()
            await self.config.schema_version.set(_SCHEMA_VERSION)

        if database_entries:
            await self.api_interface.local_cache_api.lavalink.insert(database_entries)

    def _restart_connect(self) -> None:
        if self._connect_task:
            self._connect_task.cancel()

        self._connect_task = self.bot.loop.create_task(self.attempt_connect())

    async def attempt_connect(self, timeout: int = 50) -> None:
        self._connection_aborted = False
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            external = await self.config.use_external_lavalink()
            if external is False:
                settings = self._default_lavalink_settings
                host = settings["host"]
                password = settings["password"]
                rest_port = settings["rest_port"]
                ws_port = settings["ws_port"]
                if self._manager is not None:
                    await self._manager.shutdown()
                self._manager = ServerManager()
                try:
                    await self._manager.start()
                except LavalinkDownloadFailed as exc:
                    await asyncio.sleep(1)
                    if exc.should_retry:
                        log.exception(
                            "Exception whilst starting internal Lavalink server, retrying...",
                            exc_info=exc,
                        )
                        retry_count += 1
                        continue
                    else:
                        log.exception(
                            "Fatal exception whilst starting internal Lavalink server, "
                            "aborting...",
                            exc_info=exc,
                        )
                        self._connection_aborted = True
                        raise
                except asyncio.CancelledError:
                    log.exception("Invalid machine architecture, cannot run Lavalink.")
                    raise
                except Exception as exc:
                    log.exception(
                        "Unhandled exception whilst starting internal Lavalink server, "
                        "aborting...",
                        exc_info=exc,
                    )
                    self._connection_aborted = True
                    raise
                else:
                    break
            else:
                host = await self.config.host()
                password = await self.config.password()
                rest_port = await self.config.rest_port()
                ws_port = await self.config.ws_port()
                break
        else:
            log.critical(
                "Setting up the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )
            self._connection_aborted = True
            return

        retry_count = 0
        while retry_count < max_retries:
            try:
                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    rest_port=rest_port,
                    ws_port=ws_port,
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                log.error("Connecting to Lavalink server timed out, retrying...")
                if external is False and self._manager is not None:
                    await self._manager.shutdown()
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink, aborting...", exc_info=exc
                )
                self._connection_aborted = True
                raise
            else:
                break
        else:
            self._connection_aborted = True
            log.critical(
                "Connecting to the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )

    async def disconnect_timer(self):
        stop_times = {}
        pause_times = {}
        while True:
            for p in lavalink.all_players():
                server = p.channel.guild

                if [self.bot.user] == p.channel.members:
                    stop_times.setdefault(server.id, time.time())
                    pause_times.setdefault(server.id, time.time())
                else:
                    stop_times.pop(server.id, None)
                    if p.paused and server.id in pause_times:
                        try:
                            await p.pause(False)
                        except Exception:
                            log.error(
                                "Exception raised in Audio's emptypause_timer.", exc_info=True
                            )
                    pause_times.pop(server.id, None)
            servers = stop_times.copy()
            servers.update(pause_times)
            for sid in servers:
                server_obj = self.bot.get_guild(sid)
                if sid in stop_times and await self.config.guild(server_obj).emptydc_enabled():
                    emptydc_timer = await self.config.guild(server_obj).emptydc_timer()
                    if (time.time() - stop_times[sid]) >= emptydc_timer:
                        stop_times.pop(sid)
                        try:
                            player = lavalink.get_player(sid)
                            await player.stop()
                            await player.disconnect()
                        except Exception as err:
                            log.error("Exception raised in Audio's emptydc_timer.", exc_info=True)
                            if "No such player for that guild" in str(err):
                                stop_times.pop(sid, None)
                elif (
                    sid in pause_times and await self.config.guild(server_obj).emptypause_enabled()
                ):
                    emptypause_timer = await self.config.guild(server_obj).emptypause_timer()
                    if (time.time() - pause_times.get(sid)) >= emptypause_timer:
                        try:
                            await lavalink.get_player(sid).pause()
                        except Exception as err:
                            if "No such player for that guild" in str(err):
                                pause_times.pop(sid, None)
                            log.error(
                                "Exception raised in Audio's emptypause_timer.", exc_info=True
                            )
            await asyncio.sleep(5)
