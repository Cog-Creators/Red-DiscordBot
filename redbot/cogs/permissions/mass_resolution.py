from redbot.core import commands
from redbot.core.config import Config
from .resolvers import entries_from_ctx, resolve_lists

# This has optimizations in it that may not hold True if other parts of the permission
# model are changed from the state they are in currently.
#
# This is primarily to help with the performance of the help formatter

async def mass_resolve(*, ctx: commands.Context, config: Config):
    """
    Get's all the permission cog interactions for all loaded commands
    in the given context.
    """

    owner_settings = await config.owner_models()
    guild_owner_settings = (
        await config.guild(ctx.guild).owner_models()
        if ctx.guild else None
    )

    ret = {'allowed': [], 'denied': [], 'default': []}

    for cogname, cog in ctx.bot.cogs.items():
        cog_setting = resolve_cog_or_command(
            objname=cogname, models=owner_settings, ctx=ctx, typ='cogs'
        )
        if cog_setting is None and guild_owner_settings:
            cog_setting = resolve_cog_or_command(
                objname=cogname, models=guild_owner_settings, ctx=ctx, typ='cogs'
            )

        for command in ctx.bot.get_cog_commands(cogname):
            resolution = recursively_resolve(
                com_or_group=command,
                o_models=owner_settings,
                g_models=guild_owner_settings,
                ctx=ctx,
                default=cog_setting,
            )
            
            ret['allowed'].extend(resolution['allowed'])
            ret['denied'].extend(resolution['denied'])
            ret['default'].extend(resolution['default'])


def recursively_resolve(*, com_or_group, o_models, g_models, ctx, default):
    return {}
    # TODO

def resolve_cog_or_command(*, typ, ctx, objname, models: dict) -> bool:
    """
    Resolves models in order.
    """

    resolved = None

    if objname in models.get(typ, {}):
        blacklist = models[typ][objname].get("deny", [])
        whitelist = models[typ][objname].get("allow", [])
        resolved = resolve_lists(ctx=ctx, whitelist=whitelist, blacklist=blacklist)
        if resolved is not None:
            return resolved
        resolved = models[typ][objname].get("default", None)
        if resolved is not None:
            return resolved
    return None