import asyncio
import os
import sys
from operator import itemgetter
from typing import Any, Final, List, Literal, Optional, Set, Tuple

import click
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from python_discovery import PythonInfo, get_interpreter
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text

from redbot.core import data_manager
from redbot.core._cli import asyncio_run
from redbot.core.utils._internal_utils import fetch_latest_red_version

from . import changelog, cog_compatibility_checker, common
from .tui import ChangelogReaderApp, ChangelogReaderResult


instance_data = data_manager.load_existing_config()
if instance_data is None:
    instance_list = []
else:
    instance_list = list(instance_data.keys())

_EXIT_INSTANCE_SITE_PREFIX_MISMATCH: Final = 3
_CHECK_COG_COMPATIBILITY_CMD_NAME: Final = "check-cog-compatibility"
_RED_VERSION_CMD_ARG_NAME: Final = "--red-version"
_PYTHON_VERSION_CMD_ARG_NAME: Final = "--python-version"
_CHECK_OTHER_PYTHON_INSTALLS_CMD_ARG_NAME: Final = "--check-other-python-installs"


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


async def main(instances: List[str], excluded_instances: Set[str], *, ignore_prefix: bool) -> None:
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

    breaking_update = current_version.release[:2] != latest.version.release[:2]
    with console.status("Fetching changelogs..."):
        changelogs = await changelog.fetch_changelogs()
        changelogs = changelog.get_changelogs_newer_than(changelogs, current_version)
    common.print_with_prefix_column(common.ICON_SUCCESS, "Changelogs fetched.")

    first_changelog_version = min(changelogs)
    last_changelog_version = max(changelogs)
    parts = []
    if first_changelog_version == last_changelog_version:
        parts.append(
            "You will now be presented with the changelog for"
            f" [b]Red {first_changelog_version}[/]."
        )
    else:
        parts.append(
            "You will now be presented with the changelogs for"
            f" [b]Red {first_changelog_version}[/]-[b]{last_changelog_version}[/]."
        )
    parts.append(
        f"\n[bold]{common.ICON_WARN}"
        '  Make sure to read through the [green]"Read before updating"[/] section'
        f" before continuing. {common.ICON_WARN}[/bold]\n"
    )
    if breaking_update:
        parts.append(
            f"[bold]{common.ICON_WARN}"
            "  Please note that this is a major release and it may have some changes that your bot"
            " or its cogs are affected by.[/bold]\n"
        )
    parts.append(
        "After the changelog is open and you're ready to continue, hit the [b]Q[/] key"
        " to close the changelog and continue the update process.\n\n"
        "Hit the [b]Enter[/] key to view the changelog."
    )
    console.input(Panel("".join(parts)), password=True)

    viewer = ChangelogReaderApp(changelog.render_markdown(changelogs))
    result = await viewer.run_async()
    if result is None:
        raise RuntimeError("Unexpected state")
    if result is ChangelogReaderResult.QUIT:
        raise click.Abort()

    console.print("Changelog has been closed.\n")

    interpreter_exe = sys.executable
    interpreter_version = current_python_version
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
        interpreter_exe, interpreter_version = _ask_for_interpreter(
            current_python_version=current_python_version, requires_python=latest.requires_python
        )

    checked_instances = {}
    failed_instances = []
    for instance_name in instances:
        if instance_name in excluded_instances:
            continue
        exit_code, stdout = await _call_check_cog_compatibility_cmd(
            instance_name,
            red_version=latest.version,
            python_version=interpreter_version,
            ignore_prefix=ignore_prefix,
            internal=True,
            stdout=asyncio.subprocess.PIPE,
        )
        if exit_code != _EXIT_INSTANCE_SITE_PREFIX_MISMATCH:
            if exit_code:
                failed_instances.append(instance_name)
                print(stdout, end="")
                Text.assemble(
                    "\N{UPWARDS ARROW} " * 3, "Failure for ", (instance_name, "bold"), " instance"
                )
                console.rule(
                    Text.assemble(
                        "\N{UPWARDS ARROW} " * 3,
                        "Failure for ",
                        (instance_name, "bold"),
                        " instance above",
                        " \N{UPWARDS ARROW}" * 3,
                    ),
                    style="red",
                )
            else:
                checked_instances[instance_name] = stdout
        if stdout:
            console.print()
    console.print()

    if checked_instances:
        for instance_name, stdout in checked_instances.items():
            console.rule(Text(instance_name, style="bold"))
            print(stdout, end="")
        console.rule()

    common.print_with_prefix_column(
        common.ICON_INFO,
        "Finished checking cog compatibility.",
        (
            "\nThe results for each of the checked instances are shown above."
            if checked_instances
            else ""
        ),
    )
    if failed_instances:
        common.print_with_prefix_column(
            common.ICON_ERROR,
            "Failure occurred while trying to check compatibility for following instances: ",
            Text(", ").join(
                Text(instance_name, style="bold") for instance_name in failed_instances
            ),
            "\nScroll above to find the errors.",
        )
    if not checked_instances:
        common.print_with_prefix_column(
            common.ICON_INFO,
            "There were no",
            (" other" if failed_instances else ""),
            " instances to check cog compatibility for.",
        )
    console.print()

    if breaking_update:
        console.print(
            "[b]Remember that this is a major release and it may have some breaking changes"
            " that the bot or its cogs may be affected by.[/]"
        )
    if not Confirm.ask(f"Do you want to continue with the update to [b]Red {latest.version}[/]?"):
        return
    console.print()

    # now onto actual update...


