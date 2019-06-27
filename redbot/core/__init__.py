import colorama as _colorama
import discord as _discord
import yaml as _yaml

from .. import __version__, version_info, VersionInfo
from .config import Config
from .utils.safety import warn_unsafe as _warn_unsafe

__all__ = ["Config", "__version__", "version_info", "VersionInfo"]

_colorama.init()

# Prevent discord PyNaCl missing warning
_discord.voice_client.VoiceClient.warn_nacl = False
