from redbot.core.bot import Red
from .downloader import Downloader


def setup(bot: Red):
    bot.add_cog(Downloader(bot))
