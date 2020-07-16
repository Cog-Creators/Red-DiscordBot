# Original source of reaction-based menu idea from
# https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py
#
# Ported to Red V3 by Palm\_\_ (https://github.com/palmtree5)
import asyncio
import contextlib
import functools
import logging
from typing import Iterable, List, Optional, Union, Dict
import discord
from ._dpy_menus_utils import dpymenu as _dpymenu

from .. import commands
from .predicates import ReactionPredicate
from ..i18n import Translator

_ReactableEmoji = Union[str, discord.Emoji]

_ = Translator("Menus", __file__)

log = logging.getLogger("red.menus")


async def menu(
    ctx: commands.Context,
    pages: Iterable[Union[str, discord.Embed]],
    controls: Optional[Dict] = None,
    message: discord.Message = None,
    page: int = 0,
    timeout: int = 60,
    wait: bool = False,
    delete_message_after: bool = False,
    clear_reactions_after: bool = True,
):
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
       controls: dict
           A mapping of emoji to the function which handles the action for the
           emoji.
       message: discord.Message
           The message representing the menu. Usually :code:`None` when first opening
           the menu
       page: int
           The current page number of the menu
       timeout: float
           The time (in seconds) to wait for a reaction
       wait: bool
           Note: Only applicable when ``controls`` is `None` or ``menus.DEFAULT_CONTROLS``
           Whether the menu should be block code execution or should be run as a task (this uses d.py menus).
       delete_message_after: bool
           Note: Only applicable when ``controls`` is `None` or ``menus.DEFAULT_CONTROLS``
           Whether to delete the message once the menu exits (this uses d.py menus).
       clear_reactions_after: bool
           Note: Only applicable when ``controls`` is `None` or ``menus.DEFAULT_CONTROLS``
           Whether to remove reactions once the menu exits - Requires manage message permissions (this uses d.py menus).

       Raises
       ------
       RuntimeError
           If either of the notes above are violated
       MenuError
           Note: Only can be raised when using d.py menus.
           An error happened when verifying permissions.
       redbot.vendored.discord.ext.menus.CannotSendMessages
           Note: Only can be raised when using d.py menus.
           Tried to start the menu but bot can't send message in the context.
       redbot.vendored.discord.ext.menus.CannotAddReactions
           Note: Only can be raised when using d.py menus.
           Tried to start the menu but bot can't add reactions
       redbot.vendored.discord.ext.menus.CannotReadMessageHistory
           Note: Only can be raised when using d.py menus.
           Tried to start the menu but bot can't read message history.
       """
    if controls is None or controls == DEFAULT_CONTROLS:
        await _dpymenu(
            ctx=ctx,
            pages=pages,
            controls=None,
            message=message,
            page=page,
            timeout=timeout,
            wait=wait,
            delete_message_after=delete_message_after,
            clear_reactions_after=clear_reactions_after,
        )
    else:
        await _menu(
            ctx=ctx, pages=pages, controls=controls, message=message, page=page, timeout=timeout
        )


async def _menu(
    ctx: commands.Context,
    pages: Union[List[str], List[discord.Embed]],
    controls: dict,
    message: discord.Message = None,
    page: int = 0,
    timeout: float = 30.0,
):
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
    controls: dict
        A mapping of emoji to the function which handles the action for the
        emoji.
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
    if not isinstance(pages[0], (discord.Embed, str)):
        raise RuntimeError("Pages must be of type discord.Embed or str")
    if not all(isinstance(x, discord.Embed) for x in pages) and not all(
        isinstance(x, str) for x in pages
    ):
        raise RuntimeError("All pages must be of the same type")
    for key, value in controls.items():
        maybe_coro = value
        if isinstance(value, functools.partial):
            maybe_coro = value.func
        if not asyncio.iscoroutinefunction(maybe_coro):
            raise RuntimeError("Function must be a coroutine")
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
            asyncio.ensure_future(ctx.bot.wait_for("reaction_add", check=predicates)),
            asyncio.ensure_future(ctx.bot.wait_for("reaction_remove", check=predicates)),
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
            if message.channel.permissions_for(ctx.me).manage_messages:
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
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    if page == len(pages) - 1:
        page = 0  # Loop around to the first item
    else:
        page = page + 1
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def prev_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    if page == 0:
        page = len(pages) - 1  # Loop around to the last item
    else:
        page = page - 1
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def close_menu(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
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
    this is exactly what `menu` uses to do that.

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


DEFAULT_CONTROLS = {
    "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
    "\N{CROSS MARK}": close_menu,
    "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
}
