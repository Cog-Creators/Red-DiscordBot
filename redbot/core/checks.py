import discord
from redbot.core import commands


async def check_overrides(ctx, *, level):
    if await ctx.bot.is_owner(ctx.author):
        return True
    perm_cog = ctx.bot.get_cog("Permissions")
    if not perm_cog or ctx.cog == perm_cog:
        return None
    # don't break if someone loaded a cog named
    # permissions that doesn't implement this
    func = getattr(perm_cog, "check_overrides", None)
    val = None if func is None else await func(ctx, level)
    return val


def is_owner(**kwargs):
    async def check(ctx):
        override = await check_overrides(ctx, level="owner")
        return override if override is not None else await ctx.bot.is_owner(ctx.author, **kwargs)

    return commands.check(check)


async def check_permissions(ctx, perms):
    if await ctx.bot.is_owner(ctx.author):
        return True
    elif not perms:
        return False
    resolved = ctx.channel.permissions_for(ctx.author)

    return resolved.administrator or all(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


async def is_mod_or_superior(ctx):
    if ctx.guild is None:
        return await ctx.bot.is_owner(ctx.author)
    else:
        author = ctx.author
        settings = ctx.bot.db.guild(ctx.guild)
        mod_role_id = await settings.mod_role()
        admin_role_id = await settings.admin_role()

        mod_role = discord.utils.get(ctx.guild.roles, id=mod_role_id)
        admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id)

        return (
            await ctx.bot.is_owner(ctx.author)
            or mod_role in author.roles
            or admin_role in author.roles
            or author == ctx.guild.owner
        )


async def is_admin_or_superior(ctx):
    if ctx.guild is None:
        return await ctx.bot.is_owner(ctx.author)
    else:
        author = ctx.author
        settings = ctx.bot.db.guild(ctx.guild)
        admin_role_id = await settings.admin_role()
        admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id)

        return (
            await ctx.bot.is_owner(ctx.author)
            or admin_role in author.roles
            or author == ctx.guild.owner
        )


def mod_or_permissions(**perms):
    async def predicate(ctx):
        override = await check_overrides(ctx, level="mod")
        return (
            override
            if override is not None
            else await check_permissions(ctx, perms) or await is_mod_or_superior(ctx)
        )

    return commands.check(predicate)


def admin_or_permissions(**perms):
    async def predicate(ctx):
        override = await check_overrides(ctx, level="admin")
        return (
            override
            if override is not None
            else await check_permissions(ctx, perms) or await is_admin_or_superior(ctx)
        )

    return commands.check(predicate)


def bot_in_a_guild(**kwargs):
    async def predicate(ctx):
        return len(ctx.bot.guilds) > 0

    return commands.check(predicate)


def guildowner_or_permissions(**perms):
    async def predicate(ctx):
        has_perms_or_is_owner = await check_permissions(ctx, perms)
        if ctx.guild is None:
            return has_perms_or_is_owner
        is_guild_owner = ctx.author == ctx.guild.owner

        override = await check_overrides(ctx, level="guildowner")
        return override if override is not None else is_guild_owner or has_perms_or_is_owner

    return commands.check(predicate)


def guildowner():
    return guildowner_or_permissions()


def admin():
    return admin_or_permissions()


def mod():
    return mod_or_permissions()
