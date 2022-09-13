import discord as _discord

from .. import VersionInfo, __version__, version_info
from .config import Config

__all__ = ["Config", "__version__", "version_info", "VersionInfo"]

# Prevent discord PyNaCl missing warning
_discord.voice_client.VoiceClient.warn_nacl = False
