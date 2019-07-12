from .permissions import Permissions


async def setup(bot):
    cog = Permissions(bot)
    await cog.initialize()
    await cog.red_cog_added(cog)
    for command in cog.walk_commands():
        cog.red_command_added(command)
    bot.add_cog(cog)
