import discord as _discord

from .. import __version__, version_info, VersionInfo
from .config import Config
from .utils.safety import warn_unsafe as _warn_unsafe

__all__ = ["Config", "__version__", "version_info", "VersionInfo"]

# Okay, little bunnies! I need you to all gather here in the middle.
_discord.voice_client.VoiceClient.warn_nacl = False
