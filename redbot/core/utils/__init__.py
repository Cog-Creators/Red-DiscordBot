__all__ = ["safe_delete", "fuzzy_command_search"]

from pathlib import Path
import os
import shutil
import logging
from redbot.core import commands
from fuzzywuzzy import process
from .chat_formatting import box


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
        and await i[0].can_run(ctx)
        and all([await p.can_run(ctx) for p in i[0].parents])
        and not any([p.hidden for p in i[0].parents])
    ]


async def fuzzy_command_search(ctx: commands.Context, term: str):
    out = ""
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
        out += "{0}. {1.prefix}{2.qualified_name}{3}\n".format(
            pos,
            ctx,
            extracted[0],
            " - {}".format(extracted[0].short_doc) if extracted[0].short_doc else "",
        )
    return box(out, lang="Perhaps you wanted one of these?")
