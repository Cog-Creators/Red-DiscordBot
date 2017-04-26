import asyncio
import functools
import json
import os
from uuid import uuid4

DEFAULT_JSON_SETTINGS = {
                         "indent": 4,
                         "sort_keys": True,
                         "separators": (',', ' : ')
                        }


class JSONAutosave:
    def __init__(self, interval=5, **settings):
        self.interval = interval
        self._queue = {}
        self._lock = asyncio.Lock()
        self._json_settings = settings.pop("json_settings",
                                           DEFAULT_JSON_SETTINGS)
        self.loop = asyncio.get_event_loop()
        self.task = self.loop.create_task(self._process_queue())

    def add_to_queue(self, path, data):
        self._queue[path] = data

    async def _process_queue(self):
        try:
            while True:
                print("looping")
                queue = self._queue.copy()
                self._queue = {}
                for path, data in queue.items():
                    with await self._lock:
                        func = functools.partial(self._save_json, path, data)
                        try:
                            await self.loop.run_in_executor(None, func)
                        except Exception as e:
                            print(e) # Proper logging here

                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass

    def _save_json(self, path, data):
        print("Saving " + path)
        path, _ = os.path.splitext(path)
        tmp_file = "{}-{}.tmp".format(path, uuid4().fields[0])
        with open(tmp_file, encoding="utf-8", mode="w") as f:
            json.dump(data, f, **self._json_settings)
        os.replace(tmp_file, path)