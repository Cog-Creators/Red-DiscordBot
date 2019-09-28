"""The checks in this module run on every command."""
from . import commands


def init_global_checks(bot):
    @bot.check_once
    async def whiteblacklist_checks(ctx):
        return await ctx.bot.allowed_by_whitelist_blacklist(ctx.author)

    @bot.check_once
    async def bots(ctx):
        """Check the user is not another bot."""
        return not ctx.author.bot
