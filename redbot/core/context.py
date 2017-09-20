"""The purpose of this module is to allow for Red to
further customise the command invocation context provided
by discord.py.
"""

import discord
from discord.ext import commands

__all__ = ["RedContext"]

TICK = "\N{WHITE HEAVY CHECK MARK}"


class RedContext(commands.Context):
    """
    Command invocation context for Red.

    All context passed into commands will be of this type.

    This class inherits from
    :py:class:`commands.Context <discord.ext.commands.Context>`.
    """

    async def send_help(self):
        """Send the command help message."""
        command = self.invoked_subcommand or self.command
        pages = await self.bot.formatter.format_help_for(self, command)
        for page in pages:
            await self.send(page)

    async def tick(self):
        """Add a tick reaction to the command message.

        :return: ``True`` if adding the reaction succeeded.
        :rtype: bool
        """
        try:
            await self.message.add_reaction(TICK)
        except discord.HTTPException:
            return False
        else:
            return True
