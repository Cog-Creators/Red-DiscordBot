import collections
import warnings
from typing import Any, KeysView, ItemsView, Iterator, MutableMapping, TypeVar, ValuesView

from .base import IdentifierData


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class LRUDict(MutableMapping[_KT, _VT]):
    """
    dict with LRU-eviction and max-size

    This is intended for caching, it may not behave how you want otherwise

    This uses collections.OrderedDict under the hood, but does not directly expose
    all of its methods.
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

    # all of the below access all of the items, and therefore shouldnt modify the ordering for
    # eviction
    def keys(self) -> KeysView[_KT]:
        return self._dict.keys()

    def items(self) -> ItemsView[_KT, _VT]:
        return self._dict.items()

    def values(self) -> ValuesView[_VT]:
        return self._dict.values()


class ConfigDriverCache(MutableMapping[IdentifierData, Any]):
    def __init__(self, max_size: int = 1024) -> None:
        self._dict: LRUDict[IdentifierData, Any] = LRUDict(size=max_size)

    @property
    def max_size(self) -> int:
        return self._dict.size

    @max_size.setter
    def max_size(self, value: int) -> None:
        self._dict.size = value

    def __getitem__(self, ident: IdentifierData) -> Any:
        popped_keys = []
        while True:
            try:
                value = self._dict[ident]
            except KeyError:
                # ident isn't cached itself, maybe a parent is cached?
                try:
                    popped_key, ident = ident.get_parent()
                except IndexError:
                    break
                else:
                    popped_keys.append(popped_key)
            else:
                inner = value
                for key in reversed(popped_keys):
                    if inner is KeyError:
                        break
                    inner = inner[key]
                return inner
        raise KeyError(ident)

    def __setitem__(self, ident: IdentifierData, value: Any) -> None:
        if ident in self._dict:
            # If the ident is already cached, we know there are no children or parents, so it can
            # simply set itself and return
            self._dict[ident] = value
            return

        # Look for parents: if a parent ident is cached, set this value within the parent's data
        try:
            parent_key = next(k for k in self._dict if k > ident)
        except StopIteration:
            pass
        else:
            inner = self._dict[parent_key]
            if inner is KeyError:
                del self._dict[parent_key]
            else:
                keys = ident.primary_key + ident.identifiers
                common_prefix_len = len(parent_key.primary_key) + len(parent_key.identifiers)
                for key in keys[common_prefix_len:-1]:
                    if inner.get(key) is KeyError:
                        del inner[key]
                    try:
                        inner = inner.setdefault(key, {})
                    except AttributeError:
                        # Tried to set sub-field of non-object
                        # Driver should have already caught this - There's a bug somewhere!
                        warnings.warn(
                            "Config cache anomaly! Please report this message.", RuntimeWarning
                        )
                        # Attempt a cleanup
                        del self._dict[parent_key]
                        self._dict[ident] = value
                        return

                inner[keys[-1]] = value

                # Since there was a parent, there can't be any children
                return

        # At this point, there were no parents.
        # Cache the value and make sure there are no children cached.
        self._dict[ident] = value
        self._del_children(ident)

    def __delitem__(self, ident: IdentifierData) -> None:
        try:
            del self._dict[ident]
        except KeyError:
            if not self._del_children(ident):
                raise KeyError(ident)

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[IdentifierData]:
        return iter(self._dict)

    def clear(self) -> None:
        self._dict.clear()

    def _del_children(self, ident: IdentifierData) -> bool:
        deleted = False
        child_keys = [k for k in self._dict if k < ident]
        for child_key in child_keys:
            del self._dict[child_key]
            deleted = True
        return deleted
