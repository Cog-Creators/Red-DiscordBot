from discord.ext import commands


def is_owner(**kwargs):
    async def check(ctx):
        return await ctx.bot.is_owner(ctx.author, **kwargs)
    return commands.check(check)


async def check_permissions(ctx, perms):
    if await ctx.bot.is_owner(ctx.author):
        return True
    elif not perms:
        return False
    resolved = ctx.channel.permissions_for(ctx.author)

    return all(getattr(resolved, name, None) == value for name, value in perms.items())


def mod_or_permissions(**perms):
    async def predicate(ctx):
        has_perms_or_is_owner = await check_permissions(ctx, perms)
        if ctx.guild is None:
            return has_perms_or_is_owner
        author = ctx.author
        mod_role = ctx.bot.db.guild(ctx.guild).mod_role()
        admin_role = ctx.bot.db.guild(ctx.guild).admin_role()
        is_staff = mod_role in author.roles or admin_role in author.roles
        is_guild_owner = author == ctx.guild.owner

        return is_staff or has_perms_or_is_owner or is_guild_owner

    return commands.check(predicate)


def admin_or_permissions(**perms):
    async def predicate(ctx):
        has_perms_or_is_owner = await check_permissions(ctx, perms)
        if ctx.guild is None:
            return has_perms_or_is_owner
        author = ctx.author
        is_guild_owner = author == ctx.guild.owner
        admin_role = ctx.bot.db.guild(ctx.guild).admin_role()

        return admin_role in author.roles or has_perms_or_is_owner or is_guild_owner

    return commands.check(predicate)


def guildowner_or_permissions(**perms):
    async def predicate(ctx):
        has_perms_or_is_owner = await check_permissions(ctx, perms)
        if ctx.guild is None:
            return has_perms_or_is_owner
        is_guild_owner = ctx.author == ctx.guild.owner

        return is_guild_owner or has_perms_or_is_owner

    return commands.check(predicate)


def guildowner():
    return guildowner_or_permissions()


def admin():
    return admin_or_permissions()


def mod():
    return mod_or_permissions()