import enum
import logging
import os
import sys
from operator import itemgetter
from typing import Any, Final, Iterable, List, Literal, Optional, Tuple, Union

import click
import rich
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from python_discovery import PythonInfo, get_interpreter
from rich.console import Console, RenderableType
from rich.logging import RichHandler
from rich.table import Table
from rich.text import Text

from redbot import __version__
from redbot.core.utils._internal_utils import (
    cli_level_to_log_level,
    get_installed_extras,
    log_level_to_cli_level,
)
from redbot.core import data_manager

_instance_data = data_manager.load_existing_config()
INSTANCE_LIST: Final = () if _instance_data is None else tuple(_instance_data.keys())


ICON_SUCCESS = "[green]:white_heavy_check_mark-emoji:[/]"
ICON_INFO = "[blue]:information-emoji:[/]"
ICON_WARN = "[yellow]:warning-emoji:[/]"
ICON_ERROR = "[red]:cross_mark-emoji:[/]"

INTERNAL_LEGACY_WINDOWS_ENV_VAR = "_RED_UPDATE_INTERNAL_LEGACY_WINDOWS"
INTERNAL_UPDATER_METADATA_ENV_VAR = "_RED_UPDATE_INTERNAL_UPDATER_METADATA"
_STDERR_CONSOLE: Optional[Console] = None

RUNNER_DIR_ENV_VAR: Final = "REDBOT_UPDATE_RUNNER_DIR"
RUNNER_WRAPPER_EXE_ENV_VAR: Final = "REDBOT_UPDATE_RUNNER_WRAPPER_EXE"

OLD_VENV_BACKUP_DIR_NAME: Final = "redbot-update-old-venv-backup"


def get_red_dependency_specifier(version: Version, extras: Iterable[str]) -> str:
    specifier_template = (
        os.getenv("_RED_UPDATE_PRETEND_SPECIFIER_TEMPLATE")
        or "Red-DiscordBot {extras} {versionspec}"
    )
    joined_extras = ",".join(extras)
    return specifier_template.format(
        extras=f"[{joined_extras}]" if joined_extras else "",
        versionspec=f"=={version}",
    )


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


def _apply_legacy_windows_workaround() -> None:
    # Rich does not properly support printing to stderr, when stdout is redirected...
    # This monkeypatch should be enough to workaround this for our purposes.
    # https://github.com/Textualize/rich/issues/4071
    if sys.platform == "win32" and not sys.stdout.isatty():
        import rich._win32_console

        rich._win32_console.STDOUT = -12


def configure_rich() -> None:
    _apply_legacy_windows_workaround()
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


def get_logging_level() -> int:
    return logging.getLogger("red").level


def get_log_cli_level() -> int:
    return log_level_to_cli_level(logging.getLogger("red").level)


def ensure_supported_env() -> None:
    if sys.prefix == sys.base_prefix:
        print("redbot-update cannot be used when Red is installed outside a virtual environment.")
        raise SystemExit(1)
    if not (
        os.environ.get(RUNNER_DIR_ENV_VAR, "") and os.environ.get(RUNNER_WRAPPER_EXE_ENV_VAR, "")
    ):
        print("redbot-update was called incorrectly.")
        raise SystemExit(1)


def _get_system_interpreters(
    requires_python: SpecifierSet,
) -> List[Tuple[str, Version, PythonInfo]]:
    interpreters = {}

    def _append_interpreter(info: PythonInfo) -> Literal[False]:
        version = Version(info.version_str)
        if version in requires_python:
            # realpath call is needed because get_interpreter lists
            # /usr/bin and /bin as separate even though they're the same path
            interpreters[os.path.realpath(info.executable)] = (version, info)
        return False

    get_interpreter("cpython", predicate=_append_interpreter)

    ret = [(key, *value) for key, value in interpreters.items()]
    ret.sort(key=itemgetter(1), reverse=True)
    return ret


def search_for_interpreters(
    requires_python: SpecifierSet,
) -> List[Tuple[str, Version, PythonInfo]]:
    console = get_console()
    with console.status("Searching for compatible Python interpreters on your system..."):
        interpreters = _get_system_interpreters(requires_python)

    if not interpreters:
        url = "https://docs.discord.red/en/stable/install_guides/"
        console.print(
            f"{ICON_ERROR} Could not find a compatible Python interpreter!\n"
            'Please follow the steps from the "Installing the pre-requirements" section'
            " of the install guide for your system:"
        )
        console.print(Text(url, style=f"link {url}"))
        console.print("Once you finish installing the pre-requirements, run this command again.")
        raise SystemExit(1)

    return interpreters


class OrderedEnum(enum.Enum):
    def __ge__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class VersionParamType(click.ParamType):
    name = "version"

    def convert(
        self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> Version:
        if isinstance(value, Version):
            if len(value.release) < 2:
                self.fail(
                    f"{value!r} needs to have at least 2 release components (major and minor).",
                    param,
                    ctx,
                )
            return value

        try:
            return self.convert(Version(value), param, ctx)
        except ValueError:
            self.fail(f"{value!r} is not a valid version number", param, ctx)
