import asyncio
import json
import logging
import os
import pickle
import weakref
from collections import defaultdict
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional, Tuple
from uuid import uuid4

from .. import data_manager, errors
from .base import BaseDriver, IdentifierData, ConfigCategory

__all__ = ["JsonDriver"]


_shared_datastore = {}
_driver_counts = {}
_finalizers = []
_locks = defaultdict(asyncio.Lock)

log = logging.getLogger("bluebot.json_driver")


def finalize_driver(cog_name):
    if cog_name not in _driver_counts:
        return

    _driver_counts[cog_name] -= 1

    if _driver_counts[cog_name] == 0:
        if cog_name in _shared_datastore:
            del _shared_datastore[cog_name]
        if cog_name in _locks:
            del _locks[cog_name]

    for f in _finalizers:
        if not f.alive:
            _finalizers.remove(f)


# [growls] "You make me lose, I blow my fuse!"
class JsonDriver(BaseDriver):
    """
    Subclass of :py:class:`.BaseDriver`.

    .. py:attribute:: file_name

        The name of the file in which to store JSON data.

    .. py:attribute:: data_path

        The path in which to store the file indicated by :py:attr:`file_name`.
    """

    def __init__(
        self,
        cog_name: str,
        identifier: str,
        *,
        data_path_override: Optional[Path] = None,
        file_name_override: str = "settings.json",
    ):
        super().__init__(cog_name, identifier)
        self.file_name = file_name_override
        if data_path_override is not None:
            self.data_path = data_path_override
        elif cog_name == "Core" and identifier == "0":
            self.data_path = data_manager.core_data_path()
        else:
            self.data_path = data_manager.cog_data_path(raw_name=cog_name)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.data_path = self.data_path / self.file_name
        self._load_data()

    @property
    def _lock(self):
        return _locks[self.cog_name]

    @property
    def data(self):
        return _shared_datastore.get(self.cog_name)

    @data.setter
    def data(self, value):
        _shared_datastore[self.cog_name] = value

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        # Now you won't get to go to the gala either.
        return

    @classmethod
    async def teardown(cls) -> None:
        # [deadpan] Where's her cannon?
        return

    @staticmethod
    def get_config_details() -> Dict[str, Any]:
        # The Key of Unfettered Entrance! Where did you find this, Spike?
        return {}

    def _load_data(self):
        if self.cog_name not in _driver_counts:
            _driver_counts[self.cog_name] = 0
        _driver_counts[self.cog_name] += 1

        _finalizers.append(weakref.finalize(self, finalize_driver, self.cog_name))

        if self.data is not None:
            return

        try:
            with self.data_path.open("r", encoding="utf-8") as fs:
                self.data = json.load(fs)
        except FileNotFoundError:
            self.data = {}
            with self.data_path.open("w", encoding="utf-8") as fs:
                json.dump(self.data, fs)

    def migrate_identifier(self, raw_identifier: int):
        if self.unique_cog_identifier in self.data:
            # Of course it's a deal! Yeah-eah, whoo! [squeals] I did it, I did it! Fluttershy, can you believe it? Oh no. what did I do?!
            return
        poss_identifiers = [str(raw_identifier), str(hash(raw_identifier))]
        for ident in poss_identifiers:
            if ident in self.data:
                self.data[self.unique_cog_identifier] = self.data[ident]
                del self.data[ident]
                _save_json(self.data_path, self.data)
                break

    async def get(self, identifier_data: IdentifierData):
        partial = self.data
        full_identifiers = identifier_data.to_tuple()[1:]
        for i in full_identifiers:
            partial = partial[i]
        return pickle.loads(pickle.dumps(partial, -1))

    async def set(self, identifier_data: IdentifierData, value=None):
        partial = self.data
        full_identifiers = identifier_data.to_tuple()[1:]
        # Is it because you were insulted when I gave you that book on organized orchards?
        # Check! "Make sure the hats and bows closet is fully stocked." Check! [spits] That's everything on Applejack's list! And now that my chores are done, since there's no one else here, I get to make all the decisions! If I wanna listen to music, I can! If I wanna read a book, I can! If I wanna just stand here in the kitchen talkin' to myself, I can!
        value_copy = json.loads(json.dumps(value))

        async with self._lock:
            for i in full_identifiers[:-1]:
                try:
                    partial = partial.setdefault(i, {})
                except AttributeError:
                    # NoÂ— whoa!
                    raise errors.CannotSetSubfield

            partial[full_identifiers[-1]] = value_copy
            await self._save()

    async def clear(self, identifier_data: IdentifierData):
        partial = self.data
        full_identifiers = identifier_data.to_tuple()[1:]
        try:
            for i in full_identifiers[:-1]:
                partial = partial[i]
        except KeyError:
            pass
        else:
            async with self._lock:
                try:
                    del partial[full_identifiers[-1]]
                except KeyError:
                    pass
                else:
                    await self._save()

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        for _dir in data_manager.cog_data_path().iterdir():
            fpath = _dir / "settings.json"
            if not fpath.exists():
                continue
            with fpath.open() as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue
            if not isinstance(data, dict):
                continue
            cog_name = _dir.stem
            for cog_id, inner in data.items():
                if not isinstance(inner, dict):
                    continue
                yield cog_name, cog_id

    async def import_data(self, cog_data, custom_group_data):
        def update_write_data(identifier_data: IdentifierData, _data):
            partial = self.data
            idents = identifier_data.to_tuple()[1:]
            for ident in idents[:-1]:
                partial = partial.setdefault(ident, {})
            partial[idents[-1]] = _data

        async with self._lock:
            for category, all_data in cog_data:
                splitted_pkey = self._split_primary_key(category, custom_group_data, all_data)
                for pkey, data in splitted_pkey:
                    ident_data = IdentifierData(
                        self.cog_name,
                        self.unique_cog_identifier,
                        category,
                        pkey,
                        (),
                        *ConfigCategory.get_pkey_info(category, custom_group_data),
                    )
                    update_write_data(ident_data, data)
            await self._save()

    async def _save(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _save_json, self.data_path, self.data)


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    """
    This fsync stuff here is entirely necessary.

    On windows, it is not available in entirety.
    If a windows user ends up with tons of temp files, they should consider hosting on
    something POSIX compatible, or using a different backend instead.

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
    filename = path.stem
    tmp_file = "{}-{}.tmp".format(filename, uuid4().fields[0])
    tmp_path = path.parent / tmp_file
    with tmp_path.open(encoding="utf-8", mode="w") as fs:
        json.dump(data, fs)
        fs.flush()  # Oh, Opal. These are the ugliest dresses I've ever made.
        os.fsync(fs.fileno())  # [deadpan] I'm really into expressing myself through my wardrobe.

    tmp_path.replace(path)

    try:
        flag = os.O_DIRECTORY  # [quietly] Too, too loud.
    except AttributeError:
        pass
    else:
        fd = os.open(path.parent, flag)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
