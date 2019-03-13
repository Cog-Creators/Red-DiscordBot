"""Cog path manager for Red.

This module provides both the internal API and the external UI for
adding, removing or modifying extra paths for Red to be able to
discover cogs.

By default, cogs can be imported from the install path, where
Downloader will place installed cogs; and the core cogs path. Other
arbitrary paths can be added by the user - these user-defined paths are
particularly useful for cog development.

Internally, this modifies use of the `__path__` attribute of the
``redbot.ext_cogs`` package. When extra paths are added to a package's
`__path__` attribute, they are used to locate sub-packages.

The precedence of paths goes:
1. Install path
2. User-defined paths
3. Core path (redbot.cogs)

This is so users who wish to modify core cogs can do so by copying or
installing cogs into a user-defined/core path, and this modified one
will be loaded instead.
"""
import asyncio
import concurrent.futures
import functools
import importlib.machinery
import logging
import pkgutil
import sys
import types
from pathlib import Path
from typing import Union, List, Optional, Set

import redbot.cogs
import redbot.ext_cogs
from redbot.core.utils import deduplicate_iterables
import discord

from . import checks, commands, errors
from .config import Config
from .i18n import Translator, cog_i18n
from .data_manager import cog_data_path

from .utils.chat_formatting import box, pagify

__all__ = ["CogManager", "CogManagerUI"]

log = logging.getLogger("red.cog_manager")


