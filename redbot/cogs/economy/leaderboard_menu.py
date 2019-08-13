from typing import List, Tuple, Dict, Any, Optional

import discord

from redbot.core.i18n import Translator
from redbot.core.utils import chat_formatting as chatutils
from redbot.core.utils.menus import PagedMenu

_ = Translator("what is the point of this", __file__)


class LeaderboardMenu(PagedMenu, exit_button=True, initial_emojis=("⬅", "❌", "➡")):
    def __init__(self, *, accounts: List[Tuple[int, Dict[str, Any]]], **kwargs) -> None:
        self._accounts = accounts
        self._cur_rank = 0
        super().__init__(pages=[], arrows_always=True, **kwargs)

    async def _before_send(self, **kwargs) -> None:
        if not self._pages:
            self._pages = [await self._format_page()]
        if len(self._accounts) < 10:
            # Only one page, no need for arrows
            self._initial_emojis = ("❌",)

    @PagedMenu.handler("⬅")
    async def prev_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        num_accounts = len(self._accounts)
        if num_accounts < 10:
            return
        if self._cur_rank == 0:
            self._cur_rank = num_accounts - num_accounts % 10
            if self._cur_rank == num_accounts:
                self._cur_rank -= 10
        else:
            self._cur_rank -= 10

        if self._cur_page == 0:
            self._cur_page = 1
            self._pages.insert(0, await self._format_page())

        await super().prev_page(payload=payload)

    @PagedMenu.handler("➡")
    async def next_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        num_accounts = len(self._accounts)
        if num_accounts < 10:
            return
        if self._cur_rank > num_accounts - 10:
            self._cur_rank = 0
        else:
            self._cur_rank += 10

        if self._cur_page == len(self._pages) - 1:
            self._pages.append(await self._format_page())

        await super().next_page(payload=payload)

    async def _format_page(self) -> str:
        accounts = self._accounts[self._cur_rank : self._cur_rank + 10]

        bal_colwidth = len(chatutils.humanize_number(accounts[0][1]["balance"])) + 5
        pos_colwidth = len(chatutils.humanize_number(len(accounts))) + 2

        lines = [
            "{pound:{pound_len}} {score:{bal_len}} {name:2}".format(
                pound="#",
                name=_("Name"),
                score=_("Score"),
                bal_len=bal_colwidth,
                pound_len=pos_colwidth,
            )
        ]

        if self.ctx is not None:
            author = self.ctx.author
            is_owner = await self.bot.is_owner(author)
        else:
            author = None
            is_owner = False

        if isinstance(self.channel, discord.abc.GuildChannel):
            guild = self.channel.guild
        else:
            guild = None

        for pos, (user_id, account_data) in enumerate(accounts, start=self._cur_rank + 1):
            if guild is not None:
                member = guild.get_member(user_id)
            else:
                member = None

            if member is not None:
                username = member.display_name
            else:
                user = self.bot.get_user(user_id)
                if user is None:
                    continue

                username = user.name
                if is_owner is True:
                    username += f" ({user_id})"

            if user_id == author.id:
                # Highlight the author's position
                username = f"<<{username}>>"

            pos_str = f"{chatutils.humanize_number(pos)}."
            balance = chatutils.humanize_number(account_data["balance"])
            lines.append(f"{pos_str:<{pos_colwidth}} {balance:<{bal_colwidth}} {username}")

        return chatutils.box("\n".join(lines), lang="md")