@click.group(invoke_without_command=True)
# command-specific options
@click.option(
    "--include-instance",
    "included_instances",
    multiple=True,
    type=click.Choice(instance_list),
    help="When specified, the cog compatibility will only be checked for instances specified with"
    " the --include-instance option. Otherwise, all instances are checked.",
)
@click.option(
    "--exclude-instance",
    "excluded_instances",
    multiple=True,
    type=click.Choice(instance_list),
    help="Exclude an instance from the list of instances to check cog compatibility for.",
)
# global options
@click.option(
    "--debug",
    "--verbose",
    "-v",
    "logging_level",
    count=True,
    help=(
        "Increase the verbosity of the logs, each usage of this flag increases the verbosity"
        " level by 1."
    ),
)
@click.option(
    "--check-other-venvs",
    _CHECK_OTHER_PYTHON_INSTALLS_CMD_ARG_NAME,
    "ignore_prefix",
    help="Check the compatibility of cogs for instances that are normally ran with"
    " a different Python installation and/or virtual environment than the current one.",
    is_flag=True,
)
@click.pass_context
def cli(
    ctx: click.Context,
    included_instances: Tuple[str, ...],
    excluded_instances: Tuple[str, ...],
    logging_level: int,
    ignore_prefix: bool,
) -> None:
    common.configure_logging(logging_level)

    ctx.ensure_object(dict)
    ctx.obj["IGNORE_PREFIX"] = ignore_prefix

    if ctx.invoked_subcommand is None:
        if included_instances:
            # de-duplicate with order intact
            instances = list(dict.fromkeys(included_instances))
        else:
            instances = instance_list
        asyncio_run(main(instances, set(excluded_instances), ignore_prefix=ignore_prefix))
    # these should not be available to subcommands
    elif included_instances:
        raise click.NoSuchOption("--include-instance", ctx=ctx)
    elif excluded_instances:
        raise click.NoSuchOption("--exclude-instance", ctx=ctx)


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


