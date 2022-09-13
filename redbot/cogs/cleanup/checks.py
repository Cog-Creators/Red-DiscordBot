from redbot.core.commands import Context, permissions_check
from redbot.core.utils.mod import check_permissions, is_mod_or_superior


def check_self_permissions():
    async def predicate(ctx: Context):
        if not ctx.guild:
            return True
        if await check_permissions(ctx, {"manage_messages": True}) or await is_mod_or_superior(
            ctx.bot, ctx.author
        ):
            return True
        return False

    return permissions_check(predicate)
