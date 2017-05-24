import functools
import json
import os
import asyncio
import aiofiles
import logging
from uuid import uuid4

# This is basically our old DataIO, except that it's now threadsafe
# and just a base for much more elaborate classes


log = logging.getLogger("red")

PRETTY = {"indent": 4, "sort_keys": True, "separators": (',', ' : ')}
MINIFIED = {"sort_keys": True, "separators": (',', ':')}


class JsonIO:
    """Basic functions for atomic saving / loading of json files"""
    _lock = asyncio.Lock()

    def _get_tmp_file(self, path):
        filename, _ = os.path.splitext(path)
        tmp_file = "{}-{}.tmp".format(filename, uuid4().fields[0])
        return tmp_file

    def _save_json(self, path, data, settings=PRETTY):
        log.debug("Saving file {}".format(path))
        tmp_file = self._get_tmp_file(path)
        with open(tmp_file, encoding="utf-8", mode="w") as f:
            json.dump(data, f, **settings)
        os.replace(tmp_file, path)

    async def _threadsafe_save_json(self, path, data, settings=PRETTY):
        tmp_path = self._get_tmp_file(path)
        async with aiofiles.open(tmp_path, encoding='utf-8', mode='w') as f:
            data = json.dumps(data, **settings)
            await f.write(data)
        os.replace(tmp_path, path)

    def _load_json(self, path):
        log.debug("Reading file {}".format(path))
        with open(path, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    async def _threadsafe_load_json(self, path):
        async with aiofiles.open(path, encoding='utf-8', mode='r') as f:
            data = await f.read()
            return json.loads(data)
