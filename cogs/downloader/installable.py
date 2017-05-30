import json
from enum import Enum
from pathlib import Path
from typing import Tuple, Union, MutableMapping, Any

from .downloader import log


class InstallableType(Enum):
    UNKNOWN = 0
    COG = 1
    SHARED_LIBRARY = 2


class Installable:
    """
    Base class for anything the Downloader cog can install.
        - Modules
        - Repo Libraries
        - Other stuff?
    """

    INFO_FILE_NAME = "info.json"
    INFO_FILE_DESCRIPTION = """
    The info.json file may exist inside every package folder in the repo,
    it is optional however. This string describes the valid keys within
    an info file (and maybe how the Downloader cog uses them).
    
    KEYS (case sensitive):
        author (tuple of strings) - list of names of authors of the cog
        bot_version (integer) - Major version number of Red that this cog
            was developed for.
        description (string) - A long description of the cog that appears
            when a user executes `!cog info`
        hidden (bool) - Determines if a cog is available for install.
        install_msg (string) - The message that gets displayed when a cog is
            installed
        requirements (tuple of strings) - list of required libraries that are
            passed to pip on cog install
        short (string) - A short description of the cog that appears when
            a user executes `!cog list`
        tags (tuple of strings) - A list of strings that are related to the
            functionality of the cog. Used to aid in searching.
    """

    def __init__(self, location: Path):
        """
        Base installable initializer.
        :param location: Location (file or folder) to the installable.
        """
        self.__location = location

        self.__dependencies = ()
        self.__installable_type = InstallableType.UNKNOWN

        self.__info_file = self._info_file()
        self.__info = {}

        if self.__info_file is not None:
            self.__info = self._process_info_file(self.__info_file)

    async def install_to(self, install_dir: Path) -> bool:
        """
        Installs this installable to the given directory.
        :param install_dir: The installation directory to install to.
        :return: bool - status of installation
        """
        raise NotImplementedError()

    def _info_file(self) -> Union[Path, None]:
        """
        Determines if an information file exists.
        :return: Path to info file or None
        """
        info_path = self.__location / self.INFO_FILE_NAME
        if info_path.is_file():
            return info_path

        return None

    def _process_info_file(self, info_file_path: Path=None) -> MutableMapping[str, Any]:
        """
        Processes an information file. Loads dependencies among other
            information into this object.
        :param info_file_path: Optional path to information file, defaults to `self.__info_file`
        :return: Raw information dictionary
        """
        info_file_path = info_file_path or self.__info_file
        if info_file_path is None or not info_file_path.is_file():
            raise ValueError("No valid information file path was found.")

        info = {}
        with info_file_path.open(encoding='utf-8') as f:
            try:
                info = json.load(f)
            except json.JSONDecodeError:
                info = {}
                log.exception("Invalid JSON information file at path:"
                              " {}".format(info_file_path))

        # TODO: Determine which keys go in the info file.

        return info


class Cog(Installable):
    def __init__(self, location: Path):
        super().__init__(location)
        raise NotImplementedError()


class RepoLibrary(Installable):
    """
    You're welcome Caleb.
    """
    def __init__(self, location: Path):
        super().__init__(location)
        raise NotImplementedError()
