from typing import NamedTuple, Union, Optional, cast, Type

from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("PermissionsConverters", __file__)


class GlobalUniqueObjectFinder(commands.Converter):
    @staticmethod
    async def convert(ctx: commands.Context, arg: str):
        objects = set(ctx.bot.get_all_channels())
        objects += set(ctx.bot.users)
        for guild in ctx.bot.guilds:
            objects += {r for r in guild.roles if not r.is_default}
            objects.add(guild)

        for func in (
            lambda obj: str(obj.id) == arg,
            lambda obj: getattr(obj, "mention", False) == arg,
            lambda obj: str(obj) == arg,
            lambda obj: obj.name == arg,
        ):
            maybe_matches = list(filter(func, objects))
            if len(maybe_matches) == 1:
                return maybe_matches[0]
            if len(maybe_matches) > 0:
                raise commands.BadArgument(
                    "Could not uniquely match that, please use an id or mention for this", arg
                )
        raise commands.BadArgument(
            "Could not uniquely match that, please use an id or mention for this", arg
        )


class GuildUniqueObjectFinder(commands.Converter):
    @staticmethod
    async def convert(ctx: commands.Context, arg: str):
        objects = set(ctx.guild.channels)
        objects += set(ctx.guild.members)
        objects += set(ctx.guild.roles)

        for func in (
            lambda obj: str(obj.id) == arg,
            lambda obj: getattr(obj, "mention", False) == arg,
            lambda obj: str(obj) == arg,
            lambda obj: obj.name == arg,
        ):
            maybe_matches = list(filter(func, objects))
            if len(maybe_matches) == 1:
                return maybe_matches[0]
            if len(maybe_matches) > 0:
                raise commands.BadArgument(
                    "Could not uniquely match that, please use an id or mention for this", arg
                )
        raise commands.BadArgument(
            "Could not uniquely match that, please use an id or mention for this", arg
        )


class CogOrCommand(NamedTuple):
    type: str
    name: str
    obj: Union[commands.Command, commands.Cog]

    # noinspection PyArgumentList
    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> "CogOrCommand":
        cog = ctx.bot.get_cog(arg)
        if cog:
            return cls(type="COG", name=cog.__class__.__name__, obj=cog)
        cmd = ctx.bot.get_command(arg)
        if cmd:
            return cls(type="COMMAND", name=cmd.qualified_name, obj=cmd)

        raise commands.BadArgument(
            _(
                'Cog or command "{name}" not found. Please note that this is case sensitive.'
            ).format(name=arg)
        )


def RuleType(arg: str) -> bool:
    if arg.lower() in ("allow", "whitelist", "allowed"):
        return True
    if arg.lower() in ("deny", "blacklist", "denied"):
        return False

    raise commands.BadArgument(
        _('"{arg}" is not a valid rule. Valid rules are "allow" or "deny"').format(arg=arg)
    )


def ClearableRuleType(arg: str) -> Optional[bool]:
    if arg.lower() in ("allow", "whitelist", "allowed"):
        return True
    if arg.lower() in ("deny", "blacklist", "denied"):
        return False
    if arg.lower() in ("clear", "reset"):
        return None

    raise commands.BadArgument(
        _(
            '"{arg}" is not a valid rule. Valid rules are "allow" or "deny", or "clear" to '
            "remove the rule"
        ).format(arg=arg)
    )