@cli.command(_CHECK_COG_COMPATIBILITY_CMD_NAME)
@click.argument(
    "instances",
    nargs=-1,
    type=click.Choice(instance_list),
    default=None,
    metavar="[INSTANCE_NAME]",
)
@click.option(
    _RED_VERSION_CMD_ARG_NAME,
    type=VersionParamType(),
    default=None,
    help="The Red version to check cog compatibility for."
    " If not provided, the information about latest available version will be fetched"
    " and the command will check whether installed cogs support that version.\n"
    "If this option is provided, --python-version also has to be provided.",
)
@click.option(
    _PYTHON_VERSION_CMD_ARG_NAME,
    type=VersionParamType(),
    default=None,
    help="The Python version to check cog compatibility for."
    " If not provided, the command will either use the current interpreter's version or,"
    " if that version is not compatible with the latest Red version, it will try to"
    " find the latest available CPython interpreter on the system and will check whether"
    " installed cogs support it.\n"
    "If this option is provided, --red-version also has to be provided.",
)
@click.pass_context
def check_cog_compatibility(
    ctx: click.Context,
    instances: Tuple[str, ...],
    red_version: Optional[Version],
    python_version: Optional[Version],
) -> None:
    """
    Check if the installed cogs are compatible with the given version.
    """
    if (red_version, python_version).count(None) == 1:
        raise click.BadParameter(
            "Either both --red-version and --python-version options"
            " have to be specified or neither.",
            param_hint=[_RED_VERSION_CMD_ARG_NAME, _PYTHON_VERSION_CMD_ARG_NAME],
        )

    asyncio_run(
        _check_cog_compatibility_command_impl(
            red_version=red_version,
            python_version=python_version,
            instances=instances,
            ignore_prefix=ctx.obj["IGNORE_PREFIX"],
        )
    )


async def _check_cog_compatibility_command_impl(
    *,
    red_version: Optional[Version],
    python_version: Optional[Version],
    instances: Tuple[str, ...] = (),
    ignore_prefix: bool = False,
) -> None:
    console = common.get_console()
    if red_version is None or python_version is None:
        with console.status("Checking latest version..."):
            latest = await fetch_latest_red_version()
            red_version = latest.version

        python_version = Version(".".join(map(str, sys.version_info[:3])))
        if python_version not in latest.requires_python:
            interpreters = _search_for_interpreters(latest.requires_python)
            _, python_version = interpreters[0]

    if len(instances) == 1:
        try:
            await cog_compatibility_checker.check_instance(
                instances[0],
                latest_version=red_version,
                interpreter_version=python_version,
                ignore_prefix=ignore_prefix,
            )
        except cog_compatibility_checker.InstanceSitePrefixMismatchError as exc:
            if not common.is_internal_cmd_call():
                common.print_with_prefix_column(
                    common.ICON_ERROR,
                    Text(exc.instance_name, style="bold"),
                    " instance could not be checked as it is a part of"
                    " a different Python installation and/or virtual environment.",
                )
            raise SystemExit(_EXIT_INSTANCE_SITE_PREFIX_MISMATCH)
        return

    if not instances:
        instances = tuple(instance_list)
    checked_instances = []
    for instance_name in instances:
        exit_code, _ = await _call_check_cog_compatibility_cmd(
            instance_name,
            red_version=red_version,
            python_version=python_version,
            ignore_prefix=ignore_prefix,
        )
        if exit_code != _EXIT_INSTANCE_SITE_PREFIX_MISMATCH:
            if exit_code:
                raise SystemExit(exit_code)
            checked_instances.append(instance_name)

    if not checked_instances:
        common.print_with_prefix_column(
            common.ICON_ERROR, "There were no instances to check cog compatibility for."
        )
        raise SystemExit(1)


async def _call_check_cog_compatibility_cmd(
    instance_name: str,
    *,
    red_version: Version,
    python_version: Version,
    ignore_prefix: bool = False,
    internal: bool = False,
    stdout: Optional[int] = None,
) -> Tuple[int, Optional[str]]:
    args = [
        "-m",
        "redbot._update",
        _CHECK_COG_COMPATIBILITY_CMD_NAME,
        instance_name,
        _RED_VERSION_CMD_ARG_NAME,
        str(red_version),
        _PYTHON_VERSION_CMD_ARG_NAME,
        str(python_version),
    ]
    if ignore_prefix:
        args.append(_CHECK_OTHER_PYTHON_INSTALLS_CMD_ARG_NAME)
    env = os.environ.copy()
    if internal:
        env[common.INTERNAL_CMD_CALL_ENV_VAR] = "1"
    if common.get_console().is_terminal:
        env["TTY_COMPATIBLE"] = "1"
    proc = await asyncio.create_subprocess_exec(sys.executable, *args, env=env, stdout=stdout)
    stdout_data, _ = await proc.communicate()
    decoded_stdout = None
    if stdout_data is not None:
        decoded_stdout = stdout_data.decode()
    return await proc.wait(), decoded_stdout


if __name__ == "__main__":
    cli()
