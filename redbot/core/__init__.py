import pkg_resources

__version__ = version = pkg_resources.require("Red-DiscordBot")[0].version

from .config import Config
from .main import main

__all__ = ["Config", "main", "__version__"]
