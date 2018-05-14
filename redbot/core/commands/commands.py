"""Module for command helpers and classes.

This module contains extended classes and functions which are intended to
replace those from the `discord.ext.commands` module.
"""
import inspect

from discord.ext import commands


__all__ = ["Command", "Group", "command", "group"]


class Command(commands.Command):
    """Command class for Red.

    This should not be created directly, and instead via the decorator.

    This class inherits from `discord.ext.commands.Command`.
    """

    def __init__(self, *args, **kwargs):
        self._help_override = kwargs.pop("help_override", None)
        super().__init__(*args, **kwargs)
        self.translator = kwargs.pop("i18n", None)

    @property
    def help(self):
        """Help string for this command.

        If the :code:`help` kwarg was passed into the decorator, it will
        default to that. If not, it will attempt to translate the docstring
        of the command's callback function.
        """
        if self._help_override is not None:
            return self._help_override
        if self.translator is None:
            translator = lambda s: s
        else:
            translator = self.translator
        command_doc = self.callback.__doc__
        if command_doc is None:
            return ""
        return inspect.cleandoc(translator(command_doc))

    @help.setter
    def help(self, value):
        # We don't want our help property to be overwritten, namely by super()
        pass


class Group(Command, commands.Group):
    """Group command class for Red.

    This class inherits from `discord.ext.commands.Group`, with `Command` mixed
    in.
    """
    pass


# decorators


def command(name=None, cls=Command, **attrs):
    """A decorator which transforms an async function into a `Command`.

    Same interface as `discord.ext.commands.command`.
    """
    attrs["help_override"] = attrs.pop("help", None)
    return commands.command(name, cls, **attrs)


def group(name=None, **attrs):
    """A decorator which transforms an async function into a `Group`.

    Same interface as `discord.ext.commands.group`.
    """
    return command(name, cls=Group, **attrs)
