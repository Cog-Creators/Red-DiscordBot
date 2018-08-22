import sys
import os
from pathlib import Path
from typing import List
from copy import deepcopy
import hashlib
import shutil
import logging

import appdirs
import tempfile

from .json_io import JsonIO

__all__ = [
    "create_temp_config",
    "load_basic_configuration",
    "cog_data_path",
    "core_data_path",
    "cog_global_data_path",
    "core_global_data_path",
    "load_bundled_data",
    "bundled_data_path",
    "storage_details",
    "storage_type",
]

log = logging.getLogger("red.data_manager")

jsonio = None
basic_config = None

instance_name = None

basic_config_default = {"DATA_PATH": None, "COG_PATH_APPEND": "cogs", "CORE_PATH_APPEND": "core"}

config_dir = None
appdir = appdirs.AppDirs("Red-DiscordBot")
if sys.platform == "linux":
    if 0 < os.getuid() < 1000:
        config_dir = Path(appdir.site_data_dir)
if not config_dir:
    config_dir = Path(appdir.user_config_dir)


def _base_data_path() -> Path:
    if basic_config is None:
        raise RuntimeError("You must load the basic config before you can get the base data path.")
    path = basic_config["DATA_PATH"]
    return Path(path).resolve()


def _base_global_data_path() -> Path:
    if basic_config is None:
        raise RuntimeError("You must load the basic config before you can get the base data path.")
    return config_dir.resolve()


def cog_data_path(cog_instance=None, raw_name: str = None) -> Path:
    """Gets the base cog data path. If you want to get the folder with
    which to store your own cog's data please pass in an instance
    of your cog class.

    Either ``cog_instance`` or ``raw_name`` will be used, not both.

    Parameters
    ----------
    cog_instance
        The instance of the cog you wish to get a data path for.
    raw_name : str
        The name of the cog to get a data path for.

    Returns
    -------
    pathlib.Path
        If ``cog_instance`` is provided it will return a path to a folder
        dedicated to a given cog. Otherwise it will return a path to the
        folder that contains data for all cogs.
    """
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the cog data path."
        ) from e
    cog_path = base_data_path / basic_config["COG_PATH_APPEND"]

    if raw_name is not None:
        cog_path = cog_path / raw_name
    elif cog_instance is not None:
        cog_path = cog_path / cog_instance.__class__.__name__
    cog_path.mkdir(exist_ok=True, parents=True)

    return cog_path.resolve()


def core_data_path() -> Path:
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the core data path."
        ) from e
    core_path = base_data_path / basic_config["CORE_PATH_APPEND"]
    core_path.mkdir(exist_ok=True, parents=True)

    return core_path.resolve()


def global_cog_data_path(cog_instance=None, raw_name: str = None) -> Path:
    """Gets the global cog data path. If you want to get the folder with
    which to store your own cog's data please pass in an instance
    of your cog class.

    Instead of :py:func:`cog_data_path` which returns a folder in the
    instance's files, this function returns a folder in Red's internal
    files. **This means that the same folder will be returned for all
    instance**. This can be useful for running a server or storing
    huge files, but should not be used for values depending on the bot.

    Either ``cog_instance`` or ``raw_name`` will be used, not both.

    Parameters
    ----------
    cog_instance
        The instance of the cog you wish to get a data path for.
    raw_name : str
        The name of the cog to get a data path for.

    Returns
    -------
    pathlib.Path
        If ``cog_instance`` is provided it will return a path to a folder
        dedicated to a given cog. Otherwise it will return a path to the
        folder that contains data for all cogs.
    """
    try:
        base_global_data_path = Path(_base_global_data_path())
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the cog data path."
        ) from e
    cog_path = base_global_data_path / basic_config["COG_PATH_APPEND"]

    if raw_name is not None:
        cog_path = cog_path / raw_name
    elif cog_instance is not None:
        cog_path = cog_path / cog_instance.__class__.__name__
    cog_path.mkdir(exist_ok=True, parents=True)

    return cog_path.resolve()


def global_core_data_path() -> Path:
    try:
        base_global_data_path = Path(_base_global_data_path())
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the core data path."
        ) from e
    global_core_path = base_global_data_path / basic_config["CORE_PATH_APPEND"]
    global_core_path.mkdir(exist_ok=True, parents=True)

    return global_core_path.resolve()


def create_temp_config():
    """
    Creates a default instance for Red, so it can be ran
    without creating an instance.

    .. warning:: The data of this instance will be removed
        on next system restart.
    """
    name = "temporary_red"

    default_dirs = deepcopy(basic_config_default)
    default_dirs["DATA_PATH"] = tempfile.mkdtemp()
    default_dirs["STORAGE_TYPE"] = "JSON"
    default_dirs["STORAGE_DETAILS"] = {}

    config = JsonIO(config_file)._load_json()
    config[name] = default_dirs
    JsonIO(config_file)._save_json(config)


