# -*- coding: utf-8 -*-
# Standard Library
import argparse
import functools

from typing import Optional, Tuple, Union

# Red Dependencies
import discord

# Red Imports
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator

# Red Relative Imports
from .playlists import PlaylistScope, standardize_scope

_ = Translator("Audio", __file__)

__all__ = [
    "ComplexScopeParser",
    "PlaylistConverter",
    "ScopeParser",
    "LazyGreedyConverter",
    "standardize_scope",
    "get_lazy_converter",
    "get_playlist_converter",
]

_config = None
_bot = None

_SCOPE_HELP = """
Scope must be a valid version of one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User
"""
_USER_HELP = """
Author must be a valid version of one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123
"""
_GUILD_HELP = """
Guild must be a valid version of one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name
"""


def _pass_config_to_converters(config: Config, bot: Red):
    global _config, _bot
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot


class PlaylistConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> dict:
        global_scope = await _config.custom(PlaylistScope.GLOBAL.value).all()
        guild_scope = await _config.custom(PlaylistScope.GUILD.value).all()
        user_scope = await _config.custom(PlaylistScope.USER.value).all()
        user_matches = [
            (uid, pid, pdata)
            for uid, data in user_scope.items()
            for pid, pdata in data.items()
            if arg == pid or arg.lower() in pdata.get("name", "").lower()
        ]
        guild_matches = [
            (gid, pid, pdata)
            for gid, data in guild_scope.items()
            for pid, pdata in data.items()
            if arg == pid or arg.lower() in pdata.get("name", "").lower()
        ]
        global_matches = [
            (None, pid, pdata)
            for pid, pdata in global_scope.items()
            if arg == pid or arg.lower() in pdata.get("name", "").lower()
        ]
        if not user_matches and not guild_matches and not global_matches:
            raise commands.BadArgument(_("Could not match '{}' to a playlist.").format(arg))

        return {
            PlaylistScope.GLOBAL.value: global_matches,
            PlaylistScope.GUILD.value: guild_matches,
            PlaylistScope.USER.value: user_matches,
            "arg": arg,
        }


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise commands.BadArgument()


