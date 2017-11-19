"""Module for Red's Context class

The purpose of this module is to allow for Red to further customise the command
invocation context provided by discord.py.
"""

import discord
from discord.ext import commands

__all__ = ["RedContext"]

TICK = "\N{WHITE HEAVY CHECK MARK}"


class RedContext(commands.Context):
    """Command invocation context for Red.

    All context passed into commands will be of this type.

    This class inherits from `commands.Context <discord.ext.commands.Context>`.
    """

    async def send_help(self):
        """Send the command help message.
        
        Returns
        -------
        `list` of `discord.Message`
            A list of help messages which were sent to the user.

        """
        command = self.invoked_subcommand or self.command
        embeds = await self.bot.formatter.format_help_for(self, command)
        ret = []
        for embed in embeds:
            ret.append(await self.send(embed=embed))
        return ret

    async def tick(self):
        """Add a tick reaction to the command message.

        Returns
        -------
        bool
            :code:`True` if adding the reaction succeeded.

        """
        try:
            await self.message.add_reaction(TICK)
        except discord.HTTPException:
            return False
        else:
            return True
