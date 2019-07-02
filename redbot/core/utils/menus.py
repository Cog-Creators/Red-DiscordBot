"""This module provides utilities for assisting in sending common types
of reaction menus, as well as extending these menus, or creating new
ones from scratch.

The :class:`ReactionMenu` abstract base class and its concrete
subclasses were added in version 3.2. Prior to that, the legacy
:func:`menu` was used, which has been kept for backwards compatibility.

These documents hope to be aimed at cog creators who may use reaction
menus in one or two ways:

1. Sending and managing a common type of reaction menu which is provided
   with this module, and
2. Customising the existing reaction menus, or creating new ones from
   the :class:`ReactionMenu` ABC.

For those who fit into the 1st category, these are the provided
reaction menus:

- :class:`PagedMenu`, for a menu where reactions can be used to scroll
  through a list of pages (text, embed or a combination of both)
- :class:`OptionsMenu`, where reactions select an option from a list
  displayed on the menu, and can pass this onto a provided callback
  function.
- :class:`PagedOptionsMenu`, a combination of the above two menus.

For those who fit into the 2nd category, some protected methods of the
reaction menu classes are documented for your interest. Those which are
documented are considered part of Red's public API for cog creators and
will be subject to the same care with regards to breaking changes.
"""
import abc
import asyncio
import contextlib
import enum
import functools
import inspect
import types
from typing import (
    Union,
    Iterable,
    Optional,
    Callable,
    Awaitable,
    List,
    Iterator,
    TYPE_CHECKING,
    Tuple,
    ClassVar,
    Dict,
    Any,
    Sequence,
    Set,
    TypeVar,
    Generic,
    cast,
)

import discord

from .. import commands
from .chat_formatting import bold, underline
from .predicates import ReactionPredicate
from .tasks import DeferrableTimer
from .utils import deduplicate_iterables

if TYPE_CHECKING:
    from ..bot import Red

_T = TypeVar("_T")
_ReactableEmoji = Union[str, discord.Emoji]
_CoroutineFunction = Callable[..., Awaitable[None]]
_Page = Union[str, discord.Embed, Tuple[str, discord.Embed]]


class ReactionEvent(enum.Flag):
    """Reaction event enumeration flags.

    This enumeration should be used when passing the ``event`` kwarg
    to `ReactionMenu.handler` and `ReactionMenu.add_handler`. If a
    handler accepts multiple events, they should be combined with
    the bitwise *OR* operator ``|``, like so:

    .. code-block:: python

        class MyReactionMenu(ReactionMenu)

            @ReactionMenu.handler(event=ReactionEvent.REACTION_ADD | ReactionEvent.REACTION_REMOVE)
            async def my_handler(self, reaction, user):
                ...

    """

    REACTION_ADD = enum.auto()
    """The :func:`~discord.on_reaction_add` event."""
    REACTION_REMOVE = enum.auto()
    """The :func:`~discord.on_reaction_remove` event."""
    REACTION_CLEAR = enum.auto()
    """The :func:`~discord.on_reaction_clear` event."""
    RAW_REACTION_ADD = enum.auto()
    """The :func:`~discord.on_raw_reaction_add` event."""
    RAW_REACTION_REMOVE = enum.auto()
    """The :func:`~discord.on_raw_reaction_remove` event."""
    RAW_REACTION_CLEAR = enum.auto()
    """The :func:`~discord.on_raw_reaction_clear` event."""


