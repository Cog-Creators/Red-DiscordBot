import argparse
from typing import Union

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


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise commands.BadArgument()


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


class ScopeParser(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):

        target_scope: str = PlaylistScope.GUILD.value
        target_user: Union[discord.Member, discord.User] = ctx.author
        target_guild: discord.Guild = ctx.guild

        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = None

        parser = NoExitParser(description="Playlist Scope Parsing", add_help=False)

        parser.add_argument("--scope", nargs="*", dest="scope", default=[])
        parser.add_argument("--guild", nargs="*", dest="guild", default=[])
        parser.add_argument("--author", nargs="*", dest="author", default=[])
        if not command:
            parser.add_argument("command", nargs="*")

        try:
            vals = vars(parser.parse_args(argument.split()))
        except Exception as exc:
            raise commands.BadArgument() from exc

        if vals["scope"]:
            scope_raw = " ".join(vals["scope"]).strip()
            scope = scope_raw.upper().strip()
            valid_scopes = PlaylistScope.list() + [
                "GLOBAL",
                "GUILD",
                "USER",
                "SERVER",
                "MEMBER",
                "BOT",
            ]
            if scope not in valid_scopes:
                raise commands.BadArgument(
                    _("{} doesn't look like a valid scope.").format(scope_raw)
                )
            target_scope = standardize_scope(scope)

        if await ctx.bot.is_owner(ctx.author) and vals["guild"]:
            guild_raw = " ".join(vals["guild"]).strip()
            if guild_raw.isnumeric():
                guild_raw = int(guild_raw)
                target_guild = ctx.bot.get_guild(guild_raw)
            else:
                guild_converter = commands.GuildConverter(ctx, guild_raw)
                try:
                    target_guild = await guild_converter.convert(ctx, guild_raw)
                except commands.BadArgument:
                    target_guild = None
            if target_guild is None:
                target_guild = await ctx.bot.fetch_guild(guild_raw) or ctx.author

        if vals["author"]:
            user_raw = " ".join(vals["author"]).strip()
            if user_raw.isnumeric():
                user_raw = int(user_raw)
                target_user = ctx.bot.get_user(user_raw)
            else:
                member_converter = commands.MemberConverter()
                user_converter = commands.UserConverter()
                try:
                    target_user = await member_converter.convert(ctx, user_raw)
                except commands.BadArgument:
                    try:
                        target_user = await user_converter.convert(ctx, user_raw)
                    except commands.BadArgument:
                        target_user = None
            if target_user is None:
                target_user = await ctx.bot.fetch_user(user_raw) or ctx.author

        return target_scope, target_user, target_guild
