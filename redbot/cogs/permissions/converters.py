import re
from typing import NamedTuple, Union, Optional, cast, Type

from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("PermissionsConverters", __file__)

MENETION_RE = re.compile(r"^<(@[!&]?)|#([0-9]{15,21})>$")


class GlobalUniqueObjectFinder(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):

        objects = {str(c.id): c for c in ctx.bot.get_all_channels()}
        objects.update({str(u.id): u for u in ctx.bot.users})
        for guild in ctx.bot.guilds:
            objects.update({str(r.id): r for r in guild.roles if not r.is_default()})
            objects.update({str(guild.id): guild})

        if arg in objects:
            return objects[arg]

        m = MENETION_RE.match(arg)
        if m:
            ret = objects.get(m.group(2), None)
            if ret:
                return ret

        for func in (lambda obj: str(obj) == arg, lambda obj: obj.name == arg):
            maybe_matches = list(filter(func, objects))
            if len(maybe_matches) == 1:
                return maybe_matches[0]
            if len(maybe_matches) > 0:
                raise commands.BadArgument(
                    _("Could not uniquely match that, please use an id or mention for this"), arg
                )
        raise commands.BadArgument(
            _("Could not uniquely match that, please use an id or mention for this"), arg
        )


class GuildUniqueObjectFinder(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        objects = {str(c.id): c for c in ctx.guild.channels}
        objects.update({str(u.id): u for u in ctx.guild.members})
        objects.update({str(r.id): r for r in ctx.guild.roles})

        if arg in objects:
            return objects[arg]

        m = MENETION_RE.match(arg)
        if m:
            ret = objects.get(m.group(2), None)
            if ret:
                return ret

        for func in (lambda obj: str(obj) == arg, lambda obj: obj.name == arg):
            maybe_matches = list(filter(func, objects))
            if len(maybe_matches) == 1:
                return maybe_matches[0]
            if len(maybe_matches) > 0:
                raise commands.BadArgument(
                    _("Could not uniquely match that, please use an id or mention for this"), arg
                )
        raise commands.BadArgument(
            _("Could not uniquely match that, please use an id or mention for this"), arg
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
