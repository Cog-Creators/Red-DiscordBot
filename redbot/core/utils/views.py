from __future__ import annotations

import discord

from discord.ext.commands import BadArgument
from typing import TYPE_CHECKING, List, Union, Optional, Dict, Any
from redbot.core.commands.converter import get_dict_converter
from redbot.core.i18n import Translator
from redbot.vendored.discord.ext import menus


if TYPE_CHECKING:
    from redbot.core.bot import Red
    from redbot.core.commands import Context

_ = Translator("UtilsViews", __file__)

class SimplePageSource(menus.ListPageSource):
    def __init__(self, items: List[Union[str, discord.Embed]]):
        super().__init__(items, per_page=1)

    async def format_page(
        self, menu: menus.MenuPages, page: Union[str, discord.Embed]
    ) -> Union[str, discord.Embed]:
        return page


class SimpleMenu(discord.ui.View):
    def __init__(
        self,
        pages: List[Union[str, discord.Embed]],
        clear_reactions_after: bool = True,
        delete_message_after: bool = False,
        timeout: int = 180,
        message: discord.Message = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            timeout=timeout,
        )
        self.author = None
        self.message = message
        self._source = SimplePageSource(items=pages)
        self.ctx = None
        self.current_page = kwargs.get("page_start", 0)

    @property
    def source(self):
        return self._source

    async def on_timeout(self):
        await self.message.edit(view=None)

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.send_initial_message(ctx, ctx.channel)

    async def get_page(self, page_num: int):
        try:
            page = await self.source.get_page(page_num)
        except IndexError:
            self.current_page = 0
            page = await self.source.get_page(self.current_page)
        value = await self.source.format_page(self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"embed": value, "content": None}

    async def send_initial_message(self, ctx, channel):
        """|coro|
        The default implementation of :meth:`Menu.send_initial_message`
        for the interactive pagination session.
        This implementation shows the first page of the source.
        """
        self.author = ctx.author

        self.ctx = ctx
        kwargs = await self.get_page(self.current_page)
        self.message = await channel.send(**kwargs, view=self)
        return self.message

    async def interaction_check(self, interaction: discord.Interaction):
        """Just extends the default reaction_check to use owner_ids"""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                content=_("You are not authorized to interact with this."), ephemeral=True
            )
            return False
        self.interaction = interaction
        return True

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
    )
    async def go_to_first_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the first page"""
        kwargs = await self.get_page(0)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
    )
    async def go_to_previous_page(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        """go to the previous page"""
        self.current_page -= 1
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
    )
    async def go_to_next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the next page"""
        self.current_page += 1
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
    )
    async def go_to_last_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        self.current_page = self.source.get_max_pages() - 1
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(
        style=discord.ButtonStyle.red,
        emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
    )
    async def stop_pages(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        """stops the pagination session."""
        self.stop()
        await interaction.message.delete()
