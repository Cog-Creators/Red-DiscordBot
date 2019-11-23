from __future__ import annotations

from typing import Dict, List, Optional
from argparse import Namespace

import discord

from .config import Config


class PrefixManager:
    def __init__(self, config: Config, cli_flags: Namespace):
        self._config: Config = config
        self._global_prefix_overide: Optional[List[str]] = sorted(
            cli_flags.prefix, reverse=True
        ) or None
        self._cached: Dict[Optional[discord.Guild], List[str]] = {}

    async def get_prefixes(self, guild: Optional[discord.Guild] = None) -> List[str]:
        ret: List[str]

        if guild in self._cached:
            ret = self._cached[guild].copy()
        else:
            if guild:
                ret = await self._config.guild(guild).prefix()
                if not ret:
                    ret = await self.get_prefixes(None)
            else:
                ret = self._global_prefix_overide or (await self._config.prefix())

            self._cached[guild] = ret.copy()

        return ret

    async def set_prefixes(
        self, guild: Optional[discord.Guild] = None, prefixes: Optional[List[str]] = None
    ):
        prefixes = prefixes or []
        if not isinstance(prefixes, list) and not all(isinstance(pfx, str) for pfx in prefixes):
            raise TypeError("Prefixes must be a list of strings")
        prefixes = sorted(prefixes, reverse=True)
        if guild is None:
            self._cached.clear()
            await self._config.prefix.set(prefixes)
            self._cached[guild] = self._global_prefix_overide or prefixes
        else:
            del self._cached[guild]
            await self._config.prefix.set(prefixes)
            self._cached[guild] = prefixes
