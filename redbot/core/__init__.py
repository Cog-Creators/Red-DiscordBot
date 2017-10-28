import pkg_resources

from .config import Config
from .context import RedContext

__all__ = ["Config", "RedContext", "__version__"]

try:
    __version__ = pkg_resources.require("Red-DiscordBot")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "3.0.0"
