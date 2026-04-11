import asyncio
from pathlib import Path
from typing import Any, Final, Optional, Tuple

import click
from packaging.version import Version
from python_discovery import PythonInfo

from redbot.core._cli import asyncio_run

from . import cmd, common, updater


_CHECK_OTHER_PYTHON_INSTALLS_CMD_ARG_NAME: Final = "--check-other-python-installs"


def _help_major_update_example() -> str:
    version = common.get_current_red_version().__replace__(dev=None, local=None)
    release = (version.major, version.minor + 1) + (0,) * (len(version.release) - 2)
    next_major_version = version.__replace__(release=release)
    return f"updating from Red {version} to Red {next_major_version}"


def _help_minor_update_example() -> str:
    version = common.get_current_red_version().__replace__(dev=None, local=None)
    release = (version.major, version.minor, version.micro + 1) + (0,) * (len(version.release) - 3)
    next_minor_version = version.__replace__(release=release)
    return f"updating from Red {version} to Red {next_minor_version}"


class _PythonInfoParamType(click.ParamType):
    name = "Python interpreter"

    def convert(
        self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> PythonInfo:
        if isinstance(value, PythonInfo):
            return value

        try:
            return PythonInfo.from_exe(value)
        except RuntimeError:
            self.fail(f"{value!r} is not a valid Python executable.", param, ctx)


@click.group(invoke_without_command=True)
# command-specific options
@click.option(
    "--include-instance",
    "included_instances",
    multiple=True,
    type=click.Choice(common.INSTANCE_LIST),
    help="The list of instances to backup and check cog compatibility for. If not specified,"
    " all instances that use the current virtual environment will be backed up and checked.",
)
@click.option(
    "--exclude-instance",
    "excluded_instances",
    multiple=True,
    type=click.Choice(common.INSTANCE_LIST),
    help="Exclude an instance from the list of instances to backup"
    " and check cog compatibility for.",
)
@click.option(
    "--backup-dir",
    default=None,
    type=click.Path(
        dir_okay=True, file_okay=False, resolve_path=True, writable=True, path_type=Path
    ),
    help="The directory to place the backups of the virtual environment and instances.",
)
@click.option(
    "--no-backup",
    help="Do not make backups of the virtual environment and instances before update.",
    is_flag=True,
)
@click.option(
    "--red-version",
    "--version",
    type=common.VersionParamType(),
    default=None,
    help="Version of Red to update to instead of the latest.",
)
@click.option(
    "--no-major-updates",
    help=f"Skip major updates. For example: {_help_major_update_example()} is a major update"
    f" but {_help_minor_update_example()} isn't.",
    is_flag=True,
)
@click.option(
    "--no-full-changelog",
    help='Skip showing full changelog in a terminal user interface. The "Read before updating"'
    " sections will still be printed.",
    is_flag=True,
)
@click.option(
    "--no-cog-compatibility-check",
    help="Skip performing cog compatibility check before the update.",
    is_flag=True,
)
@click.option(
    "--new-python-interpreter",
    type=_PythonInfoParamType(),
    help="The new Python interpreter that should be used when creating a virtual environment"
    " for Red. This can either be a path to a Python executable or a name of a Python executable"
    " on the PATH.",
)
@click.option(
    "--update-cogs/--no-update-cogs",
    default=None,
    help="When this option is used, it determines whether the cogs should be updated after Red"
    " is updated. By default, you'll be asked, if you want to update.\n"
    "In non-interactive mode, cogs will be updated unless this option is used to override"
    " the default behavior.",
)
@click.option(
    # `pip install` having an option with the same name is coincidental,
    # this does not call `pip install` with the `--force-reinstall` option.
    # Not that there would be any point in doing so - we create a fresh virtual environment.
    "--force-reinstall",
    type=bool,
    is_flag=True,
    help="Force the update process to proceed even, if there is no new version detected."
    " This will essentially reinstall latest Red version into a fresh virtual environment. You can"
    " combine it with the --new-python-interpreter option to change Red's Python interpreter.",
)
@click.option(
    "--no-prompt",
    "interactive",
    type=bool,
    is_flag=True,
    default=True,
    help="Don't ask for user input during the process (non-interactive mode).\n"
    "NOTE: If you want to use this to automate Red updates, consider specifying --no-major-update"
    " to avoid performing major updates without making an explicit decision to.\n"
    "When performing a major update where the current Python interpreter is no longer compatible,"
    " the --new-python-interpreter option has to be specified or the command will fail.",
)
# global options
@click.option(
    cmd.arg_names.DEBUG,
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
    backup_dir: Optional[Path],
    no_backup: bool,
    red_version: Optional[Version],
    no_major_updates: bool,
    no_full_changelog: bool,
    no_cog_compatibility_check: bool,
    new_python_interpreter: Optional[PythonInfo],
    update_cogs: Optional[bool],
    force_reinstall: bool,
    interactive: bool,
    logging_level: int,
    ignore_prefix: bool,
) -> None:
    common.ensure_supported_env()
    common.configure_logging(logging_level)

    ctx.ensure_object(dict)
    ctx.obj["IGNORE_PREFIX"] = ignore_prefix

    if ctx.invoked_subcommand is None:
        if included_instances:
            # de-duplicate with order intact
            instances = list(dict.fromkeys(included_instances))
        else:
            instances = list(common.INSTANCE_LIST)
        options = updater.UpdaterOptions(
            instances=instances,
            excluded_instances=set(excluded_instances),
            ignore_prefix=ignore_prefix,
            backup_dir=backup_dir,
            no_backup=no_backup,
            red_version=red_version,
            no_major_updates=no_major_updates,
            no_full_changelog=no_full_changelog,
            no_cog_compatibility_check=no_cog_compatibility_check,
            new_python_interpreter=new_python_interpreter,
            update_cogs=update_cogs,
            force_reinstall=force_reinstall,
            interactive=interactive,
        )
        app = updater.Updater(options)
        asyncio_run(app.run())
    # these should not be available to subcommands
    elif included_instances:
        raise click.NoSuchOption("--include-instance", ctx=ctx)
    elif excluded_instances:
        raise click.NoSuchOption("--exclude-instance", ctx=ctx)
    elif backup_dir is not None:
        raise click.NoSuchOption("--backup-dir", ctx=ctx)
    elif no_backup:
        raise click.NoSuchOption("--no-backup", ctx=ctx)
    elif red_version:
        raise click.NoSuchOption("--red-version", ctx=ctx)
    elif no_major_updates:
        raise click.NoSuchOption("--no-major-updates", ctx=ctx)
    elif no_cog_compatibility_check:
        raise click.NoSuchOption("--no-cog-compatibility-check", ctx=ctx)
    elif new_python_interpreter:
        raise click.NoSuchOption("--new-python-interpreter", ctx=ctx)
    elif update_cogs is True:
        raise click.NoSuchOption("--update-cogs", ctx=ctx)
    elif update_cogs is False:
        raise click.NoSuchOption("--no-update-cogs", ctx=ctx)
    elif not interactive:
        raise click.NoSuchOption("--no-prompt", ctx=ctx)
    elif force_reinstall:
        raise click.NoSuchOption("--force-reinstall", ctx=ctx)


cli.add_command(cmd.cog_compatibility.check_cog_compatibility)


if __name__ == "__main__":
    cli()
