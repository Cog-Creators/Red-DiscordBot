from __future__ import annotations

from collections import namedtuple
from typing import Union, Dict, List, Any, Tuple

import discord

from redbot.core import bank
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number, box, escape

from redbot.core.utils._dpy_menus_utils import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("Economy", __file__)

MOCK_MEMBER = namedtuple("Member", "id guild")


class LeaderboardSource(menus.ListPageSource):
    def __init__(self, entries: List[Tuple[str, Dict[str, Any]]]):
        super().__init__(entries, per_page=10)
        self.max_bal = -1

    async def format_page(
        self, menu: SimpleHybridMenu, entries: List[Tuple[str, Dict[str, Any]]]
    ) -> Union[discord.Embed, str]:
        guild = menu.ctx.guild
        author = menu.ctx.author
        bot = menu.ctx.bot
        position = (menu.current_page * self.per_page) + 1
        if self.max_bal == -1:
            self.max_bal = await bank.get_max_balance(guild)
        bal_len = len(humanize_number(entries[0][1]["balance"]))
        bal_len_max = len(humanize_number(self.max_bal))
        if bal_len > bal_len_max:
            bal_len = bal_len_max
        pound_len = len(str(position + 9))
        header = "{pound:{pound_len}}{score:{bal_len}}{name:2}\n".format(
            pound="#",
            name=_("Name"),
            score=_("Score"),
            bal_len=bal_len + 6,
            pound_len=pound_len + 3,
        )
        for pos, acc in enumerate(entries, start=position):
            try:
                name = guild.get_member(acc[0]).display_name
            except AttributeError:
                user_id = ""
                if await bot.is_owner(menu.ctx.author):
                    user_id = f"({str(acc[0])})"
                name = f"{acc[1]['name']} {user_id}"

            balance = acc[1]["balance"]
            if balance > self.max_bal:
                balance = self.max_bal
                await bank.set_balance(MOCK_MEMBER(acc[0], guild), balance)
            balance = humanize_number(balance)
            if acc[0] != author.id:
                header += (
                    f"{f'{humanize_number(pos)}.': <{pound_len + 2}} "
                    f"{balance: <{bal_len + 5}} {escape(name, formatting=True)}\n"
                )
            else:
                header += (
                    f"{f'{humanize_number(pos)}.': <{pound_len + 2}} "
                    f"{balance: <{bal_len + 5}} "
                    f"<<{escape(author.display_name, formatting=True)}>>\n"
                )

        return box(header, lang="md")
