from typing import Final

from .ll_version import LavalinkVersion

__all__ = ("JAR_VERSION", "YT_PLUGIN_VERSION")


JAR_VERSION: Final[LavalinkVersion] = LavalinkVersion(3, 7, 11, red=3)
YT_PLUGIN_VERSION: Final[str] = "1.5.2"
