import types
import contextlib
import asyncio
import logging
from redbot.core import commands

log = logging.getLogger("redbot.cogs.permissions.resolvers")


async def val_if_check_is_valid(*, ctx: commands.Context, check: object, level: str) -> bool:
    """
    Returns the value from a check if it is valid
    """

    val = None
    # let's not spam the console with improperly made 3rd party checks
    try:
        # pretty sure this is redunant, but if it is, it will short circuit at or
        if asyncio.iscoroutine(check) or asyncio.iscoroutinefunction(check):
            val = await check(ctx, level=level)
        else:
            val = check(ctx, level=level)
    except Exception as e:
        # but still provide a way to view it (run with debug flag)
        log.debug(str(e))

    return val


def resolve_models(*, ctx: commands.Context, models: dict) -> bool:
    """
    Resolves models in order.
    """

    cmd_name = ctx.command.qualified_name
    cog_name = ctx.cog.__class__.__name__

    resolved = None

    to_iter = (("commands", cmd_name), ("cogs", cog_name))

    for model_name, ctx_attr in to_iter:
        if ctx_attr in models.get(model_name, {}):
            blacklist = models[model_name][ctx_attr].get("deny", [])
            whitelist = models[model_name][ctx_attr].get("allow", [])
            resolved = resolve_lists(ctx=ctx, whitelist=whitelist, blacklist=blacklist)
            if resolved is not None:
                return resolved
            resolved = models[model_name][ctx_attr].get("default", None)
            if resolved is not None:
                return resolved

    return None


def resolve_lists(*, ctx: commands.Context, whitelist: list, blacklist: list) -> bool:
    """
    resolves specific lists
    """

    voice_channel = None
    with contextlib.suppress(Exception):
        voice_channel = ctx.author.voice.voice_channel

    entries = [x.id for x in (ctx.author, voice_channel, ctx.channel) if x]
    roles = sorted(ctx.author.roles, reverse=True) if ctx.guild else []
    entries.extend([x.id for x in roles])
    # entries now contains the following (in order) (if applicable)
    # author.id
    # author.voice.voice_channel.id
    # channel.id
    # role.id for each role (highest to lowest)
    # (implicitly) guild.id because
    #     the @everyone role shares an id with the guild

    for entry in entries:
        if entry in whitelist:
            return True
        if entry in blacklist:
            return False
    return None
