from __future__ import annotations

from typing import Dict, Union

import discord

from .abc import CacheBase


class ManagedNodeYamlManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[str, Union[int, str, bool]] = {}

    async def get_server_address(self) -> str:
        ret: str
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["server_address"]
        else:
            ret = await self._config.lavalink.managed_yaml.server.address()
            self._cached_global["server_address"] = ret
        return ret

    async def set_server_address(self, set_to: str) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.server.address.set(set_to)
            self._cached_global["server_address"] = set_to
        else:
            await self._config.lavalink.managed_yaml.server.address.clear()
            self._cached_global["server_address"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["server"]["address"]

    async def get_server_port(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["server_port"]
        else:
            ret = await self._config.lavalink.managed_yaml.server.port()
            self._cached_global["server_port"] = ret
        return ret

    async def set_server_port(self, set_to: int) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.server.port.set(set_to)
            self._cached_global["server_port"] = set_to
        else:
            await self._config.lavalink.managed_yaml.server.port.clear()
            self._cached_global["server_port"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["server"]["port"]

    async def get_lavalink_password(self) -> str:
        ret: str
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["lavalink_password"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.password()
            self._cached_global["lavalink_password"] = ret
        return ret

    async def set_lavalink_password(self, set_to: str) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.password.set(set_to)
            self._cached_global["lavalink_password"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.password.clear()
            self._cached_global["lavalink_password"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["password"]

    async def get_lavalink_ytsearch(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["lavalink_ytsearch"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.youtubeSearchEnabled()
            self._cached_global["lavalink_ytsearch"] = ret
        return ret

    async def set_lavalink_ytsearch(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.youtubeSearchEnabled.set(
                set_to
            )
            self._cached_global["lavalink_ytsearch"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.youtubeSearchEnabled.clear()
            self._cached_global["lavalink_ytsearch"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["youtubeSearchEnabled"]

    async def get_lavalink_scsearch(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["lavalink_scsearch"]
        else:
            ret = (
                await self._config.lavalink.managed_yaml.lavalink.server.soundcloudSearchEnabled()
            )
            self._cached_global["lavalink_scsearch"] = ret
        return ret

    async def set_lavalink_scsearch(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.soundcloudSearchEnabled.set(
                set_to
            )
            self._cached_global["lavalink_scsearch"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.soundcloudSearchEnabled.clear()
            self._cached_global["lavalink_scsearch"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["soundcloudSearchEnabled"]

    async def get_lavalink_update_intervals(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["lavalink_update_intervals"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.playerUpdateInterval()
            self._cached_global["lavalink_update_intervals"] = ret
        return ret

    async def set_lavalink_update_intervals(self, set_to: int) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.playerUpdateInterval.set(
                set_to
            )
            self._cached_global["lavalink_update_intervals"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.playerUpdateInterval.clear()
            self._cached_global["lavalink_update_intervals"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["managed_yaml"]["lavalink"]["server"]["playerUpdateInterval"]

    async def get_lavalink_buffer(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["lavalink_update_intervals"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.bufferDurationMs()
            self._cached_global["lavalink_update_intervals"] = ret
        return ret

    async def set_lavalink_lavalink_buffer(self, set_to: int) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.bufferDurationMs.set(set_to)
            self._cached_global["lavalink_update_intervals"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.bufferDurationMs.clear()
            self._cached_global["lavalink_update_intervals"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["managed_yaml"]["lavalink"]["server"]["bufferDurationMs"]

    async def get_jda_nsa(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["jdanas"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.jdanas()
            self._cached_global["jdanas"] = ret
        return ret

    async def set_jda_nsa(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.jdanas.set(set_to)
            self._cached_global["jdanas"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.jdanas.clear()
            self._cached_global["jdanas"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["jdanas"]

    async def get_source_http(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["source_http"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.sources.http()
            self._cached_global["source_http"] = ret
        return ret

    async def set_source_http(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.http.set(set_to)
            self._cached_global["source_http"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.http.clear()
            self._cached_global["source_http"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["sources"]["http"]

    async def get_source_local(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["source_http"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.sources.http()
            self._cached_global["source_http"] = ret
        return ret

    async def set_source_local(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.local.set(set_to)
            self._cached_global["source_local"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.local.clear()
            self._cached_global["source_local"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["sources"]["local"]

    async def get_source_bandcamp(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["source_bandcamp"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.sources.bandcamp()
            self._cached_global["source_bandcamp"] = ret
        return ret

    async def set_source_bandcamp(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.bandcamp.set(set_to)
            self._cached_global["source_bandcamp"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.bandcamp.clear()
            self._cached_global["source_bandcamp"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["sources"]["bandcamp"]

    async def get_source_soundcloud(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["source_soundcloud"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.sources.soundcloud()
            self._cached_global["source_soundcloud"] = ret
        return ret

    async def set_source_soundcloud(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.soundcloud.set(set_to)
            self._cached_global["source_soundcloud"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.soundcloud.clear()
            self._cached_global["source_soundcloud"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["sources"]["soundcloud"]

    async def get_source_twitch(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["source_twitch"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.sources.twitch()
            self._cached_global["source_twitch"] = ret
        return ret

    async def set_source_twitch(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.twitch.set(set_to)
            self._cached_global["source_twitch"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.twitch.clear()
            self._cached_global["source_twitch"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["sources"]["twitch"]

    async def get_source_youtube(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global["source_youtube"]
        else:
            ret = await self._config.lavalink.managed_yaml.lavalink.server.sources.youtube()
            self._cached_global["source_youtube"] = ret
        return ret

    async def set_source_youtube(self, set_to: bool) -> None:
        if set_to is not None:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.youtube.set(set_to)
            self._cached_global["source_youtube"] = set_to
        else:
            await self._config.lavalink.managed_yaml.lavalink.server.sources.youtube.clear()
            self._cached_global["source_youtube"] = self._config.defaults["GLOBAL"]["lavalink"][
                "managed_yaml"
            ]["lavalink"]["server"]["sources"]["youtube"]

    async def get_context_value(self, guild: discord.Guild = None) -> bool:
        return NotImplemented

    def reset_globals(self) -> None:
        self._cached_global = {}
