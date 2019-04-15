from discord.ext import commands
from .commands import Command

__all__ = ["HelpCommand", "DefaultHelpCommand", "MinimalHelpCommand"]


class _HelpCommandImpl(Command, commands.help._HelpCommandImpl):
    pass


class HelpCommand(commands.help.HelpCommand):
    def _add_to_bot(self, bot):
        command = _HelpCommandImpl(self, self.command_callback, **self.command_attrs)
        bot.add_command(command)
        self._command_impl = command


class DefaultHelpCommand(HelpCommand, commands.help.DefaultHelpCommand):
    pass


class MinimalHelpCommand(HelpCommand, commands.help.MinimalHelpCommand):
    pass
