from .warnings import Warnings


async def setup(bot):
    await bot.add_cog(Warnings(bot))
