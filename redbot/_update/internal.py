import asyncio
import os
import subprocess
import shutil
import sys
import sysconfig
from pathlib import Path
from typing import Tuple

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from redbot import __version__
from redbot.core import _downloader, _drivers, data_manager
from redbot.core._cli import asyncio_run, parse_cli_flags
from redbot.core.bot import Red

from . import changelog, cmd, common, runner
from .updater import UpdaterMetadata, get_updater_metadata


FINISH_UPDATE_CMD_NAME = "finish-update"
_UPDATE_COGS_CMD_NAME = "update-cogs"
_UPDATE_REPOS_OPTION_NAME = "--update-repos"
_EXIT_INSTANCE_SITE_PREFIX_MISMATCH = 4
_EXIT_INSTANCE_BACKEND_UNSUPPORTED = 5


@click.group(invoke_without_command=True)
@click.option(cmd.arg_names.DEBUG, "logging_level", count=True)
def cli(logging_level: int) -> None:
    common.ensure_supported_env()
    common.configure_logging(logging_level)


@cli.command(_UPDATE_COGS_CMD_NAME)
@click.argument("instance_name")
@click.option(_UPDATE_REPOS_OPTION_NAME, default=False, is_flag=True)
def update_cogs(instance_name: str, update_repos: bool) -> None:
    asyncio.run(_update_cogs(instance_name, update_repos))


async def _update_cogs(instance: str, update_repos: bool) -> None:
    data_manager.load_basic_configuration(instance)
    red = Red(cli_flags=parse_cli_flags([instance]))
    driver_cls = _drivers.get_driver_class()
    await driver_cls.initialize(**data_manager.storage_details())
    try:
        await _run_cog_update(red, update_repos=update_repos)
    except _drivers.MissingExtraRequirements:
        raise SystemExit(_EXIT_INSTANCE_BACKEND_UNSUPPORTED)
    finally:
        await driver_cls.teardown()


async def _run_cog_update(bot: Red, *, update_repos: bool) -> None:
    stdout_console = common.get_console()
    console = common.get_console(stderr=True)

    instance_name = data_manager.instance_name()
    last_system_info = await bot._config.last_system_info()
    last_known_prefix = last_system_info["python_prefix"]
    same_install = False
    if last_known_prefix is not None:
        try:
            same_install = os.path.samefile(last_known_prefix, sys.prefix)
        except OSError:
            pass
    if not same_install:
        raise SystemExit(_EXIT_INSTANCE_SITE_PREFIX_MISMATCH)

    common.print_with_prefix_column(
        common.ICON_INFO,
        "Started updating cogs for the ",
        Text(instance_name, style="bold"),
        " instance.",
        console=console,
    )

    await _downloader._init(bot)

    ver_info = list(sys.version_info[:2])
    if ver_info != last_system_info["python_version"]:
        await bot._config.last_system_info.python_version.set(ver_info)
        if any(_downloader.LIB_PATH.iterdir()):
            shutil.rmtree(str(_downloader.LIB_PATH))
            _downloader.LIB_PATH.mkdir()
            common.print_with_prefix_column(
                common.ICON_INFO,
                "We detected a change in minor Python version and cleared packages in lib folder.",
            )
            status = Text.assemble(
                "Reinstalling cog requirements on the ", (instance_name, "bold"), " instance..."
            )
            with console.status(status):
                failed_reqs, failed_libs = await _downloader.reinstall_requirements()
            stdout_console.print(
                "Cog requirements and shared libraries for all installed cogs"
                " have been reinstalled."
            )
            if failed_reqs:
                common.print_with_prefix_column(
                    common.ICON_ERROR,
                    "Failed to reinstall requirements: ",
                    Text(", ").join(Text(req, style="bold") for req in failed_reqs),
                )
            if failed_libs:
                common.print_with_prefix_column(
                    common.ICON_ERROR,
                    "Failed to reinstall shared libraries: ",
                    Text(", ").join(Text(lib.name, style="bold") for lib in failed_libs),
                )

    status = Text.assemble(
        "Update cogs installed on the ", (instance_name, "bold"), " instance..."
    )
    with console.status(status):
        result = await _downloader.update_cogs(update_repos=update_repos)

    common.print_with_prefix_column(
        common.ICON_INFO,
        "Finished updating cogs for the ",
        Text(instance_name, style="bold"),
        " instance.",
        console=console,
    )

    if not result.checked_cogs:
        stdout_console.print("There were no cogs to check.")
        return
    if not result.updates_available:
        stdout_console.print("All installed cogs are already up to date.")
        return

    current_cog_versions_map = {cog.name: cog for cog in result.checked_cogs}
    if result.failed_reqs:
        console.print(
            "Failed to install requirements:",
            Text(", ").join(Text(req, style="bold") for req in result.failed_reqs),
        )
        return

    message = Text("Cog update completed successfully.")

    if result.updated_cogs:
        cogs_with_changed_eud_statement = set()
        for cog in result.updated_cogs:
            current_eud_statement = current_cog_versions_map[cog.name].end_user_data_statement
            if current_eud_statement != cog.end_user_data_statement:
                cogs_with_changed_eud_statement.add(cog.name)
        message.append("\nUpdated: ")
        message.append_text(
            Text(", ").join(Text(cog.name, style="bold") for cog in result.updated_cogs)
        )
        if cogs_with_changed_eud_statement:
            message.append("\nEnd user data statements of these cogs have changed: ")
            message.append_text(
                Text(", ").join(
                    Text(cog_name, style="bold") for cog_name in cogs_with_changed_eud_statement
                )
            )
            message.append("\nYou can use ")
            message.append("[p]cog info <repo> <cog>", style="bold")
            message.append(" to see the updated statements.\n")
        # If the bot has any slash commands enabled, warn them to sync
        enabled_slash = await bot.list_enabled_app_commands()
        if any(enabled_slash.values()):
            message.append("\nYou may need to resync your slash commands with ")
            message.append("[p]slash sync")
            message.append(".")
    if result.failed_cogs:
        message.append("\nFailed to update cogs: ")
        message.append_text(
            Text(", ").join(Text(cog.name, style="bold") for cog in result.failed_cogs)
        )
    if not result.outdated_cogs:
        message = Text("No cogs were updated.")
    if result.failed_libs:
        message.append("\nFailed to install shared libraries: ")
        message.append_text(
            Text(", ").join(Text(lib.name, style="bold") for lib in result.failed_libs)
        )

    stdout_console.print(message)


