from __future__ import annotations  # py3.9-style string annotations
import asyncio
import contextlib
import enum
from itertools import islice
from reprlib import recursive_repr
from typing import Optional, TYPE_CHECKING, ChainMap, Iterator, MutableMapping, Tuple, Union

if TYPE_CHECKING:
    # avoid circular import
    from .commands import Command


__all__ = ["Ephemeral"]


class Ephemeral(enum.IntEnum):
    DEFAULT = 0

    EPHEMERAL = enum.auto()
    """For ephemeral commands which may be overwritten by other cogs."""

    # Items marked with a leading underscore will error Command's __init__
    _DEFAULT_ALIAS = enum.auto()
    """For aliases of DEFAULT commands. Should not be used directly."""

    _EPHEMERAL_ALIAS = enum.auto()
    """For aliases of EPHEMERAL commands. Should not be used directly."""

    # This one should and must be last in the list
    DYNAMIC = enum.auto()
    """For dynamic commands"""


# Base type has quotes despite the __future__ import because it's present at runtime
class EphemeralMapping(MutableMapping[str, "Command"]):
    def __init__(self, *others):
        # use an iter here so every mapping is unique
        self._chain = ChainMap(*islice(iter(dict, None), Ephemeral.DYNAMIC + 1))
        self.__shields: dict[Optional[asyncio.Task], dict[str, Command]] = {}
        for other in others:
            self.update(other)

    @contextlib.contextmanager
    def _shield(self, *commands: Command):
        """
        Alerts the internal mapping that the specified commands are being modified.

        This ensures that only the intended commands are modified, even if strings are passed.
        """
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        if task in self.__shields:
            yield self
            return
        self.__shields[task] = {}
        for command in commands:
            if command and not command.parent:
                self.__shields[task].update(
                    (name, command) for name in (command.name, *command.aliases)
                )
        try:
            yield self
        finally:
            del self.__shields[task]

    def _get_shield(self, key: str = None, default: Command = None):
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        map = self.__shields.get(task)
        if map and key is not None:
            return map.get(key, default)
        return map

    # region [abstract methods]

    def __setitem__(self, k: str, v: Command) -> None:
        level = v.ephemerality
        if level < Ephemeral.DYNAMIC and k != v.name:
            level += 2
        self._chain.maps[level][k] = v

    def __delitem__(self, k: Union[str, Command]) -> None:
        cmd: Command
        names: Tuple[str, ...]
        # check by str here since Command isn't imported
        if isinstance(k, str):
            cmd = self._get_shield(k)
            if not cmd:
                cmd = self._chain.maps[Ephemeral.DEFAULT][k]
            names = (k,)
        else:
            cmd = k
            names = (cmd.name, *cmd.aliases)
        deleted = False
        for map in self.maps:
            for name in names:
                try:
                    if map[name] == cmd:
                        del map[name]
                        deleted = True
                except KeyError:
                    continue
        if not deleted:
            raise KeyError(k)

    def __getitem__(self, k: Union[str, Command]) -> Command:
        if isinstance(k, str):
            cmd = self._get_shield(k)
            if cmd:
                for map in self._chain.maps:
                    if map[k] == cmd:
                        return cmd
                raise KeyError(k)
            return self._chain[k]
        for map in self._chain.maps:
            if k in map.values():
                return k
        raise KeyError(k)

    def __iter__(self) -> Iterator[str]:
        return iter(self._chain)

    def __len__(self) -> int:
        return len(self._chain)

    # endregion [abstract methods]

    @property
    def maps(self) -> list[MutableMapping[str, Command]]:
        # Should this be read-only?
        # return tuple(types.MappingProxyType(map) for map in self._chain.maps)
        return self._chain.maps

    @property
    def flattened(self) -> dict[str, Command]:
        return {k: v for k, v in self.items()}

    @recursive_repr()
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(map(repr, self._chain.maps))})'

    def copy(self):
        return type(self)(*self._chain.maps)
