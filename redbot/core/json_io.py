import functools
import json
import os
import asyncio
import logging
from copy import deepcopy
from uuid import uuid4

# This is basically our old DataIO and just a base for much more elaborate classes
# This still isn't completely threadsafe, (do not use config in threads)
from pathlib import Path

log = logging.getLogger("red")

PRETTY = {"indent": 4, "sort_keys": False, "separators": (",", " : ")}
MINIFIED = {"sort_keys": False, "separators": (",", ":")}


class JsonIO:
    """Basic functions for atomic saving / loading of json files"""

    def __init__(self, path: Path = Path.cwd()):
        """
        :param path: Full path to file.
        """
        self._lock = asyncio.Lock()
        self.path = path



    # noinspection PyUnresolvedReferences
    def _load_json(self):
        with self.path.open(encoding="utf-8", mode="r") as f:
            data = json.load(f)
        return data

    async def _threadsafe_load_json(self, path):
        loop = asyncio.get_event_loop()
        func = functools.partial(self._load_json, path)
        async with self._lock:
            return await loop.run_in_executor(None, func)
