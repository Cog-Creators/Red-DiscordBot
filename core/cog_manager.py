import pkgutil
from importlib import invalidate_caches
from importlib.machinery import ModuleSpec
from typing import Tuple, Union
from pathlib import Path

from core.config import Config


class CogManagerException(Exception):
    pass


class InvalidPath(CogManagerException):
    pass


class NoModuleFound(CogManagerException):
    pass


class CogManager:
    def __init__(self, paths: Tuple[str]=()):
        self.conf = Config.get_conf(self, 2938473984732, True)
        self.conf.register_global(
            paths=()
        )

        self._paths = set(self.conf.paths() + paths)

    @property
    def paths(self) -> Tuple[Path, ...]:
        """
        This will return all currently valid path directories.
        :return:
        """
        paths = [Path(p) for p in self._paths]
        return tuple(p for p in paths if p.is_dir())

    @staticmethod
    def _ensure_path_obj(path: Union[Path, str]) -> Path:
        """
        Guarantees an object will be a path object.
        :param path:
        :return:
        """
        try:
            path.exists()
        except AttributeError:
            path = Path(path)
        return path

    async def add_path(self, path: Union[Path, str]):
        """
        Adds a cog path to current list, will ignore duplicates. Does have
            a side effect of removing all invalid paths from the saved path
            list.

        Will raise InvalidPath if given anything that does not resolve to
            a directory.
        :param path:
        :return:
        """
        path = self._ensure_path_obj(path)

        # This makes the path absolute, will break if a bot install
        # changes OS/Computer?
        path = path.resolve()

        if not path.is_dir():
            raise InvalidPath("'{}' is not a valid directory.".format(path))

        all_paths = set(self.paths + (path, ))
        to_save = [str(p) for p in all_paths]
        await self.conf.set("paths", to_save)

    async def remove_path(self, path: Union[Path, str]) -> Tuple[Path, ...]:
        """
        Removes a path from the current paths list.
        :param path:
        :return:
        """
        path = self._ensure_path_obj(path)
        all_paths = list(self.paths)
        if path in all_paths:
            all_paths.remove(path)  # Modifies in place
            await self.conf.set("paths", all_paths)
        return tuple(all_paths)

    def find_cog(self, name: str) -> ModuleSpec:
        """
        Finds a cog in the list of available path.

        Raises NoModuleFound if unavailable.
        :param name:
        :return:
        """
        resolved_paths = [str(p.resolve()) for p in self.paths]
        for finder, module_name, _ in pkgutil.iter_modules(resolved_paths):
            if name == module_name:
                spec = finder.find_spec(name)
                if spec:
                    return spec

        raise NoModuleFound("No module by the name of '{}' was found"
                            " in any available path.".format(name))

    @staticmethod
    def invalidate_caches():
        """
        This is an alias for an importlib internal and should be called
            any time that a new module has been installed to a cog directory.

            *I think.*
        :return:
        """
        invalidate_caches()