class ReactionMenu(abc.ABC):
    """Abstract base class for reaction menus.

    This class does the vast majority of the work when writing reaction
    menus, and allows for easy customisation of the default behaviour
    through overriding methods.

    It also provides an abstract interface for sending and managing
    custom menus: most importantly, the classmethods
    :meth:`ReactionMenu.send_and_wait` and
    :meth:`ReactionMenu.send_and_return`. These methods accept a handful
    of positional arguments, as well as keyword arguments which can be
    specific to the menu subclass being used. These keyword arguments
    should be detailed in the class docstring of the menu subclass being
    used, just as the built-in ones are detailed below under the
    *Keyword Arguments* heading.

    Keyword Arguments
    -----------------
    timeout : Optional[float]
        The timeout for the menu. This timeout is restarted every time
        a reaction event is handled which passes the event check - which
        usually means, when a controller adds or removes a reaction to
        or from the menu. Defaults to 30 seconds. Set to ``None`` to
        disable the timeout.

    Important
    ---------
    `ReactionMenu` subclasses should not be instantiated directly:
    instead, they should be created through the
    :meth:`ReactionMenu.send_and_wait` or
    :meth:`ReactionMenu.send_and_return` classmethods.

    .. versionadded:: 3.2

    Attributes
    ----------
    ctx : Optional[commands.Context]
        The ``ctx`` object passed when sending the message, if provided.
    channel : discord.abc.Messageable
        The messageable where the menu was sent.
    bot : Red
        The bot object.
    message : Optional[discord.Message]
        The object for the message which contains the menu. Before the
        menu is sent, this will be ``None``.

    """

    INITIAL_EMOJIS: ClassVar[Optional[Sequence[str]]] = None
    """ClassVar[Optional[Sequence[str]]: A class variable containing the
    emojis which should be added to the initial menu message by default.
    
    By default, this will be set to the emojis passed to
    :meth:`ReactionMenu.handler` decorators, in the order they appear in
    the source (with emojis from any inherited handlers appearing
    first). Alternatively, subclasses may override this behaviour with
    the ``initial_emojis`` argument to
    :meth:`ReactionMenu.__init_subclass__`.
    """

    _HANDLERS: ClassVar[Dict[str, Set[Tuple[ReactionEvent, Union[str, _CoroutineFunction]]]]]

    def __init__(
        self,
        *,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        bot: Optional["Red"] = None,
        controller_ids: Optional[Set[int]] = None,
        initial_emojis: Optional[Sequence[str]] = None,
        timeout: float = 30.0,
        **kwargs,
    ) -> None:
        """Default constructor for a `ReactionMenu`.

        This method is only documented for the convenience of anyone
        subclassing `ReactionMenu`. Menus should not be constructed
        directly.

        Subclasses should *always* call
        ``super().__init__(**kwargs)`` from their custom constructors.

        Constructors are called from the
        :func:`ReactionMenu.send_and_return` and
        :func:`ReactionMenu.send_and_wait` classmethods with the
        ``ctx``, ``channel`` and ``bot`` arguments, as well as any
        other keyword arguments passed. *All* arguments are passed as
        keyword arguments. See below for details.

        Keyword Arguments
        -----------------
        ctx : Optional[commands.Context]
            The context object for this menu. This should be the ``ctx``
            argument to the send classmethods.
        channel : Optional[discord.abc.Messageable]
            The channel for this menu. This should be the ``channel``
            argument to the send classmethods.
        bot : Optional[Red]
            The bot object. This should be the ``bot`` argument to the
            send classmethods.
        controller_ids : Optional[Set[int]]
            A set of IDs of users given the ability to control this
            menu. This shouldn't need to be handled by subclasses.
        initial_emojis : Optional[Sequence[str]]
            The initial emojis to be reacted to this menu. Defaults to
            the class attribute :attr:`ReactionMenu.INITIAL_EMOJIS`.

        """
        if channel is None:
            if ctx is None:
                raise TypeError('Must pass at least one of "ctx" or "channel"')
            channel = ctx.channel

        if bot is None:
            if ctx is None:
                raise TypeError('Must pass at least one of "ctx" or "bot"')
            bot = ctx.bot

        self.ctx: Optional[commands.Context] = ctx
        self.channel: discord.abc.Messageable = channel
        self.bot: "Red" = bot
        self.message: Optional[discord.Message] = None

        self._controller_ids: Optional[Set[int]] = controller_ids
        if initial_emojis is None:
            self._initial_emojis = self.INITIAL_EMOJIS
        else:
            self._initial_emojis = initial_emojis
        self._wait_task: Optional[asyncio.Task] = None

        self.__done_event = asyncio.Event()
        self.__timer = DeferrableTimer(timeout=timeout)

    @classmethod
    def __init_subclass__(
        cls,
        *args,
        exit_button: bool = False,
        initial_emojis: Optional[Sequence[str]] = None,
        **kwargs,
    ) -> None:
        """Subclass initializer for `ReactionMenu`.

        This method is called whenever `ReactionMenu` is subclassed,
        much like a class decorator. Arguments are passed to it through
        the same parentheses where base classes are specified, like so::

            class MyMenu(ReactionMenu, exit_button=True):
                ...

        See :meth:`object.__init_subclass__` for more info on this
        special method more generally.

        Keyword Arguments
        -----------------
        exit_button : bool
            Set to ``True`` to include the default exit button reaction,
            which uses the \N{CROSS MARK} emoji, and is handled by
            `ReactionMenu.exit_menu` (or your subclass's overridden
            version of that). Note that the exit button handler won't
            be inherited from any base classes - it must be explicitly
            enabled for every subclass.
        initial_emojis : Optional[Sequence[str]]
            An override for :attr:`ReactionMenu.INITIAL_EMOJIS`. The
            order of this sequence is preserved when adding reactions.

        """
        super().__init_subclass__(*args, **kwargs)
        cls._HANDLERS = {}
        _emoji_linenos = {}
        for member_name, member in inspect.getmembers(cls, predicate=inspect.iscoroutinefunction):
            try:
                emojis = member.__handle_emojis__
                event = member.__handle_event__
                lineno = member.__decorator_lineno__
            except AttributeError:
                continue
            else:
                cls.add_handler(member, *emojis, event=event)
                if initial_emojis is None:
                    for emoji in emojis:
                        _emoji_linenos[emoji] = lineno

        if exit_button is True:
            cls.add_handler(cls.exit_menu, "❌")

        if initial_emojis is None:
            # In order of appearance in source code
            emojis = (
                emoji for emoji, lineno in sorted(_emoji_linenos.items(), key=lambda t: t[1])
            )
            # Prepended with those inherited from bases
            cls.INITIAL_EMOJIS = deduplicate_iterables(
                *(
                    base.INITIAL_EMOJIS
                    for base in cls.__bases__
                    if issubclass(base, ReactionMenu) and base.INITIAL_EMOJIS is not None
                ),
                emojis,
            )
        else:
            cls.INITIAL_EMOJIS = initial_emojis

    @staticmethod
    def handler(
        *emojis: str,
        event: ReactionEvent = ReactionEvent.RAW_REACTION_ADD | ReactionEvent.RAW_REACTION_REMOVE,
    ):
        """A decorator for reaction handlers.

        Handlers must be methods of a `ReactionMenu` subclass, they must
        be `coroutine functions <coroutine function>`, and they must
        take the same arguments as listeners to whichever event(s) the
        handler is responding to.

        Parameters
        ----------
        *emojis : str
            The emojis to handle. Leave blank to handle all emojis.
        event : ReactionEvent
            The event(s) to react to. See the example in that class's
            description for how to react to multiple events. Defaults to
            ``RAW_REACTION_ADD | RAW_REACTION_REMOVE``.

        """
        # To retain order of appearance in source code, we can use stack inspection to record
        # the line number where this decorator was called.
        caller_lineno = inspect.stack()[1].lineno

        def decorator(callback: _CoroutineFunction) -> _CoroutineFunction:
            if not inspect.iscoroutinefunction(callback):
                raise TypeError("Handlers must be coroutine functions")
            callback.__handle_emojis__ = emojis
            callback.__handle_event__ = event
            callback.__decorator_lineno__ = caller_lineno
            return callback

        return decorator

    @classmethod
    def add_handler(
        cls,
        handler: Union[_CoroutineFunction, functools.partial, functools.partialmethod],
        *emojis: str,
        event: ReactionEvent = ReactionEvent.RAW_REACTION_ADD | ReactionEvent.RAW_REACTION_REMOVE,
    ) -> None:
        """Non-decorator alternative to `ReactionMenu.handler`.

        This classmethod must be called from the actual class which you
        want the handler to be included in. Calling this method directly
        from the `ReactionMenu` class will raise a `RuntimeError`.

        Parameters
        ----------
        handler : Union[`coroutine function`, `functools.partial`]
            The handler function. This must follow the same rules as
            described in :meth:`ReactionMenu.handler`, except that it
            does not have to be a method of a `ReactionMenu` subclass.
        *emojis : str
            Same as ``*emojis`` in :meth:`ReactionMenu.handler`.
        event : str
            Same as ``event`` in :meth:`ReactionMenu.handler`.

        """
        if cls is ReactionMenu:
            raise RuntimeError("You may only add handlers to *subclasses* of ReactionMenu")

        if isinstance(handler, functools.partial):
            actual_callback = handler.func
        else:
            actual_callback = handler
            if handler is getattr(cls, handler.__name__, None):
                # If the handler is a method of this subclass, we should use getattr() *on the
                # instance* rather than on the class itself. The reason for this is to ensure
                # consistency between staticmethods, classmethods and instance methods.
                handler = handler.__name__
        if not inspect.iscoroutinefunction(actual_callback):
            raise TypeError("`handler` must be an `async def` method")

        if not emojis:
            cls._HANDLERS.setdefault("", set()).add((event, handler))
        else:
            for emoji in deduplicate_iterables(emojis):
                cls._HANDLERS.setdefault(emoji, set()).add((event, handler))

    @classmethod
    async def send_and_wait(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        bot: Optional["Red"] = None,
        controllers: Optional[Iterable[discord.abc.User]] = None,
        **kwargs,
    ) -> "ReactionMenu":
        """Send the menu and wait for it to be marked as done.

        This will usually wait for either a timeout (if the ``timeout``
        option is enabled for this menu instance), an exit button to be
        pressed (if the menu class includes it), or some other condition
        set by the menu subclass.

        Note
        ----
        **Subclasses**: Do not override this method if you can avoid
        it. To force this method to return control to the caller,
        call the :meth:`set_done` method.

        Parameters
        ----------
        ctx : Optional[commands.Context]
            The context object to use for the menu's context. If
            provided, the context object provides defaults for the
            ``channel``, ``bot``, and ``controllers`` parameters, where
            ``controllers`` is set to ``[ctx.author]``. If omitted,
            both ``channel`` and ``bot`` become required arguments.
        channel : Optional[discord.abc.Messageable]
            The channel to send the menu in. If ommitted, ``ctx`` must
            be provided instead, and this argument becomes
            :attr:`Context.channel`.
        bot : Optional[Red]
            The bot object. If omitted, ``ctx`` must be provided
            instead, and this argument becomes :attr:`Context.bot`.
        controllers : Optional[Iterable[discord.abc.User]]
            The users who are allowed to control this menu with
            reactions. To allow anyone to take control of this menu, set
            to an empty iterable. If omitted, this defaults to
            ``[ctx.author]``, or if ``ctx`` is also omitted, this will
            default to an empty iterable.
        **kwargs
            Other options, specific to the menu subclass being created.
            See the *Keyword Argument* section in the class doc for
            whichever menu subclass you're using. Some default options
            can also be passed, as outlined `above <ReactionMenu>`.

        Returns
        -------
        ReactionMenu
            The menu object, once it is marked as done.

        """
        self = await cls.send_and_return(ctx, channel, bot, controllers, **kwargs)
        await self._wait_task
        return self

    @classmethod
    async def send_and_return(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        bot: Optional["Red"] = None,
        controllers: Optional[Iterable[discord.abc.User]] = None,
        **kwargs,
    ) -> "ReactionMenu":
        """Send this menu, and return straight after sending.

        The menu actions will be handled in a background task, and the
        menu can be force closed externally using the asynchonous
        :meth:`ReactionMenu.exit_menu` method, which will wait for the
        menu to be deleted, or the synchonous, non-blocking
        :meth:`set_done` method.

        The parameters are the same as in
        :meth:`ReactionMenu.send_and_wait`.

        Note
        ----
        **Subclasses**: Do not override this method if you can avoid
        it.

        Returns
        -------
        ReactionMenu
            The menu object, once the initial message containing the
            menu has been sent (likely before all reactions are added).

        """
        if cls is ReactionMenu:
            raise RuntimeError("You must use a subclass of ReactionMenu to send menus!")

        if controllers is not None:
            # These users can control the menu
            controller_ids = {u.id for u in controllers}
        elif ctx is not None:
            # The author can control the menu
            controller_ids = {ctx.author.id}
        else:
            # Anyone can control the menu (chaos)
            controller_ids = None

        self = cls(ctx=ctx, channel=channel, bot=bot, controller_ids=controller_ids, **kwargs)
        await self._before_send(**kwargs)
        self.message = await self._send(**kwargs)
        await self._after_send(**kwargs)
        self.__add_listeners()
        self._wait_task = asyncio.create_task(self.__wait())
        return self

    def set_done(self) -> None:
        """Synchonous, non-blocking method to mark the menu as done."""
        self.__done_event.set()

    # noinspection PyUnusedLocal
    async def exit_menu(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        """Delete the menu message and mark the menu as done.

        Note
        ----
        **Subclasses**: Override this method to implement custom
        behaviour when the exit menu button (\N{CROSS MARK}) is
        pressed, and your subclass enables the ``exit_button`` option.
        """
        with contextlib.suppress(discord.NotFound):
            await self.message.delete()
        self.set_done()

    def _check(self, reaction: discord.Reaction, user: discord.abc.User) -> bool:
        """The default check for non-raw reaction add/remove events.

        Subclasses may override this method for custom behaviour. By
        default, it checks that the reaction's message matches the menu,
        the user is one of the authorized controllers, and that it
        wasn't the bot itself triggerring the event.
        """
        return (
            self.message is not None
            and self.message.id == reaction.message.id
            and (self._controller_ids is None or user.id in self._controller_ids)
            and self.bot.user.id != user.id
        )

    def _reaction_add_check(self, reaction: discord.Reaction, user: discord.abc.User) -> bool:
        """The check for the :func:`~discord.on_reaction_add` event.

        By default, this calls :meth:`ReactionMenu._check`. Subclasses
        should override this method if they want different behaviour
        specifically for the reaction *add* event.
        """
        return self._check(reaction, user)

    def _reaction_remove_check(self, reaction: discord.Reaction, user: discord.abc.User) -> bool:
        """The check for the :func:`~discord.on_reaction_remove` event.

        By default, this calls :meth:`ReactionMenu._check`. Subclasses
        should override this method if they want different behaviour
        specifically for the reaction *remove* event.
        """
        return self._check(reaction, user)

    # noinspection PyUnusedLocal
    def _reaction_clear_check(
        self, message: discord.Message, reactions: List[discord.Reaction]
    ) -> bool:
        """The check for the :func:`~discord.on_reaction_clear` event.

        By default, this checks if the reaction's message matches the
        menu.
        """
        return self.message is not None and self.message.id == message.id

    def _raw_check(self, payload: discord.RawReactionActionEvent) -> bool:
        """The default check for raw reaction add/remove events.

        Subclasses may override this method for custom behaviour. By
        default, it checks that the reaction's message matches the menu,
        the user is one of the authorized controllers, and that it
        wasn't the bot itself triggerring the event.
        """
        return (
            self.message is not None
            and self.message.id == payload.message_id
            and (self._controller_ids is None or payload.user_id in self._controller_ids)
            and self.bot.user.id != payload.user_id
        )

    def _raw_reaction_add_check(self, payload: discord.RawReactionActionEvent) -> bool:
        """The check for the :func:`~discord.on_raw_reaction_add` event.

        By default, this calls :meth:`ReactionMenu._raw_check`.
        Subclasses should override this method if they want different
        behaviour specifically for the raw reaction *add* event.
        """
        return self._raw_check(payload)

    def _raw_reaction_remove_check(self, payload: discord.RawReactionActionEvent) -> bool:
        """The check for the :func:`~discord.on_raw_reaction_remove`
        event.

        By default, this calls :meth:`ReactionMenu._raw_check`.
        Subclasses should override this method if they want different
        behaviour specifically for the raw reaction *remove* event.
        """
        return self._raw_check(payload)

    def _raw_reaction_clear_check(self, payload: discord.RawReactionClearEvent) -> bool:
        """The check for the :func:`~discord.on_raw_reaction_clear`
        event.

        By default, this checks if the reaction's message matches the
        menu.
        """
        return self.message is not None and self.message.id == payload.message_id

    async def _before_send(self, **kwargs) -> None:
        """This method is called before sending the menu.

        Subclasses may override this for custom behaviour. By default,
        it does nothing.

        Parameters
        ----------
        **kwargs
            The keyword arguments passed to one of the send classethods.

        """
        pass

    async def _send(self, **kwargs) -> discord.Message:
        """This method sends the actual menu.

        Overridden methods *must* return the message object.

        Parameters
        ----------
        **kwargs
            The keyword arguments passed to one of the send classethods.

        Returns
        -------
        discord.Message
            The object for the message that was sent. This will be
            assigned to the :attr:`message` attribute.

        """
        return await self.channel.send(
            content=kwargs.get("content"),
            tts=kwargs.get("tts"),
            embed=kwargs.get("embed"),
            file=kwargs.get("file"),
            files=kwargs.get("file"),
            delete_after=kwargs.get("delete_after"),
        )

    # noinspection PyUnusedLocal
    async def _after_send(self, **kwargs) -> None:
        """This method is called after sending the menu.

        Subclasses may override this for custom behaviour. By default,
        it calls :meth:`ReactionMenu._start_adding_reactions`.

        Parameters
        ----------
        **kwargs
            The keyword arguments passed to one of the send classethods.

        """
        self._start_adding_reactions()

    async def _after_timeout(self):
        """This method is called after the menu times out.

        By default, it simply calls :meth:`ReactionMenu.exit_menu`.
        """
        await self.exit_menu()

    async def _cleanup(self):
        """The cleanup method for the menu.

        This method is called when the menu closes, times out, or
        somehow forcibly exits. It is called within a
        `finally <finally>` clause, so it shouldn't be missed.

        By default, it does nothing.
        """
        pass

    def _start_adding_reactions(self, emojis: Optional[Sequence[str]] = None) -> asyncio.Task:
        """This method starts the task which adds the initial reactions.

        This method simply returns the result of the
        :func:`start_adding_reactions` function.

        Parameters
        ----------
        emojis : Optional[Sequence[str]]
            The emojis to use for the reactions. If omitted, it will
            default to :attr:`ReactionMenu._initial_emojis`.

        Returns
        -------
        asyncio.Task
            The task which is adding the reactions.

        """
        if emojis is None:
            emojis = self._initial_emojis
        return start_adding_reactions(self.message, emojis)

    def __add_listeners(self) -> None:
        for event, listener in (
            (ReactionEvent.REACTION_ADD, self.__on_reaction_add),
            (ReactionEvent.REACTION_REMOVE, self.__on_reaction_remove),
            (ReactionEvent.REACTION_CLEAR, self.__on_reaction_clear),
            (ReactionEvent.RAW_REACTION_ADD, self.__on_raw_reaction_add),
            (ReactionEvent.RAW_REACTION_REMOVE, self.__on_raw_reaction_remove),
            (ReactionEvent.RAW_REACTION_CLEAR, self.__on_raw_reaction_clear),
        ):
            for handler_set in self._HANDLERS.values():
                for handler_event, handler in handler_set:
                    if event & handler_event:
                        break
                else:
                    continue
                break
            else:
                continue
            self.bot.add_listener(listener, listener.__name__[2:])

    def __remove_listeners(self) -> None:
        for listener in (
            self.__on_reaction_add,
            self.__on_reaction_remove,
            self.__on_reaction_clear,
            self.__on_raw_reaction_add,
            self.__on_raw_reaction_remove,
            self.__on_raw_reaction_clear,
        ):
            self.bot.remove_listener(listener, listener.__name__[2:])

    async def __wait(self):
        try:
            await self.__timer.wait_for(self.__done_event.wait())
        except asyncio.TimeoutError:
            await self._after_timeout()
        finally:
            self.__remove_listeners()
            await self._cleanup()

    async def __on_reaction_add(self, reaction: discord.Reaction, user: discord.abc.User) -> None:
        if not self._reaction_add_check(reaction, user):
            return
        self.__timer.restart()
        await self.__call_handlers((reaction, user), ReactionEvent.REACTION_ADD, reaction.emoji)

    async def __on_reaction_remove(
        self, reaction: discord.Reaction, user: discord.abc.User
    ) -> None:
        if not self._reaction_remove_check(reaction, user):
            return
        self.__timer.restart()
        await self.__call_handlers((reaction, user), ReactionEvent.REACTION_REMOVE, reaction.emoji)

    async def __on_reaction_clear(
        self, message: discord.Message, reactions: List[discord.Reaction]
    ) -> None:
        if not self._reaction_clear_check(message, reactions):
            return
        self.__timer.restart()
        await self.__call_handlers((message, reactions), ReactionEvent.REACTION_CLEAR)

    async def __on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if not self._raw_reaction_add_check(payload):
            return
        self.__timer.restart()
        await self.__call_handlers((payload,), ReactionEvent.RAW_REACTION_ADD, str(payload.emoji))

    async def __on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if not self._raw_reaction_remove_check(payload):
            return
        self.__timer.restart()
        await self.__call_handlers(
            (payload,), ReactionEvent.RAW_REACTION_REMOVE, str(payload.emoji)
        )

    async def __on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent) -> None:
        if not self._raw_reaction_clear_check(payload):
            return
        self.__timer.restart()
        await self.__call_handlers((payload,), ReactionEvent.RAW_REACTION_CLEAR)

    def __iter_handlers(
        self, event: Optional[ReactionEvent] = None, emoji: Optional[str] = None
    ) -> Iterator[_CoroutineFunction]:
        handler_list = []
        for key in (emoji, ""):
            with contextlib.suppress(KeyError):
                handler_list.extend(self._HANDLERS[key])

        for handler_event, handler in handler_list:
            if event is None or event & handler_event:
                if isinstance(handler, str):
                    yield getattr(self, handler)
                else:
                    yield handler

    async def __call_handlers(
        self, args, event: ReactionEvent, emoji: Optional[str] = None
    ) -> None:
        if emoji not in self._HANDLERS and "" not in self._HANDLERS:
            return
        await asyncio.gather(*(handler(*args) for handler in self.__iter_handlers(event, emoji)))


