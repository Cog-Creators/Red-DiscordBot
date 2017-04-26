def init_global_checks(bot):

    @bot.check
    async def global_perms(ctx):
        if await bot.is_owner(ctx.author):
            return True

        if bot.db.get_global("whitelist", []):
            return ctx.author.id in bot.db.get_global("whitelist", [])

        return ctx.author.id not in bot.db.get_global("blacklist", [])

    @bot.check
    async def local_perms(ctx):
        if await bot.is_owner(ctx.author):
            return True
        elif ctx.message.guild is None:
            return True
        guild_perms = bot.db.get_all(ctx.guild, {})
        local_blacklist = guild_perms.get("blacklist", [])
        local_whitelist = guild_perms.get("whitelist", [])

        if local_whitelist:
            return ctx.author.id in local_whitelist

        return ctx.author.id not in local_blacklist

    @bot.check
    async def bots(ctx):
        return not ctx.author.bot
