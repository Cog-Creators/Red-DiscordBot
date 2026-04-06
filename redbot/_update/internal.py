import subprocess
import shutil
import sys
import sysconfig
from pathlib import Path

import click
from rich.text import Text

from redbot import __version__

from . import common, runner


@click.group(invoke_without_command=True)
@click.option("--debug", "logging_level")
def cli(logging_level: int) -> None:
    common.ensure_supported_env()
    common.configure_logging(logging_level)


@cli.command()
def finish_update() -> None:
    """
    Entrypoint for finishing up the update that runs with the new version of Red.
    """
    assert runner.get_request_output().request_type is runner.RequestType.exec

    with common.get_console().status("Cleaning up..."):
        backup_dir = Path(sys.prefix) / common.OLD_VENV_BACKUP_DIR_NAME
        shutil.rmtree(backup_dir)

    common.get_console().print()
    common.print_with_prefix_column(
        common.ICON_SUCCESS,
        "Update to Red ",
        Text(__version__, style="bold"),
        " has been finished!",
    )


@cli.command()
@click.argument("base_executable")
@click.argument("venv_dir", type=click.Path(path_type=Path))
@click.argument("scripts_path", type=click.Path(path_type=Path))
@click.argument("dependency_specifier")
def reinstall(
    base_executable: str, venv_dir: Path, scripts_path: Path, dependency_specifier: str
) -> None:
    assert runner.get_request_output().request_type is runner.RequestType.exec

    subprocess.check_call((base_executable, "-m", "venv", str(venv_dir)))
    executable = str(scripts_path / f"python{sysconfig.get_config_var('EXE')}")

    common.print_with_prefix_column(common.ICON_INFO, "Starting the install process...")
    try:
        subprocess.check_call((executable, "-m", "pip", "install", "-U", "pip"))
        subprocess.check_call((executable, "-m", "pip", "install", dependency_specifier))
    except subprocess.CalledProcessError:
        console = common.get_console()
        console.print()
        common.print_with_prefix_column(
            common.ICON_ERROR,
            "Failed to install new version of Red.",
        )
        status = console.status("Attempting to restore old virtual environment...")
        status.start()
        try:
            _remove_new_venv(venv_dir)
        except Exception:
            status.stop()
            common.print_with_prefix_column(
                common.ICON_ERROR, "Failed to remove newly created virtual environment."
            )
            raise SystemExit(1)
        try:
            _restore_old_venv(venv_dir)
        except Exception:
            status.stop()
            common.print_with_prefix_column(
                common.ICON_ERROR, "Failed to restore old virtual environment."
            )
        else:
            common.print_with_prefix_column(
                common.ICON_INFO, "The old virtual environment has been restored."
            )
        raise SystemExit(1)

    # NOTE: this will run with the updated version of Red
    runner.make_exec_request(executable, "finish-update")


def _remove_new_venv(venv_dir: Path) -> None:
    backup_dir = venv_dir / common.OLD_VENV_BACKUP_DIR_NAME
    wrapper_exe = runner.get_wrapper_executable()

    for path in venv_dir.iterdir():
        if path == backup_dir or path == wrapper_exe:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def _restore_old_venv(venv_dir: Path) -> None:
    backup_dir = venv_dir / common.OLD_VENV_BACKUP_DIR_NAME
    for path in backup_dir.iterdir():
        path.rename(venv_dir / path.name)


if __name__ == "__main__":
    cli()
