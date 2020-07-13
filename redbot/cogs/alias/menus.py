from __future__ import annotations

from typing import Iterable


from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box

from redbot.core.utils.menus import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("Alias", __file__)


class AliasSource(menus.ListPageSource):
    def __init__(self, entries: Iterable[str]):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: SimpleHybridMenu, entry: str) -> str:
        current_entry = menu.current_page + 1
        total_entries = self._max_pages
        page = _("Aliases:\n") + entry.lstrip("\n")
        if total_entries > 1:
            page += _("\n\nPage {page}/{total}").format(page=current_entry, total=total_entries)
        return box("".join(page), "diff")
