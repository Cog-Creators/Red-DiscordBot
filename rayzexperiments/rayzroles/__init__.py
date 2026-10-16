"""RayzRoles Cog setup for Red-DiscordBot."""

from .rayzroles import RayzRoles


async def setup(bot):
    await bot.add_cog(RayzRoles(bot))
