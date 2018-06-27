from redbot.core import commands
from redbot.core.config import Config
from .resolvers import entries_from_ctx, resolve_lists

# This has optimizations in it that may not hold True if other parts of the permission
# model are changed from the state they are in currently.
#
# This is primarily to help with the performance of the help formatter

# This is less efficient if only checking one command,
# but is much faster for checking all of them.


async def mass_resolve(*, ctx: commands.Context, config: Config):
    """
    Get's all the permission cog interactions for all loaded commands
    in the given context.
    """

    owner_settings = await config.owner_models()
    guild_owner_settings = await config.guild(ctx.guild).owner_models() if ctx.guild else None

    ret = {"allowed": [], "denied": [], "default": []}

    for cogname, cog in ctx.bot.cogs.items():

        cog_setting = resolve_cog_or_command(
            objname=cogname, models=owner_settings, ctx=ctx, typ="cogs"
        )
        if cog_setting is None and guild_owner_settings:
            cog_setting = resolve_cog_or_command(
                objname=cogname, models=guild_owner_settings, ctx=ctx, typ="cogs"
            )

        for command in [c for c in ctx.bot.all_commands.values() if c.instance is cog]:
            resolution = recursively_resolve(
                com_or_group=command,
                o_models=owner_settings,
                g_models=guild_owner_settings,
                ctx=ctx,
            )

            for com, resolved in resolution:
                if resolved is None:
                    resolved = cog_setting
                if resolved is True:
                    ret["allowed"].append(com)
                elif resolved is False:
                    ret["denied"].append(com)
                else:
                    ret["default"].append(com)

    ret = {k: set(v) for k, v in ret.items()}

    return ret


def recursively_resolve(*, com_or_group, o_models, g_models, ctx, override=False):
    ret = []
    if override:
        current = False
    else:
        current = resolve_cog_or_command(
            typ="commands", objname=com_or_group.qualified_name, ctx=ctx, models=o_models
        )
        if current is None and g_models:
            current = resolve_cog_or_command(
                typ="commands", objname=com_or_group.qualified_name, ctx=ctx, models=o_models
            )
    ret.append((com_or_group, current))
    if isinstance(com_or_group, commands.Group):
        for com in com_or_group.commands:
            ret.extend(
                recursively_resolve(
                    com_or_group=com,
                    o_models=o_models,
                    g_models=g_models,
                    ctx=ctx,
                    override=(current is False),
                )
            )
    return ret


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
