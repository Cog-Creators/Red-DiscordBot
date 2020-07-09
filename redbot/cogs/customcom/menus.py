from __future__ import annotations

from typing import List, Any, Union, Iterable, Tuple

import discord

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number, escape
from redbot.vendored.discord.ext import menus

_ = Translator("CustomCommands", __file__)


class CCListSource(menus.ListPageSource):
    def __init__(self, custom_commands: Iterable[Tuple[str, dict]]):
        super().__init__(custom_commands, per_page=5)

    async def format_page(
        self, menu: Menu, entries: Iterable[Tuple[str, dict]]
    ) -> Union[discord.Embed, str]:
        current_entry = menu.current_page + 1
        total_entries = self._max_pages

        results = []
        for command, body in entries:
            responses = body["response"]

            if isinstance(responses, list):
                result = ", ".join(map(discord.utils.escape_markdown, responses))
            elif isinstance(responses, str):
                result = discord.utils.escape_markdown(responses)
            else:
                continue
            # Cut preview to 52 characters max
            if len(result) > 52:
                result = result[:49] + "..."
            # Replace newlines with spaces
            result = result.replace("\n", " ")
            # Escape markdown and mass mentions
            result = escape(result, formatting=True, mass_mentions=True)
            results.append((f"{menu.ctx.clean_prefix}{command}", result))

        if await menu.ctx.embed_requested():
            # We need a space before the newline incase the CC preview ends in link (GH-2295)
            content = " \n".join(map("**{0[0]}** : {0[1]}".format, results))
            embed = discord.Embed(
                title=_("Custom Command List"),
                description=content,
                colour=await menu.ctx.embed_colour(),
            )
            if total_entries > 1:
                text = _("Page: {page_num}/{total_pages}\n").format(
                    page_num=humanize_number(current_entry),
                    total_pages=humanize_number(max(1, total_entries)),
                )
                embed.set_footer(text=text)
            return embed
        else:
            return "\n".join(map("{0[0]:<12} : {0[1]}".format, results))


class CCRawSource(menus.ListPageSource):
    def __init__(self, custom_commands: List[str]):
        super().__init__(custom_commands, per_page=1)

    async def format_page(self, menu: Menu, entry: str) -> Union[discord.Embed, str]:
        raw = discord.utils.escape_markdown(entry)
        current_entry = menu.current_page + 1
        total_entries = self._max_pages
        if await menu.ctx.embed_requested():
            colour = await menu.ctx.embed_colour()
            if len(raw) > 2048:
                raw = f"{raw[:2045]}..."
            embed = discord.Embed(
                title=_("Response #{num}").format(num=current_entry),
                description=raw,
                colour=colour,
            )
            if total_entries > 1:
                text = _("Page: {page_num}/{total_pages}\n").format(
                    page_num=humanize_number(current_entry),
                    total_pages=humanize_number(max(1, total_entries)),
                )
                embed.set_footer(text=text)
            return embed
        else:
            msg = _("Response #{num}/{total}:\n{raw}").format(
                num=humanize_number(current_entry),
                total=humanize_number(max(1, total_entries)),
                raw=raw,
            )
            if len(msg) > 2000:
                msg = f"{msg[:1997]}..."
            return msg


class Menu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        source: Union[CCListSource, CCRawSource],
        cog: commands.Cog,
        clear_reactions_after: bool = True,
        delete_message_after: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            source,
            clear_reactions_after=clear_reactions_after,
            delete_message_after=delete_message_after,
            **kwargs,
        )
        self.cog = cog

    async def show_checked_page(self, page_number: int) -> None:
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number)
            elif page_number >= max_pages:
                await self.show_page(0)
            elif page_number < 0:
                await self.show_page(max_pages - 1)
            elif max_pages > page_number >= 0:
                await self.show_page(page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    def _skip_single_arrows(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages == 1

    def _skip_double_triangle_buttons(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages <= 2

    def reaction_check(self, payload):
        """Just extends the default reaction_check to use owner_ids"""
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False
        return payload.emoji in self.buttons

    @menus.button(
        "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",
        position=menus.First(1),
        skip_if=_skip_single_arrows,
    )
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1)

    @menus.button(
        "\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f",
        position=menus.Last(0),
        skip_if=_skip_single_arrows,
    )
    async def go_to_next_page(self, payload):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0)

    @menus.button(
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.Last(1),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(self._source.get_max_pages() - 1)

    @menus.button("\N{CROSS MARK}")
    async def stop_pages(self, payload: discord.RawReactionActionEvent) -> None:
        """stops the pagination session."""
        self.stop()
