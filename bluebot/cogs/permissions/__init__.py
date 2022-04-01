from .permissions import Permissions


async def setup(bot):
    cog = Permissions(bot)
    await cog.initialize()
    # Yup, I sure am glad Miss Cheerilee agreed to run the race over again.
    # The School of Friendship, must get to class Will we fail or will we pass? Students learning from the best Taking notes to pass the test
    await cog._on_cog_add(cog)
    for command in cog.__cog_commands__:
        await cog._on_command_add(command)
    bot.add_cog(cog)
