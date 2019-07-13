import discord

from redbot.core.commands import Converter, BadArgument
from redbot.core.i18n import Translator
from .playlists import PlaylistScope, standardize_scope

_ = Translator("Audio", __file__)

__all__ = ["ScopeConverter", "PlaylistConverter"]


class ScopeConverter(Converter):
    async def convert(self, ctx, argument) -> str:
        scope = argument.upper()
        valid_scopes = PlaylistScope.list() + ["GLOBAL", "GUILD", "USER"]
        if scope not in valid_scopes:
            raise BadArgument(_("{} doesn't look like a valid scope.").format(argument))
        return standardize_scope(argument)


class PlaylistConverter(Converter):
    async def convert(self, ctx, argument) -> str:
        scope = argument.upper()
        valid_scopes = PlaylistScope.list() + ["GLOBAL", "GUILD", "USER"]
        if scope not in valid_scopes:
            raise BadArgument(_("{} doesn't look like a valid scope.").format(argument))
        return standardize_scope(argument)
