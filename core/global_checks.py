from discord.ext import commands


def init_global_checks(bot):

    @bot.check
    async def global_perms(ctx):
        if await bot.is_owner(ctx.author):
            return True

        if bot.db.whitelist():
            return ctx.author.id in bot.db.whitelist()

        return ctx.author.id not in bot.db.blacklist()

    @bot.check
    async def local_perms(ctx: commands.Context):
        if await bot.is_owner(ctx.author):
            return True
        elif ctx.message.guild is None:
            return True
        local_blacklist = bot.db.guild(ctx.guild).blacklist()
        local_whitelist = bot.db.guild(ctx.guild).whitelist()

        if local_whitelist:
            return ctx.author.id in local_whitelist

        return ctx.author.id not in local_blacklist

    @bot.check
    async def bots(ctx):
        return not ctx.author.bot
