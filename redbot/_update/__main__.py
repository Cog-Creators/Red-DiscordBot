import asyncio
from pathlib import Path
from typing import Final, Optional, Tuple

import click

from redbot.core._cli import asyncio_run

from . import cmd, common, updater


_CHECK_OTHER_PYTHON_INSTALLS_CMD_ARG_NAME: Final = "--check-other-python-installs"


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
    backup_dir: Optional[Path],
    no_backup: bool,
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


cli.add_command(cmd.cog_compatibility.check_cog_compatibility)


if __name__ == "__main__":
    cli()
