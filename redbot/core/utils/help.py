from __future__ import annotations

from typing import Union, Dict, List, Any, Tuple, Iterable

import discord

from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box

from redbot.core.utils.menus import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("Alias", __file__)


class HelpSource(menus.ListPageSource):
    def __init__(self, entries: Iterable[Union[str, discord.Embed]]):
        super().__init__(entries, per_page=1)

    async def format_page(
        self, menu: SimpleHybridMenu, entry: Union[str, discord.Embed]
    ) -> Union[str, discord.Embed]:
        return entry
