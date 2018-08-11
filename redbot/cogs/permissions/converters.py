from redbot.core import commands
from typing import Tuple


class CogOrCommand(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Tuple[str]:
        ret = ctx.bot.get_cog(arg)
        if ret:
            return "cogs", ret.__class__.__name__
        ret = ctx.bot.get_command(arg)
        if ret:
            return "commands", ret.qualified_name

        raise commands.BadArgument(
            'Cog or command "{arg}" not found. Please note that this is case sensitive.'
            "".format(arg=arg)
        )


class RuleType(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.lower() in ("allow", "whitelist", "allowed"):
            return "allow"
        if arg.lower() in ("deny", "blacklist", "denied"):
            return "deny"

        raise commands.BadArgument(
            '"{arg}" is not a valid rule. Valid rules are "allow" or "deny"'.format(arg=arg)
        )


class ClearableRuleType(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.lower() in ("allow", "whitelist", "allowed"):
            return "allow"
        if arg.lower() in ("deny", "blacklist", "denied"):
            return "deny"
        if arg.lower() in ("clear", "reset"):
            return "clear"

        raise commands.BadArgument(
            '"{arg}" is not a valid rule. Valid rules are "allow" or "deny", or "clear" to remove the rule'
            "".format(arg=arg)
        )
