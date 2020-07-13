from __future__ import annotations

from typing import Union, List

import discord

from redbot.core.i18n import Translator
from redbot.core.modlog import Case

from redbot.core.utils.menus import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("General", __file__)


class CasesForSource(menus.ListPageSource):
    def __init__(self, cases: List[Case]):
        super().__init__(cases, per_page=1)

    async def format_page(self, menu: SimpleHybridMenu, case: Case) -> Union[discord.Embed, str]:
        return await case.message_content(embed=await menu.ctx.embed_requested())
