from pathlib import Path

from core.json_io import JsonIO

jsonio = None
basic_config = None

basic_config_default = {
    "DATA_PATH": None,
    "COG_PATH_APPEND": "cogs",
    "CORE_PATH_APPEND": "core"
}


def load_basic_configuration(path: Path):
    global jsonio
    global basic_config

    jsonio = JsonIO(path)
    basic_config = jsonio._load_json()


def _base_data_path() -> Path:
    if basic_config is None:
        raise RuntimeError("You must load the basic config before you"
                           " can get the base data path.")
    path = basic_config['DATA_PATH']
    return Path(path).resolve()


def cog_data_path(cog_instance=None) -> Path:
    """
    Gets the base cog data path. If you want to get the folder with
        which to store your own cog's data please pass in an instance
        of your cog class.
    :param cog_instance:
    :return:
    """
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError as e:
        raise RuntimeError("You must load the basic config before you"
                           " can get the cog data path.") from e
    cog_path = base_data_path / basic_config['COG_PATH_APPEND']
    if cog_instance:
        cog_path = cog_path / cog_instance.__class__.__name__
    cog_path.mkdir(exist_ok=True, parents=True)

    return cog_path.resolve()


def core_data_path() -> Path:
    try:
        base_data_path = Path(_base_data_path())
    except RuntimeError as e:
        raise RuntimeError("You must load the basic config before you"
                           " can get the core data path.") from e
    core_path = base_data_path / basic_config['CORE_PATH_APPEND']
    core_path.mkdir(exist_ok=True, parents=True)

    return core_path.resolve()