def load_basic_configuration(instance_name_: str):
    """Loads the basic bootstrap configuration necessary for `Config`
    to know where to store or look for data.

    .. important::
        It is necessary to call this function BEFORE getting any `Config`
        objects!

    Parameters
    ----------
    instance_name_ : str
        The instance name given by CLI argument and created during
        redbot setup.
    """
    global jsonio
    global basic_config
    global instance_name

    jsonio = JsonIO(config_file)

    instance_name = instance_name_

    try:
        config = jsonio._load_json()
        basic_config = config[instance_name]
    except (FileNotFoundError, KeyError):
        print(
            "You need to configure the bot instance using `redbot-setup`"
            " prior to running the bot."
        )
        sys.exit(1)


def _find_data_files(init_location: str) -> (Path, List[Path]):
    """
    Discovers all files in the bundled data folder of an installed cog.

    Parameters
    ----------
    init_location

    Returns
    -------
    (pathlib.Path, list of pathlib.Path)
    """
    init_file = Path(init_location)
    if not init_file.is_file():
        return []

    package_folder = init_file.parent.resolve() / "data"
    if not package_folder.is_dir():
        return []

    all_files = list(package_folder.rglob("*"))

    return package_folder, [p.resolve() for p in all_files if p.is_file()]


def _compare_and_copy(to_copy: List[Path], bundled_data_dir: Path, cog_data_dir: Path):
    """
    Filters out files from ``to_copy`` that already exist, and are the
    same, in ``data_dir``. The files that are different are copied into
    ``data_dir``.

    Parameters
    ----------
    to_copy : list of pathlib.Path
    bundled_data_dir : pathlib.Path
    cog_data_dir : pathlib.Path
    """

    def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
        for block in bytesiter:
            hasher.update(block)
        return hasher.hexdigest() if ashexstr else hasher.digest()

    def file_as_blockiter(afile, blocksize=65536):
        with afile:
            block = afile.read(blocksize)
            while len(block) > 0:
                yield block
                block = afile.read(blocksize)

    lookup = {p: cog_data_dir.joinpath(p.relative_to(bundled_data_dir)) for p in to_copy}

    for orig, poss_existing in lookup.items():
        if not poss_existing.is_file():
            poss_existing.parent.mkdir(exist_ok=True, parents=True)
            exists_checksum = None
        else:
            exists_checksum = hash_bytestr_iter(
                file_as_blockiter(poss_existing.open("rb")), hashlib.sha256()
            )

        orig_checksum = ...
        if exists_checksum is not None:
            orig_checksum = hash_bytestr_iter(file_as_blockiter(orig.open("rb")), hashlib.sha256())

        if exists_checksum != orig_checksum:
            shutil.copy(str(orig), str(poss_existing))
            log.debug("Copying {} to {}".format(orig, poss_existing))


def load_bundled_data(cog_instance, init_location: str):
    """
    This function copies (and overwrites) data from the ``data/`` folder
    of the installed cog.

    .. important::

        This function MUST be called from the ``setup()`` function of your
        cog.

    Examples
    --------
    >>> from redbot.core import data_manager
    >>>
    >>> def setup(bot):
    >>>     cog = MyCog()
    >>>     data_manager.load_bundled_data(cog, __file__)
    >>>     bot.add_cog(cog)

    Parameters
    ----------
    cog_instance
        An instance of your cog class.
    init_location : str
        The ``__file__`` attribute of the file where your ``setup()``
        function exists.
    """
    bundled_data_folder, to_copy = _find_data_files(init_location)

    cog_data_folder = cog_data_path(cog_instance) / "bundled_data"

    _compare_and_copy(to_copy, bundled_data_folder, cog_data_folder)


def bundled_data_path(cog_instance) -> Path:
    """
    The "data" directory that has been copied from installed cogs.

    .. important::

        You should *NEVER* write to this directory. Data manager will
        overwrite files in this directory each time `load_bundled_data`
        is called. You should instead write to the directory provided by
        `cog_data_path`.

    Parameters
    ----------
    cog_instance

    Returns
    -------
    pathlib.Path
        Path object to the bundled data folder.

    Raises
    ------
    FileNotFoundError
        If no bundled data folder exists or if it hasn't been loaded yet.
    """

    bundled_path = cog_data_path(cog_instance) / "bundled_data"

    if not bundled_path.is_dir():
        raise FileNotFoundError("No such directory {}".format(bundled_path))

    return bundled_path


def storage_type() -> str:
    """Gets the storage type as a string.

    Returns
    -------
    str
    """
    try:
        return basic_config["STORAGE_TYPE"]
    except KeyError as e:
        raise RuntimeError("Bot basic config has not been loaded yet.") from e


def storage_details() -> dict:
    """Gets any details necessary for config drivers to load.

    These are set on setup.

    Returns
    -------
    dict
    """
    try:
        return basic_config["STORAGE_DETAILS"]
    except KeyError as e:
        raise RuntimeError("Bot basic config has not been loaded yet.") from e
