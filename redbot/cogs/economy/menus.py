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
        self._total_balance = None
        self._author_position = None
        self._author_balance = None
        self._bank_name = None

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
        if self._bank_name is None:
            self._bank_name = await bank.get_bank_name(guild)
        bank_name = _("{} leaderboard.").format(self._bank_name)
        if self._total_balance is None:
            if await bank.is_global():
                accounts = await bank._config.all_users()
            else:
                accounts = await bank._config.all_members(guild=guild)
            overall = 0
            for key, value in accounts.items():
                overall += value["balance"]
            self._total_balance = overall
        if self._author_position is None:
            self._author_position = await bank.get_leaderboard_position(menu.ctx.author)
        if self._author_balance is None:
            self._author_balance = await bank.get_balance(menu.ctx.author)

        pound_len = len(str(position + 9))
        header = "{pound:{pound_len}}{score:{bal_len}}{name:2}\n".format(
            pound="#",
            name=_("Name"),
            score=_("Score"),
            bal_len=bal_len + 6,
            pound_len=pound_len + 3,
        )
        percent = round((int(self._author_balance) / self._total_balance * 100), 3)
        for pos, acc in enumerate(entries, start=position):
            try:
                user = guild.get_member(int(acc[0])) or bot.get_user(int(acc[0]))
                name = user.display_name
            except AttributeError:
                user_id = ""
                if await bot.is_owner(menu.ctx.author):
                    user_id = f"({acc[0]})"
                name = f"{acc[1]['name']} {user_id}"
            name = escape(name, formatting=True)

            balance = acc[1]["balance"]
            if balance > self.max_bal:
                balance = self.max_bal
                await bank.set_balance(MOCK_MEMBER(acc[0], guild), balance)
            balance = humanize_number(balance)
            if acc[0] != author.id:
                header += (
                    f"{f'{humanize_number(pos)}.': <{pound_len + 2}} "
                    f"{balance: <{bal_len + 5}} "
                    f"{name}\n"
                )
            else:
                header += (
                    f"{f'{humanize_number(pos)}.': <{pound_len + 2}} "
                    f"{balance: <{bal_len + 5}} "
                    f"<<{name}>>\n"
                )
        if await menu.ctx.embed_requested():
            page = discord.Embed(
                title=_("{}\nYou are currently #{}/{}").format(
                    bank_name, self._author_position, len(self.entries)
                ),
                color=await menu.ctx.embed_color(),
                description="{} ```py\n{}\n{}```".format(
                    box(header, lang="md"),
                    _("Total bank amount {}").format(humanize_number(self._total_balance)),
                    _("You have {}% of the total amount!").format(percent),
                ),
            )
            page.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        else:
            page = box(header, lang="md")

        return page
