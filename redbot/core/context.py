from discord.ext import commands


class Context(commands.Context):
    """
    We can subclass context to allow easier
    exposure of commands
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def show_help(self, command=None):
        """
        can be used as
        await ctx.show_help()
        from within command code
        """
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)
