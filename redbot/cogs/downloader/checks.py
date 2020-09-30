import asyncio

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.predicates import MessagePredicate

__all__ = ["do_install_agreement", "do_update_confirmation"]

T_ = Translator("DownloaderChecks", __file__)

_ = lambda s: s
REPO_INSTALL_MSG = _(
    "You're about to add a 3rd party repository. The creator of Red"
    " and its community have no responsibility for any potential "
    "damage that the content of 3rd party repositories might cause."
    "\n\nBy typing '**I agree**' you declare that you have read and"
    " fully understand the above message. This message won't be "
    "shown again until the next reboot.\n\nYou have **30** seconds"
    " to reply to this message."
)
UPDATE_CONFIRM_MSG = _(
    "Are you sure that you would like to update cogs? Reply with "
    "'**update**' within 30 seconds to continue."
)
_ = T_


async def do_install_agreement(ctx: commands.Context) -> bool:
    downloader = ctx.cog
    if downloader is None or downloader.already_agreed:
        return True

    await ctx.send(T_(REPO_INSTALL_MSG))

    try:
        await ctx.bot.wait_for(
            "message", check=MessagePredicate.lower_equal_to("i agree", ctx), timeout=30
        )
    except asyncio.TimeoutError:
        await ctx.send(_("Your response has timed out, please try again."))
        return False

    downloader.already_agreed = True
    return True


async def do_update_confirmation(ctx: commands.Context, message: str) -> bool:
    await ctx.send(message + "\n\n" + T_(UPDATE_CONFIRM_MSG))

    try:
        await ctx.bot.wait_for(
            "message", check=MessagePredicate.lower_equal_to("update", ctx), timeout=30
        )
    except asyncio.TimeoutError:
        await ctx.send(_("Your response has timed out, please try again."))
        return False

    return True
