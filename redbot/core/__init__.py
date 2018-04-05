from collections import namedtuple

from .config import Config
from .context import RedContext

__all__ = ["Config", "RedContext", "__version__"]

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')

__version__ = "3.0.0b11"
version_info = VersionInfo(3, 0, 0, 'beta', 11)
