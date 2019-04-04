from .admin import Admin


async def setup(bot):
    await bot.add_cog(Admin())
