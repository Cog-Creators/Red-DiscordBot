import functools
import json
import os
import asyncio
import logging
from uuid import uuid4

# This is basically our old DataIO, except that it's now threadsafe
# and just a base for much more elaborate classes
from pathlib import Path

log = logging.getLogger("red")

PRETTY = {"indent": 4, "sort_keys": True, "separators": (",", " : ")}
MINIFIED = {"sort_keys": True, "separators": (",", ":")}


class JsonIO:
    """Basic functions for atomic saving / loading of json files"""

    def __init__(self, path: Path = Path.cwd()):
        """
        :param path: Full path to file.
        """
        self._lock = asyncio.Lock()
        self.path = path

    # noinspection PyUnresolvedReferences
    def _save_json(self, data, settings=PRETTY):
        log.debug("Saving file {}".format(self.path))
        filename = self.path.stem
        tmp_file = "{}-{}.tmp".format(filename, uuid4().fields[0])
        tmp_path = self.path.parent / tmp_file
        with tmp_path.open(encoding="utf-8", mode="w") as f:
            json.dump(data, f, **settings)
        tmp_path.replace(self.path)

    async def _threadsafe_save_json(self, data, settings=PRETTY):
        loop = asyncio.get_event_loop()
        func = functools.partial(self._save_json, data, settings)
        with await self._lock:
            await loop.run_in_executor(None, func)

    # noinspection PyUnresolvedReferences
    def _load_json(self):
        log.debug("Reading file {}".format(self.path))
        with self.path.open(encoding="utf-8", mode="r") as f:
            data = json.load(f)
        return data

    async def _threadsafe_load_json(self, path):
        loop = asyncio.get_event_loop()
        func = functools.partial(self._load_json, path)
        task = loop.run_in_executor(None, func)
        with await self._lock:
            return await asyncio.wait_for(task)
