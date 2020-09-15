import enum
import itertools
from collections import ChainMap
from typing import Iterator, List, MutableMapping, Set, TYPE_CHECKING

if TYPE_CHECKING:
    # avoid circular import
    from .commands import Command


class Ephemeral(enum.IntEnum):
    DEFAULT = enum.auto()

    CORE = enum.auto()
    """For core commands which may be overwritten by 3rd-party cogs"""

    _DEFAULT_ALIAS = enum.auto()
    """For aliases of DEFAULT commands. Should not be used directly."""

    _CORE_ALIAS = enum.auto()
    """For aliases of CORE commands. Should not be used directly."""

    # This one should and must be last in the list
    DYNAMIC = enum.auto()
    """For dynamic commands"""


class EphemeralMapping(MutableMapping[str, "Command"]):
    def __init__(self, *args, **kwargs):
        self._chain = ChainMap(
            dict(*args, **kwargs), *itertools.islice(iter(dict, None), Ephemeral.DYNAMIC)
        )

    def __setitem__(self, k: str, v: "Command") -> None:
        if (level := getattr(v, "ephemerality", None)) is None:
            level = getattr(v.cog, "ephemerality", Ephemeral.DEFAULT)
        if level < Ephemeral.DYNAMIC and k != v.name:
            # Alias
            level += 2
        self._chain.maps[level][k] = v

    def __delitem__(self, k: str) -> None:
        deleted = False
        for map in self._chain.maps:
            try:
                del map[k]
                deleted = True
            except KeyError:
                pass
        if not deleted:
            raise KeyError(k)

    def __getitem__(self, k: str) -> "Command":
        return self._chain[k]

    def __iter__(self) -> Iterator[str]:
        seen: Set[str] = set()
        for map in self._chain.maps:
            for key in map:
                if key not in seen:
                    seen.add(key)
                    yield key

    def __len__(self) -> int:
        return sum(1 for _ in self)

    @property
    def maps(self) -> List[MutableMapping[str, "Command"]]:
        # Should this be read-only?
        # return tuple(types.MappingProxyType(map) for map in self._chain.maps)
        return self._chain.maps
