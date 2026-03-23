import logging
import sys

import click

from redbot.core.utils._internal_utils import cli_level_to_log_level


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
        print("Hello world!")


if __name__ == "__main__":
    cli()
