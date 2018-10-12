# These should be gotten rid of
from redbot.core import commands


def mod_or_voice_permissions(**perms):
    async def pred(ctx: commands.Context):
        author = ctx.author
        guild = ctx.guild
        if await ctx.bot.is_owner(author) or guild.owner == author:
            # Author is bot owner or guild owner
            return True

        admin_role = guild.get_role(await ctx.bot.db.guild(guild).admin_role())
        mod_role = guild.get_role(await ctx.bot.db.guild(guild).mod_role())

        if admin_role in author.roles or mod_role in author.roles:
            return True

        for vc in guild.voice_channels:
            resolved = vc.permissions_for(author)
            good = resolved.administrator or all(
                getattr(resolved, name, None) == value for name, value in perms.items()
            )
            if not good:
                return False
        else:
            return True

    return commands.permissions_check(pred)


def admin_or_voice_permissions(**perms):
    async def pred(ctx: commands.Context):
        author = ctx.author
        guild = ctx.guild
        if await ctx.bot.is_owner(author) or guild.owner == author:
            return True
        admin_role = guild.get_role(await ctx.bot.db.guild(guild).admin_role())
        if admin_role in author.roles:
            return True
        for vc in guild.voice_channels:
            resolved = vc.permissions_for(author)
            good = resolved.administrator or all(
                getattr(resolved, name, None) == value for name, value in perms.items()
            )
            if not good:
                return False
        else:
            return True

    return commands.permissions_check(pred)


def bot_has_voice_permissions(**perms):
    async def pred(ctx: commands.Context):
        guild = ctx.guild
        for vc in guild.voice_channels:
            resolved = vc.permissions_for(guild.me)
            good = resolved.administrator or all(
                getattr(resolved, name, None) == value for name, value in perms.items()
            )
            if not good:
                return False
        else:
            return True

    return commands.check(pred)
