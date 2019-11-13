"""The checks in this module run on every command."""


def init_global_checks(bot):
    @bot.check_once
    def actually_up(ctx):
        """
        Uptime is set during the initial startup process.
        If this hasn't been set, we should assume the bot isn't ready yet.
        """
        return ctx.bot.uptime is not None

    @bot.check_once
    async def whiteblacklist_checks(ctx):
        return await ctx.bot.allowed_by_whitelist_blacklist(ctx.author)

    @bot.check_once
    def bots(ctx):
        """Check the user is not another bot."""
        return not ctx.author.bot
