import contextlib
import pkgutil
from importlib import import_module, invalidate_caches
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Tuple, Union, List, Optional

import redbot.cogs
from redbot.core.utils import deduplicate_iterables
import discord

from . import checks, commands
from .config import Config
from .i18n import Translator, cog_i18n
from .data_manager import cog_data_path

from .utils.chat_formatting import box, pagify

__all__ = ["CogManager"]


class NoSuchCog(ImportError):
    """Thrown when a cog is missing.

    Different from ImportError because some ImportErrors can happen inside cogs.
    """

    pass


class CogManager:
    """Directory manager for Red's cogs.

    This module allows you to load cogs from multiple directories and even from
    outside the bot directory. You may also set a directory for downloader to
    install new cogs to, the default being the :code:`cogs/` folder in the root
    bot directory.
    """

    CORE_PATH = Path(redbot.cogs.__path__[0])

    def __init__(self, paths: Tuple[str] = ()):
        self.conf = Config.get_conf(self, 2938473984732, True)
        tmp_cog_install_path = cog_data_path(self) / "cogs"
        tmp_cog_install_path.mkdir(parents=True, exist_ok=True)
        self.conf.register_global(paths=[], install_path=str(tmp_cog_install_path))
        self._paths = [Path(p) for p in paths]

    async def paths(self) -> Tuple[Path, ...]:
        """Get all currently valid path directories.

        Returns
        -------
        `tuple` of `pathlib.Path`
            All valid cog paths.

        """
        conf_paths = [Path(p) for p in await self.conf.paths()]
        other_paths = self._paths

        all_paths = deduplicate_iterables(conf_paths, other_paths, [self.CORE_PATH])

        if self.install_path not in all_paths:
            all_paths.insert(0, await self.install_path())
        return tuple(p.resolve() for p in all_paths if p.is_dir())

    async def install_path(self) -> Path:
        """Get the install path for 3rd party cogs.

        Returns
        -------
        pathlib.Path
            The path to the directory where 3rd party cogs are stored.

        """
        p = Path(await self.conf.install_path())
        return p.resolve()

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

    async def add_path(self, path: Union[Path, str]):
        """Add a cog path to current list.

        This will ignore duplicates. Does have a side effect of removing all
        invalid paths from the saved path list.

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

        async with self.conf.paths() as paths:
            if not any(Path(p) == path for p in paths):
                paths.append(str(path))

    async def remove_path(self, path: Union[Path, str]) -> Tuple[Path, ...]:
        """Remove a path from the current paths list.

        Parameters
        ----------
        path : `pathlib.Path` or `str`
            Path to remove.

        Returns
        -------
        `tuple` of `pathlib.Path`
            Tuple of new valid paths.

        """
        path = self._ensure_path_obj(path).resolve()

        paths = [Path(p) for p in await self.conf.paths()]
        if path in paths:
            paths.remove(path)
            await self.set_paths(paths)

        return tuple(paths)

    async def set_paths(self, paths_: List[Path]):
        """Set the current paths list.

        Parameters
        ----------
        paths_ : `list` of `pathlib.Path`
            List of paths to set.

        """
        str_paths = [str(p) for p in paths_]
        await self.conf.paths.set(str_paths)

    async def _find_ext_cog(self, name: str) -> ModuleSpec:
        """
        Attempts to find a spec for a third party installed cog.

        Parameters
        ----------
        name : str
            Name of the cog package to look for.

        Returns
        -------
        importlib.machinery.ModuleSpec
            Module spec to be used for cog loading.

        Raises
        ------
        NoSuchCog
            When no cog with the requested name was found.
        """
        resolved_paths = await self.paths()
        real_paths = [str(p) for p in resolved_paths if p != self.CORE_PATH]

        for finder, module_name, _ in pkgutil.iter_modules(real_paths):
            if name == module_name:
                spec = finder.find_spec(name)
                if spec:
                    return spec

        raise NoSuchCog(
            "No 3rd party module by the name of '{}' was found in any available path.".format(
                name
            ),
            name=name,
        )

    @staticmethod
    async def _find_core_cog(name: str) -> ModuleSpec:
        """
        Attempts to find a spec for a core cog.

        Parameters
        ----------
        name : str

        Returns
        -------
        importlib.machinery.ModuleSpec

        Raises
        ------
        RuntimeError
            When no matching spec can be found.
        """
        real_name = ".{}".format(name)
        package = "redbot.cogs"

        try:
            mod = import_module(real_name, package=package)
        except ImportError as e:
            if e.name == package + real_name:
                raise NoSuchCog(
                    "No core cog by the name of '{}' could be found.".format(name),
                    path=e.path,
                    name=e.name,
                ) from e

            raise

        return mod.__spec__

    # noinspection PyUnreachableCode
    async def find_cog(self, name: str) -> Optional[ModuleSpec]:
        """Find a cog in the list of available paths.

        Parameters
        ----------
        name : str
            Name of the cog to find.

        Returns
        -------
        Optional[importlib.machinery.ModuleSpec]
            A module spec to be used for specialized cog loading, if found.

        """
        with contextlib.suppress(NoSuchCog):
            return await self._find_ext_cog(name)

        with contextlib.suppress(NoSuchCog):
            return await self._find_core_cog(name)

    async def available_modules(self) -> List[str]:
        """Finds the names of all available modules to load.
        """
        paths = (await self.install_path(),) + await self.paths()
        paths = [str(p) for p in paths]

        ret = []
        for finder, module_name, _ in pkgutil.iter_modules(paths):
            ret.append(module_name)
        return ret

    @staticmethod
    def invalidate_caches():
        """Re-evaluate modules in the py cache.

        This is an alias for an importlib internal and should be called
        any time that a new module has been installed to a cog directory.
        """
        invalidate_caches()


_ = Translator("CogManagerUI", __file__)


@cog_i18n(_)
class CogManagerUI:
    """Commands to interface with Red's cog manager."""

    @staticmethod
    async def visible_paths(ctx):
        install_path = await ctx.bot.cog_mgr.install_path()
        cog_paths = await ctx.bot.cog_mgr.paths()
        cog_paths = [p for p in cog_paths if p != install_path]
        return cog_paths

    @commands.command()
    @checks.is_owner()
    async def paths(self, ctx: commands.Context):
        """
        Lists current cog paths in order of priority.
        """
        cog_mgr = ctx.bot.cog_mgr
        install_path = await cog_mgr.install_path()
        core_path = cog_mgr.CORE_PATH
        cog_paths = await cog_mgr.paths()
        cog_paths = [p for p in cog_paths if p not in (install_path, core_path)]

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
        cog_paths = await self.visible_paths(ctx)
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

        all_paths = await self.visible_paths(ctx)
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
