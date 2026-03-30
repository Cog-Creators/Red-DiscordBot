import os
import sys
from typing import Optional, Union

import rich
from packaging.version import Version
from rich.console import Console, RenderableType
from rich.table import Table
from rich.text import Text

from redbot import __version__


# The cell width of text-style emojis that, by default, prefer emoji-style
# is not well-defined in the Unicode spec and so it varies between different terminals
# (e.g. kitty does things differently).
# Therefore, I avoided using :white_heavy_check_mark-text: and :cross_mark-text:,
# opting for less ideal :heavy_check_mark-text: and :heavy_multiplication_x-text:.
# More details can be found at: https://github.com/jquast/wcwidth/issues/211
ICON_SUCCESS = "[green]:heavy_check_mark-text:[/]"
ICON_INFO = "[blue]\N{CIRCLED INFORMATION SOURCE}[/]"
ICON_WARN = "[yellow]:warning-text:[/]"
ICON_ERROR = "[red]:heavy_multiplication_x-text:[/]"

INTERNAL_CMD_CALL_ENV_VAR = "_RED_UPDATE_INTERNAL_CMD_CALL"
_STDERR_CONSOLE: Optional[Console] = None


def get_current_red_version() -> Version:
    return Version(os.getenv("_RED_UPDATE_PRETEND_VERSION") or __version__)


def get_current_python_version() -> Version:
    return Version(".".join(map(str, sys.version_info[:3])))


def prefix_column(prefix: RenderableType, *parts: Union[str, Text]) -> Table:
    output = Table.grid(padding=(0, 2))
    output.add_column()
    output.add_column()
    text = Text()
    for renderable in parts:
        if isinstance(renderable, str):
            text.append_text(Text.from_markup(renderable))
        else:
            text.append_text(renderable)
    output.add_row(prefix, text)
    return output


def print_with_prefix_column(
    prefix: RenderableType, *parts: Union[str, Text], console: Optional[Console] = None
) -> None:
    if console is None:
        console = rich.get_console()
    console.print(prefix_column(prefix, *parts))


def is_internal_cmd_call() -> bool:
    return os.getenv(INTERNAL_CMD_CALL_ENV_VAR) == "1"


def configure_rich() -> None:
    rich.reconfigure(highlight=False)
    global _STDERR_CONSOLE
    _STDERR_CONSOLE = Console(highlight=False, stderr=True)


def get_console(stderr: bool = False) -> Console:
    global _STDERR_CONSOLE
    if _STDERR_CONSOLE is None:
        raise RuntimeError("_STDERR_CONSOLE is not set")
    return _STDERR_CONSOLE if stderr else rich.get_console()
