from .timezone import TimeZone
import asyncio


def setup(bot):
    n = TimeZone(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.setup_data())
    bot.add_cog(n)
