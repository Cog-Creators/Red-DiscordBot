import pkg_resources

from .config import Config
from .context import RedContext

__all__ = ["Config", "RedContext", "__version__"]

__version__ = version = pkg_resources.require("Red-DiscordBot")[0].version
