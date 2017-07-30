import pkgutil
from importlib import invalidate_caches
from importlib.machinery import ModuleSpec
from typing import Tuple, Union, List
from pathlib import Path

from discord.ext import commands

from core import checks
from core.config import Config
from core.utils.chat_formatting import box


class CogManagerException(Exception):
    pass


class InvalidPath(CogManagerException):
    pass


class NoModuleFound(CogManagerException):
    pass


class CogManager:
    def __init__(self, paths: Tuple[str]=(), bot_dir: Path=Path.cwd()):
        self.conf = Config.get_conf(self, 2938473984732, True)
        self.conf.register_global(
            paths=(),
            install_path=str(bot_dir.resolve() / "cogs")
        )

        self._paths = set(list(self.conf.paths()) + list(paths))

    @property
    def paths(self) -> Tuple[Path, ...]:
        """
        This will return all currently valid path directories.
        :return:
        """
        paths = [Path(p) for p in self._paths]
        if self.install_path not in paths:
            paths.insert(0, self.install_path)
        return tuple(p.resolve() for p in paths if p.is_dir())

    @property
    def install_path(self) -> Path:
        """
        Returns the install path for 3rd party cogs.
        :return:
        """
        p = Path(self.conf.install_path())
        return p.resolve()

    async def set_install_path(self, path: Path) -> Path:
        """
        Install path setter, will return the absolute path to
            the given path.
        :param path:
        :return:
        """
        if not path.is_dir():
            raise ValueError("The install path must be an existing directory.")
        resolved = path.resolve()
        await self.conf.install_path.set(str(resolved))
        return resolved

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

        if path == self.install_path:
            raise ValueError("Cannot add the install path as an additional path.")

        all_paths = set(self.paths + (path, ))
        # noinspection PyTypeChecker
        await self.set_paths(all_paths)

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
            await self.set_paths(all_paths)
        return tuple(all_paths)

    async def set_paths(self, paths_: List[Path]):
        """
        Sets the current paths list.
        :param paths_:
        :return:
        """
        self._paths = paths_
        str_paths = [str(p) for p in paths_]
        await self.conf.paths.set(str_paths)

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


class CogManagerUI:
    @commands.command()
    @checks.is_owner()
    async def paths(self, ctx: commands.Context):
        """
        Lists current cog paths in order of priority.
        """
        install_path = ctx.bot.cog_mgr.install_path
        cog_paths = ctx.bot.cog_mgr.paths
        cog_paths = [p for p in cog_paths if p != install_path]

        msg = "Install Path: {}\n\n".format(install_path)

        partial = []
        for i, p in enumerate(cog_paths, start=1):
            partial.append("{}. {}".format(i, p))

        msg += "\n".join(partial)
        await ctx.send(box(msg))

    @commands.command()
    @checks.is_owner()
    async def addpath(self, ctx: commands.Context, path: Path):
        """
        Add a path to the list of available cog paths.
        """
        if not path.is_dir():
            await ctx.send("That path is does not exist or does not"
                           " point to a valid directory.")
            return

        try:
            await ctx.bot.cog_mgr.add_path(path)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await ctx.send("Path successfully added.")

    @commands.command()
    @checks.is_owner()
    async def removepath(self, ctx: commands.Context, path_number: int):
        """
        Removes a path from the available cog paths given the path_number
            from !paths
        """
        cog_paths = ctx.bot.cog_mgr.paths
        try:
            to_remove = cog_paths[path_number]
        except IndexError:
            await ctx.send("That is an invalid path number.")
            return

        await ctx.bot.cog_mgr.remove_path(to_remove)
        await ctx.send("Path successfully removed.")

    @commands.command()
    @checks.is_owner()
    async def reorderpath(self, ctx: commands.Context, from_: int, to: int):
        """
        Reorders paths internally to allow discovery of different cogs.
        """
        # Doing this because in the paths command they're 1 indexed
        from_ -= 1
        to -= 1

        all_paths = list(ctx.bot.cog_mgr.paths)
        try:
            to_move = all_paths.pop(from_)
        except IndexError:
            await ctx.send("Invalid 'from' index.")
            return

        try:
            all_paths.insert(to, to_move)
        except IndexError:
            await ctx.send("Invalid 'to' index.")
            return

        await ctx.bot.cog_mgr.set_paths(all_paths)
        await ctx.send("Paths reordered.")

    @commands.command()
    @checks.is_owner()
    async def installpath(self, ctx: commands.Context, path: Path=None):
        """
        Returns the current install path or sets it if one is provided.
            The provided path must be absolute or relative to the bot's
            directory and it must already exist.

        No installed cogs will be transferred in the process.
        """
        if path:
            if not path.is_absolute():
                path = (ctx.bot.main_dir / path).resolve()
            try:
                await ctx.bot.cog_mgr.set_install_path(path)
            except ValueError:
                await ctx.send("That path does not exist.")
                return

        install_path = ctx.bot.cog_mgr.install_path
        await ctx.send("The bot will install new cogs to the `{}`"
                       " directory.".format(install_path))
