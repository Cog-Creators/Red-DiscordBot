import discord
from discord.ext import commands


class timeout:
    """Adds the ability to place users in a timeout role"""

    def __init__(self, bot):
            self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def timeout(self, ctx):
        """Place a user in timeout, if the user is already in timeout this will also remove him from it"""
        server = ctx.message.server
        # Check if timeout exists.
        if 'timeout' not in [r.name for r in server.roles]:
            await self.bot.say("```diff\n- The Timeout role doesn't exist. Creating!\n```")
            try:
                self.bot.create_role(server, "timeout", permissions(send_messages=False))
                self.bot.say("```diff\n+ Role created, please ensure that your moderator roles are ABOVE the timeout role!\n```")
            except discord.Forbidden:
                await self.bot.say("```diff\n- I cannot create a role. Please assign Manage Roles to me!\n```")
        await self.bot.say("Outside loop")


def setup(bot):
    n = timeout(bot)
    bot.add_cog(n)