@cli.command(FINISH_UPDATE_CMD_NAME)
def finish_update() -> None:
    """
    Entrypoint for finishing up the update that runs with the new version of Red.
    """
    asyncio_run(_finish_update())


async def _finish_update() -> None:
    assert runner.get_request_output().request_type is runner.RequestType.exec
    updater_metadata = get_updater_metadata()
    console = common.get_console()
    console.print()

    if updater_metadata.options.interactive and not updater_metadata.options.update_cogs:
        msg = Text("It is highly recommended to update 3rd-party cogs after updating Red")
        if updater_metadata.breaking_update:
            msg.append(", especially after a major update")
        msg.append(".")
        console.print(msg)

    cog_compatibility = updater_metadata.cog_compatibility
    if cog_compatibility is not None:
        unsupported_cogs = set()
        cogs_with_improved_compatibility = set()
        unaffected_cogs = set()
        for summary in cog_compatibility.checked.values():
            for before in summary.before_update.values():
                cog_name = before.name
                after = summary.after_update[cog_name]
                if after.compatibility_status.unsupported:
                    unsupported_cogs.add(cog_name)
                elif after.compatibility_status.explicitly_supported:
                    if before.compatibility_status.explicitly_supported:
                        unaffected_cogs.add(cog_name)
                    else:
                        cogs_with_improved_compatibility.add(cog_name)
                elif before.compatibility_status.unsupported:
                    cogs_with_improved_compatibility.add(cog_name)
                else:
                    unaffected_cogs.add(cog_name)

        if cogs_with_improved_compatibility:
            common.print_with_prefix_column(
                common.ICON_INFO,
                "Updating will improve compatibility of ",
                Text(str(len(cogs_with_improved_compatibility)), style="bold"),
                " cogs.",
            )
        if unsupported_cogs:
            common.print_with_prefix_column(
                common.ICON_WARN,
                Text(str(len(unsupported_cogs)), style="bold"),
                " cogs will remain unsupported after updating:\n",
                Text(", ").join(
                    Text(cog_name, style="bold") for cog_name in sorted(unsupported_cogs)
                ),
            )

    old_python_version = updater_metadata.current_python_version.release[:2]
    new_python_version = updater_metadata.interpreter_version.release[:2]
    if old_python_version != new_python_version:
        common.print_with_prefix_column(
            common.ICON_INFO,
            "Downloader's library folder needs to be regenerated"
            " because the used Python version changed.\n"
            "Choosing to update cogs now will perform this step automatically.",
        )

    update_cogs = updater_metadata.options.update_cogs
    if update_cogs is None:
        if updater_metadata.options.interactive:
            update_cogs = Confirm.ask("Do you want to update all your cogs?", default=True)
        else:
            update_cogs = True
    if update_cogs:
        await _handle_cog_updates(updater_metadata)

    with console.status("Cleaning up..."):
        backup_dir = Path(sys.prefix) / common.OLD_VENV_BACKUP_DIR_NAME
        shutil.rmtree(backup_dir)

    changelog_markdown = changelog.render_markdown(updater_metadata.changelogs)
    if changelog_markdown:
        console.print(Panel(Markdown(changelog_markdown)))

    console.print()
    common.print_with_prefix_column(
        common.ICON_SUCCESS,
        "Update to Red ",
        Text(__version__, style="bold"),
        " has been finished!",
    )

    if changelog_markdown:
        common.print_with_prefix_column(
            common.ICON_INFO,
            'Remember to follow instructions from the "Read before updating" section,'
            " if any were provided.",
        )

    if updater_metadata.backup_dir:
        additional_text = ""
        if not updater_metadata.options.backup_dir:
            additional_text = (
                "\nNote that this is a temporary directory and may eventually get auto-removed"
                " by your system."
            )
        common.print_with_prefix_column(
            common.ICON_INFO,
            "If needed, you can find the backups of the virtual environment"
            " and the instances at: ",
            Text(str(updater_metadata.backup_dir), style="bold"),
            additional_text,
        )


