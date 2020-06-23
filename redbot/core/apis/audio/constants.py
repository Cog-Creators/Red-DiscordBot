from __future__ import annotations

import pathlib

from typing import Dict, Final, List, Mapping, Optional, Set, Union

from redbot.core import data_manager, Config
from redbot.core.data_manager import cog_data_path

__all__ = [
    "SCHEMA_VERSION",
    "ARG_PARSER_SCOPE_HELP",
    "ARG_PARSER_USER_HELP",
    "ARG_PARSER_GUILD_HELP",
    "HUMANIZED_PERMS_MAPPING",
    "DEFAULT_COG_PERMISSIONS_SETTINGS",
    "DEFAULT_COG_LAVALINK_SETTINGS",
    "DEFAULT_COG_GUILD_SETTINGS",
    "DEFAULT_COG_GLOBAL_SETTINGS",
    "DEFAULT_COG_PLAYLISTS_SETTINGS",
    "DEFAULT_COG_USER_SETTINGS",
    "DEFAULT_COG_CHANNEL_SETTINGS",
    "DEFAULT_COG_EQUALIZER_SETTINGS",
    "VALID_GLOBAL_DEFAULTS",
    "VALID_GUILD_DEFAULTS",
    "LAVALINK_DOWNLOAD_DIR",
    "LAVALINK_DOWNLOAD_URL",
    "LAVALINK_JAR_ENDPOINT",
    "LAVALINK_JAR_FILE",
    "BUNDLED_APP_YML",
    "LAVALINK_APP_YML",
    "JAR_VERSION",
    "JAR_BUILD",
]

# Needed here so that `LAVALINK_DOWNLOAD_DIR` doesnt blow up
Config.get_conf(None, 2711759130, force_registration=True, cog_name="Audio")

SCHEMA_VERSION: Final[int] = 4
JAR_VERSION: Final[str] = "3.3.1"
JAR_BUILD: Final[int] = 987
LAVALINK_DOWNLOAD_URL: Final[str] = (
    "https://github.com/Cog-Creators/Lavalink-Jars/releases/download/"
    f"{JAR_VERSION}_{JAR_BUILD}/"
    "Lavalink.jar"
)
LAVALINK_JAR_ENDPOINT: Final[str] = (
    "https://api.github.com/repos/Cog-Creators/Lavalink-Jars/releases/latest"
)
LAVALINK_DOWNLOAD_DIR: Final[pathlib.Path] = data_manager.cog_data_path(raw_name="Audio")
LAVALINK_JAR_FILE: Final[pathlib.Path] = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"
BUNDLED_APP_YML: Final[pathlib.Path] = pathlib.Path(
    __file__
).parent.parent / "data" / "application.yml"
LAVALINK_APP_YML: Final[pathlib.Path] = LAVALINK_DOWNLOAD_DIR / "application.yml"

ARG_PARSER_SCOPE_HELP: Final[
    str
] = """
Scope must be a valid version of one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User
"""
ARG_PARSER_USER_HELP: Final[
    str
] = """
Author must be a valid version of one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123
"""
ARG_PARSER_GUILD_HELP: Final[
    str
] = """
Guild must be a valid version of one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name
"""


