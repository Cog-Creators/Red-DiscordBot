import discord
from discord.ext import commands

TICK = "\N{WHITE HEAVY CHECK MARK}"


class RedContext(commands.Context):
    """
    Command invokation context for Red.

    :show-inheritance:
    """

    async def send_help(self):
        """Send the command help message."""
        command = self.invoked_subcommand or self.command
        pages = await self.bot.formatter.format_help_for(self, command)
        for page in pages:
            await self.send(page)

    async def tick(self):
        """Add a tick reaction to the command message.

        Returns
        -------
        bool
            ``True`` if adding the reaction succeeded.
        """
        try:
            await self.message.add_reaction(TICK)
        except discord.HTTPException:
            return False
        else:
            return True