async def _handle_cog_updates(updater_metadata: UpdaterMetadata) -> None:
    cog_compatibility = updater_metadata.cog_compatibility
    console = common.get_console()

    instances = (
        list(cog_compatibility.checked)
        if cog_compatibility is not None
        else updater_metadata.options.instances
    )
    checked_instances = {}
    failed_instances = []
    unsupported_storage_instances = []
    for instance_name in instances:
        if instance_name in updater_metadata.options.excluded_instances:
            continue
        exit_code, stdout = await _call_cog_update(
            instance_name, update_repos=cog_compatibility is None
        )
        if exit_code == _EXIT_INSTANCE_BACKEND_UNSUPPORTED:
            unsupported_storage_instances.append(instance_name)
        elif exit_code == _EXIT_INSTANCE_SITE_PREFIX_MISMATCH:
            pass
        elif exit_code:
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

    if checked_instances:
        for instance_name, stdout in checked_instances.items():
            console.rule(Text(instance_name, style="bold"))
            print(stdout, end="")
        console.rule()

    common.print_with_prefix_column(
        common.ICON_INFO,
        "Finished updating cogs.",
        "\nThe results for each instance are shown above." if checked_instances else "",
    )
    if failed_instances:
        common.print_with_prefix_column(
            common.ICON_ERROR,
            "Failure occurred while trying to perform update for following instances: ",
            Text(", ").join(
                Text(instance_name, style="bold") for instance_name in failed_instances
            ),
            "\nScroll above to find the errors.",
        )
    if unsupported_storage_instances:
        common.print_with_prefix_column(
            common.ICON_INFO,
            "The following instances were skipped as they use a storage backend that is"
            " not supported by the current Red installation (some requirements are missing): ",
            Text(", ").join(
                Text(instance_name, style="bold")
                for instance_name in unsupported_storage_instances
            ),
        )
    if not checked_instances:
        common.print_with_prefix_column(
            common.ICON_INFO,
            "There were no",
            (" other" if failed_instances or unsupported_storage_instances else ""),
            " instances to update cogs for.",
        )


async def _call_cog_update(instance_name: str, *, update_repos: bool) -> Tuple[int, str]:
    debug_args = (cmd.arg_names.DEBUG,) * common.get_log_cli_level()
    args = [
        "-m",
        "redbot._update.internal",
        *debug_args,
        _UPDATE_COGS_CMD_NAME,
        "--",
        instance_name,
    ]
    if update_repos:
        args.append(_UPDATE_REPOS_OPTION_NAME)
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

    proc = await asyncio.create_subprocess_exec(
        sys.executable, *args, env=env, stdout=asyncio.subprocess.PIPE
    )
    stdout_data, _ = await proc.communicate()
    decoded_stdout = stdout_data.decode()
    exit_code = await proc.wait()

    return exit_code, decoded_stdout


@cli.command()
@click.argument("base_executable")
@click.argument("venv_dir", type=click.Path(path_type=Path))
@click.argument("scripts_path", type=click.Path(path_type=Path))
@click.argument("dependency_specifier")
def reinstall(
    base_executable: str, venv_dir: Path, scripts_path: Path, dependency_specifier: str
) -> None:
    assert runner.get_request_output().request_type is runner.RequestType.exec

    console = common.get_console()
    with console.status("Creating a new virtual environment..."):
        subprocess.check_call((base_executable, "-m", "venv", str(venv_dir)))
    console.print("Created a new virtual environment.")
    executable = str(scripts_path / f"python{sysconfig.get_config_var('EXE')}")

    common.print_with_prefix_column(common.ICON_INFO, "Starting the install process...")
    try:
        subprocess.check_call((executable, "-m", "pip", "install", "-U", "pip"))
        subprocess.check_call((executable, "-m", "pip", "install", dependency_specifier))
    except subprocess.CalledProcessError:
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