class ScopeParser(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Tuple[str, discord.User, Optional[discord.Guild], bool]:
        target_scope: str = PlaylistScope.GUILD.value
        target_user: Optional[Union[discord.Member, discord.User]] = ctx.author
        target_guild: Optional[discord.Guild] = ctx.guild
        specified_user = False

        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = None

        parser = NoExitParser(description="Playlist Scope Parsing.", add_help=False)

        parser.add_argument("--scope", nargs="*", dest="scope", default=[])
        parser.add_argument("--guild", nargs="*", dest="guild", default=[])
        parser.add_argument("--server", nargs="*", dest="guild", default=[])
        parser.add_argument("--author", nargs="*", dest="author", default=[])
        parser.add_argument("--user", nargs="*", dest="author", default=[])
        parser.add_argument("--member", nargs="*", dest="author", default=[])

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
                "AUTHOR",
                "USER",
                "SERVER",
                "MEMBER",
                "BOT",
            ]
            if scope not in valid_scopes:
                raise commands.ArgParserFailure("--scope", scope_raw, custom_help=_SCOPE_HELP)
            target_scope = standardize_scope(scope)
        elif "--scope" in argument and not vals["scope"]:
            raise commands.ArgParserFailure("--scope", "Nothing", custom_help=_SCOPE_HELP)

        is_owner = await ctx.bot.is_owner(ctx.author)
        guild = vals.get("guild", None) or vals.get("server", None)
        if is_owner and guild:
            target_guild = None
            guild_raw = " ".join(guild).strip()
            if guild_raw.isnumeric():
                guild_raw = int(guild_raw)
                try:
                    target_guild = ctx.bot.get_guild(guild_raw)
                except Exception:
                    target_guild = None
                guild_raw = str(guild_raw)
            if target_guild is None:
                try:
                    target_guild = await commands.GuildConverter.convert(ctx, guild_raw)
                except Exception:
                    target_guild = None
            if target_guild is None:
                try:
                    target_guild = await ctx.bot.fetch_guild(guild_raw)
                except Exception:
                    target_guild = None
            if target_guild is None:
                raise commands.ArgParserFailure("--guild", guild_raw, custom_help=_GUILD_HELP)
        elif not is_owner and (guild or any(x in argument for x in ["--guild", "--server"])):
            raise commands.BadArgument("You cannot use `--guild`")
        elif any(x in argument for x in ["--guild", "--server"]):
            raise commands.ArgParserFailure("--guild", "Nothing", custom_help=_GUILD_HELP)

        author = vals.get("author", None) or vals.get("user", None) or vals.get("member", None)
        if author:
            target_user = None
            user_raw = " ".join(author).strip()
            if user_raw.isnumeric():
                user_raw = int(user_raw)
                try:
                    target_user = ctx.bot.get_user(user_raw)
                except Exception:
                    target_user = None
                user_raw = str(user_raw)
            if target_user is None:
                member_converter = commands.MemberConverter()
                user_converter = commands.UserConverter()
                try:
                    target_user = await member_converter.convert(ctx, user_raw)
                except Exception:
                    try:
                        target_user = await user_converter.convert(ctx, user_raw)
                    except Exception:
                        target_user = None
            if target_user is None:
                try:
                    target_user = await ctx.bot.fetch_user(user_raw)
                except Exception:
                    target_user = None
            if target_user is None:
                raise commands.ArgParserFailure("--author", user_raw, custom_help=_USER_HELP)
            else:
                specified_user = True
        elif any(x in argument for x in ["--author", "--user", "--member"]):
            raise commands.ArgParserFailure("--scope", "Nothing", custom_help=_USER_HELP)

        return target_scope, target_user, target_guild, specified_user


