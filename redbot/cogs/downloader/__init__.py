from .downloader import Downloader


async def setup(bot):
    cog = Downloader(bot)
    bot.add_cog(cog)
    cog.create_init_task()
