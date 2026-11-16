import asyncio
import json
import os
import sys
import tempfile
from typing import Final, Optional, Tuple

import click
from packaging.version import Version
from rich.text import Text

from redbot._update import cog_compatibility_checker, common
from redbot._update.cog_compatibility_checker import CompatibilitySummary
from redbot.core import _drivers
from redbot.core._cli import asyncio_run
from redbot.core.utils._internal_utils import fetch_latest_red_version

from . import arg_names


EXIT_INSTANCE_SITE_PREFIX_MISMATCH: Final = 4
EXIT_INSTANCE_BACKEND_UNSUPPORTED: Final = 5
CMD_NAME: Final = "check-cog-compatibility"
_COMPATIBILITY_RESULTS_ENV_VAR = "_RED_UPDATE_COMPATIBILITY_RESULTS_FILE"


@click.command(CMD_NAME)
@click.argument(
    "instances",
    nargs=-1,
    type=click.Choice(common.INSTANCE_LIST),
    default=None,
    metavar="[INSTANCE_NAME]",
)
@click.option(
    arg_names.RED_VERSION,
    type=common.VersionParamType(),
    default=None,
    help="The Red version to check cog compatibility for."
    " If not provided, the information about latest available version will be fetched"
    " and the command will check whether installed cogs support that version.\n"
    "If this option is provided, --python-version also has to be provided.",
)
@click.option(
    arg_names.PYTHON_VERSION,
    type=common.VersionParamType(),
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
            param_hint=[arg_names.RED_VERSION, arg_names.PYTHON_VERSION],
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
            latest = await fetch_latest_red_version(
                include_prereleases=common.get_current_red_version().is_prerelease
            )
            red_version = latest.version

        python_version = Version(".".join(map(str, sys.version_info[:3])))
        if python_version not in latest.requires_python:
            interpreters = common.search_for_interpreters(latest.requires_python)
            _, python_version, _ = interpreters[0]

    if len(instances) == 1:
        results_file = os.getenv(_COMPATIBILITY_RESULTS_ENV_VAR, "")
        try:
            results = await cog_compatibility_checker.check_instance(
                instances[0],
                latest_version=red_version,
                interpreter_version=python_version,
                ignore_prefix=ignore_prefix,
            )
        except _drivers.MissingExtraRequirements:
            if not results_file:
                common.print_with_prefix_column(
                    common.ICON_ERROR,
                    Text(instances[0], style="bold"),
                    " instance could not be checked as it uses a storage backend"
                    " that is not supported by the current Red installation"
                    " (some requirements are missing).",
                )
            raise SystemExit(EXIT_INSTANCE_BACKEND_UNSUPPORTED)
        except cog_compatibility_checker.InstanceSitePrefixMismatchError as exc:
            if not results_file:
                common.print_with_prefix_column(
                    common.ICON_ERROR,
                    Text(exc.instance_name, style="bold"),
                    " instance could not be checked as it is a part of"
                    " a different Python installation and/or virtual environment.",
                )
            raise SystemExit(EXIT_INSTANCE_SITE_PREFIX_MISMATCH)
        if results_file:
            with open(results_file, "w", encoding="utf-8") as fp:
                json.dump(results.to_json_dict(), fp)
        return

    if not instances:
        instances = tuple(common.INSTANCE_LIST)
    checked_instances = []
    for instance_name in instances:
        exit_code, _, _ = await call(
            instance_name,
            red_version=red_version,
            python_version=python_version,
            ignore_prefix=ignore_prefix,
        )
        if exit_code != EXIT_INSTANCE_SITE_PREFIX_MISMATCH:
            if exit_code:
                raise SystemExit(exit_code)
            checked_instances.append(instance_name)

    if not checked_instances:
        common.print_with_prefix_column(
            common.ICON_ERROR, "There were no instances to check cog compatibility for."
        )
        raise SystemExit(1)


async def call(
    instance_name: str,
    *,
    red_version: Version,
    python_version: Version,
    ignore_prefix: bool = False,
    return_results: bool = False,
    stdout: Optional[int] = None,
) -> Tuple[int, Optional[str], Optional[CompatibilitySummary]]:
    debug_args = (arg_names.DEBUG,) * common.get_log_cli_level()
    args = [
        "-m",
        "redbot._update",
        *debug_args,
        CMD_NAME,
        arg_names.RED_VERSION,
        str(red_version),
        arg_names.PYTHON_VERSION,
        str(python_version),
        "--",
        instance_name,
    ]
    if ignore_prefix:
        args.append(arg_names.CHECK_OTHER_PYTHON_INSTALLS)
    env = os.environ.copy()

    # terminal woes
    console = common.get_console()
    if console.is_terminal:
        env["TTY_COMPATIBLE"] = "1"
        # Rich only checks stdout for Windows console features:
        # https://github.com/Textualize/rich/blob/fc41075a3206d2a5fd846c6f41c4d2becab814fa/rich/_windows.py#L46
        env[common.INTERNAL_LEGACY_WINDOWS_ENV_VAR] = "1" if console.legacy_windows else "0"
    else:
        # Rich does not set legacy_windows correctly when is_terminal is False
        # https://github.com/Textualize/rich/issues/3647
        env[common.INTERNAL_LEGACY_WINDOWS_ENV_VAR] = "0"
    env["PYTHONIOENCODING"] = sys.stdout.encoding

    results = None
    results_file = None
    if return_results:
        results_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        if results_file is not None:
            results_file.close()
            env[_COMPATIBILITY_RESULTS_ENV_VAR] = str(results_file.name)

        proc = await asyncio.create_subprocess_exec(sys.executable, *args, env=env, stdout=stdout)
        stdout_data, _ = await proc.communicate()
        decoded_stdout = None
        if stdout_data is not None:
            decoded_stdout = stdout_data.decode()
        exit_code = await proc.wait()
        if not exit_code and results_file is not None:
            with open(results_file.name, encoding="utf-8") as fp:
                results = CompatibilitySummary.from_json_dict(json.load(fp))
    finally:
        if results_file is not None:
            os.remove(results_file.name)

    return exit_code, decoded_stdout, results
