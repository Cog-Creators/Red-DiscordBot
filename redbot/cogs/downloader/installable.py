from __future__ import annotations

import json
import distutils.dir_util
import shutil
from enum import Enum
from pathlib import Path
from typing import MutableMapping, Any, TYPE_CHECKING, Optional, Dict, Union, Callable, Tuple, cast

from .log import log
from .json_mixins import RepoJSONMixin

from redbot.core import __version__, version_info as red_version_info, VersionInfo

if TYPE_CHECKING:
    from .repo_manager import RepoManager, Repo


class InstallableType(Enum):
    UNKNOWN = 0
    COG = 1
    SHARED_LIBRARY = 2


class Installable(RepoJSONMixin):
    """Base class for anything the Downloader cog can install.

     - Modules
     - Repo Libraries
     - Other stuff?

    The attributes of this class will mostly come from the installation's
    info.json.

    Attributes
    ----------
    repo_name : `str`
        Name of the repository which this package belongs to.
    repo : Repo, optional
        Repo object of the Installable, if repo is missing this will be `None`
    commit : `str`, optional
        Installable's commit. This is not the same as ``repo.commit``
    author : `tuple` of `str`, optional
        Name(s) of the author(s).
    bot_version : `tuple` of `int`
        The minimum bot version required for this installation. Right now
        this is always :code:`3.0.0`.
    min_python_version : `tuple` of `int`
        The minimum python version required for this cog. This field will not
        apply to repo info.json's.
    hidden : `bool`
        Whether or not this cog will be hidden from the user when they use
        `Downloader`'s commands.
    required_cogs : `dict`
        In the form :code:`{cog_name : repo_url}`, these are cogs which are
        required for this installation.
    requirements : `tuple` of `str`
        Required libraries for this installation.
    tags : `tuple` of `str`
        List of tags to assist in searching.
    type : `int`
        The type of this installation, as specified by
        :class:`InstallationType`.

    """

    def __init__(self, location: Path, repo: Optional[Repo] = None, commit: str = ""):
        """Base installable initializer.

        Parameters
        ----------
        location : pathlib.Path
            Location (file or folder) to the installable.
        repo : Repo, optional
            Repo object of the Installable, if repo is missing this will be `None`
        commit : str
            Installable's commit. This is not the same as ``repo.commit``

        """
        super().__init__(location)

        self._location = location

        self.repo = repo
        self.repo_name = self._location.parent.stem
        self.commit = commit

        self.author: Tuple[str, ...] = ()
        self.min_bot_version = red_version_info
        self.max_bot_version = red_version_info
        self.min_python_version = (3, 5, 1)
        self.hidden = False
        self.disabled = False
        self.required_cogs: Dict[str, str] = {}  # Cog name -> repo URL
        self.requirements: Tuple[str, ...] = ()
        self.tags: Tuple[str, ...] = ()
        self.type = InstallableType.UNKNOWN

        if self._info_file.exists():
            self._process_info_file(self._info_file)

        if self._info == {}:
            self.type = InstallableType.COG

    def __eq__(self, other: Any) -> bool:
        # noinspection PyProtectedMember
        return self._location == other._location

    def __hash__(self) -> int:
        return hash(self._location)

    @property
    def name(self) -> str:
        """`str` : The name of this package."""
        return self._location.stem

    async def copy_to(self, target_dir: Path) -> bool:
        """
        Copies this cog/shared_lib to the given directory. This
        will overwrite any files in the target directory.

        :param pathlib.Path target_dir: The installation directory to install to.
        :return: Status of installation
        :rtype: bool
        """
        copy_func: Callable[..., Any]
        if self._location.is_file():
            copy_func = shutil.copy2
        else:
            # clear copy_tree's cache to make sure missing directories are created (GH-2690)
            distutils.dir_util._path_created = {}
            copy_func = distutils.dir_util.copy_tree

        # noinspection PyBroadException
        try:
            copy_func(src=str(self._location), dst=str(target_dir / self._location.stem))
        except:  # noqa: E722
            log.exception("Error occurred when copying path: {}".format(self._location))
            return False
        return True

    def _read_info_file(self) -> None:
        super()._read_info_file()

        if self._info_file.exists():
            self._process_info_file()

    def _process_info_file(
        self, info_file_path: Optional[Path] = None
    ) -> MutableMapping[str, Any]:
        """
        Processes an information file. Loads dependencies among other
        information into this object.

        :type info_file_path:
        :param info_file_path: Optional path to information file, defaults to `self.__info_file`
        :return: Raw information dictionary
        """
        info_file_path = info_file_path or self._info_file
        if info_file_path is None or not info_file_path.is_file():
            raise ValueError("No valid information file path was found.")

        info: Dict[str, Any] = {}
        with info_file_path.open(encoding="utf-8") as f:
            try:
                info = json.load(f)
            except json.JSONDecodeError:
                info = {}
                log.exception("Invalid JSON information file at path: {}".format(info_file_path))
            else:
                self._info = info

        try:
            author = tuple(info.get("author", []))
        except ValueError:
            author = ()
        self.author = author

        try:
            min_bot_version = VersionInfo.from_str(str(info.get("min_bot_version", __version__)))
        except ValueError:
            min_bot_version = self.min_bot_version
        self.min_bot_version = min_bot_version

        try:
            max_bot_version = VersionInfo.from_str(str(info.get("max_bot_version", __version__)))
        except ValueError:
            max_bot_version = self.max_bot_version
        self.max_bot_version = max_bot_version

        try:
            min_python_version = tuple(info.get("min_python_version", (3, 5, 1)))
        except ValueError:
            min_python_version = self.min_python_version
        self.min_python_version = min_python_version

        try:
            hidden = bool(info.get("hidden", False))
        except ValueError:
            hidden = False
        self.hidden = hidden

        try:
            disabled = bool(info.get("disabled", False))
        except ValueError:
            disabled = False
        self.disabled = disabled

        self.required_cogs = info.get("required_cogs", {})

        self.requirements = info.get("requirements", ())

        try:
            tags = tuple(info.get("tags", ()))
        except ValueError:
            tags = ()
        self.tags = tags

        installable_type = info.get("type", "")
        if installable_type in ("", "COG"):
            self.type = InstallableType.COG
        elif installable_type == "SHARED_LIBRARY":
            self.type = InstallableType.SHARED_LIBRARY
            self.hidden = True
        else:
            self.type = InstallableType.UNKNOWN

        return info


