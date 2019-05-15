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

    def __init__(self, path: Path):
        """
        :param path: Full path to file.
        """
        self._lock = asyncio.Lock()
        self.path = path

    # noinspection PyUnresolvedReferences
    def _save_json(self, data, settings=PRETTY):
        """
        This fsync stuff here is entirely neccessary. 
        
        On windows, it is not available in entirety.
        If a windows user ends up with tons of temp files, they should consider hosting on
        something POSIX compatible, or using the mongo backend instead.

        Most users wont encounter this issue, but with high write volumes, 
        without the fsync on both the temp file, and after the replace on the directory,
        There's no real durability or atomicity guarantee from the filesystem.

        In depth overview of underlying reasons why this is needed:
            https://lwn.net/Articles/457667/

        Also see:  
            http://man7.org/linux/man-pages/man2/open.2.html#NOTES (synchronous I/O section)
        And:
            https://www.mjmwired.net/kernel/Documentation/filesystems/ext4.txt#310
        """
        filename = self.path.stem
        tmp_file = "{}-{}.tmp".format(filename, uuid4().fields[0])
        tmp_path = self.path.parent / tmp_file
        with tmp_path.open(encoding="utf-8", mode="w") as f:
            json.dump(data, f, **settings)
            f.flush()  # This does get closed on context exit, ...
            os.fsync(f.fileno())  #  but that needs to happen prior to this line

        tmp_path.replace(self.path)

        # pylint: disable=E1101
        try:
            fd = os.open(self.path.parent, os.O_DIRECTORY)
            os.fsync(fd)
        except AttributeError:
            fd = None
        finally:
            if fd is not None:
                os.close(fd)

    async def _threadsafe_save_json(self, data, settings=PRETTY):
        loop = asyncio.get_event_loop()
        # the deepcopy is needed here. otherwise,
        # the dict can change during serialization
        # and this will break the encoder.
        data_copy = deepcopy(data)
        func = functools.partial(self._save_json, data_copy, settings)
        async with self._lock:
            await loop.run_in_executor(None, func)

    def _load_json(self):
        with self.path.open(encoding="utf-8", mode="r") as f:
            data = json.load(f)
        return data
