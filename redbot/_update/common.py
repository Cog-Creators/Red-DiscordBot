import os
import sys
from typing import Union

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


def print_with_prefix_column(prefix: RenderableType, *parts: Union[str, Text]) -> None:
    console = rich.get_console()
    console.print(prefix_column(prefix, *parts))


def configure_rich() -> None:
    rich.reconfigure(highlight=False)


def get_console() -> Console:
    return rich.get_console()