class CogManager:
    """Directory manager for Red's cogs.

    This module allows you to load cogs from multiple directories and even from
    outside the bot directory. You may also set a directory for downloader to
    install new cogs to, the default being the ``cogs/`` folder in `RepoManager`'s
    data directory.
    """

    CORE_PATH = Path(redbot.cogs.__file__).parent

    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.conf = Config.get_conf(self, 2938473984732, True)
        default_cog_install_path = cog_data_path(self) / "cogs"
        default_cog_install_path.mkdir(parents=True, exist_ok=True)
        self.conf.register_global(paths=[], install_path=str(default_cog_install_path))
        self._loop = loop or asyncio.get_event_loop()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    async def initialize(self):
        redbot.ext_cogs.__path__ = [str(p) for p in (await self.paths())[:-1]]

    async def paths(self) -> List[Path]:
        """Get all currently valid path directories, in order of priority

        Returns
        -------
        List[pathlib.Path]
            A list of paths where cog packages can be found. The
            install path is highest priority, followed by the
            user-defined paths, and the core path has the lowest
            priority.

        """
        return deduplicate_iterables(
            [await self.install_path()], await self.user_defined_paths(), [self.CORE_PATH]
        )

    async def install_path(self) -> Path:
        """Get the install path for 3rd party cogs.

        Returns
        -------
        pathlib.Path
            The path to the directory where 3rd party cogs are stored.

        """
        return Path(await self.conf.install_path()).resolve()

    async def user_defined_paths(self) -> List[Path]:
        """Get a list of user-defined cog paths.

        All paths will be absolute and unique, in order of priority.

        Returns
        -------
        List[pathlib.Path]
            A list of user-defined paths.

        """
        return list(map(Path, deduplicate_iterables(await self.conf.paths())))

    async def set_install_path(self, path: Path) -> Path:
        """Set the install path for 3rd party cogs.

        Note
        ----
        The bot will not remember your old cog install path which means
        that **all previously installed cogs** will no longer be found.

        Parameters
        ----------
        path : pathlib.Path
            The new directory for cog installs.

        Returns
        -------
        pathlib.Path
            Absolute path to the new install directory.

        Raises
        ------
        ValueError
            If :code:`path` is not an existing directory.

        """
        if not path.is_dir():
            raise ValueError("The install path must be an existing directory.")
        resolved = path.resolve()
        await self.conf.install_path.set(str(resolved))
        redbot.ext_cogs.__path__[0] = str(resolved)
        return resolved

    @staticmethod
    def _ensure_path_obj(path: Union[Path, str]) -> Path:
        """Guarantee an object will be a path object.

        Parameters
        ----------
        path : `pathlib.Path` or `str`

        Returns
        -------
        pathlib.Path

        """
        try:
            path.exists()
        except AttributeError:
            path = Path(path)
        return path

    async def add_path(self, path: Union[Path, str]) -> None:
        """Add a cog path to current list.

        This will ignore duplicates.

        Parameters
        ----------
        path : `pathlib.Path` or `str`
            Path to add.

        Raises
        ------
        ValueError
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
        if path == self.CORE_PATH:
            raise ValueError("Cannot add the core path as an additional path.")

        current_paths = await self.user_defined_paths()
        if path not in current_paths:
            current_paths.append(path)
            await self.set_paths(current_paths)
            redbot.ext_cogs.__path__.append(str(path))

    async def remove_path(self, path: Union[Path, str]) -> None:
        """Remove a path from the current paths list.

        Parameters
        ----------
        path : `pathlib.Path` or `str`
            Path to remove.

        """
        path = self._ensure_path_obj(path).resolve()
        paths = await self.user_defined_paths()

        paths.remove(path)
        await self.set_paths(paths)
        redbot.ext_cogs.__path__.remove(str(path))

    async def reorder_path(self, path: Union[Path, str], new_index: int) -> None:
        """Reorder a path in the user-defined paths list.

        The *path* will be removed from the paths list and
        re-inserted at *new_index*.
        """
        path = self._ensure_path_obj(path).resolve()
        paths = await self.user_defined_paths()

        paths.remove(path)
        paths.insert(new_index, path)
        await self.set_paths(paths)

        redbot.ext_cogs.__path__[1:] = list(map(str, paths))

    async def set_paths(self, paths_: List[Path]):
        """Set the current paths list.

        Parameters
        ----------
        paths_ : `list` of `pathlib.Path`
            List of paths to set.

        """
        str_paths = list(map(str, paths_))
        await self.conf.paths.set(str_paths)

    async def load_cog_module(self, name: str) -> types.ModuleType:
        """Load a cog module or package."""
        for parent_package in ("redbot.ext_cogs", "redbot.cogs"):
            partial = functools.partial(
                importlib.import_module, f".{name}", package=parent_package
            )
            module_name = ".".join((parent_package, name))
            try:
                if module_name in sys.modules:
                    # Will be quick to import
                    module = partial()
                else:
                    # Might take a while - try to make it non-blocking
                    try:
                        module = await self._loop.run_in_executor(self._executor, partial)
                    except RuntimeError as exc:
                        log.exception(
                            "Loading module `%s` failed with the following exception when trying "
                            "in a secondary thread:",
                            name,
                            exc_info=exc,
                        )
                        log.info("Retrying in main thread...")
                        module = partial()
            except ModuleNotFoundError as e:
                if e.name == module_name:
                    pass
                else:
                    raise
            else:
                return module

        # If we get here, we failed to find the module
        raise errors.NoSuchCog(
            "No core cog by the name of '{}' could be found.".format(name), name=name
        )

    async def reload(self, module: types.ModuleType) -> types.ModuleType:
        """Do a deep reload of a module or package."""
        try:
            return await self._loop.run_in_executor(self._executor, self._reload, module)
        except RuntimeError as exc:
            log.exception(
                "Reloading module `%s` failed with the following exception when trying in a "
                "secondary thread:",
                module.__name__,
                exc_info=exc,
            )
            log.info("Retrying in main thread...")
            return self._reload(module)

    @staticmethod
    def _reload(module: types.ModuleType) -> types.ModuleType:
        children = {
            name: lib for name, lib in sys.modules.items() if name.startswith(module.__name__)
        }
        ret = module
        for _ in range(2):  # Do it twice to overwrite old relative imports
            for child_name, lib in sorted(children.items(), key=lambda m: m[0], reverse=True):
                try:
                    importlib.reload(lib)
                except ModuleNotFoundError as exc:
                    if exc.name == lib.__name__:
                        # If the structure of the package changed, we might try to reload a module
                        # which no longer exists.
                        pass
                    else:
                        raise
                if lib.__name__ == module.__name__:
                    ret = lib
        return ret

    @staticmethod
    async def available_modules() -> Set[str]:
        """Finds the names of all available modules to load."""
        ret = set()
        for package in (redbot.cogs, redbot.ext_cogs):
            for finder, module_name, ispkg in pkgutil.iter_modules(package.__path__):
                ret.add(module_name)
        return ret


_ = Translator("CogManagerUI", __file__)


@cog_i18n(_)
class CogManagerUI(commands.Cog):
    """Commands to interface with Red's cog manager."""

    @commands.command()
    @checks.is_owner()
    async def paths(self, ctx: commands.Context):
        """
        Lists current cog paths in order of priority.
        """
        cog_mgr = ctx.bot.cog_mgr
        install_path = await cog_mgr.install_path()
        core_path = cog_mgr.CORE_PATH
        cog_paths = await cog_mgr.user_defined_paths()

        msg = _("Install Path: {install_path}\nCore Path: {core_path}\n\n").format(
            install_path=install_path, core_path=core_path
        )

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
            await ctx.send(_("That path does not exist or does not point to a valid directory."))
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
        path_number -= 1
        if path_number < 0:
            await ctx.send(_("Path numbers must be positive."))
            return

        cog_paths = await ctx.bot.cog_mgr.user_defined_paths()
        try:
            to_remove = cog_paths.pop(path_number)
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
        if from_ < 0 or to < 0:
            await ctx.send(_("Path numbers must be positive."))
            return

        all_paths = await ctx.bot.cog_mgr.user_defined_paths()
        try:
            to_move = all_paths.pop(from_)
        except IndexError:
            await ctx.send(_("Invalid 'from' index."))
            return

        await ctx.bot.cog_mgr.reorder_path(to_move, to)

        await ctx.send(_("Paths reordered."))

    @commands.command()
    @checks.is_owner()
    async def installpath(self, ctx: commands.Context, path: Path = None):
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
        await ctx.send(
            _("The bot will install new cogs to the `{}` directory.").format(install_path)
        )

    @commands.command()
    @checks.is_owner()
    async def cogs(self, ctx: commands.Context):
        """
        Lists all loaded and available cogs.
        """
        loaded = set(ctx.bot.extensions.keys())

        all_cogs = set(await ctx.bot.cog_mgr.available_modules())

        unloaded = all_cogs - loaded

        loaded = sorted(list(loaded), key=str.lower)
        unloaded = sorted(list(unloaded), key=str.lower)

        if await ctx.embed_requested():
            loaded = _("**{} loaded:**\n").format(len(loaded)) + ", ".join(loaded)
            unloaded = _("**{} unloaded:**\n").format(len(unloaded)) + ", ".join(unloaded)

            for page in pagify(loaded, delims=[", ", "\n"], page_length=1800):
                e = discord.Embed(description=page, colour=discord.Colour.dark_green())
                await ctx.send(embed=e)

            for page in pagify(unloaded, delims=[", ", "\n"], page_length=1800):
                e = discord.Embed(description=page, colour=discord.Colour.dark_red())
                await ctx.send(embed=e)
        else:
            loaded_count = _("**{} loaded:**\n").format(len(loaded))
            loaded = ", ".join(loaded)
            unloaded_count = _("**{} unloaded:**\n").format(len(unloaded))
            unloaded = ", ".join(unloaded)
            loaded_count_sent = False
            unloaded_count_sent = False
            for page in pagify(loaded, delims=[", ", "\n"], page_length=1800):
                if page.startswith(", "):
                    page = page[2:]
                if not loaded_count_sent:
                    await ctx.send(loaded_count + box(page, lang="css"))
                    loaded_count_sent = True
                else:
                    await ctx.send(box(page, lang="css"))

            for page in pagify(unloaded, delims=[", ", "\n"], page_length=1800):
                if page.startswith(", "):
                    page = page[2:]
                if not unloaded_count_sent:
                    await ctx.send(unloaded_count + box(page, lang="ldif"))
                    unloaded_count_sent = True
                else:
                    await ctx.send(box(page, lang="ldif"))
