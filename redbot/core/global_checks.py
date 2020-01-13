"""The checks in this module run on every command."""
from . import commands


def init_global_checks(bot):
    @bot.check_one
    def minimum_bot_perms(ctx) -> bool:
        """
        Too many 403, 401, and 429 Errors can cause bots to get global'd
        
        It's reasonable to assume the below as a minimum amount of perms for
        commands.
        """
        return ctx.channel.permissions_for(ctx.me).send_messages

    @bot.check_once
    def actually_up(ctx) -> bool:
        """ 
        Uptime is set during the initial startup process.
        If this hasn't been set, we should assume the bot isn't ready yet. 
        """
        return ctx.bot.uptime is not None

    @bot.check_once
    async def whiteblacklist_checks(ctx) -> bool:
        return await ctx.bot.allowed_by_whitelist_blacklist(ctx.author)

    @bot.check_once
    def bots(ctx) -> bool:
        """Check the user is not another bot."""
        return not ctx.author.bot
