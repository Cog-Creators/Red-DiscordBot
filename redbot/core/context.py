"""
The purpose of this module is to allow for Red to further customise the command
invocation context provided by discord.py.
"""
import asyncio
from typing import Iterable, List

import discord
from discord.ext import commands

from redbot.core.utils.chat_formatting import box

__all__ = ["RedContext"]

TICK = "\N{WHITE HEAVY CHECK MARK}"


class RedContext(commands.Context):
    """Command invocation context for Red.

    All context passed into commands will be of this type.

    This class inherits from `commands.Context <discord.ext.commands.Context>`.
    """

    async def send_help(self) -> List[discord.Message]:
        """Send the command help message.

        Returns
        -------
        `list` of `discord.Message`
            A list of help messages which were sent to the user.

        """
        command = self.invoked_subcommand or self.command
        pages = await self.bot.formatter.format_help_for(self, command)
        ret = []
        for page in pages:
            ret.append(await self.send(page))
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
                    await self.channel.delete_messages((query, resp))
        return ret
