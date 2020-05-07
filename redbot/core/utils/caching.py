import collections
from typing import MutableMapping, TypeVar, Iterator, KeysView, ItemsView, ValuesView

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class LRUDict(MutableMapping[_KT, _VT]):
    """
    dict with LRU-eviction and max-size

    This is intended for caching, it may not behave how you want otherwise

    This uses collections.OrderedDict under the hood, but does not directly expose
    all of it's methods (intentional)
    """

    def __init__(self, *keyval_pairs, size):
        self._size = size
        self._dict = collections.OrderedDict(*keyval_pairs)

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        while len(self._dict) > value:
            self._dict.popitem()
        self._size = value

    def __contains__(self, key: _KT) -> bool:
        if key in self._dict:
            self._dict.move_to_end(key, last=True)
            return True
        return False

    def __getitem__(self, key: _KT) -> _VT:
        ret = self._dict.__getitem__(key)
        self._dict.move_to_end(key, last=True)
        return ret

    def __setitem__(self, key: _KT, value: _VT) -> None:
        if key in self._dict:
            self._dict.move_to_end(key, last=True)
        self._dict[key] = value
        if len(self._dict) > self.size:
            self._dict.popitem(last=False)

    def __delitem__(self, key: _KT) -> None:
        return self._dict.__delitem__(key)

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[_KT]:
        return iter(self._dict)

    def clear(self) -> None:
        return self._dict.clear()

    def pop(self, key: _KT) -> _VT:
        return self._dict.pop(key)

    # all of the below access all of the items, and therefore shouldn't modify the ordering for eviction
    def keys(self) -> KeysView[_KT]:
        return self._dict.keys()

    def items(self) -> ItemsView[_KT, _VT]:
        return self._dict.items()

    def values(self) -> ValuesView[_VT]:
        return self._dict.values()
