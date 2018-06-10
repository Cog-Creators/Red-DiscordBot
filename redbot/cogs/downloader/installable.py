import json
import distutils.dir_util
import shutil
from enum import Enum
from pathlib import Path
from typing import MutableMapping, Any, TYPE_CHECKING

from .log import log
from .json_mixins import RepoJSONMixin

if TYPE_CHECKING:
    from .repo_manager import RepoManager


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

    def __init__(self, location: Path):
        """Base installable initializer.

        Parameters
        ----------
        location : pathlib.Path
            Location (file or folder) to the installable.

        """
        super().__init__(location)

        self._location = location

        self.repo_name = self._location.parent.stem

        self.author = ()
        self.bot_version = (3, 0, 0)
        self.min_python_version = (3, 5, 1)
        self.hidden = False
        self.disabled = False
        self.required_cogs = {}  # Cog name -> repo URL
        self.requirements = ()
        self.tags = ()
        self.type = InstallableType.UNKNOWN

        if self._info_file.exists():
            self._process_info_file(self._info_file)

        if self._info == {}:
            self.type = InstallableType.COG

    def __eq__(self, other):
        # noinspection PyProtectedMember
        return self._location == other._location

    def __hash__(self):
        return hash(self._location)

    @property
    def name(self):
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
        if self._location.is_file():
            copy_func = shutil.copy2
        else:
            copy_func = distutils.dir_util.copy_tree

        # noinspection PyBroadException
        try:
            copy_func(src=str(self._location), dst=str(target_dir / self._location.stem))
        except:
            log.exception("Error occurred when copying path: {}".format(self._location))
            return False
        return True

    def _read_info_file(self):
        super()._read_info_file()

        if self._info_file.exists():
            self._process_info_file()

    def _process_info_file(self, info_file_path: Path = None) -> MutableMapping[str, Any]:
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

        info = {}
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
            bot_version = tuple(info.get("bot_version", [3, 0, 0]))
        except ValueError:
            bot_version = self.bot_version
        self.bot_version = bot_version

        try:
            min_python_version = tuple(info.get("min_python_version", [3, 5, 1]))
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

    def to_json(self):
        return {"repo_name": self.repo_name, "cog_name": self.name}

    @classmethod
    def from_json(cls, data: dict, repo_mgr: "RepoManager"):
        repo_name = data["repo_name"]
        cog_name = data["cog_name"]

        repo = repo_mgr.get_repo(repo_name)
        if repo is not None:
            repo_folder = repo.folder_path
        else:
            repo_folder = repo_mgr.repos_folder / "MISSING_REPO"

        location = repo_folder / cog_name

        return cls(location=location)
