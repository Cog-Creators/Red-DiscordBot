import logging
import os
import sys
from operator import itemgetter
from typing import List, Literal, Tuple

import click
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from python_discovery import PythonInfo, get_interpreter
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text

from redbot.core._cli import asyncio_run
from redbot.core.utils._internal_utils import cli_level_to_log_level, fetch_latest_red_version

from . import changelog, common
from .tui import ChangelogReaderApp, ChangelogReaderResult


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


def _search_for_interpreters(requires_python: SpecifierSet) -> List[Tuple[str, Version]]:
    console = common.get_console()
    with console.status("Searching for compatible Python interpreters on your system..."):
        interpreters = _get_system_interpreters(requires_python)

    if not interpreters:
        url = "https://docs.discord.red/en/latest/install_guides/"
        console.print(
            f"{common.ICON_ERROR} Could not find a compatible Python interpreter!\n"
            'Please follow the steps from the "Installing the pre-requirements" section'
            " of the install guide for your system:"
        )
        console.print(Text(url, style=f"link {url}"))
        console.print("Once you finish installing the pre-requirements, run this command again.")
        raise SystemExit(1)

    return interpreters


def _ask_for_interpreter(
    *, current_python_version: Version, requires_python: SpecifierSet
) -> Tuple[str, Version]:
    interpreters = _search_for_interpreters(requires_python)
    console = common.get_console()

    def _render_interpreter(interpreter_exe: str, interpreter_version: Version) -> Text:
        return Text.assemble(
            "CPython ",
            (str(interpreter_version), "repr.number"),
            " (",
            (interpreter_exe, "log.path"),
            ")",
        )

    text = Text("Found the following compatible Python interpreters on your system:")
    for idx, (interpreter_exe, interpreter_version) in enumerate(interpreters, 1):
        text.append_text(Text(f"\n{idx}. ", style="markdown.item.number"))
        text.append_text(_render_interpreter(interpreter_exe, interpreter_version))
    console.print(Panel(text))

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
            if info.implementation != "CPython" or interpreter_version not in requires_python:
                console.print(
                    "[prompt.invalid] The provided path points to an incompatible Python"
                    f" interpreter. Latest version requires CPython {requires_python} but"
                    f" the provided interpreter is {info.implementation} {interpreter_version}."
                )
                continue
            interpreter_exe = info.executable
        else:
            interpreter_exe, interpreter_version = interpreters[result - 1]

        console.print(
            "\n[b]You selected:[/]", _render_interpreter(interpreter_exe, interpreter_version)
        )
        if Confirm.ask("Do you want to continue with this choice?"):
            console.print()
            break

    return interpreter_exe, interpreter_version


async def main() -> None:
    console = common.get_console()
    current_version = common.get_current_red_version()
    current_python_version = common.get_current_python_version()

    with console.status("Checking latest version..."):
        latest = await fetch_latest_red_version()

    if current_version >= latest.version:
        common.print_with_prefix_column(
            common.ICON_SUCCESS,
            "You are already running the latest available version of Red.",
        )
        return

    common.print_with_prefix_column(
        common.ICON_SUCCESS,
        Text("New version available: ").append(str(latest.version), style="bold"),
    )
    if current_python_version not in latest.requires_python:
        common.print_with_prefix_column(
            common.ICON_WARN,
            "The latest version of Red requires a different version (",
            Text(str(latest.requires_python), style="bold"),
            ") from the one that you are currently using (",
            Text(str(current_python_version), style="bold"),
            ")\nredbot-update will have to recreate the virtual environment"
            " with a compatible version of Python.",
        )

    with console.status("Fetching changelogs..."):
        changelogs = await changelog.fetch_changelogs()
        changelogs = changelog.get_changelogs_newer_than(changelogs, current_version)
    common.print_with_prefix_column(common.ICON_SUCCESS, "Changelogs fetched.")

    first_changelog_version = min(changelogs)
    last_changelog_version = max(changelogs)
    if first_changelog_version == last_changelog_version:
        msg = (
            "You will now be presented with the changelog for"
            f" [b]Red {first_changelog_version}[/]."
        )
    else:
        msg = (
            "You will now be presented with the changelogs for"
            f" [b]Red {first_changelog_version}[/]-[b]{last_changelog_version}[/]."
        )
    msg += (
        f"\n[bold]{common.ICON_WARN}"
        '  Make sure to read through the [green]"Read before updating"[/] section'
        f" before continuing. {common.ICON_WARN}[/bold]\n"
        "After the changelog is open and you're ready to continue, hit the [b]Q[/] key"
        " to close the changelog and continue the update process.\n\n"
        "Hit the [b]Enter[/] key to view the changelog."
    )
    console.input(Panel(msg), password=True)

    viewer = ChangelogReaderApp(changelog.render_markdown(changelogs))
    result = await viewer.run_async()
    if result is None:
        raise RuntimeError("Unexpected state")
    if result is ChangelogReaderResult.QUIT:
        raise click.Abort()

    common.print_with_prefix_column(
        common.ICON_SUCCESS,
        "Changelog closed, continuing with the update process...",
    )

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
    common.configure_rich()
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
