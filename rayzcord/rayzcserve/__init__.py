"""RayzCServe Cog setup entrypoint for Red-DiscordBot."""

from .rayzcserve import RayzCServe


async def setup(bot):
    await bot.add_cog(RayzCServe(bot))
