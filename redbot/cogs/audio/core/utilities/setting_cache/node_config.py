from __future__ import annotations

from typing import Dict, Optional, Set, Union

import discord

from .abc import CacheBase


class NodeConfigManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[
            Optional[str], Union[Dict[str, Union[str, int, bool]], Set[str]]
        ] = {}

    async def get_host(self, node_identifier: str = "primary") -> str:
        ret: str
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["host"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "host")
            self._cached_global[node_identifier]["host"] = ret
        return ret

    async def set_host(self, set_to: str, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "host", value=set_to)
            self._cached_global[node_identifier]["host"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "host")
            self._cached_global[node_identifier]["host"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["host"]

    async def get_port(self, node_identifier: str = "primary") -> int:
        ret: int
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["port"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "port")
            self._cached_global[node_identifier]["port"] = ret
        return ret

    async def set_port(self, set_to: int, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "port", value=set_to)
            self._cached_global[node_identifier]["port"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "port")
            self._cached_global[node_identifier]["port"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["port"]

    async def get_rest_uri(self, node_identifier: str = "primary") -> str:
        ret: str
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["rest_uri"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "rest_uri")
            self._cached_global[node_identifier]["rest_uri"] = ret
        return ret

    async def set_rest_uri(self, set_to: str, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "rest_uri", value=set_to)
            self._cached_global[node_identifier]["rest_uri"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "rest_uri")
            self._cached_global[node_identifier]["rest_uri"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["rest_uri"]

    async def get_password(self, node_identifier: str = "primary") -> str:
        ret: str
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["password"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "password")
            self._cached_global[node_identifier]["password"] = ret
        return ret

    async def set_password(self, set_to: str, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "password", value=set_to)
            self._cached_global[node_identifier]["password"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "password")
            self._cached_global[node_identifier]["password"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["password"]

    async def get_identifier(self, node_identifier: str = "primary") -> str:
        ret: str
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["identifier"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "identifier")
            self._cached_global[node_identifier]["identifier"] = ret
        return ret

    async def set_identifier(self, set_to: str, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "identifier", value=set_to)
            self._cached_global[node_identifier]["identifier"] = set_to
            await self._config.lavalink.nodes.clear_raw(node_identifier)
            self._cached_global[set_to] = self._cached_global.pop(node_identifier)
            await self._config.lavalink.nodes.set_raw(set_to, value=self._cached_global[set_to])
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "identifier")
            self._cached_global[node_identifier]["identifier"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["identifier"]

    async def get_region(self, node_identifier: str = "primary") -> str:
        ret: str
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["region"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "region")
            self._cached_global[node_identifier]["region"] = ret
        return ret

    async def set_region(self, set_to: str, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "region", value=set_to)
            self._cached_global[node_identifier]["region"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "region")
            self._cached_global[node_identifier]["region"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["region"]

    async def get_shard_id(self, node_identifier: str = "primary") -> int:
        ret: int
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["shard_id"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "shard_id")
            self._cached_global[node_identifier]["shard_id"] = ret
        return ret

    async def set_shard_id(self, set_to: int, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "shard_id", value=set_to)
            self._cached_global[node_identifier]["shard_id"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "shard_id")
            self._cached_global[node_identifier]["shard_id"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["shard_id"]

    async def get_search_only(self, node_identifier: str = "primary") -> bool:
        ret: bool
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[node_identifier]["search_only"]
        else:
            ret = await self._config.lavalink.nodes.get_raw(node_identifier, "search_only")
            self._cached_global[node_identifier]["search_only"] = ret
        return ret

    async def set_search_only(self, set_to: bool, node_identifier: str = "primary") -> None:
        self._cached_global.setdefault(
            node_identifier, self._config.defaults["GLOBAL"]["lavalink"]["nodes"]["primary"]
        )
        if set_to is not None:
            await self._config.lavalink.nodes.set_raw(node_identifier, "search_only", value=set_to)
            self._cached_global[node_identifier]["search_only"] = set_to
        else:
            await self._config.lavalink.nodes.clear_raw(node_identifier, "search_only")
            self._cached_global[node_identifier]["search_only"] = self._config.defaults["GLOBAL"][
                "lavalink"
            ]["nodes"]["primary"]["search_only"]

    async def get_all_identifiers(self) -> Set[str]:
        if None not in self._cached_global:
            return await self.refresh_all_identifiers()
        return self._cached_global[None]

    async def delete_node(self, node_identifier: str = "primary") -> None:
        await self._config.lavalink.nodes.clear_raw(node_identifier)
        if node_identifier in self._cached_global:
            del self._cached_global[node_identifier]

    async def refresh_all_identifiers(self) -> Set[str]:
        self._cached_global[None] = set((await self._config.lavalink.nodes.all()).keys())
        return self._cached_global[None]

    async def get_context_value(self, guild: discord.Guild = None) -> bool:
        return NotImplemented

    def reset_globals(self) -> None:
        self._cached_global = {}
