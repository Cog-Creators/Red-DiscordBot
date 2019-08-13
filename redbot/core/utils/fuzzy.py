import logging
from typing import Optional, List, Union, Sequence, TYPE_CHECKING

import discord
from fuzzywuzzy import process, fuzz

from .chat_formatting import box

if TYPE_CHECKING:
    from ..commands import Context, Command

__all__ = ["fuzzy_command_search", "format_fuzzy_results"]


async def fuzzy_command_search(
    ctx: "Context",
    term: Optional[str] = None,
    *,
    commands: Optional[Sequence["Command"]] = None,
    min_score: int = 80,
) -> Optional[List["Command"]]:
    """Search for commands which are similar in name to the one invoked.

    Returns a maximum of 5 commands which must all be at least matched
    greater than ``min_score``.

    Parameters
    ----------
    ctx : `commands.Context <redbot.core.commands.Context>`
        The command invocation context.
    term : Optional[str]
        The name of the invoked command. If ``None``, `Context.invoked_with`
        will be used instead.
    commands : Optional[Sequence[commands.Command]]
    min_score : int
        The minimum score for matched commands to reach. Defaults to 80.

    Returns
    -------
    Optional[List[`commands.Command <redbot.core.commands.Command>`]]
        A list of commands which were fuzzily matched with the invoked
        command.

    """
    if ctx.guild is not None:
        enabled = await ctx.bot.db.guild(ctx.guild).fuzzy()
    else:
        enabled = await ctx.bot.db.fuzzy()

    if not enabled:
        return

    if term is None:
        term = ctx.invoked_with

    # If the term is an alias or CC, we don't want to send a supplementary fuzzy search.
    alias_cog = ctx.bot.get_cog("Alias")
    if alias_cog is not None:
        is_alias, alias = await alias_cog.is_alias(ctx.guild, term)

        if is_alias:
            return
    customcom_cog = ctx.bot.get_cog("CustomCommands")
    if customcom_cog is not None:
        cmd_obj = customcom_cog.commandobj

        try:
            await cmd_obj.get(ctx.message, term)
        except:
            pass
        else:
            return

    # Do the scoring. `extracted` is a list of tuples in the form `(command, score)`
    extracted = process.extract(
        term, (commands or ctx.bot.walk_commands()), limit=5, scorer=fuzz.QRatio
    )
    if not extracted:
        return

    # Filter through the fuzzy-matched commands.
    matched_commands = []
    for command, score in extracted:
        if score < min_score:
            # Since the list is in decreasing order of score, we can exit early.
            break
        if await command.can_see(ctx):
            matched_commands.append(command)

    return matched_commands


async def format_fuzzy_results(
    ctx: "Context", matched_commands: List["Command"], *, embed: Optional[bool] = None
) -> Union[str, discord.Embed]:
    """Format the result of a fuzzy command search.

    Parameters
    ----------
    ctx : `commands.Context <redbot.core.commands.Context>`
        The context in which this result is being displayed.
    matched_commands : List[`commands.Command <redbot.core.commands.Command>`]
        A list of commands which have been matched by the fuzzy search, sorted
        in order of decreasing similarity.
    embed : bool
        Whether or not the result should be an embed. If set to ``None``, this
        will default to the result of `ctx.embed_requested`.

    Returns
    -------
    Union[str, discord.Embed]
        The formatted results.

    """
    if embed is not False and (embed is True or await ctx.embed_requested()):
        lines = []
        for cmd in matched_commands:
            lines.append(f"**{ctx.clean_prefix}{cmd.qualified_name}** {cmd.short_doc}")
        return discord.Embed(
            title="Perhaps you wanted one of these?",
            colour=await ctx.embed_colour(),
            description="\n".join(lines),
        )
    else:
        lines = []
        for cmd in matched_commands:
            lines.append(f"{ctx.clean_prefix}{cmd.qualified_name} -- {cmd.short_doc}")
        return "Perhaps you wanted one of these? " + box("\n".join(lines), lang="vhdl")


def _fuzzy_log_filter(record):
    return record.funcName != "extractWithoutOrder"


logging.getLogger().addFilter(_fuzzy_log_filter)
