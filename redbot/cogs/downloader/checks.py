import asyncio

import discord
from discord.ext import commands

__all__ = ["install_agreement"]

REPO_INSTALL_MSG = (
    "You're about to add a 3rd party repository. The creator of Red"
    " and its community have no responsibility for any potential "
    "damage that the content of 3rd party repositories might cause."
    "\n\nBy typing '**I agree**' you declare that you have read and"
    " fully understand the above message. This message won't be "
    "shown again until the next reboot.\n\nYou have **30** seconds"
    " to reply to this message."
)


def install_agreement():
    async def pred(ctx: commands.Context):
        downloader = ctx.command.instance
        if downloader is None:
            return True
        elif downloader.already_agreed:
            return True
        elif ctx.invoked_subcommand is None or isinstance(
            ctx.invoked_subcommand, discord.ext.commands.Group
        ):
            return True

        def does_agree(msg: discord.Message):
            return (
                ctx.author == msg.author
                and ctx.channel == msg.channel
                and msg.content == "I agree"
            )

        await ctx.send(REPO_INSTALL_MSG)

        try:
            await ctx.bot.wait_for("message", check=does_agree, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Your response has timed out, please try again.")
            return False

        downloader.already_agreed = True
        return True

    return commands.check(pred)
