# Original source of reaction-based menu idea from
# https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py
#
# Ported to Red V3 by Palm\_\_ (https://github.com/palmtree5)
import asyncio
import contextlib
import functools
import logging
from typing import Iterable, List, Optional, Union, Any, Dict
import discord

from redbot.vendored.discord.ext import menus as _dpy_menus

from .. import commands
from .predicates import ReactionPredicate
from ..commands import Context
from ..i18n import Translator

_ReactableEmoji = Union[str, discord.Emoji]

_ = Translator("Menus", __file__)

log = logging.getLogger("red.menus")


async def menu(
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
        react, user = await ctx.bot.wait_for(
            "reaction_add",
            check=ReactionPredicate.with_emojis(tuple(controls.keys()), message, ctx.author),
            timeout=timeout,
        )
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
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
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
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
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


async def dpymenu(
    ctx: commands.Context,
    pages: Iterable[Union[str, discord.Embed]],
    controls: Optional[Dict] = None,
    message: discord.Message = None,
    page: int = 0,
    timeout: int = 180,
    wait: bool = False,
    delete_message_after: bool = True,
    clear_reactions_after: bool = True,
):
    if controls is not None:
        log.warning(
            "dpymenu function does not accept controls, this is being ignored. "
            f"Called by {ctx.cog}"
        )

    await SimpleHybridMenu(
        source=SimpleSource(pages=pages),
        cog=ctx.cog,
        message=message,
        delete_message_after=delete_message_after,
        clear_reactions_after=clear_reactions_after,
        timeout=timeout,
    ).start(ctx=ctx, wait=wait, page=page)


class CannotReadMessage(_dpy_menus.MenuError):
    def __init__(self):
        super().__init__("Bot does not have Read Message permissions in this channel.")


class HybridMenu(_dpy_menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        source: _dpy_menus.PageSource,
        cog: Optional[commands.Cog] = None,
        clear_reactions_after: bool = True,
        delete_message_after: bool = True,
        add_reactions: bool = True,
        using_custom_emoji: bool = False,
        using_embeds: bool = False,
        keyword_to_reaction_mapping: Dict[str, str] = None,
        timeout: int = 180,
        message: discord.Message = None,
        **kwargs: Any,
    ) -> None:
        self._add_reactions = add_reactions
        self._using_custom_emoji = using_custom_emoji
        super().__init__(
            source,
            clear_reactions_after=clear_reactions_after,
            delete_message_after=delete_message_after,
            check_embeds=using_embeds,
            timeout=timeout,
            message=message,
            **kwargs,
        )
        if (
            bad_stop := _dpy_menus._cast_emoji("\N{BLACK SQUARE FOR STOP}\ufe0f")
        ) and bad_stop in self._buttons:
            del self._buttons[bad_stop]
        self.cog = cog
        self.__keyword_to_reaction_mapping = keyword_to_reaction_mapping
        self._actions = {}
        self.__tasks = self._Menu__tasks

    def _register_keyword(self):
        if isinstance(self.__keyword_to_reaction_mapping, dict):
            for k, v in self.__keyword_to_reaction_mapping.items():
                emoji = _dpy_menus._cast_emoji(v)
                if emoji not in self.buttons:
                    continue
                self._actions[k] = emoji

    def should_add_reactions(self):
        if self._add_reactions:
            return len(self.buttons)

    def _verify_permissions(self, ctx, channel, permissions):
        if not permissions.send_messages:
            raise _dpy_menus.CannotSendMessages()

        if self.check_embeds and not permissions.embed_links:
            raise _dpy_menus.CannotEmbedLinks()

        self._can_remove_reactions = permissions.manage_messages

        if self.should_add_reactions():
            if not permissions.add_reactions:
                raise _dpy_menus.CannotAddReactions()
            if self._using_custom_emoji and not permissions.external_emojis:
                raise _dpy_menus.CannotAddReactions()

        if not permissions.read_message_history:
            raise _dpy_menus.CannotReadMessageHistory()

        if self._actions and not permissions.read_messages:
            raise CannotReadMessage()

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

    def message_check(self, message: discord.Message):
        if message.author.bot or message.author.id not in (*self.bot.owner_ids, self._author_id):
            return False
        return message.content.lower() in self._actions

    async def _internal_loop(self):
        try:
            loop = self.bot.loop
            # Ensure the name exists for the cancellation handling
            tasks = []
            while self._running:
                tasks = [
                    asyncio.ensure_future(
                        self.bot.wait_for("raw_reaction_add", check=self.reaction_check)
                    ),
                    asyncio.ensure_future(
                        self.bot.wait_for("raw_reaction_remove", check=self.reaction_check)
                    ),
                ]
                if self._actions:
                    tasks.append(
                        asyncio.ensure_future(
                            self.bot.wait_for("message_without_command", check=self.message_check)
                        )
                    )

                done, pending = await asyncio.wait(
                    tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()

                if len(done) == 0:
                    raise asyncio.TimeoutError()

                # Exception will propagate if e.g. cancelled or timed out
                payload = done.pop().result()
                loop.create_task(self.update(payload))

                # NOTE: Removing the reaction ourselves after it's been done when
                # mixed with the checks above is incredibly racy.
                # There is no guarantee when the MESSAGE_REACTION_REMOVE event will
                # be called, and chances are when it does happen it'll always be
                # after the remove_reaction HTTP call has returned back to the caller
                # which means that the stuff above will catch the reaction that we
                # just removed.

                # For the future sake of myself and to save myself the hours in the future
                # consider this my warning.

        except asyncio.TimeoutError:
            pass
        finally:
            self._event.set()

            # Cancel any outstanding tasks (if any)
            for task in tasks:
                task.cancel()

            try:
                await self.finalize()
            except Exception:
                pass

            # Can't do any requests if the bot is closed
            if self.bot.is_closed():
                return

            # Wrap it in another block anyway just to ensure
            # nothing leaks out during clean-up
            try:
                if self.delete_message_after:
                    return await self.message.delete()

                if self.clear_reactions_after:
                    if self._can_remove_reactions:
                        return await self.message.clear_reactions()

                    for button_emoji in self.buttons:
                        try:
                            await self.message.remove_reaction(button_emoji, self.__me)
                        except discord.HTTPException:
                            continue
            except Exception:
                pass

    async def update(self, payload):
        """

        Updates the menu after an event has been received.

        Parameters
        -----------
        payload: :class:`discord.RawReactionActionEvent`
            The reaction event that triggered this update.
        """
        if isinstance(payload, discord.RawReactionActionEvent):
            button = self.buttons[payload.emoji]
            if not self._running:
                return

            try:
                if button.lock:
                    async with self._lock:
                        if self._running:
                            await button(self, payload)
                else:
                    await button(self, payload)
            except Exception:
                # TODO: logging?
                import traceback

                traceback.print_exc()
        elif isinstance(payload, discord.Message):
            emoji = self._actions.get(payload.content)
            if not emoji or emoji not in self.buttons:
                return
            button = self.buttons[emoji]
            if not self._running:
                return
            try:
                if button.lock:
                    async with self._lock:
                        if self._running:
                            await button(self, payload)
                else:
                    await button(self, payload)
            except Exception:
                # TODO: logging?
                import traceback

                traceback.print_exc()

    async def start(self, ctx, *, channel=None, wait=False, page: int = 0):
        """
        Starts the interactive menu session.

        Parameters
        -----------
        ctx: :class:`Context`
            The invocation context to use.
        channel: :class:`discord.abc.Messageable`
            The messageable to send the message to. If not given
            then it defaults to the channel in the context.
        wait: :class:`bool`
            Whether to wait until the menu is completed before
            returning back to the caller.

        Raises
        -------
        MenuError
            An error happened when verifying permissions.
        discord.HTTPException
            Adding a reaction failed.
        """

        # Clear the buttons cache and re-compute if possible.
        try:
            del self.buttons
        except AttributeError:
            pass

        self.bot = bot = ctx.bot
        self.ctx = ctx
        self._author_id = ctx.author.id
        channel = channel or ctx.channel
        is_guild = isinstance(channel, discord.abc.GuildChannel)
        me = ctx.guild.me if is_guild else ctx.bot.user
        permissions = channel.permissions_for(me)
        self.__me = discord.Object(id=me.id)
        self._verify_permissions(ctx, channel, permissions)
        self._event.clear()
        msg = self.message
        if msg is None:
            self.message = msg = await self.send_initial_message(ctx, channel, page=0)
        self._register_keyword()
        if self.should_add_reactions() or self._actions:
            # Start the task first so we can listen to reactions before doing anything
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

            self._running = True
            self.__tasks.append(bot.loop.create_task(self._internal_loop()))

            if self.should_add_reactions():

                async def add_reactions_task():
                    for emoji in self.buttons:
                        await msg.add_reaction(emoji)

                self.__tasks.append(bot.loop.create_task(add_reactions_task()))

            if wait:
                await self._event.wait()

    async def send_initial_message(
        self, ctx: Context, channel: discord.abc.Messageable, page: int = 0
    ):
        """

        The default implementation of :meth:`Menu.send_initial_message`
        for the interactive pagination session.

        This implementation shows the first page of the source.
        """
        page = await self._source.get_page(page)
        kwargs = await self._get_kwargs_from_page(page)
        return await channel.send(**kwargs)

    @_dpy_menus.button(
        "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",
        position=_dpy_menus.First(1),
        skip_if=_skip_single_arrows,
    )
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1)

    @_dpy_menus.button(
        "\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f",
        position=_dpy_menus.Last(0),
        skip_if=_skip_single_arrows,
    )
    async def go_to_next_page(self, payload):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1)

    @_dpy_menus.button(
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=_dpy_menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0)

    @_dpy_menus.button(
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=_dpy_menus.Last(1),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(self._source.get_max_pages() - 1)

    @_dpy_menus.button("\N{CROSS MARK}")
    async def stop_pages(self, payload: discord.RawReactionActionEvent) -> None:
        """stops the pagination session."""
        self.stop()


class SimpleHybridMenu(HybridMenu, inherit_buttons=True):
    def __init__(
        self,
        source: _dpy_menus.PageSource,
        cog: Optional[commands.Cog] = None,
        clear_reactions_after: bool = True,
        delete_message_after: bool = True,
        add_reactions: bool = True,
        timeout: int = 180,
        **kwargs: Any,
    ):

        keyword_to_reaction_mapping = {
            _("last"): "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
            _("first"): "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
            _("next"): "\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f",
            _("previous"): "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",
            _("prev"): "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",
            _("close"): "\N{CROSS MARK}",
        }
        super().__init__(
            source=source,
            cog=cog,
            add_reactions=add_reactions,
            timeout=timeout,
            clear_reactions_after=clear_reactions_after,
            delete_message_after=delete_message_after,
            keyword_to_reaction_mapping=keyword_to_reaction_mapping,
            **kwargs,
        )


class SimpleSource(_dpy_menus.ListPageSource):
    def __init__(self, pages: Iterable[Union[List[str], List[discord.Embed]]]):
        super().__init__(pages, per_page=1)

    async def format_page(
        self, menu: SimpleHybridMenu, page: Union[List[str], List[discord.Embed]]
    ) -> Union[discord.Embed, str]:
        """Sends thee specified page to the menu."""
        return page