HUMANIZED_PERMS_MAPPING: Final[Mapping[str, str]] = {
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

DEFAULT_COG_PERMISSIONS_SETTINGS: Final[Dict[str, bool]] = {
    "embed_links": True,
    "read_messages": True,
    "send_messages": True,
    "read_message_history": True,
    "add_reactions": True,
}

DEFAULT_COG_LAVALINK_SETTINGS: Final[Dict[str, Dict[str, Union[int, str]]]] = {
    "2711759130": {
        "host": "localhost",
        "port": 2333,
        "rest_uri": "http://localhost:2333",
        "password": "youshallnotpass",
        "identifier": "2711759130",
        "region": "",
        "shard_id": 1,
        "search_only": False,
    }
}

DEFAULT_COG_GUILD_SETTINGS: Final[
    Dict[str, Union[bool, None, int, str, List, Dict[str, Optional[bool]]]]
] = {
    "auto_play": False,
    "autoplaylist": {"enabled": False, "id": None, "name": None, "scope": None},
    "persist_queue": None,
    "disconnect": None,
    "dj_enabled": False,
    "dj_role": None,
    "dj_roles": [],
    "daily_playlists": False,
    "emptydc_enabled": None,
    "emptydc_timer": 0,
    "emptypause_enabled": False,
    "emptypause_timer": 0,
    "jukebox": False,
    "jukebox_price": 0,
    "maxlength": 0,
    "notify": False,
    "prefer_lyrics": False,
    "repeat": False,
    "shuffle": False,
    "shuffle_bumped": True,
    "thumbnail": False,
    "volume": 100,
    "vote_enabled": False,
    "vote_percent": 51,
    "url_keyword_blacklist": [],
    "url_keyword_whitelist": [],
    "whitelisted_vc": [],
    "whitelisted_text": [],
    "country_code": "US",
    "vc_restricted": True,
}
VALID_GUILD_DEFAULTS: Set[str] = {
    "auto_play",
    "autoplaylist",
    "persist_queue",
    "disconnect",
    "dj_enabled",
    "dj_roles",
    "daily_playlists",
    "emptydc_enabled",
    "emptydc_timer",
    "emptypause_enabled",
    "emptypause_timer",
    "jukebox",
    "jukebox_price",
    "jukebox_price",
    "maxlength",
    "notify",
    "prefer_lyrics",
    "repeat",
    "shuffle",
    "shuffle_bumped",
    "thumbnail",
    "volume",
    "vote_enabled",
    "vote_percent",
    "url_keyword_blacklist",
    "url_keyword_whitelist",
    "whitelisted_vc",
    "whitelisted_text",
    "country_code",
    "vc_restricted",
}

DEFAULT_COG_CHANNEL_SETTINGS: Final[str, Union[None, bool, str, int]] = {"volume": 100}
DEFAULT_COG_GLOBAL_SETTINGS: Final[
    Dict[str, Union[None, bool, str, List, int, Dict[str, Dict[str, Union[int, str]]]]]
] = {
    "schema_version": 1,
    "cache_level": 0,
    "cache_age": 365,
    "daily_playlists": False,
    "global_db_enabled": True,
    "global_db_get_timeout": 5,
    "status": False,
    "volume": 250,
    "use_external_lavalink": False,
    "restrict": True,
    "disconnect": False,
    "localpath": str(cog_data_path(raw_name="Audio")),
    "persist_queue": None,
    "emptydc_enabled": False,
    "emptydc_timer": 0,
    "thumbnail": None,
    "maxlength": 0,
    "url_keyword_blacklist": [],
    "url_keyword_whitelist": [],
    "nodes": {},
    "lavalink__jar_url": None,
    "lavalink__jar_build": None,
    "lavalink__use_managed": True,
    "lavalink__autoupdate": False,
    "vc_restricted": True,
}
VALID_GLOBAL_DEFAULTS: Set[str] = {
    "schema_version",
    "cache_level",
    "cache_age",
    "daily_playlists",
    "global_db_enabled",
    "global_db_get_timeout",
    "status",
    "restrict",
    "disconnect",
    "localpath",
    "persist_queue",
    "emptydc_enabled",
    "thumbnail",
    "emptydc_timer",
    "maxlength",
    "url_keyword_blacklist",
    "url_keyword_whitelist",
    "nodes",
    "lavalink",
    "volume",
    "vc_restricted",
}

DEFAULT_COG_GLOBAL_SETTINGS.update(DEFAULT_COG_LAVALINK_SETTINGS["2711759130"])

DEFAULT_COG_PLAYLISTS_SETTINGS: Final[Dict[str, Union[None, List]]] = {
    "id": None,
    "author": None,
    "name": None,
    "playlist_url": None,
    "tracks": [],
}

DEFAULT_COG_EQUALIZER_SETTINGS: Final[Dict[str, Union[Dict, List]]] = {
    "eq_bands": [],
    "eq_presets": {},
}
DEFAULT_COG_USER_SETTINGS: Final[Dict[str, None]] = {"country_code": None}


REGION_AGGREGATION: Dict[str, str] = {
    "dubai": "singapore",
    "amsterdam": "europe",
    "london": "europe",
    "frankfurt": "europe",
    "eu-central": "europe",
    "eu-west": "europe",
}
