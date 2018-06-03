__all__ = ["safe_delete", "fuzzy_command_search"]

from pathlib import Path
import os
import shutil
from redbot.core import commands
from fuzzywuzzy import process
from .chat_formatting import box


def safe_delete(pth: Path):
    if pth.exists():
        for root, dirs, files in os.walk(str(pth)):
            os.chmod(root, 0o755)
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
        shutil.rmtree(str(pth), ignore_errors=True)


def fuzzy_command_search(ctx: commands.Context, term: str):
    out = ""
    for pos, extracted in enumerate(process.extract(term, ctx.bot.walk_commands(), limit=5), 1):
        out += "{0}. {1.prefix}{2.qualified_name}{3}\n".format(
            pos,
            ctx,
            extracted[0],
            " - {}".format(extracted[0].short_doc) if extracted[0].short_doc else "",
        )
    return box(out, lang="Perhaps you wanted one of these?")
