from .permissions import Permissions


async def setup(bot):
    cog = Permissions(bot)
    await cog.initialize()
    # We should add the rules for the Permissions cog and its own commands *before* adding the cog.
    # The actual listeners ought to skip the ones we're passing here.
    # noinspection PyProtectedMember
    await cog._on_cog_add(cog)
    for command in cog.__cog_commands__:
        # noinspection PyProtectedMember
        await cog._on_command_add(command)
    bot.add_cog(cog)
