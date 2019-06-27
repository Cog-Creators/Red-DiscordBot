import asyncio
import functools
import inspect
import warnings
from typing import (
    Optional,
    Union,
    Awaitable,
    Generator,
    Any,
    TypeVar,
    AsyncIterator,
    List,
    Callable,
    AsyncIterable,
    Iterable,
    Tuple,
    Iterator,
    Sequence,
)

_T = TypeVar("_T")

__all__ = [
    "DeferrableTimer",
    "async_filter",
    "async_enumerate",
    "bounded_gather",
    "bounded_gather_iter",
]


class DeferrableTimer:
    """Countdown timer which can be deferred.

    This class can be used in place of things like `asyncio.wait_for` to
    control timeouts whilst awaiting a task, however this class has the
    advantage of being deferrable.

    Only one task can be waited on at a time. Waiting for a new task
    before the old one has completed or timed out will cause a
    `RuntimeWarning` to be issued. For this reason, it is recommended
    to create a new `DeferrableTimer` for every task.

    Parameters
    ----------
    timeout : Optional[float]
        The timeout period. If ``None``, then the timer basically
        serves no purpose and `~DeferrableTimer.wait_for` will only
        return once the task is complete.

    Examples
    --------
    Say for example, we want to wait for a particular reaction to a
    message, or time out after a certain period. But if someone reacts
    with a different emoji, we want to restart the timeout period to
    give them extra time::

        class MyCog(commands.Cog):

            def __init__(self):
                self._timers = {}

            @commands.guild_only()
            @commands.command()
            async def mycommand(self, ctx):
                msg = await ctx.send("Give me the right reaction!")
                self._timers[msg.id] = timer = DeferrableTimer(timeout=30)
                try:
                    reaction, user = await timer.wait_for(
                        ctx.bot.wait_for(
                            "reaction_add", check=lambda r, u: r.emoji.name == "yeet"
                        )
                    )
                except asyncio.TimeoutError:
                    await msg.edit(content="You took too long.")
                else:
                    await msg.edit(content=f"{user.display_name} got there first!")
                finally:
                    del self._timers[msg.id]

            @commands.Cog.listener()
            async def on_reaction_add(self, reaction, user):
                if reaction.message.id in self._timers:
                    self._timers[reaction.message.id].restart()

    """

    def __init__(self, timeout: Optional[float] = None) -> None:
        self.timeout = timeout
        self._loop = asyncio.get_running_loop()
        self._future: Optional[asyncio.Future] = None
        self._task: Optional[asyncio.Task] = None
        self._timer_handle: Optional[asyncio.TimerHandle] = None

    async def wait_for(
        self, aw: Union[Awaitable[_T], Generator[None, Any, _T], functools.partial]
    ) -> _T:
        """Wait for an `awaitable` to either complete or time out.

        Parameters
        ----------
        aw
            The awaitable object. If it isn't already an `asyncio.Task`,
            it will be wrapped in one.

        """
        if self._task is not None and self._task.done() is False:
            warnings.warn(
                "Waiting for a task before the previous one has completed or timed out is not "
                "recommended",
                RuntimeWarning,
            )

        if isinstance(aw, asyncio.Task):
            self._task = aw
        elif self.__isawaitable(aw):
            self._task = self._loop.create_task(aw)
        else:
            raise TypeError('"aw" must be an awaitable object')

        self._future = self._loop.create_future()

        self._task.add_done_callback(self.__task_done)
        if self.timeout is not None:
            self._timer_handle = self._loop.call_later(self.timeout, self.__task_timed_out)

        result = await self._future
        if result is False:
            raise asyncio.TimeoutError
        else:
            if self._timer_handle is not None:
                self._timer_handle.cancel()
            return self._task.result()

    def restart(self) -> None:
        """Restart the timer, using the timeout value given on
        instantiation.

        Raises
        ------
        RuntimeError
            If this method is called before `~DeferrableTimer.wait_for`
            is called.

        """
        if self.timeout is None:
            return
        if self._timer_handle is None:
            raise RuntimeError("Cannot restart before waiting")
        self._timer_handle.cancel()
        self._timer_handle = self._loop.call_later(self.timeout, self.__task_timed_out)

    def cancel(self) -> bool:
        """Cancel the timer.

        This will cause the `DeferrableTimer.wait_for` call to raise
        `asyncio.CancelledError`.

        Returns
        -------
        bool
            ``True`` if the task was not already complete or timed out,
            or ``False`` otherwise.

        Raises
        ------
        RuntimeError
            If this method is called before `~DeferrableTimer.wait_for`
            is called.

        """
        if self._task is None:
            raise RuntimeError("Cannot cancel before waiting")
        if self._future.done():
            return False
        else:
            self._task.cancel()
            self._future.cancel()
            if self._timer_handle is not None:
                self._timer_handle.cancel()
            return True

    def __task_done(self, task: asyncio.Task) -> None:
        if not task.cancelled():
            self._future.set_result(True)

    def __task_timed_out(self) -> None:
        self._task.cancel()
        if not self._future.cancelled():
            self._future.set_result(False)

    @staticmethod
    def __isawaitable(obj: Any) -> bool:
        return inspect.isawaitable(obj) or (
            isinstance(obj, functools.partial) and inspect.isawaitable(obj.func)
        )


