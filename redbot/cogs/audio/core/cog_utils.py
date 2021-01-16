from abc import ABC
from typing import Final

from redbot import VersionInfo
from redbot.core import commands

from ..converters import get_lazy_converter, get_playlist_converter

__version__ = VersionInfo.from_json({"major": 2, "minor": 3, "micro": 0, "releaselevel": "final"})

__author__ = ["aikaterna", "Draper"]

_SCHEMA_VERSION: Final[int] = 3
_OWNER_NOTIFICATION: Final[int] = 1

LazyGreedyConverter = get_lazy_converter("--")
PlaylistConverter = get_playlist_converter()
HUMANIZED_PERM = {
    "create_instant_invite": "Create Instant Invite",
    "kick_members": "Kick Members",
    "ban_members": "Ban Members",
    "administrator": "Administrator",
    "manage_channels": "Manage Channels",
    "manage_guild": "Manage Server",
    "add_reactions": "Add Reactions",
    "view_audit_log": "View Audit Log",
    "priority_speaker": "Priority Speaker",
    "stream": "Go Live",
    "read_messages": "Read Text Channels & See Voice Channels",
    "send_messages": "Send Messages",
    "send_tts_messages": "Send TTS Messages",
    "manage_messages": "Manage Messages",
    "embed_links": "Embed Links",
    "attach_files": "Attach Files",
    "read_message_history": "Read Message History",
    "mention_everyone": "Mention @everyone, @here, and All Roles",
    "external_emojis": "Use External Emojis",
    "view_guild_insights": "View Server Insights",
    "connect": "Connect",
    "speak": "Speak",
    "mute_members": "Mute Members",
    "deafen_members": "Deafen Members",
    "move_members": "Move Members",
    "use_voice_activation": "Use Voice Activity",
    "change_nickname": "Change Nickname",
    "manage_nicknames": "Manage Nicknames",
    "manage_roles": "Manage Roles",
    "manage_webhooks": "Manage Webhooks",
    "manage_emojis": "Manage Emojis",
}


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass
