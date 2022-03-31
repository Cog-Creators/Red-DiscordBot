import collections
from typing import Any, Iterable, Sequence


class LRUDict:
    """
    Dictionary with LRU-eviction and maximum-size, intended for caching.

    Attributes
    ----------
    keyval_pairs : Sequence[Iterable[Any]]
        A sequence of key value pairs to instantiate the dictionary.
    size : int
        The maximum size of the dictionary at any given time.
    """

    def __init__(self, *keyval_pairs: Sequence[Iterable[Any]], size: int):
        self.size = size
        self._dict = collections.OrderedDict(*keyval_pairs)

    def __len__(self):
        return len(self._dict)

    def __bool__(self):
        return bool(self._dict)

    def __contains__(self, key):
        if key in self._dict:
            self._dict.move_to_end(key, last=True)
            return True
        return False

    def __getitem__(self, key):
        ret = self._dict.__getitem__(key)
        self._dict.move_to_end(key, last=True)
        return ret

    def __setitem__(self, key, value):
        if key in self._dict:
            self._dict.move_to_end(key, last=True)
        self._dict[key] = value
        if len(self._dict) > self.size:
            self._dict.popitem(last=False)

    def __delitem__(self, key):
        return self._dict.__delitem__(key)

    def clear(self):
        return self._dict.clear()

    def pop(self, key):
        return self._dict.pop(key)

    # all of the below access all of the items, and therefore shouldn't modify the ordering for eviction
    def keys(self):
        return self._dict.keys()

    def items(self):
        return self._dict.items()

    def values(self):
        return self._dict.values()
