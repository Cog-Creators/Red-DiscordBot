"""
Original source of reaction-based menu idea from
https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py

Ported to Red V3 by Palm\_\_ (https://github.com/palmtree5)
"""
import asyncio
import contextlib
from typing import Union, Iterable
import discord

from redbot.core import commands

_ReactableEmoji = Union[str, discord.Emoji]


async def menu(
    ctx: commands.Context,
    pages: list,
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
    if not all(isinstance(x, discord.Embed) for x in pages) and not all(
        isinstance(x, str) for x in pages
    ):
        raise RuntimeError("All pages must be of the same type")
    for key, value in controls.items():
        if not asyncio.iscoroutinefunction(value):
            raise RuntimeError("Function must be a coroutine")
    current_page = pages[page]

    if not message:
        if isinstance(current_page, discord.Embed):
            message = await ctx.send(embed=current_page)
        else:
            message = await ctx.send(current_page)
        # Don't wait for reactions to be added (GH-1797)
        ctx.bot.loop.create_task(_add_menu_reactions(message, controls.keys()))
    else:
        if isinstance(current_page, discord.Embed):
            await message.edit(embed=current_page)
        else:
            await message.edit(content=current_page)

    def react_check(r, u):
        return u == ctx.author and r.message.id == message.id and str(r.emoji) in controls.keys()

    try:
        react, user = await ctx.bot.wait_for("reaction_add", check=react_check, timeout=timeout)
    except asyncio.TimeoutError:
        try:
            await message.clear_reactions()
        except discord.Forbidden:  # cannot remove all reactions
            for key in controls.keys():
                await message.remove_reaction(key, ctx.bot.user)
        return None

    return await controls[react.emoji](ctx, pages, controls, message, page, timeout, react.emoji)


async def next_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.guild.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        try:
            await message.remove_reaction(emoji, ctx.author)
        except discord.NotFound:
            pass
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
    perms = message.channel.permissions_for(ctx.guild.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        try:
            await message.remove_reaction(emoji, ctx.author)
        except discord.NotFound:
            pass
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
    if message:
        await message.delete()
    return None


async def _add_menu_reactions(message: discord.Message, emojis: Iterable[_ReactableEmoji]):
    """Add the reactions"""
    # The task should exit silently if the message is deleted
    with contextlib.suppress(discord.NotFound):
        for emoji in emojis:
            await message.add_reaction(emoji)


DEFAULT_CONTROLS = {"⬅": prev_page, "❌": close_menu, "➡": next_page}
