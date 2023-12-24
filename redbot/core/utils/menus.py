# Original source of reaction-based menu idea from
# https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py
#
# Ported to Red V3 by Palm\_\_ (https://github.com/palmtree5)
import asyncio
import contextlib
import functools
from types import MappingProxyType
from typing import Callable, Dict, Iterable, List, Mapping, Optional, TypeVar, Union

import discord

from .. import commands
from .predicates import ReactionPredicate
from .views import SimpleMenu, _SimplePageSource

__all__ = (
    "menu",
    "next_page",
    "prev_page",
    "close_menu",
    "start_adding_reactions",
    "DEFAULT_CONTROLS",
)

_T = TypeVar("_T")
_PageList = TypeVar("_PageList", List[str], List[discord.Embed])
_ReactableEmoji = Union[str, discord.Emoji]
_ControlCallable = Callable[[commands.Context, _PageList, discord.Message, int, float, str], _T]

_active_menus: Dict[int, SimpleMenu] = {}


class _GenericButton(discord.ui.Button):
    def __init__(self, emoji: discord.PartialEmoji, func: _ControlCallable):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.grey)
        self.func = func

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = self.view.ctx
        pages = self.view.source.entries
        controls = None
        message = self.view.message
        page = self.view.current_page
        timeout = self.view.timeout
        emoji = (
            str(self.emoji)
            if self.emoji.is_unicode_emoji()
            else (ctx.bot.get_emoji(self.emoji.id) or self.emoji)
        )
        try:
            await self.func(ctx, pages, controls, message, page, timeout, emoji)
        except Exception:
            pass


