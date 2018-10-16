from asyncio import PriorityQueue, AbstractEventLoop, get_event_loop
import time
from contextlib import suppress


class Scheduler:
    def __init__(self, loop: AbstractEventLoop = None):
        self._loop = get_event_loop() if loop is None else loop
        self._scheduled_funcs = PriorityQueue(loop=self._loop)
        self.counter = 0
        self.events = {}
        self.events_at_shutdown = {}

        self.shutting_down = False
        self._runner_task = self._loop.create_task(self._runner())

    def loop(
        self,
        func,
        period: int,
        name=None,
        args=[],
        kwargs={},
        now: bool = False,
        call_at_shutdown: bool = False,
    ):
        async def wrapper():
            try:
                await func(*args, **kwargs)
            except Exception as e:
                pass
            finally:
                if not self.shutting_down:
                    return self.call_once(
                        wrapper, delay=period, name=name, call_at_shutdown=call_at_shutdown
                    )

        if now is True:
            return self.call_once(wrapper, delay=0, name=name, call_at_shutdown=call_at_shutdown)

    def call_once(
        self, func, delay: int = 0, name=None, args=[], kwargs={}, call_at_shutdown: bool = False
    ):
        if self.shutting_down:
            raise RuntimeError("Cannot add new calls because the bot is currently shutting down.")

        if name is None:
            name = self.counter
            self.counter += 1

        if name in self.events or name in self.events_at_shutdown:
            raise ValueError("An event with that name has already been scheduled")

        call_time = time.time() + delay
        self._scheduled_funcs.put_nowait((call_time, (name, args, kwargs)))

        if delay >= 0:
            self.events[name] = func
        if call_at_shutdown is True:
            self.events_at_shutdown[name] = func

        return name

    def call_at_shutdown(self, func, name=None, args=[], kwargs={}):
        return self.call_once(
            func, delay=-1, name=name, args=args, kwargs=kwargs, call_at_shutdown=True
        )

    def remove(self, name):
        with suppress(KeyError):
            del self.events[name]

        with suppress(KeyError):
            del self.events_at_shutdown[name]

    async def _runner(self):
        while not self.shutting_down:
            t, (name, args, kwargs) = await self._scheduled_funcs.get()
            if name not in self.events:
                continue
            if t < time.time():
                func = self.events[name]
                await func(*args, **kwargs)
            else:
                await self._scheduled_funcs.put((t, (name, args, kwargs)))

        while not self._scheduled_funcs.empty():
            _, (name, args, kwargs) = await self._scheduled_funcs.get()
            if name in self.events_at_shutdown:
                func = self.events_at_shutdown[name]
                await func(*args, **kwargs)
