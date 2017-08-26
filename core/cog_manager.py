import pkgutil
from importlib import invalidate_caches
from importlib.machinery import ModuleSpec
from typing import Tuple, Union, List
from pathlib import Path

from discord.ext import commands

from core import checks
from core.config import Config
from core.utils.chat_formatting import box
from core.i18n import CogI18n

__all__ = ["CogManager"]


class CogManager:
    """
    This module allows you to load cogs from multiple directories and even from outside the bot
    directory. You may also set a directory for downloader to install new cogs to, the default
    being the :code:`cogs/` folder in the root bot directory.
    """
    def __init__(self, paths: Tuple[str]=(), bot_dir: Path=Path.cwd()):
        self.conf = Config.get_conf(self, 2938473984732, True)
        self.conf.register_global(
            paths=(),
            install_path=str(bot_dir.resolve() / "cogs")
        )

        self._paths = list(paths)

    async def paths(self) -> Tuple[Path, ...]:
        """
        All currently valid path directories.
        """
        conf_paths = await self.conf.paths()
        other_paths = self._paths

        all_paths = set(list(conf_paths) + list(other_paths))

        paths = [Path(p) for p in all_paths]
        if self.install_path not in paths:
            paths.insert(0, await self.install_path())
        return tuple(p.resolve() for p in paths if p.is_dir())

    async def install_path(self) -> Path:
        """
        The install path for 3rd party cogs.
        """
        p = Path(await self.conf.install_path())
        return p.resolve()

    async def set_install_path(self, path: Path) -> Path:
        """
        Install path setter, will return the absolute path to
        the given path.

        .. note::

            The bot will not remember your old cog install path which means
            that ALL PREVIOUSLY INSTALLED COGS will now be unfindable.

        :param pathlib.Path path:
            The new directory for cog installs.
        :raises ValueError:
            If :code:`path` is not an existing directory.
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
        :type path:
            pathlib.Path or str
        :rtype:
            pathlib.Path
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

        :param path:
            Path to add.
        :type path:
            pathlib.Path or str
        :raises ValueError:
            If :code:`path` does not resolve to an existing directory.
        """
        path = self._ensure_path_obj(path)

        # This makes the path absolute, will break if a bot install
        # changes OS/Computer?
        path = path.resolve()

        if not path.is_dir():
            raise ValueError("'{}' is not a valid directory.".format(path))

        if path == await self.install_path():
            raise ValueError("Cannot add the install path as an additional path.")

        all_paths = set(await self.paths() + (path, ))
        # noinspection PyTypeChecker
        await self.set_paths(all_paths)

    async def remove_path(self, path: Union[Path, str]) -> Tuple[Path, ...]:
        """
        Removes a path from the current paths list.

        :param path: Path to remove.
        :type path:
            pathlib.Path or str
        :return:
            Tuple of new valid paths.
        :rtype: tuple
        """
        path = self._ensure_path_obj(path)
        all_paths = list(await self.paths())
        if path in all_paths:
            all_paths.remove(path)  # Modifies in place
            await self.set_paths(all_paths)
        return tuple(all_paths)

    async def set_paths(self, paths_: List[Path]):
        """
        Sets the current paths list.

        :param List[pathlib.Path] paths_:
            List of paths to set.
        """
        str_paths = [str(p) for p in paths_]
        await self.conf.paths.set(str_paths)

    async def find_cog(self, name: str) -> ModuleSpec:
        """
        Finds a cog in the list of available paths.

        :param name:
            Name of the cog to find.
        :raises RuntimeError:
            If there is no cog with the given name.
        :return:
            A module spec to be used for specialized cog loading.
        :rtype:
            importlib.machinery.ModuleSpec
        """
        resolved_paths = [str(p.resolve()) for p in await self.paths()]
        for finder, module_name, _ in pkgutil.iter_modules(resolved_paths):
            if name == module_name:
                spec = finder.find_spec(name)
                if spec:
                    return spec

        raise RuntimeError("No module by the name of '{}' was found"
                           " in any available path.".format(name))

    @staticmethod
    def invalidate_caches():
        """
        This is an alias for an importlib internal and should be called
        any time that a new module has been installed to a cog directory.

        *I think.*
        """
        invalidate_caches()


_ = CogI18n("CogManagerUI", __file__)


class CogManagerUI:
    @commands.command()
    @checks.is_owner()
    async def paths(self, ctx: commands.Context):
        """
        Lists current cog paths in order of priority.
        """
        install_path = await ctx.bot.cog_mgr.install_path()
        cog_paths = ctx.bot.cog_mgr.paths
        cog_paths = [p for p in cog_paths if p != install_path]

        msg = _("Install Path: {}\n\n").format(install_path)

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
            await ctx.send(_("That path is does not exist or does not"
                             " point to a valid directory."))
            return

        try:
            await ctx.bot.cog_mgr.add_path(path)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await ctx.send(_("Path successfully added."))

    @commands.command()
    @checks.is_owner()
    async def removepath(self, ctx: commands.Context, path_number: int):
        """
        Removes a path from the available cog paths given the path_number
            from !paths
        """
        cog_paths = await ctx.bot.cog_mgr.paths()
        try:
            to_remove = cog_paths[path_number]
        except IndexError:
            await ctx.send(_("That is an invalid path number."))
            return

        await ctx.bot.cog_mgr.remove_path(to_remove)
        await ctx.send(_("Path successfully removed."))

    @commands.command()
    @checks.is_owner()
    async def reorderpath(self, ctx: commands.Context, from_: int, to: int):
        """
        Reorders paths internally to allow discovery of different cogs.
        """
        # Doing this because in the paths command they're 1 indexed
        from_ -= 1
        to -= 1

        all_paths = list(await ctx.bot.cog_mgr.paths())
        try:
            to_move = all_paths.pop(from_)
        except IndexError:
            await ctx.send(_("Invalid 'from' index."))
            return

        try:
            all_paths.insert(to, to_move)
        except IndexError:
            await ctx.send(_("Invalid 'to' index."))
            return

        await ctx.bot.cog_mgr.set_paths(all_paths)
        await ctx.send(_("Paths reordered."))

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
                await ctx.send(_("That path does not exist."))
                return

        install_path = await ctx.bot.cog_mgr.install_path()
        await ctx.send(_("The bot will install new cogs to the `{}`"
                         " directory.").format(install_path))
