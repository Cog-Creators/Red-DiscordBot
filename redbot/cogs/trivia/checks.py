from redbot.core import commands

__all__ = ("trivia_stop_check",)


def trivia_stop_check():
    async def predicate(ctx: commands.GuildContext) -> bool:
        author = ctx.author
        auth_checks = (
            await ctx.bot.is_owner(author),
            await ctx.bot.is_mod(author),
            await ctx.bot.is_admin(author),
            author == ctx.guild.owner,
            author == session.ctx.author,
        )
        return any(auth_checks)

    return commands.permissions_check(predicate)
