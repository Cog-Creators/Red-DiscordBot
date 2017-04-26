import asyncio
import logging
from core.json_io import JsonIO, PRETTY

# This is where individual cogs can queue low priority writes to files
#
# Only the last queued write to a file actually gets executed.
# This helps considerably in reducing the total writes (especially in poorly
# coded cogs that would otherwise hammer the system with them)
#
# The flusher is used by the DB helpers in autosave mode
#
# The JSONFlusher class is supposed to be instanced only once, at boot

log = logging.getLogger("red")
_flusher = None


class JSONFlusher(JsonIO):
    def __init__(self, interval=5, **settings):
        self.interval = interval
        self._queue = {}
        self._lock = asyncio.Lock()
        self._json_settings = settings.pop("json_settings", PRETTY)
        self._loop = asyncio.get_event_loop()
        self.task = self._loop.create_task(self._process_queue())

    def add_to_queue(self, path, data):
        """Schedules a json file for later write

        Calling this function multiple times with the same path will
        result in only the last one getting scheduled"""
        self._queue[path] = data

    def remove_from_queue(self, path):
        """Removes json file from the writing queue"""
        try:
            del self._queue[path]
        except:
            pass

    async def _process_queue(self):
        try:
            while True:
                queue = self._queue.copy()
                self._queue = {}
                for path, data in queue.items():
                    with await self._lock:
                        try:
                            await self._threadsafe_save_json(path,
                                                             data,
                                                             self._json_settings)
                        except Exception as e:
                            log.critical("Flusher failed to write: {}"
                                         "".format(e))
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            if self._queue:
                log.warning("Flusher interrupted with "
                            "non-empty queue")
            else:
                log.debug("Flusher shutting down.")


def init_flusher():
    """Instances the flusher and initializes its task"""
    global _flusher
    _flusher = JSONFlusher()


def get_flusher():
    """Returns the global flusher instance"""
    if _flusher is None:
        raise RuntimeError("The flusher has not been initialized.")
    return _flusher
