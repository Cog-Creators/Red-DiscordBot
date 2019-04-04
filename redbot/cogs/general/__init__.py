from .general import General


async def setup(bot):
    await bot.add_cog(General())
