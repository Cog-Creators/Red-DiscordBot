import types
import contextlib
import asyncio
from redbot.core import RedContext
import logging

log = logging.getLogger("redbot.cogs.permissions.resolvers")


async def val_if_check_is_valid(*, ctx: RedContext, check: object, level: str) -> bool:
    """
    Returns the value from a check if it is valid
    """

    # Non staticmethods should not be run without their parent
    # class, even if the parent class did not deregister them
    if isinstance(check, types.FunctionType):
        if next(filter(lambda x: check.__module__ == x.__module__, ctx.bot.cogs), None) is None:
            return None

    val = None
    # let's not spam the console with improperly made 3rd party checks
    try:
        if asyncio.iscoroutine(check) or asyncio.iscoroutinefunction(check):
            val = await check(ctx, level=level)
        else:
            val = check(ctx, level=level)
    except Exception as e:
        # but still provide a way to view it (run with debug flag)
        log.debug(str(e))

    return val


def resolve_models(
    *, ctx: RedContext, models: dict, debug: bool = False, debug_ids: list = None
) -> bool:

    cmd_name = ctx.command.qualified_name
    cog_name = ctx.cog.__class__.__name__

    resolved = None
    if debug:
        debug_list = []

    if cmd_name in models.get("commands", {}):
        blacklist = models["commands"][cmd_name].get("deny", [])
        whitelist = models["commands"][cmd_name].get("allow", [])
        _resolved = resolve_lists(
            ctx=ctx, whitelist=whitelist, blacklist=blacklist, debug_ids=debug_ids
        )
        if debug:
            if resolved is None and _resolved[0] is not None:
                resolved = _resolved[0]
            debug_list.extend(_resolved[1])
        elif _resolved is not None:
            return _resolved

    if cog_name in models.get("cogs", {}):
        blacklist = models["cogs"][cog_name].get("deny", [])
        whitelist = models["cogs"][cog_name].get("allow", [])
        _resolved = resolve_lists(
            ctx=ctx, whitelist=whitelist, blacklist=blacklist, debug_ids=debug_ids
        )
        if debug:
            if resolved is None and _resolved[0] is not None:
                resolved = _resolved[0]
            debug_list.extend(_resolved[1])
        elif _resolved is not None:
            return _resolved

    if resolved is None:
        with contextlib.suppress(KeyError):
            resolved = models["commands"][cmd_name]["default"]
    if resolved is None:
        with contextlib.suppress(KeyError):
            resolved = models["cogs"][cog_name]["default"]

    if debug:
        return resolved, debug_list
    else:
        return resolved


def resolve_lists(
    *,
    ctx: RedContext,
    whitelist: list,
    blacklist: list,
    debug: bool = False,
    debug_ids: list = None
) -> bool:

    voice_channel = None
    with contextlib.suppress(Exception):
        voice_channel = ctx.author.voice.voice_channel

    if debug and debug_ids:
        entries = debug_ids
    else:
        entries = [x for x in (ctx.author, voice_channel, ctx.channel) if x]
        roles = sorted(ctx.author.roles, reverse=True) if ctx.guild else []
        entries.extend([x.id for x in roles])
        # entries now contains the following (in order) (if applicable)
        # author.id
        # author.voice.voice_channel.id
        # channel.id
        # role.id for each role (highest to lowest)
        # (implicitly) guild.id because
        #     the @everyone role shares an id with the guild

    val = None
    if debug:
        debug_list = []
    for entry in entries:
        val = None
        if entry in whitelist:
            val = True
            if not debug:
                return val
        if entry in blacklist:
            val = False
            if not debug:
                return val
        if debug:
            debug_list.append((val, entry))
    else:
        if debug:
            val = next(filter(lambda x: x[0] is not None, debug_list), None)
            return val, debug_list
        else:
            return None
