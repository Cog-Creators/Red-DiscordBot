import builtins
import os
import pickle
from uuid import uuid4

from typing import Tuple
from functools import lru_cache
from pathlib import Path

try:
    import xxhash
except ImportError:
    xxhash = None

# Using an lru cache here rather than storing data about hashes per object
# Due to our design, this should have a good size/performance tradeoff
# An example of why: all cogs which use ``config.member(same_member)``
# would have the same primary key for that member.
# The structure below only operates on the primary key.


@lru_cache(maxsize=256)
def _get_bin(k: str, bin_count: int) -> int:
    return xxhash.xxh32(k).intdigest() % bin_count


class _SafishUnpickler(pickle.Unpickler):

    _safeish_builtins = ("tuple", "dict", "complex", "int", "float", "bool", "None", "str")

    def find_class(self, module, name):
        if module == "builtins" and name in self._safeish_builtins:
            return getattr(builtins, name)
        raise pickle.UnpicklingError("Not unpickling data which wasn't provided via this.")

    # We could also add an HMAC, but limiting the types allowed should realistically be plenty
    # If people are taking arbitrary files from other people, there are certain risks we shouldn't
    # be designing for.


class XXHashStorage:
    """
    This exists seperately from config to allow using this outside of config.
    """

    def __init__(self, path: Path, bin_count: int, *, load_on_creation: bool = False):
        self.data_path = path
        self._bin_count = bin_count
        self._bins = [dict() for _ in range(bin_count)]
        if load_on_creation:
            self.load()
            self._loaded_bins = set(range(bin_count))
        else:
            self._loaded_bins = set()

    def load(self, *bins):
        bins = bins or range(self._bin_count)
        for i in bins:
            if i not in self._loaded_bins:
                self._loaded_bins.add(i)
                fpath = self.data_path / f"{i}.pickle"
                if fpath.exists() and fpath.is_file():
                    with fpath.open(mode="rb") as fp:
                        try:
                            data = _SafishUnpickler(fp).load()
                        except pickle.UnpicklingError:
                            self._bins[i] = dict()
                        else:
                            self._bins[i] = data
                else:
                    self._bins[i] = dict()

    def insert(self, key, value):
        """ Inserts a value, returning the bin number which was changed """
        b = _get_bin(".".join(key), self._bin_count)
        self.load(b)
        # We dont want to be sticking user provided mutables into this.
        value_copy = pickle.loads(pickle.dumps(value))
        self._bins[b][key] = value_copy
        return b

    def iter_by_key_prefix(self, key_prefix):
        self.load()

        def is_prefixed(key):
            return key[: len(key_prefix)] == key_prefix

        for b in self._bins:
            for k, v in b.items():
                if is_prefixed(k):
                    yield k, v

    def clear(self, key) -> int:
        """ clears a specific key, returning the bin number which was changed """
        b = _get_bin(".".join(key), self._bin_count)
        self.load(b)
        self._bins[b].pop(key, None)
        return b

    def get(self, key):
        b = _get_bin(".".join(key), self._bin_count)
        self.load(b)
        val = self._bins[b][key]
        # Don't give back a anything from the actual internal data structure
        return pickle.loads(pickle.dumps(val))

    def write_bins(self, *bin_numbers: int):
        """ 
        For config's use, this needs to be wrapped in a lock. 

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
        """  # Consider making a custom context manager for this extra behavior?
        for b in bin_numbers:
            path = self.data_path / f"{b}.pickle"
            tmp_file = f"{b}.pickle-{uuid4().fields[0]}.tmp"
            tmp_path = self.data_path / tmp_file

            with tmp_path.open(mode="wb") as fs:
                pickle.dump(self._bins[b], fs)
                fs.flush()  # This does get closed on context exit, ...
                os.fsync(fs.fileno())  # but that needs to happen prior to this line

            tmp_path.replace(path)

            try:
                flag = os.O_DIRECTORY  # pylint: disable=no-member
            except AttributeError:
                pass
            else:
                fd = os.open(path.parent, flag)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
