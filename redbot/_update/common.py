import logging
import os
import sys
from typing import Final, Optional, Union

import rich
from packaging.version import Version
from rich.console import Console, RenderableType
from rich.logging import RichHandler
from rich.table import Table
from rich.text import Text

from redbot import __version__
from redbot.core._cli import cli_level_to_log_level


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

INTERNAL_LEGACY_WINDOWS_ENV_VAR = "_RED_UPDATE_INTERNAL_LEGACY_WINDOWS"
INTERNAL_CMD_CALL_ENV_VAR = "_RED_UPDATE_INTERNAL_CMD_CALL"
_STDERR_CONSOLE: Optional[Console] = None

RUNNER_DIR_ENV_VAR: Final = "REDBOT_UPDATE_RUNNER_DIR"
RUNNER_WRAPPER_EXE_ENV_VAR: Final = "REDBOT_UPDATE_RUNNER_WRAPPER_EXE"


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
    value = os.getenv(INTERNAL_LEGACY_WINDOWS_ENV_VAR, "")
    legacy_windows = int(value) if value else None
    rich.reconfigure(highlight=False, legacy_windows=legacy_windows)
    global _STDERR_CONSOLE
    _STDERR_CONSOLE = Console(highlight=False, stderr=True, legacy_windows=legacy_windows)


def get_console(stderr: bool = False) -> Console:
    global _STDERR_CONSOLE
    if _STDERR_CONSOLE is None:
        raise RuntimeError("_STDERR_CONSOLE is not set")
    return _STDERR_CONSOLE if stderr else rich.get_console()


def configure_logging(logging_level: int) -> None:
    configure_rich()
    level = cli_level_to_log_level(logging_level)
    base_logger = logging.getLogger("red")
    base_logger.setLevel(level)
    base_logger.addHandler(RichHandler(console=get_console(stderr=True), show_path=False))


def ensure_supported_env() -> None:
    if sys.prefix == sys.base_prefix:
        print("redbot-update cannot be used when Red is installed outside a virtual environment.")
        raise SystemExit(1)
    if not (
        os.environ.get(RUNNER_DIR_ENV_VAR, "") and os.environ.get(RUNNER_WRAPPER_EXE_ENV_VAR, "")
    ):
        print("redbot-update was called incorrectly.")
        raise SystemExit(1)
