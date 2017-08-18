from .image import Image
import asyncio


def setup(bot):
    n = Image(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.set_giphy_key())
    bot.add_cog(n)
