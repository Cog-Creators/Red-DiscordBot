from discord.ext import commands


def is_owner(**kwargs):
    async def check(ctx):
        return await ctx.bot.is_owner(ctx.author, **kwargs)
    return commands.check(check)