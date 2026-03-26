import logging
import os
import sys
from operator import itemgetter
from typing import List, Literal, Tuple

import click
import rich
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from python_discovery import PythonInfo, get_interpreter
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text

from redbot import __version__
from redbot.core._cli import asyncio_run
from redbot.core.utils._internal_utils import cli_level_to_log_level, fetch_latest_red_version

from . import changelog
from .tui import MarkdownViewerApp


def _get_system_interpreters(requires_python: SpecifierSet) -> List[Tuple[str, Version]]:
    interpreters = {}

    def _append_interpreter(info: PythonInfo) -> Literal[False]:
        version = Version(info.version_str)
        if version in requires_python:
            # realpath call is needed because get_interpreter lists
            # /usr/bin and /bin as separate even though they're the same path
            interpreters[os.path.realpath(info.executable)] = version
        return False

    get_interpreter("cpython", predicate=_append_interpreter)

    return sorted(interpreters.items(), key=itemgetter(1), reverse=True)


def _ask_for_interpreter(
    *, current_python_version: Version, requires_python: SpecifierSet
) -> Tuple[str, Version]:
    console = rich.get_console()
    console.print(
        "[yellow]:warning-text:[/] The latest version of Red requires a different version (",
        Text(str(requires_python)),
        ") from the one that you are currently using (",
        Text(str(current_python_version)),
        ")\nredbot-update will have to recreate the virtual environment"
        " with a compatible version of Python.\n",
        sep="",
    )
    with console.status("Searching for compatible Python interpreters on your system..."):
        interpreters = _get_system_interpreters(requires_python)

    if not interpreters:
        url = "https://docs.discord.red/en/latest/install_guides/"
        console.print(
            "[red]:cross_mark-text:[/] Could not find a compatible Python interpreter!\n"
            'Please follow the steps from the "Installing the pre-requirements" section'
            " of the install guide for your system:"
        )
        console.print(Text(url, style=f"link {url}"))
        console.print("Once you finish installing the pre-requirements, run this command again.")
        raise SystemExit(1)

    console.print("Found the following compatible Python interpreters on your system:")
    for idx, (interpreter_exe, interpreter_version) in enumerate(interpreters, 1):
        console.print(f"{idx}. CPython {interpreter_version} ({interpreter_exe})", markup=False)

    while True:
        result = IntPrompt.ask(
            "\nEnter the number of the Python interpreter above that you want to use"
            " or type 0 to input the path to it yourself. Generally, you should choose"
            " the interpreter with the latest version on the above list.\nEnter your selection",
            default=1,
        )
        if result < 0 or result > len(interpreters):
            console.print("[prompt.invalid] This is not a valid choice.")
            continue

        if result == 0:
            response = Prompt.ask(
                "Please input the path to the Python interpreter that you want to use"
            )
            if not response:
                console.print("[prompt.invalid] No path was provided.")
                continue
            info = PythonInfo.from_exe(response, raise_on_error=True)
            interpreter_version = Version(info.version_str)
            if interpreter_version not in requires_python:
                console.print(
                    "[prompt.invalid] The provided path points to an incompatible Python"
                    f" interpreter. Latest version requires CPython {requires_python} but"
                    f" the provided interpreter is {info.implementation} {interpreter_version}."
                )
                continue
            interpreter_exe = info.executable
        else:
            interpreter_exe, interpreter_version = interpreters[result - 1]

        if Confirm.ask(
            f"You selected: Python {interpreter_version} ({interpreter_exe})\n"
            "Do you want to continue with this choice?"
        ):
            break

    return interpreter_exe, interpreter_version


async def main() -> None:
    console = rich.get_console()
    current_version = Version(__version__)
    current_python_version = Version(".".join(map(str, sys.version_info[:3])))

    with console.status("Checking latest version..."):
        latest = await fetch_latest_red_version()

    if current_version >= latest.version:
        console.print(
            "[green]:white_heavy_check_mark-text:[/]"
            " You are already running the latest available version of Red."
        )
        return

    console.print(
        "[green]:white_heavy_check_mark-text:[/] New version available:", Text(str(latest.version))
    )

    with console.status("Fetching changelogs..."):
        changelogs = await changelog.fetch_changelogs()

    await MarkdownViewerApp(changelog.render_markdown(changelogs, current_version)).run_async()

    interpreter_exe = sys.executable
    interpreter_version = current_python_version
    if current_python_version not in latest.requires_python:
        interpreter_exe, interpreter_version = _ask_for_interpreter(
            current_python_version=current_python_version, requires_python=latest.requires_python
        )

    with console.status("Checking compatibility of installed cogs..."):
        import asyncio

        await asyncio.sleep(10)


@click.group(invoke_without_command=True)
@click.option(
    "--debug",
    "--verbose",
    "-v",
    count=True,
    help=(
        "Increase the verbosity of the logs, each usage of this flag increases the verbosity"
        " level by 1."
    ),
)
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
) -> None:
    level = cli_level_to_log_level(debug)
    base_logger = logging.getLogger("red")
    base_logger.setLevel(level)
    formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    base_logger.addHandler(stdout_handler)

    if ctx.invoked_subcommand is None:
        asyncio_run(main())


if __name__ == "__main__":
    cli()
