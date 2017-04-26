import functools
import json
import os
import asyncio
import logging
from uuid import uuid4

# This is basically our old DataIO, except that it's now threadsafe
# and just a base for much more elaborate classes


log = logging.getLogger("red")

PRETTY = {"indent": 4, "sort_keys": True, "separators": (',', ' : ')}
MINIFIED = {"sort_keys": True, "separators": (',', ':')}


class JsonIO:
    """Basic functions for atomic saving / loading of json files

    This is inherited by the flusher and db helpers"""

    def _save_json(self, path, data, settings=PRETTY):
        log.debug("Saving file {}".format(path))
        filename, _ = os.path.splitext(path)
        tmp_file = "{}-{}.tmp".format(filename, uuid4().fields[0])
        with open(tmp_file, encoding="utf-8", mode="w") as f:
            json.dump(data, f, **settings)
        os.replace(tmp_file, path)

    async def _threadsafe_save_json(self, path, data, settings=PRETTY):
        loop = asyncio.get_event_loop()
        func = functools.partial(self._save_json, path, data, settings)
        await loop.run_in_executor(None, func)

    def _load_json(self, path):
        log.debug("Reading file {}".format(path))
        with open(path, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    async def _threadsafe_load_json(self, path):
        loop = asyncio.get_event_loop()
        func = functools.partial(self._load_json, path)
        task = loop.run_in_executor(None, func)
        return await asyncio.wait_for(task)
