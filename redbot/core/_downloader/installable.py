from __future__ import annotations

import functools
import shutil
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Union, cast

from packaging.version import Version

from .log import log
from .info_schemas import INSTALLABLE_SCHEMA, update_mixin
from .json_mixins import RepoJSONMixin

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
    author : `tuple` of `str`
        Name(s) of the author(s).
    end_user_data_statement : `str`
        End user data statement of the module.
    min_bot_version : `packaging.version.Version`
        The minimum bot version required for this Installable.
    max_bot_version : `packaging.version.Version`
        The maximum bot version required for this Installable.
        Ignored if `min_bot_version` is newer than `max_bot_version`.
    min_python_version : `packaging.version.Version`
        The minimum python version required for this cog.
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

    def __init__(
        self,
        location: Path,
        repo: Optional[Repo] = None,
        commit: str = "",
        *,
        info_file: Optional[Path] = None,
    ):
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
        self._location = location

        self.repo = repo
        self.repo_name = self._location.parent.name
        self.commit = commit

        self.end_user_data_statement: str
        self.min_bot_version: Version
        self.max_bot_version: Version
        self.min_python_version: Version
        self.hidden: bool
        self.disabled: bool
        self.required_cogs: Dict[str, str]  # Cog name -> repo URL
        self.requirements: Tuple[str, ...]
        self.tags: Tuple[str, ...]
        self.type: InstallableType

        super().__init__(location, info_file=info_file)

    def __eq__(self, other: Any) -> bool:
        # noinspection PyProtectedMember
        return self._location == other._location

    def __hash__(self) -> int:
        return hash(self._location)

    @property
    def name(self) -> str:
        """`str` : The name of this package."""
        return self._location.stem

    async def copy_to(self, target_dir: Path) -> Optional[Path]:
        """
        Copies this cog/shared_lib to the given directory. This
        will overwrite any files in the target directory.

        :param pathlib.Path target_dir: The installation directory to install to.
        :return: Install location of the cog or None in case of copy failure.
        :rtype: `Path`, optional
        """
        copy_func: Callable[..., Any]
        if self._location.is_file():
            copy_func = shutil.copy2
        else:
            copy_func = functools.partial(shutil.copytree, dirs_exist_ok=True)

        dst = target_dir / self._location.name
        # noinspection PyBroadException
        try:
            copy_func(src=str(self._location), dst=str(dst))
        except:  # noqa: E722
            log.exception("Error occurred when copying path: %s", self._location)
            return None
        return dst

    def _read_info_file(self) -> None:
        super()._read_info_file()

        update_mixin(self, INSTALLABLE_SCHEMA)
        if self.type is InstallableType.SHARED_LIBRARY:
            self.hidden = True


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
        self,
        location: Path,
        repo: Optional[Repo] = None,
        commit: str = "",
        pinned: bool = False,
        json_repo_name: str = "",
        *,
        info_file: Optional[Path] = None,
        install_location: Path,
    ):
        info_file = info_file or install_location / self.INFO_FILE_NAME
        super().__init__(location=location, repo=repo, commit=commit, info_file=info_file)
        self._install_location = install_location
        self.pinned: bool = pinned if self.type is InstallableType.COG else False
        # this is here so that Downloader could use real repo name instead of "MISSING_REPO"
        self._json_repo_name = json_repo_name

    def to_json(self) -> Dict[str, Union[str, bool]]:
        module_json: Dict[str, Union[str, bool]] = {
            "repo_name": self.repo_name,
            "module_name": self.name,
            "commit": self.commit,
        }
        if self.type is InstallableType.COG:
            module_json["pinned"] = self.pinned
        return module_json

    @classmethod
    def from_json(
        cls, data: Dict[str, Union[str, bool]], repo_mgr: RepoManager, *, base_target_dir: Path
    ) -> InstalledModule:
        repo_name = cast(str, data["repo_name"])
        module_name = cast(str, data["module_name"])
        commit = cast(str, data.get("commit", ""))
        pinned = cast(bool, data.get("pinned", False))

        # TypedDict, where are you :/
        repo = repo_mgr.get_repo(repo_name)
        if repo is not None:
            repo_folder = repo.folder_path
        else:
            repo_folder = repo_mgr.repos_folder / "MISSING_REPO"

        location = repo_folder / module_name
        install_location = base_target_dir / module_name

        return cls(
            location=location,
            repo=repo,
            commit=commit,
            pinned=pinned,
            json_repo_name=repo_name,
            install_location=install_location,
        )

    @classmethod
    def from_installable(
        cls, module: Installable, install_location: Path, *, pinned: bool = False
    ) -> InstalledModule:
        return cls(
            location=module._location,
            repo=module.repo,
            commit=module.commit,
            pinned=pinned,
            install_location=install_location,
        )
