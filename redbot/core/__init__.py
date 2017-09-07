import pkg_resources

from .config import Config

__all__ = ["Config", "__version__"]

__version__ = version = pkg_resources.require("Red-DiscordBot")[0].version