async def menu(
    ctx: commands.Context,
    pages: _PageList,
    controls: Optional[Mapping[str, _ControlCallable]] = None,
    message: discord.Message = None,
    page: int = 0,
    timeout: float = 30.0,
) -> _T:
    """
    An emoji-based menu

    .. note:: All pages should be of the same type

    .. note:: All functions for handling what a particular emoji does
              should be coroutines (i.e. :code:`async def`). Additionally,
              they must take all of the parameters of this function, in
              addition to a string representing the emoji reacted with.
              This parameter should be the last one, and none of the
              parameters in the handling functions are optional

    Parameters
    ----------
    ctx: commands.Context
        The command context
    pages: `list` of `str` or `discord.Embed`
        The pages of the menu.
    controls: Optional[Mapping[str, Callable]]
        A mapping of emoji to the function which handles the action for the
        emoji. The signature of the function should be the same as of this function
        and should additionally accept an ``emoji`` parameter of type `str`.
        If not passed, `DEFAULT_CONTROLS` is used *or*
        only a close menu control is shown when ``pages`` is of length 1.
    message: discord.Message
        The message representing the menu. Usually :code:`None` when first opening
        the menu
    page: int
        The current page number of the menu
    timeout: float
        The time (in seconds) to wait for a reaction

    Raises
    ------
    RuntimeError
        If either of the notes above are violated
    """
    if message is not None and message.id in _active_menus:
        # prevents the expected callback from going any further
        # our custom button will always pass the message the view is
        # attached to, allowing one to send multiple menus on the same
        # context.
        view = _active_menus[message.id]
        if pages != view.source.entries:
            view._source = _SimplePageSource(pages)
        new_page = await view.get_page(page)
        view.current_page = page
        view.timeout = timeout
        await view.message.edit(**new_page)
        return
    if not isinstance(pages[0], (discord.Embed, str)):
        raise RuntimeError("Pages must be of type discord.Embed or str")
    if not all(isinstance(x, discord.Embed) for x in pages) and not all(
        isinstance(x, str) for x in pages
    ):
        raise RuntimeError("All pages must be of the same type")
    if controls is None:
        if len(pages) == 1:
            controls = {"\N{CROSS MARK}": close_menu}
        else:
            controls = DEFAULT_CONTROLS
    for key, value in controls.items():
        maybe_coro = value
        if isinstance(value, functools.partial):
            maybe_coro = value.func
        if not asyncio.iscoroutinefunction(maybe_coro):
            raise RuntimeError("Function must be a coroutine")

    if await ctx.bot.use_buttons() and message is None:
        # Only send the button version if `message` is None
        # This is because help deals with this menu in weird ways
        # where the original message is already sent prior to starting.
        # This is not normally the way we recommend sending this because
        # internally we already include the emojis we expect.
        if controls == DEFAULT_CONTROLS:
            view = SimpleMenu(pages, timeout=timeout)
            await view.start(ctx)
            await view.wait()
            return
        else:
            view = SimpleMenu(pages, timeout=timeout)
            view.remove_item(view.last_button)
            view.remove_item(view.first_button)
            has_next = False
            has_prev = False
            has_close = False
            to_add = {}
            for emoji, func in controls.items():
                part_emoji = discord.PartialEmoji.from_str(str(emoji))
                if func == next_page:
                    has_next = True
                    if part_emoji != view.forward_button.emoji:
                        view.forward_button.emoji = part_emoji
                elif func == prev_page:
                    has_prev = True
                    if part_emoji != view.backward_button.emoji:
                        view.backward_button.emoji = part_emoji
                elif func == close_menu:
                    has_close = True
                else:
                    to_add[part_emoji] = func
            if not has_next:
                view.remove_item(view.forward_button)
            if not has_prev:
                view.remove_item(view.backward_button)
            if not has_close:
                view.remove_item(view.stop_button)
            for emoji, func in to_add.items():
                view.add_item(_GenericButton(emoji, func))
            await view.start(ctx)
            _active_menus[view.message.id] = view
            await view.wait()
            del _active_menus[view.message.id]
            return
    current_page = pages[page]

    if not message:
        if isinstance(current_page, discord.Embed):
            message = await ctx.send(embed=current_page)
        else:
            message = await ctx.send(current_page)
        # Don't wait for reactions to be added (GH-1797)
        # noinspection PyAsyncCall
        start_adding_reactions(message, controls.keys())
    else:
        try:
            if isinstance(current_page, discord.Embed):
                await message.edit(embed=current_page)
            else:
                await message.edit(content=current_page)
        except discord.NotFound:
            return

    try:
        predicates = ReactionPredicate.with_emojis(tuple(controls.keys()), message, ctx.author)
        tasks = [
            asyncio.create_task(ctx.bot.wait_for("reaction_add", check=predicates)),
            asyncio.create_task(ctx.bot.wait_for("reaction_remove", check=predicates)),
        ]
        done, pending = await asyncio.wait(
            tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

        if len(done) == 0:
            raise asyncio.TimeoutError()
        react, user = done.pop().result()
    except asyncio.TimeoutError:
        if not ctx.me:
            return
        try:
            if (
                isinstance(message.channel, discord.PartialMessageable)
                or message.channel.permissions_for(ctx.me).manage_messages
            ):
                await message.clear_reactions()
            else:
                raise RuntimeError
        except (discord.Forbidden, RuntimeError):  # cannot remove all reactions
            for key in controls.keys():
                try:
                    await message.remove_reaction(key, ctx.bot.user)
                except discord.Forbidden:
                    return
                except discord.HTTPException:
                    pass
        except discord.NotFound:
            return
    else:
        return await controls[react.emoji](
            ctx, pages, controls, message, page, timeout, react.emoji
        )


async def next_page(
    ctx: commands.Context,
    pages: list,
    controls: Mapping[str, _ControlCallable],
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
) -> _T:
    """
    Function for showing next page which is suitable
    for use in ``controls`` mapping that is passed to `menu()`.
    """
    if page >= len(pages) - 1:
        page = 0  # Loop around to the first item
    else:
        page = page + 1
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def prev_page(
    ctx: commands.Context,
    pages: list,
    controls: Mapping[str, _ControlCallable],
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
) -> _T:
    """
    Function for showing previous page which is suitable
    for use in ``controls`` mapping that is passed to `menu()`.
    """
    if page <= 0:
        page = len(pages) - 1  # Loop around to the last item
    else:
        page = page - 1
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def close_menu(
    ctx: commands.Context,
    pages: list,
    controls: Mapping[str, _ControlCallable],
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
) -> None:
    """
    Function for closing (deleting) menu which is suitable
    for use in ``controls`` mapping that is passed to `menu()`.
    """
    with contextlib.suppress(discord.NotFound):
        await message.delete()


def start_adding_reactions(
    message: discord.Message, emojis: Iterable[_ReactableEmoji]
) -> asyncio.Task:
    """Start adding reactions to a message.

    This is a non-blocking operation - calling this will schedule the
    reactions being added, but the calling code will continue to
    execute asynchronously. There is no need to await this function.

    This is particularly useful if you wish to start waiting for a
    reaction whilst the reactions are still being added - in fact,
    this is exactly what `menu()` uses to do that.

    Parameters
    ----------
    message: discord.Message
        The message to add reactions to.
    emojis : Iterable[Union[str, discord.Emoji]]
        The emojis to react to the message with.

    Returns
    -------
    asyncio.Task
        The task for the coroutine adding the reactions.

    """

    async def task():
        # The task should exit silently if the message is deleted
        with contextlib.suppress(discord.NotFound):
            for emoji in emojis:
                await message.add_reaction(emoji)

    return asyncio.create_task(task())


#: Default controls for `menu()` that contain controls for
#: previous page, closing menu, and next page.
DEFAULT_CONTROLS: Mapping[str, _ControlCallable] = MappingProxyType(
    {
        "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
        "\N{CROSS MARK}": close_menu,
        "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
    }
)
