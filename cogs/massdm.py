from typing import List

import discord
from discord.ext import commands

from .utils import checks


class MassDM:

    """Send a direct message to all members of the specified Role."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _member_has_role(self, member: discord.Member, role: discord.Role):
        return role in member.roles

    def _get_users_with_role(self, server: discord.Server,
                             role: discord.Role) -> List[discord.User]:
        roled = []
        for member in server.members:
            if self._member_has_role(member, role):
                roled.append(member)
        return roled

    @commands.command(no_pm=True, pass_context=True, name="massdm",
                      aliases=["mdm"])
    @checks.mod_or_permissions(administrator=True)
    async def _mdm(self, ctx: commands.Context,
                   role: discord.Role, *, message: str):
        """Sends a DM to all Members with the given Role.
        Allows for the following customizations:
        {0} is the member being messaged.
        {1} is the role they are being message through.
        {2} is the person sending the message.
        """

        server = ctx.message.server
        sender = ctx.message.author

        await self.bot.delete_message(ctx.message)

        dm_these = self._get_users_with_role(server, role)

        for user in dm_these:
            try:
                await self.bot.send_message(user,
                                            message.format(user, role, sender))
            except discord.Forbidden:
                continue


def setup(bot: commands.Bot):
    bot.add_cog(MassDM(bot))
