from .permissions import Permissions


async def setup(bot):
    cog = Permissions(bot)
    await cog.initialize()
    # It's important that these listeners are added prior to load, so
    # the permissions commands themselves have rules added.
    # Automatic listeners being added in add_cog happen in arbitrary
    # order, so we want to circumvent that.
    bot.add_listener(cog.red_cog_added, "on_cog_add")
    bot.add_listener(cog.red_command_added, "on_command_add")
    bot.add_cog(cog)
