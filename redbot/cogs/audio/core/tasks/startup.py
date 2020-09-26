import asyncio
import datetime
import itertools
import logging

from typing import Optional

import lavalink

from redbot.core.data_manager import cog_data_path
from redbot.core.utils._internal_utils import send_to_owners_with_prefix_replaced
from redbot.core.utils.dbtools import APSWConnectionWrapper

from ...apis.interface import AudioAPIInterface
from ...apis.playlist_wrapper import PlaylistWrapper
from ...audio_logging import debug_exc_log
from ...utils import task_callback
from ..abc import MixinMeta
from ..cog_utils import _, _OWNER_NOTIFICATION, _SCHEMA_VERSION, CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.startup")


class StartUpTasks(MixinMeta, metaclass=CompositeMetaClass):
    def start_up_task(self):
        # There has to be a task since this requires the bot to be ready
        # If it waits for ready in startup, we cause a deadlock during initial load
        # as initial load happens before the bot can ever be ready.
        self.cog_init_task = self.bot.loop.create_task(self.initialize())
        self.cog_init_task.add_done_callback(task_callback)

    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        # Unlike most cases, we want the cache to exit before migration.
        try:
            await self.maybe_message_all_owners()
            self.db_conn = APSWConnectionWrapper(
                str(cog_data_path(self.bot.get_cog("Audio")) / "Audio.db")
            )
            self.api_interface = AudioAPIInterface(
                self.bot, self.config, self.session, self.db_conn, self.bot.get_cog("Audio")
            )
            self.playlist_api = PlaylistWrapper(self.bot, self.config, self.db_conn)
            await self.playlist_api.init()
            await self.api_interface.initialize()
            self.global_api_user = await self.api_interface.global_cache_api.get_perms()
            await self.data_schema_migration(
                from_version=await self.config.schema_version(), to_version=_SCHEMA_VERSION
            )
            await self.playlist_api.delete_scheduled()
            await self.api_interface.persistent_queue_api.delete_scheduled()
            self.lavalink_restart_connect()
            self.player_automated_timer_task = self.bot.loop.create_task(
                self.player_automated_timer()
            )
            self.player_automated_timer_task.add_done_callback(task_callback)
            lavalink.register_event_listener(self.lavalink_event_handler)
            await self.restore_players()
        except Exception as err:
            log.exception("Audio failed to start up, please report this issue.", exc_info=err)
            raise err

        self.cog_ready_event.set()

    async def restore_players(self):
        tries = 0
        tracks_to_restore = await self.api_interface.persistent_queue_api.fetch_all()
        for guild_id, track_data in itertools.groupby(tracks_to_restore, key=lambda x: x.guild_id):
            await asyncio.sleep(0)
            try:
                player: Optional[lavalink.Player]
                track_data = list(track_data)
                guild = self.bot.get_guild(guild_id)
                persist_cache = self._persist_queue_cache.setdefault(
                    guild_id, await self.config.guild(guild).persist_queue()
                )
                if not persist_cache:
                    await self.api_interface.persistent_queue_api.drop(guild_id)
                    continue
                if self.lavalink_connection_aborted:
                    player = None
                else:
                    try:
                        player = lavalink.get_player(guild_id)
                    except IndexError:
                        player = None
                    except KeyError:
                        player = None

                vc = 0
                if player is None:
                    while tries < 25 and vc is not None:
                        try:
                            vc = guild.get_channel(track_data[-1].room_id)
                            await lavalink.connect(vc)
                            player = lavalink.get_player(guild.id)
                            player.store("connect", datetime.datetime.utcnow())
                            player.store("guild", guild_id)
                            await self.self_deafen(player)
                            break
                        except IndexError:
                            await asyncio.sleep(5)
                            tries += 1
                        except Exception as exc:
                            debug_exc_log(log, exc, "Failed to restore music voice channel")
                            if vc is None:
                                break

                if tries >= 25 or guild is None or vc is None:
                    await self.api_interface.persistent_queue_api.drop(guild_id)
                    continue

                shuffle = await self.config.guild(guild).shuffle()
                repeat = await self.config.guild(guild).repeat()
                volume = await self.config.guild(guild).volume()
                shuffle_bumped = await self.config.guild(guild).shuffle_bumped()
                player.repeat = repeat
                player.shuffle = shuffle
                player.shuffle_bumped = shuffle_bumped
                if player.volume != volume:
                    await player.set_volume(volume)
                for track in track_data:
                    track = track.track_object
                    player.add(guild.get_member(track.extras.get("requester")) or guild.me, track)
                player.maybe_shuffle()

                await player.play()
            except Exception as err:
                debug_exc_log(log, err, f"Error restoring player in {guild_id}")
                await self.api_interface.persistent_queue_api.drop(guild_id)

    async def maybe_message_all_owners(self):
        current_notification = await self.config.owner_notification()
        if current_notification == _OWNER_NOTIFICATION:
            return
        if current_notification < 1 <= _OWNER_NOTIFICATION:
            msg = _(
                """Hey, first of all sorry for this notification, it is not something we wish to do often but this update to the Audio Cog warrants it in this case.
            
Audio version 2.3.0+ brings you access to the **Global Audio API**, `[p]help audioset globalapi` for more info, this **API is disabled by default and will never be enabled until you manually enable it**.

This API will allow your to use the Spotify functionally of Audio with a much smaller YouTube API key usage, as it will attempt to look for results in the API before using your key.
This API will also help your bot by reducing the likelihood of YouTube rate-limiting your bot for making requests too often.

To use this API **you will be required to have an access token**, to obtain this token please join <https://discordapp.com/invite/zkmDzhs> and read the instructions there.
Note: Just like any request your bot makes this service will be able to see your bot IP, your IP is not used for anything in the server but we felt that disclosing this to potential users is an important step since the service is managed by Draper and Cog-Creators org.

Since I'm already sending this message, I would highly recommend that you enable your local cache if you haven't yet, to do so you can run `[p]audioset cache 5` This cache only stores metadata so it shouldn't use up a lot of space, however it will make repeated audio requests faster and further reduce the likelihood of YouTube rate-limiting your bot."""
            )
            await send_to_owners_with_prefix_replaced(self.bot, msg)
            await self.config.owner_notification.set(1)
