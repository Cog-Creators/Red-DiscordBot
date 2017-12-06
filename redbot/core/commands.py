"""Module for command helpers and classes.

This module contains extended classes and functions which are intended to
replace those from the `discord.ext.commands` module.
"""
import asyncio
import inspect
from typing import Iterable, List

import discord
from discord.ext import commands

from redbot.core.utils.chat_formatting import box

__all__ = ["Context", "Command", "Group", "command", "group"]

TICK = "\N{WHITE HEAVY CHECK MARK}"


class Context(commands.Context):
    """Command invocation context for Red.

    All context passed into commands will be of this type.

    This class inherits from `discord.ext.commands.Context`.
    """

    async def send_help(self) -> List[discord.Message]:
        """Send the command help message.

        Returns
        -------
        `list` of `discord.Message`
            A list of help messages which were sent to the user.

        """
        command = self.invoked_subcommand or self.command
        embeds = await self.bot.formatter.format_help_for(self, command)
        destination = self
        ret = []
        for embed in embeds:
            try:
                m = await destination.send(embed=embed)
            except discord.HTTPException:
                destination = self.author
                m = await destination.send(embed=embed)
            ret.append(m)

        return ret

    async def tick(self) -> bool:
        """Add a tick reaction to the command message.

        Returns
        -------
        bool
            :code:`True` if adding the reaction succeeded.

        """
        try:
            await self.message.add_reaction(TICK)
        except discord.HTTPException:
            return False
        else:
            return True

    async def send_interactive(self,
                               messages: Iterable[str],
                               box_lang: str=None,
                               timeout: int=15) -> List[discord.Message]:
        """Send multiple messages interactively.

        The user will be prompted for whether or not they would like to view
        the next message, one at a time. They will also be notified of how
        many messages are remaining on each prompt.

        Parameters
        ----------
        messages : `iterable` of `str`
            The messages to send.
        box_lang : str
            If specified, each message will be contained within a codeblock of
            this language.
        timeout : int
            How long the user has to respond to the prompt before it times out.
            After timing out, the bot deletes its prompt message.

        """
        messages = tuple(messages)
        ret = []

        more_check = lambda m: (m.author == self.author and
                                m.channel == self.channel and
                                m.content.lower() == "more")

        for idx, page in enumerate(messages, 1):
            if box_lang is None:
                msg = await self.send(page)
            else:
                msg = await self.send(box(page, lang=box_lang))
            ret.append(msg)
            n_remaining = len(messages) - idx
            if n_remaining > 0:
                if n_remaining == 1:
                    plural = ""
                    is_are = "is"
                else:
                    plural = "s"
                    is_are = "are"
                query = await self.send(
                    "There {} still {} message{} remaining. "
                    "Type `more` to continue."
                    "".format(is_are, n_remaining, plural))
                try:
                    resp = await self.bot.wait_for(
                        'message', check=more_check, timeout=timeout)
                except asyncio.TimeoutError:
                    await query.delete()
                    break
                else:
                    try:
                        await self.channel.delete_messages((query, resp))
                    except discord.HTTPException:
                        # In case the bot can't delete other users' messages,
                        # or is not a bot account
                        await query.delete()
        return ret


class Command(commands.Command):
    """Command class for Red.

    This should not be created directly, and instead via the decorator.

    This class inherits from `discord.ext.commands.Command`.
    """

    def __init__(self, *args, **kwargs):
        self._help_override = kwargs.pop('help_override', None)
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
        return inspect.cleandoc(translator(self.callback.__doc__))

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
