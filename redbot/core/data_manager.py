import inspect
import json
import logging
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import platformdirs
from discord.utils import deprecated

from . import commands
from .cli import ExitCodes

__all__ = [
    "create_temp_config",
    "load_basic_configuration",
    "cog_data_path",
    "core_data_path",
    "load_bundled_data",
    "bundled_data_path",
    "storage_details",
    "storage_type",
]

log = logging.getLogger("red.data_manager")

basic_config = None

instance_name = None

basic_config_default: Dict[str, Any] = {
    "DATA_PATH": None,
    "COG_PATH_APPEND": "cogs",
    "CORE_PATH_APPEND": "core",
}

appdir = platformdirs.PlatformDirs("Red-DiscordBot")
config_dir = appdir.user_config_path
_system_user = sys.platform == "linux" and 0 < os.getuid() < 1000
if _system_user:
    if Path.home().exists():
        # We don't want to break someone just because they created home dir
        # but were already using the site_data_path.
        #
        # But otherwise, we do want Red to use user_config_path if home dir exists.
        _maybe_config_file = appdir.site_data_path / "config.json"
        if _maybe_config_file.exists():
            config_dir = _maybe_config_file.parent
    else:
        config_dir = appdir.site_data_path

config_file = config_dir / "config.json"
if not config_file.exists() and sys.platform == "darwin":
    # backwards compatibility with the location given by appdirs 1.4.4 (replaced by platformdirs 2)
    # which was the same as user_data_path
    # https://platformdirs.readthedocs.io/en/stable/changelog.html#platformdirs-2-0-0
    _old_config_location = appdir.user_data_path / "config.json"
    if _old_config_location.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        _old_config_location.rename(config_file)


def load_existing_config():
    """Get the contents of the config file, or an empty dictionary if it does not exist.

    Returns
    -------
    dict
        The config data.
    """
    if not config_file.exists():
        return {}

    with config_file.open(encoding="utf-8") as fs:
        return json.load(fs)


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

    config = load_existing_config()

    config[name] = default_dirs

    with config_file.open("w", encoding="utf-8") as fs:
        json.dump(config, fs, indent=4)


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
    global basic_config
    global instance_name
    instance_name = instance_name_

    try:
        with config_file.open(encoding="utf-8") as fs:
            config = json.load(fs)
    except FileNotFoundError:
        print(
            "You need to configure the bot instance using `redbot-setup`"
            " prior to running the bot."
        )
        sys.exit(ExitCodes.CONFIGURATION_ERROR)
    try:
        basic_config = config[instance_name]
    except KeyError:
        print(
            "Instance with this name doesn't exist."
            " You can create new instance using `redbot-setup` prior to running the bot."
        )
        sys.exit(ExitCodes.INVALID_CLI_USAGE)


def _base_data_path() -> Path:
    if basic_config is None:
        raise RuntimeError("You must load the basic config before you can get the base data path.")
    path = basic_config["DATA_PATH"]
    return Path(path).resolve()


def cog_data_path(cog_instance=None, raw_name: str = None) -> Path:
    """Gets the base cog data path. If you want to get the folder with
    which to store your own cog's data please pass in an instance
    of your cog class.

    Either ``cog_instance`` or ``raw_name`` will be used, not both.

    Parameters
    ----------
    cog_instance
        The instance of the cog you wish to get a data path for.
        If calling from a command or method of your cog, this should be ``self``.
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


# noinspection PyUnusedLocal
@deprecated("bundled_data_path() without calling this function")
def load_bundled_data(cog_instance, init_location: str):
    pass


def bundled_data_path(cog_instance: commands.Cog) -> Path:
    """
    Get the path to the "data" directory bundled with this cog.

    The bundled data folder must be located alongside the ``.py`` file
    which contains the cog class.

    .. important::

        You should *NEVER* write to this directory.

    Parameters
    ----------
    cog_instance
        An instance of your cog. If calling from a command or method of
        your cog, this should be ``self``.

    Returns
    -------
    pathlib.Path
        Path object to the bundled data folder.

    Raises
    ------
    FileNotFoundError
        If no bundled data folder exists.

    """
    bundled_path = Path(inspect.getfile(cog_instance.__class__)).parent / "data"

    if not bundled_path.is_dir():
        raise FileNotFoundError("No such directory {}".format(bundled_path))

    return bundled_path


def storage_type() -> str:
    """Gets the storage type as a string.

    Returns
    -------
    str
        Storage type.
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
        Storage details.
    """
    return basic_config.get("STORAGE_DETAILS", {})
