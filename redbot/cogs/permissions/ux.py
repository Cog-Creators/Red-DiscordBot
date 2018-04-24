import discord

from redbot.core import RedContext
from redbot.core.i18n import CogI18n

_ = CogI18n('Permissions', __file__)


async def send(ctx: RedContext, message: str) -> discord.Message:
    """
    get rid of this and use ctx.maybe_send_embed() if PR for that is merged
    """
    if await ctx.embed_requested():
        await ctx.send(embed=discord.Embed(description=message))
    else:
        await ctx.send(message)


def build_tables(things: list, responses: list, *, guild: list=None) -> str:
    """
    build a response table for allow/disallow
    """

    mapped = {
        t.id: [r[0] for r in responses if r[1] == t.id]
        for t in things
    }
    guild_map = {
        t.id: [r[0] for r in responses if r[1] == t.id]
        for t in guild
    } if guild else {}

    header = _("Rules regarding {thing}")

    # TODO: finish building this