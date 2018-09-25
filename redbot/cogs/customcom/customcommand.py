from copy import copy

import discord

from redbot.core import commands


class CustomCommand(commands.Command):
    async def prepare(self, ctx):
        # We're modifying ourselves. Let's not make that a global change.
        ctx.command = copy(self)
        result = await self.instance.cc_prepare(ctx)
        await super(CustomCommand, ctx.command).prepare(ctx)
        ctx.kwargs["raw_response"] = result


# easy decorator
def custom_command(callback):
    callback = commands.command(cls=CustomCommand)(callback)
    return commands.check(cc_check)(callback)


async def cc_check(ctx):
    if not ctx.guild:
        return False
    try:
        await ctx.cog.commandobj.get(message=ctx.message, command=ctx.invoked_with)
        return True
    except Exception:
        return False
