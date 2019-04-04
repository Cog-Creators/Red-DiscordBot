from .image import Image


async def setup(bot):
    cog = Image(bot)
    await cog.initialize()
    await bot.add_cog(cog)
