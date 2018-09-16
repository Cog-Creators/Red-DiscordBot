from .permissions import Permissions


async def setup(bot):
    cog = Permissions(bot)
    await cog.initialize()
    bot.add_listener(cog.cog_added, "on_cog_add")
    bot.add_listener(cog.command_added, "on_command_add")
    bot.add_cog(cog)
