__all__ = ["bounded_gather", "safe_delete", "fuzzy_command_search", "deduplicate_iterables"]

import asyncio
from asyncio import as_completed, AbstractEventLoop, Semaphore
from asyncio.futures import isfuture
from itertools import chain
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Awaitable, Iterator, List, Optional

from redbot.core import commands
from fuzzywuzzy import process

from .chat_formatting import box


# Benchmarked to be the fastest method.
def deduplicate_iterables(*iterables):
    """
    Returns a list of all unique items in ``iterables``, in the order they
    were first encountered.
    """
    # dict insertion order is guaranteed to be preserved in 3.6+
    return list(dict.fromkeys(chain.from_iterable(iterables)))


def fuzzy_filter(record):
    return record.funcName != "extractWithoutOrder"


logging.getLogger().addFilter(fuzzy_filter)


def safe_delete(pth: Path):
    if pth.exists():
        for root, dirs, files in os.walk(str(pth)):
            os.chmod(root, 0o755)

            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)

            for f in files:
                os.chmod(os.path.join(root, f), 0o755)

        shutil.rmtree(str(pth), ignore_errors=True)


async def filter_commands(ctx: commands.Context, extracted: list):
    return [
        i
        for i in extracted
        if i[1] >= 90
        and not i[0].hidden
        and not any([p.hidden for p in i[0].parents])
        and await i[0].can_run(ctx)
        and all([await p.can_run(ctx) for p in i[0].parents])
    ]


async def fuzzy_command_search(ctx: commands.Context, term: str):
    out = []

    if ctx.guild is not None:
        enabled = await ctx.bot.db.guild(ctx.guild).fuzzy()
    else:
        enabled = await ctx.bot.db.fuzzy()

    if not enabled:
        return None

    alias_cog = ctx.bot.get_cog("Alias")
    if alias_cog is not None:
        is_alias, alias = await alias_cog.is_alias(ctx.guild, term)

        if is_alias:
            return None

    customcom_cog = ctx.bot.get_cog("CustomCommands")
    if customcom_cog is not None:
        cmd_obj = customcom_cog.commandobj

        try:
            ccinfo = await cmd_obj.get(ctx.message, term)
        except:
            pass
        else:
            return None

    extracted_cmds = await filter_commands(
        ctx, process.extract(term, ctx.bot.walk_commands(), limit=5)
    )

    if not extracted_cmds:
        return None

    for pos, extracted in enumerate(extracted_cmds, 1):
        short = " - {}".format(extracted[0].short_doc) if extracted[0].short_doc else ""
        out.append("{0}. {1.prefix}{2.qualified_name}{3}".format(pos, ctx, extracted[0], short))

    return box("\n".join(out), lang="Perhaps you wanted one of these?")


async def _sem_wrapper(sem, task):
    async with sem:
        return await task


def bounded_gather_iter(
    *coros_or_futures,
    loop: Optional[AbstractEventLoop] = None,
    limit: int = 4,
    semaphore: Optional[Semaphore] = None,
) -> Iterator[Awaitable[Any]]:
    """
    An iterator that returns tasks as they are ready, but limits the
    number of tasks running at a time.

    Parameters
    ----------
    *coros_or_futures
        The awaitables to run in a bounded concurrent fashion.
    loop : asyncio.AbstractEventLoop
        The event loop to use for the semaphore and :meth:`asyncio.gather`.
    limit : Optional[`int`]
        The maximum number of concurrent tasks. Used when no ``semaphore`` is passed.
    semaphore : Optional[:class:`asyncio.Semaphore`]
        The semaphore to use for bounding tasks. If `None`, create one using ``loop`` and ``limit``.

    Raises
    ------
    TypeError
        When invalid parameters are passed
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    if semaphore is None:
        if not isinstance(limit, int) or limit <= 0:
            raise TypeError("limit must be an int > 0")

        semaphore = Semaphore(limit, loop=loop)

    pending = []

    for cof in coros_or_futures:
        if isfuture(cof) and cof._loop is not loop:
            raise ValueError("futures are tied to different event loops")

        cof = _sem_wrapper(semaphore, cof)
        pending.append(cof)

    return as_completed(pending, loop=loop)


def bounded_gather(
    *coros_or_futures,
    loop: Optional[AbstractEventLoop] = None,
    return_exceptions: bool = False,
    limit: int = 4,
    semaphore: Optional[Semaphore] = None,
) -> Awaitable[List[Any]]:
    """
    A semaphore-bounded wrapper to :meth:`asyncio.gather`.

    Parameters
    ----------
    *coros_or_futures
        The awaitables to run in a bounded concurrent fashion.
    loop : asyncio.AbstractEventLoop
        The event loop to use for the semaphore and :meth:`asyncio.gather`.
    return_exceptions : bool
        If true, gather exceptions in the result list instead of raising.
    limit : Optional[`int`]
        The maximum number of concurrent tasks. Used when no ``semaphore`` is passed.
    semaphore : Optional[:class:`asyncio.Semaphore`]
        The semaphore to use for bounding tasks. If `None`, create one using ``loop`` and ``limit``.

    Raises
    ------
    TypeError
        When invalid parameters are passed
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    if semaphore is None:
        if not isinstance(limit, int) or limit <= 0:
            raise TypeError("limit must be an int > 0")

        semaphore = Semaphore(limit, loop=loop)

    tasks = (_sem_wrapper(semaphore, task) for task in coros_or_futures)

    return asyncio.gather(*tasks, loop=loop, return_exceptions=return_exceptions)
