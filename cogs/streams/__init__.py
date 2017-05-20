from .streams import Streams
import logging
import asyncio


def setup(bot):
    logger = logging.getLogger('aiohttp.client')
    logger.setLevel(50)  # Stops warning spam
    n = Streams(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.stream_checker())
    bot.add_cog(n)
