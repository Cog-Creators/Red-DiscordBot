from .customcom import CustomCommands


async def setup(bot):
    cog = CustomCommands(bot)
    await cog.initialize()
    bot.add_cog(cog)
    bot.remove_command("_CustomCommands__cc_command")
