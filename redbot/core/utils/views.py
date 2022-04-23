from __future__ import annotations

import discord

from typing import TYPE_CHECKING, Any, List, Optional, Union, Dict
from redbot.core.i18n import Translator
from redbot.vendored.discord.ext import menus


if TYPE_CHECKING:
    from redbot.core.commands import Context

_ = Translator("UtilsViews", __file__)

_ACCEPTABLE_PAGE_TYPES = Union[Dict[str, Union[str, discord.Embed]], discord.Embed, str]


class _SimplePageSource(menus.ListPageSource):
    def __init__(self, items: List[_ACCEPTABLE_PAGE_TYPES]):
        super().__init__(items, per_page=1)

    async def format_page(
        self, view: discord.ui.View, page: _ACCEPTABLE_PAGE_TYPES
    ) -> Union[str, discord.Embed]:
        return page


class _SelectMenu(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(
            placeholder=_("Select a Page"), min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        self.view.current_page = index
        kwargs = await self.view.get_page(self.view.current_page)
        await interaction.response.edit_message(**kwargs)


class _NavigateButton(discord.ui.Button):
    def __init__(
        self, style: discord.ButtonStyle, emoji: Union[str, discord.PartialEmoji], direction: int
    ):
        super().__init__(style=style, emoji=emoji)
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        if self.direction == 0:
            self.view.current_page = 0
        elif self.direction == self.view.source.get_max_pages():
            self.view.current_page = self.view.source.get_max_pages() - 1
        else:
            self.view.current_page += self.direction
        kwargs = await self.view.get_page(self.view.current_page)
        await interaction.response.edit_message(**kwargs)


class _StopButton(discord.ui.Button):
    def __init__(self, style: discord.ButtonStyle, emoji: Union[str, discord.PartialEmoji]):
        super().__init__(style=style, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()
        if interaction.message.flags.ephemeral:
            await interaction.response.edit_message(view=None)
            return
        await interaction.message.delete()


class SimpleMenu(discord.ui.View):
    """
    A simple Button menu

    Parameters
    ----------
    pages: `list` of `str`, `discord.Embed`, or `dict`.
        The pages of the menu.
        if the page is a `dict` its keys must be valid messageable args.
        e,g. `{"content": "My content", "embed": discord.Embed(description="hello")}`
    page_start: int
        The page to start the menu at.
    timeout: float
        The time (in seconds) to wait for a reaction
        defaults to 180 seconds.
    delete_after_timeout: bool
        Whether or not to delete the message after
        the timeout has expired.
        Defaults to False.
    disable_after_timeout: bool
        Whether to disable all components on the
        menu after timeout has expired. By default
        the view is removed from the message on timeout.
        Defaults to False.
    use_select_menu: bool
        Whether or not to include a select menu
        to jump specifically between pages.
        Defaults to False.
    use_select_only: bool
        Whether the menu will only display the select
        menu for paginating instead of the buttons.
        The stop button will remain but is positioned
        under the select menu in this instance.
        Defaults to False.

    Examples
    --------
        from redbot.core.utils.views import SimpleMenu

        pages = ["Hello", "Hi", "Bonjour", "Salut"]
        await SimpleMenu(pages).start(ctx)
    """

    def __init__(
        self,
        pages: List[_ACCEPTABLE_PAGE_TYPES],
        timeout: float = 180.0,
        page_start: int = 0,
        delete_after_timeout: bool = False,
        disable_after_timeout: bool = False,
        use_select_menu: bool = False,
        use_select_only: bool = False,
    ) -> None:
        super().__init__(
            timeout=timeout,
        )
        self.author: Optional[discord.abc.User] = None
        self.message: Optional[discord.Message] = None
        self._source = _SimplePageSource(items=pages)
        self.ctx: Optional[Context] = None
        self.current_page = page_start
        self.delete_after_timeout = delete_after_timeout
        self.disable_after_timeout = disable_after_timeout
        self.use_select_menu = use_select_menu or use_select_only
        self.use_select_only = use_select_only

        self.forward_button = _NavigateButton(
            discord.ButtonStyle.grey,
            "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=1,
        )
        self.backward_button = _NavigateButton(
            discord.ButtonStyle.grey,
            "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=-1,
        )
        self.first_button = _NavigateButton(
            discord.ButtonStyle.grey,
            "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
            direction=0,
        )
        self.last_button = _NavigateButton(
            discord.ButtonStyle.grey,
            "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
            direction=self.source.get_max_pages(),
        )
        self.select_options = [
            discord.SelectOption(label=_("Page {num}").format(num=num + 1), value=num)
            for num, x in enumerate(pages)
        ]
        self.stop_button = _StopButton(
            discord.ButtonStyle.red, "\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}"
        )
        self.select_menu = self._get_select_menu()
        self.add_item(self.stop_button)
        if self.source.is_paginating() and not self.use_select_only:
            self.add_item(self.first_button)
            self.add_item(self.backward_button)
            self.add_item(self.forward_button)
            self.add_item(self.last_button)
        if self.use_select_menu and self.source.is_paginating():
            if self.use_select_only:
                self.remove_item(self.stop_button)
                self.add_item(self.select_menu)
                self.add_item(self.stop_button)
            else:
                self.add_item(self.select_menu)

    @property
    def source(self):
        return self._source

    async def on_timeout(self):
        if self.delete_after_timeout and not self.message.flags.ephemeral:
            await self.message.delete()
        elif self.disable_after_timeout:
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)
        else:
            await self.message.edit(view=None)

    def _get_select_menu(self):
        # handles modifying the select menu if more than 25 pages are provided
        # this will show the previous 12 and next 13 pages in the select menu
        # based on the currently displayed page. Once you reach close to the max
        # pages it will display the last 25 pages.
        if len(self.select_options) > 25:
            minus_diff = None
            plus_diff = 25
            if 12 < self.current_page < len(self.select_options) - 25:
                minus_diff = self.current_page - 12
                plus_diff = self.current_page + 13
            elif self.current_page >= len(self.select_options) - 25:
                minus_diff = len(self.select_options) - 25
                plus_diff = None
            options = self.select_options[minus_diff:plus_diff]
        else:
            options = self.select_options[:25]
        return _SelectMenu(options)

    async def start(self, ctx: Context, *, ephemeral: bool = False):
        """
        Used to start the menu displaying the first page requested.

        Parameters
        ----------
            ctx: `commands.Context`
                The context to start the menu in.
            ephemeral: `bool`
                Send the message ephemerally. This only works
                if the context is from a slash command interaction.
        """
        self.author = ctx.author
        self.ctx = ctx
        kwargs = await self.get_page(self.current_page)
        self.message = await ctx.send(**kwargs, ephemeral=ephemeral)

    async def get_page(self, page_num: int) -> Dict[str, Optional[Any]]:
        try:
            page = await self.source.get_page(page_num)
        except IndexError:
            self.current_page = 0
            page = await self.source.get_page(self.current_page)
        value = await self.source.format_page(self, page)
        if self.use_select_menu and len(self.select_options) > 25 and self.source.is_paginating():
            self.remove_item(self.select_menu)
            self.select_menu = self._get_select_menu()
            self.add_item(self.select_menu)
        ret: Dict[str, Optional[Any]] = {"view": self}
        if isinstance(value, dict):
            ret.update(value)
            ret = value
        elif isinstance(value, str):
            ret.update({"content": value, "embed": None})
        elif isinstance(value, discord.Embed):
            ret.update({"embed": value, "content": None})
        return ret

    async def interaction_check(self, interaction: discord.Interaction):
        """Ensure only the author is allowed to interact with the menu."""
        allowed_ids = (getattr(self.author, "id", None),)
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message(
                content=_("You are not authorized to interact with this."), ephemeral=True
            )
            return False
        return True