class InstalledModule(Installable):
    """Base class for installed modules,
    this is basically instance of installed `Installable`
    used by Downloader.

    Attributes
    ----------
    pinned : `bool`
        Whether or not this cog is pinned, always `False` if module is not a cog.
    """

    def __init__(
        self, location: Path, repo: Optional[Repo] = None, commit: str = "", pinned: bool = False
    ):
        super().__init__(location=location, repo=repo, commit=commit)
        self.pinned: bool = pinned if self.type == InstallableType.COG else False

    def to_json(self) -> Dict[str, Union[str, bool]]:
        module_json: Dict[str, Union[str, bool]] = {
            "repo_name": self.repo_name,
            "module_name": self.name,
            "commit": self.commit,
        }
        if self.type == InstallableType.COG:
            module_json["pinned"] = self.pinned
        return module_json

    @classmethod
    def from_json(
        cls, data: Dict[str, Union[str, bool]], repo_mgr: RepoManager
    ) -> InstalledModule:
        repo_name = cast(str, data["repo_name"])
        cog_name = cast(str, data["module_name"])
        commit = cast(str, data.get("commit", ""))
        pinned = cast(bool, data.get("pinned", False))

        # TypedDict, where are you :/
        repo = repo_mgr.get_repo(repo_name)
        if repo is not None:
            repo_folder = repo.folder_path
        else:
            repo_folder = repo_mgr.repos_folder / "MISSING_REPO"

        location = repo_folder / cog_name

        return cls(location=location, repo=repo, commit=commit, pinned=pinned)

    @classmethod
    def from_installable(cls, module: Installable, *, pinned: bool = False) -> InstalledModule:
        return cls(
            location=module._location, repo=module.repo, commit=module.commit, pinned=pinned
        )