class ComplexScopeParser(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Tuple[
        str,
        discord.User,
        Optional[discord.Guild],
        bool,
        str,
        discord.User,
        Optional[discord.Guild],
        bool,
    ]:

        target_scope: str = PlaylistScope.GUILD.value
        target_user: Optional[Union[discord.Member, discord.User]] = ctx.author
        target_guild: Optional[discord.Guild] = ctx.guild
        specified_target_user = False

        source_scope: str = PlaylistScope.GUILD.value
        source_user: Optional[Union[discord.Member, discord.User]] = ctx.author
        source_guild: Optional[discord.Guild] = ctx.guild
        specified_source_user = False

        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = None

        parser = NoExitParser(description="Playlist Scope Parsing.", add_help=False)

        parser.add_argument("--to-scope", nargs="*", dest="to_scope", default=[])
        parser.add_argument("--to-guild", nargs="*", dest="to_guild", default=[])
        parser.add_argument("--to-server", nargs="*", dest="to_server", default=[])
        parser.add_argument("--to-author", nargs="*", dest="to_author", default=[])
        parser.add_argument("--to-user", nargs="*", dest="to_user", default=[])
        parser.add_argument("--to-member", nargs="*", dest="to_member", default=[])

        parser.add_argument("--from-scope", nargs="*", dest="from_scope", default=[])
        parser.add_argument("--from-guild", nargs="*", dest="from_guild", default=[])
        parser.add_argument("--from-server", nargs="*", dest="from_server", default=[])
        parser.add_argument("--from-author", nargs="*", dest="from_author", default=[])
        parser.add_argument("--from-user", nargs="*", dest="from_user", default=[])
        parser.add_argument("--from-member", nargs="*", dest="from_member", default=[])

        if not command:
            parser.add_argument("command", nargs="*")

        try:
            vals = vars(parser.parse_args(argument.split()))
        except Exception as exc:
            raise commands.BadArgument() from exc

        is_owner = await ctx.bot.is_owner(ctx.author)
        valid_scopes = PlaylistScope.list() + [
            "GLOBAL",
            "GUILD",
            "AUTHOR",
            "USER",
            "SERVER",
            "MEMBER",
            "BOT",
        ]

        if vals["to_scope"]:
            to_scope_raw = " ".join(vals["to_scope"]).strip()
            to_scope = to_scope_raw.upper().strip()
            if to_scope not in valid_scopes:
                raise commands.ArgParserFailure(
                    "--to-scope", to_scope_raw, custom_help=_SCOPE_HELP
                )
            target_scope = standardize_scope(to_scope)
        elif "--to-scope" in argument and not vals["to_scope"]:
            raise commands.ArgParserFailure("--to-scope", "Nothing", custom_help=_SCOPE_HELP)

        if vals["from_scope"]:
            from_scope_raw = " ".join(vals["from_scope"]).strip()
            from_scope = from_scope_raw.upper().strip()

            if from_scope not in valid_scopes:
                raise commands.ArgParserFailure(
                    "--from-scope", from_scope_raw, custom_help=_SCOPE_HELP
                )
            source_scope = standardize_scope(from_scope)
        elif "--from-scope" in argument and not vals["to_scope"]:
            raise commands.ArgParserFailure("--to-scope", "Nothing", custom_help=_SCOPE_HELP)

        to_guild = vals.get("to_guild", None) or vals.get("to_server", None)
        if is_owner and to_guild:
            target_guild = None
            to_guild_raw = " ".join(to_guild).strip()
            if to_guild_raw.isnumeric():
                to_guild_raw = int(to_guild_raw)
                try:
                    target_guild = ctx.bot.get_guild(to_guild_raw)
                except Exception:
                    target_guild = None
                to_guild_raw = str(to_guild_raw)
            if target_guild is None:
                try:
                    target_guild = await commands.GuildConverter.convert(ctx, to_guild_raw)
                except Exception:
                    target_guild = None
            if target_guild is None:
                try:
                    target_guild = await ctx.bot.fetch_guild(to_guild_raw)
                except Exception:
                    target_guild = None
            if target_guild is None:
                raise commands.ArgParserFailure(
                    "--to-guild", to_guild_raw, custom_help=_GUILD_HELP
                )
        elif not is_owner and (
            to_guild or any(x in argument for x in ["--to-guild", "--to-server"])
        ):
            raise commands.BadArgument("You cannot use `--to-server`")
        elif any(x in argument for x in ["--to-guild", "--to-server"]):
            raise commands.ArgParserFailure("--to-server", "Nothing", custom_help=_GUILD_HELP)

        from_guild = vals.get("from_guild", None) or vals.get("from_server", None)
        if is_owner and from_guild:
            source_guild = None
            from_guild_raw = " ".join(from_guild).strip()
            if from_guild_raw.isnumeric():
                from_guild_raw = int(from_guild_raw)
                try:
                    source_guild = ctx.bot.get_guild(from_guild_raw)
                except Exception:
                    source_guild = None
                from_guild_raw = str(from_guild_raw)
            if source_guild is None:
                try:
                    source_guild = await commands.GuildConverter.convert(ctx, from_guild_raw)
                except Exception:
                    source_guild = None
            if source_guild is None:
                try:
                    source_guild = await ctx.bot.fetch_guild(from_guild_raw)
                except Exception:
                    source_guild = None
            if source_guild is None:
                raise commands.ArgParserFailure(
                    "--from-guild", from_guild_raw, custom_help=_GUILD_HELP
                )
        elif not is_owner and (
            from_guild or any(x in argument for x in ["--from-guild", "--from-server"])
        ):
            raise commands.BadArgument("You cannot use `--from-server`")
        elif any(x in argument for x in ["--from-guild", "--from-server"]):
            raise commands.ArgParserFailure("--from-server", "Nothing", custom_help=_GUILD_HELP)

        to_author = (
            vals.get("to_author", None) or vals.get("to_user", None) or vals.get("to_member", None)
        )
        if to_author:
            target_user = None
            to_user_raw = " ".join(to_author).strip()
            if to_user_raw.isnumeric():
                to_user_raw = int(to_user_raw)
                try:
                    source_user = ctx.bot.get_user(to_user_raw)
                except Exception:
                    source_user = None
                to_user_raw = str(to_user_raw)
            if target_user is None:
                member_converter = commands.MemberConverter()
                user_converter = commands.UserConverter()
                try:
                    target_user = await member_converter.convert(ctx, to_user_raw)
                except Exception:
                    try:
                        target_user = await user_converter.convert(ctx, to_user_raw)
                    except Exception:
                        target_user = None
            if target_user is None:
                try:
                    target_user = await ctx.bot.fetch_user(to_user_raw)
                except Exception:
                    target_user = None
            if target_user is None:
                raise commands.ArgParserFailure("--to-author", to_user_raw, custom_help=_USER_HELP)
            else:
                specified_target_user = True
        elif any(x in argument for x in ["--to-author", "--to-user", "--to-member"]):
            raise commands.ArgParserFailure("--to-user", "Nothing", custom_help=_USER_HELP)

        from_author = (
            vals.get("from_author", None)
            or vals.get("from_user", None)
            or vals.get("from_member", None)
        )
        if from_author:
            source_user = None
            from_user_raw = " ".join(from_author).strip()
            if from_user_raw.isnumeric():
                from_user_raw = int(from_user_raw)
                try:
                    target_user = ctx.bot.get_user(from_user_raw)
                except Exception:
                    source_user = None
                from_user_raw = str(from_user_raw)
            if source_user is None:
                member_converter = commands.MemberConverter()
                user_converter = commands.UserConverter()
                try:
                    source_user = await member_converter.convert(ctx, from_user_raw)
                except Exception:
                    try:
                        source_user = await user_converter.convert(ctx, from_user_raw)
                    except Exception:
                        source_user = None
            if source_user is None:
                try:
                    source_user = await ctx.bot.fetch_user(from_user_raw)
                except Exception:
                    source_user = None
            if source_user is None:
                raise commands.ArgParserFailure(
                    "--from-author", from_user_raw, custom_help=_USER_HELP
                )
            else:
                specified_source_user = True
        elif any(x in argument for x in ["--from-author", "--from-user", "--from-member"]):
            raise commands.ArgParserFailure("--from-user", "Nothing", custom_help=_USER_HELP)

        return (
            source_scope,
            source_user,
            source_guild,
            specified_source_user,
            target_scope,
            target_user,
            target_guild,
            specified_target_user,
        )


class LazyGreedyConverter(commands.Converter):
    def __init__(self, splitter: str):
        self.splitter_Value = splitter

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        full_message = ctx.message.content.partition(f" {argument} ")
        if len(full_message) == 1:
            full_message = (
                (argument if argument not in full_message else "") + " " + full_message[0]
            )
        elif len(full_message) > 1:
            full_message = (
                (argument if argument not in full_message else "") + " " + full_message[-1]
            )
        greedy_output = (" " + full_message.replace("—", "--")).partition(
            f" {self.splitter_Value}"
        )[0]
        return f"{greedy_output}".strip()


def get_lazy_converter(splitter: str) -> type:
    """Returns a typechecking safe `LazyGreedyConverter` suitable for use with discord.py."""

    class PartialMeta(type(LazyGreedyConverter)):
        __call__ = functools.partialmethod(type(LazyGreedyConverter).__call__, splitter)

    class ValidatedConverter(LazyGreedyConverter, metaclass=PartialMeta):
        pass

    return ValidatedConverter


def get_playlist_converter() -> type:
    """Returns a typechecking safe `PlaylistConverter` suitable for use with discord.py."""

    class PartialMeta(type(PlaylistConverter)):
        __call__ = functools.partialmethod(type(PlaylistConverter).__call__)

    class ValidatedConverter(PlaylistConverter, metaclass=PartialMeta):
        pass

    return ValidatedConverter
