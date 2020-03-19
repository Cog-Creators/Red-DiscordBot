from redbot.core import commands

def trivia_stop_check(func):
    async def predicate(ctx: commands.Context) -> bool:
        auth_checks = (
            await ctx.bot.is_owner(author),
            await ctx.bot.is_mod(author),
            await ctx.bot.is_admin(author),
            author == ctx.guild.owner,
            author == session.ctx.author,
        )
        return any(auth_checks)

    return commands.permissions_check(predicate)
