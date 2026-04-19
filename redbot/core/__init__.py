import discord as _discord

from .. import __version__, version_info, VersionInfo
from .config import Config

__all__ = ["Config", "__version__", "version_info", "VersionInfo"]

# Prevent discord PyNaCl and davey missing warning
_discord.voice_client.VoiceClient.warn_nacl = False
_discord.voice_client.VoiceClient.warn_dave = False
