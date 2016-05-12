import discord
from discord.ext import commands
from .utils import checks
import asyncio


class Punish:
    """Adds the ability to punish users."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def punish(self, ctx, user: discord.Member):
        """Place a user in timeout, if the user is already in timeout, this will also remove him from it"""
        server = ctx.message.server
        # Check if timeout exists.
        if 'Timeout' not in [r.name for r in server.roles]:
            await self.bot.say("```diff\n- The Timeout role doesn't exist. Creating!\n```")
            try:
                perms = discord.Permissions.none()
                # toggle permissions you want, rest are false
                await self.bot.create_role(server, name="Timeout", permissions=perms)
                await self.bot.say("```diff\n+ Role created! Setting channel permissions!\n! Please ensure that your moderator roles are ABOVE the timeout role!\n! Please wait until the user has been added to the Timeout role!\n```")
                try:
                    for c in server.channels:
                        if c.type.name == 'text':
                            perms = discord.Permissions.none()
                            perms.send_messages = True
                            r = discord.utils.get(ctx.message.server.roles, name="Timeout")
                            await self.bot.edit_channel_permissions(c, r, deny=perms)
                        await asyncio.sleep(1.5)
                except discord.Forbidden:
                    await self.bot.say("```\n- A error occured while making channel permissions.\n- Please check your channel permissions for the Timeout role!\n```")
            except discord.Forbidden:
                await self.bot.say("```diff\n- I cannot create a role. Please assign Manage Roles to me!\n```")
        r = discord.utils.get(ctx.message.server.roles, name="Timeout")
        if 'Timeout' not in [r.name for r in user.roles]:
            await self.bot.add_roles(user, r)
            await self.bot.say("```diff\n+ User is now in Timeout!\n```")
        else:
            await self.bot.remove_roles(user, r)
            await self.bot.say("```diff\n+ User is now removed from Timeout!\n```")

        # Look for new channels, and slap the role in there face!
    async def new_channel(self, c):
        if 'Timeout' in [r.name for r in c.server.roles]:
            perms = discord.Permissions.none()
            perms.send_messages = True
            r = discord.utils.get(c.server.roles, name="Timeout")
            await self.bot.edit_channel_permissions(c, r, deny=perms)
            print('Ohai a new channel!')
        else:
            print('Ignoring, no timeout role')


def setup(bot):
    n = Punish(bot)
    bot.add_listener(n.new_channel, 'on_channel_create')
    bot.add_cog(n)
