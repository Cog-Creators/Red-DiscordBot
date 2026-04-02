import click

from . import common


@click.group(invoke_without_command=True)
@click.option("--debug", "logging_level")
def cli(logging_level: int) -> None:
    common.ensure_supported_env()
    common.configure_logging(logging_level)
