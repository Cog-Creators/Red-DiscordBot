import asyncio
import contextlib
from typing import Iterable, List
import discord
from discord.ext import commands

from .requires import PermState
from ..utils.chat_formatting import box
from ..utils.predicates import MessagePredicate
from ..utils import common_filters

TICK = "\N{WHITE HEAVY CHECK MARK}"

__all__ = ["Context"]


class Context(commands.Context):
    """Command invocation context for Red.

    All context passed into commands will be of this type.

    This class inherits from `discord.ext.commands.Context`.
    """

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.permission_state: PermState = PermState.NORMAL

    async def send(self, content=None, **kwargs):
        """Sends a message to the destination with the content given.

        This acts the same as `discord.ext.commands.Context.send`, with
        one added keyword argument as detailed below in *Other Parameters*.

        Parameters
        ----------
        content : str
            The content of the message to send.

        Other Parameters
        ----------------
        filter : Callable[`str`] -> `str`
            A function which is used to sanitize the ``content`` before
            it is sent. Defaults to
            :func:`~redbot.core.utils.common_filters.filter_mass_mentions`.
            This must take a single `str` as an argument, and return
            the sanitized `str`.
        \*\*kwargs
            See `discord.ext.commands.Context.send`.

        Returns
        -------
        discord.Message
            The message that was sent.

        """

        _filter = kwargs.pop("filter", common_filters.filter_mass_mentions)

        if _filter and content:
            content = _filter(str(content))

        return await super().send(content=content, **kwargs)

    async def send_help(self) -> List[discord.Message]:
        """Send the command help message.

        Returns
        -------
        `list` of `discord.Message`
            A list of help messages which were sent to the user.

        """
        command = self.invoked_subcommand or self.command
        embed_wanted = await self.bot.embed_requested(
            self.channel, self.author, command=self.bot.get_command("help")
        )
        if self.guild and not self.channel.permissions_for(self.guild.me).embed_links:
            embed_wanted = False

        ret = []
        destination = self
        if embed_wanted:
            embeds = await self.bot.formatter.format_help_for(self, command)
            for embed in embeds:
                try:
                    m = await destination.send(embed=embed)
                except discord.HTTPException:
                    destination = self.author
                    m = await destination.send(embed=embed)
                ret.append(m)
        else:
            f = commands.HelpFormatter()
            msgs = await f.format_help_for(self, command)
            for msg in msgs:
                try:
                    m = await destination.send(msg)
                except discord.HTTPException:
                    destination = self.author
                    m = await destination.send(msg)
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

    async def send_interactive(
        self, messages: Iterable[str], box_lang: str = None, timeout: int = 15
    ) -> List[discord.Message]:
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
                    "".format(is_are, n_remaining, plural)
                )
                try:
                    resp = await self.bot.wait_for(
                        "message",
                        check=MessagePredicate.lower_equal_to("more", self),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.HTTPException):
                        await query.delete()
                    break
                else:
                    try:
                        await self.channel.delete_messages((query, resp))
                    except (discord.HTTPException, AttributeError):
                        # In case the bot can't delete other users' messages,
                        # or is not a bot account
                        # or channel is a DM
                        with contextlib.suppress(discord.HTTPException):
                            await query.delete()
        return ret

    async def embed_colour(self):
        """
        Helper function to get the colour for an embed.

        Returns
        -------
        discord.Colour:
            The colour to be used
        """
        if self.guild and await self.bot.db.guild(self.guild).use_bot_color():
            return self.guild.me.color
        else:
            return self.bot.color

    @property
    def embed_color(self):
        # Rather than double awaiting.
        return self.embed_colour

    async def embed_requested(self):
        """
        Simple helper to call bot.embed_requested
        with logic around if embed permissions are available

        Returns
        -------
        bool:
            :code:`True` if an embed is requested
        """
        if self.guild and not self.channel.permissions_for(self.guild.me).embed_links:
            return False
        return await self.bot.embed_requested(self.channel, self.author, command=self.command)

    async def maybe_send_embed(self, message: str) -> discord.Message:
        """
        Simple helper to send a simple message to context
        without manually checking ctx.embed_requested
        This should only be used for simple messages.

        Parameters
        ----------
        message: `str`
            The string to send

        Returns
        -------
        discord.Message:
            the message which was sent

        Raises
        ------
        discord.Forbidden
            see `discord.abc.Messageable.send`
        discord.HTTPException
            see `discord.abc.Messageable.send`
        """

        if await self.embed_requested():
            return await self.send(
                embed=discord.Embed(description=message, color=(await self.embed_colour()))
            )
        else:
            return await self.send(message)

    @property
    def clean_prefix(self) -> str:
        """str: The command prefix, but a mention prefix is displayed nicer."""
        me = self.me
        return self.prefix.replace(me.mention, f"@{me.display_name}")

    @property
    def me(self) -> discord.abc.User:
        """discord.abc.User: The bot member or user object.

        If the context is DM, this will be a `discord.User` object.
        """
        if self.guild is not None:
            return self.guild.me
        else:
            return self.bot.user