class PagedMenu(ReactionMenu, exit_button=True, initial_emojis=("⬅", "❌", "➡")):
    """A reaction menu for scrolling through pages.

    By default, this menu's intial reactions will be ⬅ ❌ ➡, with the
    cross being the exit button.

    Below are the keyword arguments you must/can pass to the
    :meth:`send_and_return` or :meth:`send_and_wait` classmethods.

    .. versionadded:: 3.2

    Keyword Arguments
    -----------------
    pages : Iterable[Union[str, discord.Embed, Tuple[str, discord.Embed]]], **Required**
        An iterable of pages which the menu can scroll through. It can
        be a combination of strings (for text content), embeds, or
        2-tuples containing (text, embed).
    pagenum_in_footer: bool
        Any embeds which don't already have non-empty footer text will
        have the following added to it: *Page <k>/<n>*, where *<k>* is
        the current page number and *<n>* is the number of pages.
        Defaults to ``True``.
    footer_text : Optional[str]
        Text to add to the footer of any embeds which don't already have
        non-empty footer text. If ``pagenum_in_footer`` is ``True``,
        this will be added like so: *Page <k>/<n> | <footer_text>*.
    first_page : int
        What the initial page index should be. Defaults to zero.
    arrows_always : bool
        When ``True``, the arrow reactions for previous and next page
        buttons will be added, even when there is only one page in
        ``pages``. This is only really useful for subclasses who might
        only start with one page, but generate the rest dynamically.
        Defaults to ``False``.

    Attributes
    ----------
    _pages : List[Union[str, discord.Embed, Tuple[str, discord.Embed]]]
        The list of pages provided. This is documented for the
        interest of subclasses only.
    _cur_page : int
        The current page number, indexed from zero. This should always
        be in the range [0, ``len(_pages)``). This is documented for the
        interest of subclasses only.

    """

    _pages: List[_Page]
    _cur_page: int

    def __init__(
        self,
        *,
        pages: Iterable[_Page],
        footer_text: Optional[str] = None,
        first_page: int = 0,
        arrows_always: bool = False,
        initial_emojis: Optional[Sequence[str]] = None,
        **kwargs,
    ) -> None:
        self._pages = list(pages)
        self._cur_page = first_page
        self._footer_text = footer_text

        if initial_emojis is None and arrows_always is False and len(self._pages) == 1:
            initial_emojis = ["❌"]
        super().__init__(initial_emojis=initial_emojis, **kwargs)

    # noinspection PyUnusedLocal
    @ReactionMenu.handler("⬅")
    async def prev_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        """Handler for the previous page button.

        This can be called externally (without arguments) if for some
        reason the caller wants to manually change pages.

        Subclasses may override this method. By default, it decrements
        :attr:`PagedMenu._cur_page`, wrapping back to the last page if
        necessary, and then updates the message.
        """
        if len(self._pages) == 1:
            return
        self._cur_page -= 1
        if self._cur_page < 0:
            self._cur_page = len(self._pages) - 1
        await self._update_message()

    # noinspection PyUnusedLocal
    @ReactionMenu.handler("➡")
    async def next_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        """Handler for the next page button.

        Complements :meth:`PagedMenu.prev_page`.
        """
        if len(self._pages) == 1:
            return
        self._cur_page += 1
        if self._cur_page >= len(self._pages):
            self._cur_page = 0
        await self._update_message()

    async def _send(self, **kwargs) -> discord.Message:
        content, embed = await self._get_content_and_embed(self._pages[self._cur_page])
        return await self.channel.send(content=content, embed=embed)

    async def _update_message(self) -> None:
        """Update the message's content/embed to the current page."""
        content, embed = await self._get_content_and_embed(self._pages[self._cur_page])
        await self.message.edit(content=content, embed=embed)

    async def _get_content_and_embed(
        self, page: _Page
    ) -> Tuple[Optional[str], Optional[discord.Embed]]:
        if isinstance(page, discord.Embed):
            content, embed = None, page
        elif isinstance(page, str):
            content, embed = page, None
        elif isinstance(page, tuple):
            content, embed = page
        else:
            raise TypeError(
                "Pages must be one of type str, discord.Embed or Tuple[str, discord.Embed]"
            )
        if embed is not None:
            if embed.footer.text is discord.Embed.Empty:
                footer_text = f"Page {self._cur_page + 1}/{len(self._pages)}"
                if self._footer_text is not None:
                    footer_text += f" | " + self._footer_text
                embed.set_footer(text=footer_text)
            if embed.colour is discord.Embed.Empty and self.ctx is not None:
                embed.colour = await self.ctx.embed_colour()
        return content, embed


