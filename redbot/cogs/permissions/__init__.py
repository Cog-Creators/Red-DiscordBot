from .permissions import Permissions


async def setup(bot):
    cog = Permissions(bot)
    await cog.initialize()
    # It's important that these listeners are added prior to load, so
    # the permissions commands themselves have rules added.
    # Automatic listeners being added in add_cog happen in arbitrary
    # order, so we want to circumvent that.
    await cog.on_cog_add(cog)
    for command in cog.walk_commands():
        await cog.on_command_add(command)
    bot.add_cog(cog)
