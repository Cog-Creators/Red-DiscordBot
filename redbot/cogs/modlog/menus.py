from __future__ import annotations

from typing import Union, List

import discord

from redbot.core.i18n import Translator
from redbot.core.modlog import Case
from redbot.core.utils.chat_formatting import humanize_number

from redbot.core.utils._dpy_menus_utils import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("General", __file__)


class CasesForSource(menus.ListPageSource):
    def __init__(self, cases: List[Case]):
        super().__init__(cases, per_page=1)

    async def format_page(self, menu: SimpleHybridMenu, case: Case) -> Union[discord.Embed, str]:
        current_entry = menu.current_page + 1
        total_entries = self._max_pages
        message = await case.message_content(embed=await menu.ctx.embed_requested())
        if total_entries > 1 and isinstance(message, discord.Embed):
            text = _("Case: {page_num}/{total_pages}\n").format(
                page_num=humanize_number(current_entry),
                total_pages=humanize_number(max(1, total_entries)),
            )
            message.set_footer(text=text)
        return message
