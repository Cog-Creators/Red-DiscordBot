from discord.ext import commands
import discord


def mod_or_voice_permissions(**perms):
    async def pred(ctx: commands.Context):
        author = ctx.author
        guild = ctx.guild
        if ctx.bot.is_owner(author) or guild.owner == author:
            # Author is bot owner or guild owner
            return True
        admin_roles = [r for r in guild.roles if r.id == ctx.bot.db.guild(guild).admin_role()]
        admin_role = admin_roles[0] if admin_roles else None
        mod_roles = [r for r in guild.roles if r.id == ctx.bot.db.guild(guild).mod_role()]
        mod_role = mod_roles[0] if mod_roles else None
        if admin_role in author.roles or mod_role in author.roles:
            return True

        for vc in guild.voice_channels:
            resolved = vc.permissions_for(author)
            good = all(getattr(resolved, name, None) == value for name, value in perms.items())
            if not good:
                return False
        else:
            return True
    return commands.check(pred)


def admin_or_voice_permissions(**perms):
    async def pred(ctx: commands.Context):
        author = ctx.author
        guild = ctx.guild
        if ctx.bot.is_owner(author) or guild.owner == author:
            return True
        admin_role = discord.utils.get(guild.roles, id=ctx.bot.db.guild(guild).admin_role())
        if admin_role in author.roles:
            return True
        for vc in guild.voice_channels:
            resolved = vc.permissions_for(author)
            good = all(getattr(resolved, name, None) == value for name, value in perms.items())
            if not good:
                return False
        else:
            return True
    return commands.check(pred)


def bot_has_voice_permissions(**perms):
    async def pred(ctx: commands.Context):
        guild = ctx.guild
        for vc in guild.voice_channels:
            resolved = vc.permissions_for(guild.me)
            good = all(getattr(resolved, name, None) == value for name, value in perms.items())
            if not good:
                return False
        else:
            return True
    return commands.check(pred)
