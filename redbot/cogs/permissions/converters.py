from typing import NamedTuple, Union, Optional, cast, Type

from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("PermissionsConverters", __file__)


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
