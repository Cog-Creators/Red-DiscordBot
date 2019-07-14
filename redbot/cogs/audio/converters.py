from typing import Dict, Optional, Tuple

import discord

from redbot.core import Config
from redbot.core import commands
from redbot.core.i18n import Translator
from .playlists import PlaylistScope, standardize_scope, _pass_config_to_playlist

_ = Translator("Audio", __file__)

__all__ = ["ScopeConverter", "PlaylistConverter"]
_config = None


def _pass_config_to_dependencies(config: Config):
    global _config
    if _config is None:
        _config = config
    _pass_config_to_playlist(config)


class ScopeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        scope = arg.upper()
        valid_scopes = PlaylistScope.list() + [
            "GLOBAL",
            "GUILD",
            "USER",
            "SERVER",
            "MEMBER",
            "BOT",
        ]
        if scope not in valid_scopes:
            raise commands.BadArgument(_("{} doesn't look like a valid scope.").format(arg))
        return standardize_scope(arg)


class PlaylistConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> dict:
        global_scope = await _config.custom(PlaylistScope.GLOBAL.value).all()
        guild_scope = await _config.custom(PlaylistScope.GUILD.value).all()
        user_scope = await _config.custom(PlaylistScope.USER.value).all()
        user_matches = [
            (uid, pid, pdata)
            for uid, data in user_scope.items()
            for pid, pdata in data.items()
            if arg == pid or arg.lower() == pdata.get("name").lower()
        ]
        guild_matches = [
            (gid, pid, pdata)
            for gid, data in guild_scope.items()
            for pid, pdata in data.items()
            if arg == pid or arg.lower() == pdata.get("name").lower()
        ]
        global_matches = [
            (None, pid, pdata)
            for pid, pdata in global_scope.items()
            if arg == pid or arg.lower() == pdata.get("name").lower()
        ]
        if not user_matches and not guild_matches and not global_matches:
            raise commands.BadArgument(_("Could not find match '{}' to a playlist").format(arg))

        return {
            PlaylistScope.GLOBAL.value: global_matches,
            PlaylistScope.GUILD.value: guild_matches,
            PlaylistScope.USER.value: user_matches,
            "arg": arg,
        }