# https://github.com/PyCQA/pylint/issues/2717
class AsyncFilter(AsyncIterator[_T], Awaitable[List[_T]]):  # pylint: disable=duplicate-bases
    """Class returned by `async_filter`. See that function for details.

    We don't recommend instantiating this class directly.
    """

    def __init__(
        self,
        func: Callable[[_T], Union[bool, Awaitable[bool]]],
        iterable: Union[AsyncIterable[_T], Iterable[_T]],
    ) -> None:
        self.__func: Callable[[_T], Union[bool, Awaitable[bool]]] = func
        self.__iterable: Union[AsyncIterable[_T], Iterable[_T]] = iterable

        # We assign the generator strategy based on the arguments' types
        if isinstance(iterable, AsyncIterable):
            if asyncio.iscoroutinefunction(func):
                self.__generator_instance = self.__async_generator_async_pred()
            else:
                self.__generator_instance = self.__async_generator_sync_pred()
        elif asyncio.iscoroutinefunction(func):
            self.__generator_instance = self.__sync_generator_async_pred()
        else:
            raise TypeError("Must be either an async predicate, an async iterable, or both.")

    async def __sync_generator_async_pred(self) -> AsyncIterator[_T]:
        for item in self.__iterable:
            if await self.__func(item):
                yield item

    async def __async_generator_sync_pred(self) -> AsyncIterator[_T]:
        async for item in self.__iterable:
            if self.__func(item):
                yield item

    async def __async_generator_async_pred(self) -> AsyncIterator[_T]:
        async for item in self.__iterable:
            if await self.__func(item):
                yield item

    async def __flatten(self) -> List[_T]:
        return [item async for item in self]

    def __aiter__(self):
        return self

    def __await__(self):
        # Simply return the generator filled into a list
        return self.__flatten().__await__()

    def __anext__(self) -> Awaitable[_T]:
        # This will use the generator strategy set in __init__
        return self.__generator_instance.__anext__()


def async_filter(
    func: Callable[[_T], Union[bool, Awaitable[bool]]],
    iterable: Union[AsyncIterable[_T], Iterable[_T]],
) -> AsyncFilter[_T]:
    """Filter an (optionally async) iterable with an (optionally async) predicate.

    At least one of the arguments must be async.

    Parameters
    ----------
    func : Callable[[T], Union[bool, Awaitable[bool]]]
        A function or coroutine function which takes one item of ``iterable``
        as an argument, and returns ``True`` or ``False``.
    iterable : Union[AsyncIterable[_T], Iterable[_T]]
        An iterable or async iterable which is to be filtered.

    Raises
    ------
    TypeError
        If neither of the arguments are async.

    Returns
    -------
    AsyncFilter[T]
        An object which can either be awaited to yield a list of the filtered
        items, or can also act as an async iterator to yield items one by one.

    """
    return AsyncFilter(func, iterable)


async def async_enumerate(
    async_iterable: AsyncIterable[_T], start: int = 0
) -> AsyncIterator[Tuple[int, _T]]:
    """Async iterable version of `enumerate`.

    Parameters
    ----------
    async_iterable : AsyncIterable[T]
        The iterable to enumerate.
    start : int
        The index to start from. Defaults to 0.

    Returns
    -------
    AsyncIterator[Tuple[int, T]]
        An async iterator of tuples in the form of ``(index, item)``.

    """
    async for item in async_iterable:
        yield start, item
        start += 1


async def _sem_wrapper(sem, task):
    async with sem:
        return await task


def bounded_gather_iter(
    *coros_or_futures,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    limit: int = 4,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Iterator[Union[Awaitable[Any], Generator[None, Any, Any]]]:
    """
    An iterator that returns tasks as they are ready, but limits the
    number of tasks running at a time.

    Parameters
    ----------
    *coros_or_futures
        The awaitables to run in a bounded concurrent fashion.
    loop : asyncio.AbstractEventLoop
        The event loop to use for the semaphore and :meth:`asyncio.gather`.
    limit : Optional[`int`]
        The maximum number of concurrent tasks. Used when no ``semaphore``
        is passed.
    semaphore : Optional[:class:`asyncio.Semaphore`]
        The semaphore to use for bounding tasks. If `None`, create one
        using ``loop`` and ``limit``.

    Raises
    ------
    TypeError
        When invalid parameters are passed
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    if semaphore is None:
        if not isinstance(limit, int) or limit <= 0:
            raise TypeError("limit must be an int > 0")

        semaphore = asyncio.Semaphore(limit, loop=loop)

    pending = []

    for cof in coros_or_futures:
        # noinspection PyProtectedMember
        if asyncio.isfuture(cof) and cof._loop is not loop:
            raise ValueError("futures are tied to different event loops")

        cof = _sem_wrapper(semaphore, cof)
        pending.append(cof)

    return asyncio.as_completed(pending, loop=loop)


def bounded_gather(
    *coros_or_futures,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    return_exceptions: bool = False,
    limit: int = 4,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Awaitable[Sequence[Any]]:
    """
    A semaphore-bounded wrapper to :meth:`asyncio.gather`.

    Parameters
    ----------
    *coros_or_futures
        The awaitables to run in a bounded concurrent fashion.
    loop : asyncio.AbstractEventLoop
        The event loop to use for the semaphore and :meth:`asyncio.gather`.
    return_exceptions : bool
        If true, gather exceptions in the result list instead of raising.
    limit : Optional[`int`]
        The maximum number of concurrent tasks. Used when no ``semaphore``
        is passed.
    semaphore : Optional[:class:`asyncio.Semaphore`]
        The semaphore to use for bounding tasks. If `None`, create one
        using ``loop`` and ``limit``.

    Raises
    ------
    TypeError
        When invalid parameters are passed
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    if semaphore is None:
        if not isinstance(limit, int) or limit <= 0:
            raise TypeError("limit must be an int > 0")

        semaphore = asyncio.Semaphore(limit, loop=loop)

    tasks = (_sem_wrapper(semaphore, task) for task in coros_or_futures)

    return asyncio.gather(*tasks, loop=loop, return_exceptions=return_exceptions)
