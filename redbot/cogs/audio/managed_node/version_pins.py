from typing import Final, Tuple

from .ll_version import LavalinkVersion

__all__ = (
    "JAR_VERSION",
    "YT_PLUGIN_VERSION",
    "SUPPORTED_JAVA_VERSIONS",
    "LATEST_SUPPORTED_JAVA_VERSION",
    "OLDER_SUPPORTED_JAVA_VERSIONS",
)


JAR_VERSION: Final[LavalinkVersion] = LavalinkVersion(3, 7, 13, red=5)
YT_PLUGIN_VERSION: Final[str] = "1.18.0"
# keep this sorted from oldest to latest
SUPPORTED_JAVA_VERSIONS: Final[Tuple[int, ...]] = (17, 21, 25)
LATEST_SUPPORTED_JAVA_VERSION: Final = SUPPORTED_JAVA_VERSIONS[-1]
OLDER_SUPPORTED_JAVA_VERSIONS: Final[Tuple[int, ...]] = SUPPORTED_JAVA_VERSIONS[:-1]