class OptionsMenu(Generic[_T], ReactionMenu):
    """A reaction menu for picking an option from a list.

    This menu allows the caller to provide a list of options in the form
    of 2-tuples, containing the option description being shown to the
    user, and some object associated with that option. The selected
    option's object will be assigned to the menu's :attr:`selection`
    attribute, and can also be passed to some (optionally asynchronous)
    callback function, along with the user who selected the option.

    This menu has a limit of 20 options, due to the limit in the number
    of reactions which can be added to a Discord message. Providing
    more than 20 options will raise a `ValueError`. See the
    `PagedOptionsMenu` class if you would like to be able to offer an
    arbitrarily large number of options.

    Below are the keyword arguments you must/can pass to the
    :meth:`send_and_return` or :meth:`send_and_wait` classmethods.

    .. versionadded:: 3.2

    Keyword Arguments
    -----------------
    options : Sequence[Tuple[str, _T]], **Required**
        The sequence of options, as described above.
    emojis : Optional[Sequence[str]]
        The emojis to align with ``options``. If provided, this sequence
        must be at least as long as ``options``.  If omitted, the emojis
        used depend on the number of options - if 10 or fewer options
        are provided, number emojis (1, 2, 3 etc.) will be used. If
        between 11 and 20 options are provided, "regional indicator"
        letter emojis (A, B, C etc.) will be used.
    exit_on_selection : bool
        Whether the menu should exit as soon as an option is selected.
        ``callback`` may be called multiple times if this is set to
        ``False``. Defaults to ``True``.
    callback : Optional[Callable[[discord.abc.User, _T], Union[Awaitable[None], None]]]
        A callback to pass the user who selected the option, and the
        selected option's object to. This must take two arguments: the
        user and the object, and may be an async function if desired.
    title : Optional[str]
        A title to display at the top of the menu.
    embed : Optional[bool]
        Whether or not the menu should be formatted as an embed.
        If ``None``, it will use the same logic as
        :meth:`commands.Context.embed_requested`. Defaults to ``None``.
    embed_colour : Optional[discord.Colour]
        The colour for the menu embed. If ``None``, it will use the same
        logic as :meth:`commands.Context.embed_colour`. Defaults to
        ``None``. Has no effect if the ``embed`` argument is ``False``.

    Raises
    ------
    ValueError
        If ``emojis`` is provided but is too small.

    """

    def __init__(
        self,
        *,
        options: Sequence[Tuple[str, _T]],
        initial_emojis: Optional[Sequence[str]] = None,
        num_options_per_page: Optional[int] = None,
        exit_on_selection: bool = True,
        callback: Optional[Callable[[discord.abc.User, _T], Union[Awaitable[None], None]]] = None,
        **kwargs,
    ) -> None:
        self.selection: Optional[_T] = None

        self._options = options
        self._exit_on_selection = exit_on_selection
        self._callback = callback

        num_options_per_page = num_options_per_page or len(options)
        if initial_emojis is not None:
            if len(initial_emojis) < num_options_per_page:
                raise ValueError(
                    "The number of emojis must be at least as large as the number of options on "
                    "each page."
                )

        elif num_options_per_page <= 10:
            # We can use numbers
            initial_emojis = [
                f"{i}\N{COMBINING ENCLOSING KEYCAP}" for i in range(1, num_options_per_page + 1)
            ]
        else:
            # We can (try to) use letters
            initial_emojis = [
                chr(ord("\N{REGIONAL INDICATOR SYMBOL LETTER A}") + i)
                for i in range(num_options_per_page)
            ]

        if len(initial_emojis) > 20:
            # We can't fuckin use ANYTHING (because only 20 reactions are allowed)
            raise ValueError("Too many options for a reaction menu! Must be 20 or fewer")

        super().__init__(initial_emojis=initial_emojis, **kwargs)

    @ReactionMenu.handler()
    async def handle_option(self, payload: discord.RawReactionActionEvent) -> None:
        emoji = str(payload.emoji)
        try:
            idx = self._initial_emojis.index(emoji)
        except ValueError:
            return
        else:
            if isinstance(self.channel, discord.abc.GuildChannel):
                user = self.channel.guild.get_member(payload.user_id)
            else:
                user = self.bot.get_user(payload.user_id)
            await self._option_selected(user, idx)
            if self._exit_on_selection is True:
                await self.exit_menu()

    async def _send(self, **kwargs) -> discord.Message:
        content, embed = await self._format_options_page(page_options=self._options, **kwargs)
        return await self.channel.send(content=content, embed=embed)

    async def _option_selected(self, user: discord.abc.User, idx: int) -> None:
        self.selection = self._options[idx][1]
        if self._callback is not None:
            ret = self._callback(user, self.selection)
            if inspect.isawaitable(ret):
                await ret

    # noinspection PyUnusedLocal
    async def _format_options_page(
        self,
        page_options: Sequence[Tuple[str, _T]],
        embed: bool = True,
        title: Optional[str] = None,
        embed_colour: Optional[discord.Colour] = None,
        **kwargs,
    ) -> Tuple[str, discord.Embed]:
        if self._initial_emojis[0] == "1\N{COMBINING ENCLOSING KEYCAP}":
            # The emojis themselves look big and ugly in the message.
            # The menu looks cleaner if we use inlined numbers/letters where possible.
            list_items = [f"`{i}.`" for i in range(1, len(page_options) + 1)]
        elif self._initial_emojis[0] == f"\N{REGIONAL INDICATOR SYMBOL LETTER A}":
            list_items = [f"`{chr(ord('A') + i)}.`" for i in range(len(page_options))]
        else:
            list_items = self._initial_emojis

        content = "\n".join((f"{li} {option[0]}" for li, option in zip(list_items, page_options)))

        if self.ctx is not None:
            ctx = self.ctx
        else:
            # Make a fake context
            ctx = cast(
                commands.Context,
                types.SimpleNamespace(
                    guild=getattr(self.channel, "guild", None), bot=self.bot, channel=self.channel
                ),
            )

        if embed is None:
            embed = await commands.Context.embed_requested(ctx)

        if embed is True:
            if embed_colour is None:
                embed_colour = await commands.Context.embed_colour(ctx)

            embed_ret = discord.Embed(title=title, description=content, colour=embed_colour)
            content = None
        else:
            if title is not None:
                content = "\n\n".join((underline(bold(title)), content))
            embed_ret = None

        return content, embed_ret


