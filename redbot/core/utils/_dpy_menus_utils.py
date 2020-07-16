import asyncio
import logging
from typing import Iterable, List, Optional, Union, Any, Dict
import discord

from redbot.vendored.discord.ext import menus as _dpy_menus

from .. import commands
from ..commands import Context
from ..i18n import Translator


_ = Translator("Menus", __file__)

log = logging.getLogger("red.menus")


async def dpymenu(
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
        delete_message_after: bool = False,
        add_reactions: bool = True,
        using_custom_emoji: bool = False,
        using_embeds: bool = False,
        keyword_to_reaction_mapping: Optional[Dict[str, Iterable[str]]] = None,
        timeout: int = 60,
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
                if k not in self._actions:
                    self._actions[k] = []
                for e in v:
                    emoji = _dpy_menus._cast_emoji(e)
                    if emoji not in self.buttons:
                        continue
                    self._actions[k].append(emoji)

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
            emojis = self._actions.get(payload.content, [])
            for emoji in emojis:
                if not emoji or emoji not in self.buttons:
                    continue
                button = self.buttons[emoji]
                if not self._running:
                    continue
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
        delete_message_after: bool = False,
        add_reactions: bool = True,
        timeout: int = 60,
        accept_keywords: bool = False,
        **kwargs: Any,
    ):
        if accept_keywords:
            keyword_to_reaction_mapping = {
                _("last"): ["\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f"],
                _("first"): ["\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f"],
                _("next"): ["\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f",],
                _("previous"): ["\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",],
                _("prev"): ["\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",],
                _("close"): ["\N{CROSS MARK}"],
            }
        else:
            keyword_to_reaction_mapping = None
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
