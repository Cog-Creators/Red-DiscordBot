from .downloader import Downloader


async def setup(bot):
    cog = Downloader(bot)
    await cog.initialize()
    await bot.add_cog(cog)