class PagedOptionsMenu(PagedMenu, OptionsMenu[_T], exit_button=True):
    """A combination of `PagedMenu` and `OptionsMenu`.

    This menu supports an arbitrary number of options in total. The
    number of initial reactions added will be the smallest of either
    the number of options provided, or the ``options_per_page``
    argument.

    The keyword arguments for this menu include all of those specified
    by the base classes. However, the ``pages`` argument is optional -
    if omitted, this menu will automatically generate the pages using
    the formatting keyword arguments specified with `OptionsMenu`.

    .. versionadded:: 3.2

    Keyword Arguments
    -----------------
    options_per_page : int
        The number of options to display on each page. Defaults to 5.
        Must be less than or equal to 20.
    emojis : Optional[Sequence[str]]
        Same as the ``emojis`` keyword argument to :class:`OptionsMenu`,
        however its size should be equal to ``options_per_page``. These
        should not include the page control or exit button emojis - they
        will be added to the end automatically.
    **others
        See `OptionsMenu` and `PagedMenu`, although remember that the
        ``pages`` argument is not required.

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            num_options_per_page=min(len(kwargs["options"]), kwargs.get("options_per_page", 5)),
            pages=kwargs.get("pages", []),
            **kwargs,
        )

    async def _before_send(
        self,
        options: Sequence[Tuple[str, _T]],
        pages: Optional[Sequence[str]] = None,
        options_per_page: int = 5,
        **kwargs,
    ) -> None:
        if not self._pages:
            # Generate our own pages
            for slice_start in range(0, len(options), options_per_page):
                page_options = options[slice_start : slice_start + options_per_page]
                self._pages.append(await self._format_options_page(page_options, **kwargs))
        self._options_per_page = options_per_page
        await super()._before_send(**kwargs)

    async def _option_selected(self, user: discord.abc.User, idx: int) -> None:
        # If an option is selected past the end of the options, select the last one instead
        option_idx = min(self._cur_page * self._options_per_page + idx, len(self._options) - 1)
        await super()._option_selected(user, option_idx)

    def _start_adding_reactions(self, emojis: Optional[Sequence[str]] = None) -> asyncio.Task:
        if emojis is None:
            emojis = self._initial_emojis
        return super()._start_adding_reactions([*emojis, *PagedMenu.INITIAL_EMOJIS])


# noinspection PyUnusedLocal
def start_adding_reactions(
    message: discord.Message,
    emojis: Iterable[_ReactableEmoji],
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.Task:
    """Start adding reactions to a message.

    This is a non-blocking operation - calling this will schedule the
    reactions being added, but the calling code will continue to
    execute asynchronously. There is no need to await this function.

    This is particularly useful if you wish to start waiting for a
    reaction whilst the reactions are still being added - in fact,
    this is exactly what `menu` uses to do that.

    This spawns and returns an `asyncio.Task` object.

    Parameters
    ----------
    message : discord.Message
        The message to add reactions to.
    emojis : Iterable[Union[str, discord.Emoji]]
        The emojis to react to the message with.
    loop : Optional[asyncio.AbstractEventLoop]
        This argument does nothing and is simply here for backwards
        compatibility.

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


# Original source of this legacy reaction-based menu idea from
# https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py
#
# Ported to Red V3 by Palm\_\_ (https://github.com/palmtree5)
async def menu(
    ctx: commands.Context,
    pages: List[_Page],
    controls: Dict[str, Union[Callable[..., Awaitable[None]], functools.partial]],
    message: discord.Message = None,
    page: int = 0,
    timeout: float = 30.0,
):
    """
    Legacy reaction-based menu function.

    We recommend using :class:`ReactionMenu` and/or its subclasses
    instead of this utility where possible.

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
    if controls is DEFAULT_CONTROLS:
        return await PagedMenu.send_and_wait(
            ctx=ctx, pages=pages, first_page=page, timeout=timeout
        )
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
        start_adding_reactions(message, controls.keys(), ctx.bot.loop)
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
        try:
            await message.clear_reactions()
        except discord.Forbidden:  # cannot remove all reactions
            for key in controls.keys():
                await message.remove_reaction(key, ctx.bot.user)
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


# noinspection PyUnusedLocal
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


DEFAULT_CONTROLS = {"⬅": prev_page, "❌": close_menu, "➡": next_page}
