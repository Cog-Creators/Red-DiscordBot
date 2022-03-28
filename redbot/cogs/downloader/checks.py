import asyncio

from bluebot.core import commands
from bluebot.core.i18n import Translator
from bluebot.core.utils.chat_formatting import bold
from bluebot.core.utils.predicates import MessagePredicate

__all__ = ["do_install_agreement"]

_ = Translator("DownloaderChecks", __file__)


async def do_install_agreement(ctx: commands.Context) -> bool:
    downloader = ctx.cog
    if downloader is None or downloader.already_agreed:
        return True

    confirmation_message = "I agree"
    await ctx.send(
        _(
            "You're about to add a 3rd party repository. The creator of Blue"
            " and its community have no responsibility for any potential "
            "damage that the content of 3rd party repositories might cause."
            "\n\nBy typing '{confirmation_message}' you declare that you have read and"
            " fully understand the above message. This message won't be "
            "shown again until the next reboot.\n\nYou have **30** seconds"
            " to reply to this message."
        ).format(confirmation_message=bold(confirmation_message))
    )

    try:
        await ctx.bot.wait_for(
            "message",
            check=MessagePredicate.lower_equal_to(confirmation_message.lower(), ctx),
            timeout=30,
        )
    except asyncio.TimeoutError:
        await ctx.send(_("Your response has timed out, please try again."))
        return False

    downloader.already_agreed = True
    return True
