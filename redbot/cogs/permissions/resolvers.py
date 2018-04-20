import types
import contextlib
import asyncio
from redbot.core import RedContext


async def val_if_check_is_valid(*, ctx: RedContext, check: object, level: str) -> bool:
    """
    Returns the value from a check if it is valid
    """

    # Non staticmethods should not be run without their parent
    # class, even if the parent class did not deregister them
    if isinstance(check, types.FunctionType):
        if next(
                filter(
                    lambda x: check.__module__ == x.__module__,
                    ctx.bot.cogs
                ), None) is None:
            return None

    # support both sync and async funcs, because why not
    # also, supress errors because we can't check know what
    # third party checks might raise if improperly made
    with contextlib.suppress(Exception):
        val = None
        if asyncio.iscoroutine(check) \
                or asyncio.iscoroutinefunction(check):
            val = await check(ctx, level=level)
        else:
            val = check(ctx, level=level)

    return val


def resolve_models(*, ctx: RedContext, models: dict) -> bool:

    cmd_name = ctx.command.qualified_name
    cog_name = ctx.cog.__module__

    blacklist = models.get('blacklist', [])
    whitelist = models.get('whitelist', [])
    resolved = resolve_lists(
        ctx=ctx, whitelist=whitelist, blacklist=blacklist
    )
    if resolved is not None:
        return resolved

    if cmd_name in models['cmds']:
        blacklist = models['cmds'][cmd_name].get('blacklist', [])
        whitelist = models['cmds'][cmd_name].get('whitelist', [])
        resolved = resolve_lists(
            ctx=ctx, whitelist=whitelist, blacklist=blacklist
        )
        if resolved is not None:
            return resolved

    if cog_name in models['cogs']:
        blacklist = models['cogs'][cmd_name].get('blacklist', [])
        whitelist = models['cogs'][cmd_name].get('whitelist', [])
        resolved = resolve_lists(
            ctx=ctx, whitelist=whitelist, blacklist=blacklist
        )
        if resolved is not None:
            return resolved

    # default
    return None


def resolve_lists(*, ctx: RedContext, whitelist: list, blacklist: list) -> bool:

    voice_channel = None
    with contextlib.suppress(Exception):
        voice_channel = ctx.author.voice.voice_channel

    entries = [
        x for x in (ctx.author, voice_channel, ctx.channel) if x
    ]
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
    else:
        return None
