"""The checks in this module run on every command."""
from . import commands


def init_global_checks(bot):
    @bot.check_once
    async def global_perms(ctx):
        """Check the user is/isn't globally whitelisted/blacklisted."""
        if await bot.is_owner(ctx.author):
            return True

        whitelist = await bot.db.whitelist()
        if whitelist:
            return ctx.author.id in whitelist

        return ctx.author.id not in await bot.db.blacklist()

    @bot.check_once
    async def local_perms(ctx: commands.Context):
        """Check the user is/isn't locally whitelisted/blacklisted."""
        if await bot.is_owner(ctx.author):
            return True
        elif ctx.guild is None:
            return True
        guild_settings = bot.db.guild(ctx.guild)
        local_blacklist = await guild_settings.blacklist()
        local_whitelist = await guild_settings.whitelist()

        _ids = [r.id for r in ctx.author.roles if not r.is_default()]
        _ids.append(ctx.author.id)
        if local_whitelist:
            return any(i in local_whitelist for i in _ids)

        return not any(i in local_blacklist for i in _ids)

    @bot.check_once
    async def bots(ctx):
        """Check the user is not another bot."""
        return not ctx.author.bot
