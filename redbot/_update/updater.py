import asyncio
import dataclasses
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, NoReturn, Optional, Set

import click
from packaging.version import Version
from python_discovery import PythonInfo
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text

from redbot.core.utils._internal_utils import AvailableVersion, fetch_latest_red_version

from . import changelog, cmd, common, runner
from .tui import ChangelogReaderApp, ChangelogReaderResult


@dataclasses.dataclass
class UpdaterOptions:
    instances: List[str]
    excluded_instances: Set[str]
    ignore_prefix: bool
    backup_dir: Optional[Path]
    no_backup: bool


class Updater:
    latest: AvailableVersion

    def __init__(self, options: UpdaterOptions) -> None:
        self.options = options
        self.console = common.get_console()
        self.current_version = common.get_current_red_version()
        self.current_python_version = common.get_current_python_version()
        self.interpreter_version = self.current_python_version
        self.interpreter_info = PythonInfo.current_system()
        self.interpreter_exe = self.interpreter_info.system_executable
        self.to_backup = [] if self.options.no_backup else list(common.INSTANCE_LIST)

    @property
    def breaking_update(self) -> bool:
        return self.current_version.release[:2] != self.latest.version.release[:2]

    async def run(self) -> None:
        with self.console.status("Checking latest version..."):
            self.latest = await fetch_latest_red_version()

        if self.current_version >= self.latest.version:
            common.print_with_prefix_column(
                common.ICON_SUCCESS,
                "You are already running the latest available version of Red.",
            )
            return

        common.print_with_prefix_column(
            common.ICON_SUCCESS,
            Text("New version available: ").append(str(self.latest.version), style="bold"),
        )

        await self._show_changelog()
        self._check_python_requires()
        await self._check_cog_compatiblity()

        if self.options.no_backup:
            common.print_with_prefix_column(
                common.ICON_INFO, "Will not make backups as --no-backup option was passed."
            )
        else:
            common.print_with_prefix_column(
                common.ICON_INFO,
                "The following instances will be backed up before performing the update: ",
                Text(", ").join(
                    Text(instance_name, style="bold") for instance_name in self.to_backup
                ),
            )
        if self.breaking_update:
            self.console.print(
                "[b]Remember that this is a major release and it may have some breaking changes"
                " that the bot or its cogs may be affected by.[/]"
            )
        if not Confirm.ask(
            f"Do you want to continue with the update to [b]Red {self.latest.version}[/]?"
        ):
            return
        self.console.print()

        if self.options.no_backup:
            self.console.print("Will not make backups as --no-backup option was passed.")
        else:
            await self._make_backups()

        self._update_with_fresh_venv()

    async def _show_changelog(self) -> None:
        with self.console.status("Fetching changelogs..."):
            changelogs = await changelog.fetch_changelogs()
            changelogs = changelog.get_changelogs_newer_than(changelogs, self.current_version)
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
        if self.breaking_update:
            parts.append(
                f"[bold]{common.ICON_WARN}"
                "  Please note that this is a major release and it may have some changes that"
                " your bot or its cogs are affected by.[/bold]\n"
            )
        parts.append(
            "After the changelog is open and you're ready to continue, hit the [b]Q[/] key"
            " to close the changelog and continue the update process.\n\n"
            "Hit the [b]Enter[/] key to view the changelog."
        )
        self.console.input(Panel("".join(parts)), password=True)

        viewer = ChangelogReaderApp(changelog.render_markdown(changelogs))
        result = await viewer.run_async()
        if result is None:
            raise RuntimeError("Unexpected state")
        if result is ChangelogReaderResult.QUIT:
            raise click.Abort()

        self.console.print("Changelog has been closed.\n")

    def _check_python_requires(self) -> None:
        if self.current_python_version in self.latest.requires_python:
            return
        common.print_with_prefix_column(
            common.ICON_WARN,
            "The latest version of Red requires a different Python version (",
            Text(str(self.latest.requires_python), style="bold"),
            ") from the one that you are currently using (",
            Text(str(self.current_python_version), style="bold"),
            ")\nredbot-update will have to recreate the virtual environment"
            " with a compatible version of Python.",
        )
        interpreters = common.search_for_interpreters(self.latest.requires_python)

        def _render_interpreter(interpreter_exe: str, interpreter_version: Version) -> Text:
            return Text.assemble(
                "CPython ",
                (str(interpreter_version), "repr.number"),
                " (",
                (interpreter_exe, "log.path"),
                ")",
            )

        text = Text("Found the following compatible Python interpreters on your system:")
        for idx, (interpreter_exe, interpreter_version, python_info) in enumerate(interpreters, 1):
            text.append_text(Text(f"\n{idx}. ", style="markdown.item.number"))
            text.append_text(_render_interpreter(interpreter_exe, interpreter_version))
        self.console.print(Panel(text))

        while True:
            result = IntPrompt.ask(
                "\nEnter the number of the Python interpreter above that you want to use"
                " or type 0 to input the path to it yourself. Generally, you should choose"
                " the interpreter with the latest version on the above list.\n"
                "Enter your selection",
                default=1,
            )
            if result < 0 or result > len(interpreters):
                self.console.print("[prompt.invalid] This is not a valid choice.")
                continue

            if result == 0:
                response = Prompt.ask(
                    "Please input the path to the Python interpreter that you want to use"
                )
                if not response:
                    self.console.print("[prompt.invalid] No path was provided.")
                    continue
                info = PythonInfo.from_exe(response, raise_on_error=True)
                interpreter_version = Version(info.version_str)
                if (
                    info.implementation != "CPython"
                    or interpreter_version not in self.latest.requires_python
                ):
                    self.console.print(
                        "[prompt.invalid] The provided path points to an incompatible Python"
                        " interpreter. Latest version requires CPython"
                        f" {self.latest.requires_python} but the provided interpreter is"
                        f" {info.implementation} {interpreter_version}."
                    )
                    continue
                self.interpreter_version = interpreter_version
                self.interpreter_info = info
                self.interpreter_exe = info.executable
            else:
                (
                    self.interpreter_exe,
                    self.interpreter_version,
                    self.interpreter_info,
                ) = interpreters[result - 1]

            self.console.print(
                "\n[b]You selected:[/]",
                _render_interpreter(self.interpreter_exe, self.interpreter_version),
            )
            if Confirm.ask("Do you want to continue with this choice?"):
                self.console.print()
                break

    async def _check_cog_compatiblity(self) -> None:
        checked_instances = {}
        failed_instances = []
        for instance_name in self.options.instances:
            if instance_name in self.options.excluded_instances:
                continue
            exit_code, stdout = await cmd.cog_compatibility.call(
                instance_name,
                red_version=self.latest.version,
                python_version=self.interpreter_version,
                ignore_prefix=self.options.ignore_prefix,
                internal=True,
                stdout=asyncio.subprocess.PIPE,
            )
            if exit_code != cmd.cog_compatibility.EXIT_INSTANCE_SITE_PREFIX_MISMATCH:
                if exit_code:
                    failed_instances.append(instance_name)
                    print(stdout, end="")
                    Text.assemble(
                        "\N{UPWARDS ARROW} " * 3,
                        "Failure for ",
                        (instance_name, "bold"),
                        " instance",
                    )
                    self.console.rule(
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
                self.console.print()
        self.console.print()
        if not self.options.no_backup:
            self.to_backup = [*checked_instances, *failed_instances]

        if checked_instances:
            for instance_name, stdout in checked_instances.items():
                self.console.rule(Text(instance_name, style="bold"))
                print(stdout, end="")
            self.console.rule()

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
        self.console.print()

    async def _make_backups(self) -> Path:
        backup_dir = self.options.backup_dir or Path(
            tempfile.mkdtemp(prefix="redbot-update-backup-")
        )
        console = common.get_console()
        console.print("Backups will be created at:", Text(str(backup_dir), style="bold"))
        venv_backup_dir = backup_dir / "redenv"
        with console.status("Making a backup of the virtual environment directory..."):
            venv_dir = Path(sys.prefix)
            shutil.copytree(venv_dir, venv_backup_dir, symlinks=True)
        console.print(
            "Created a backup of the virtual environment directory at:",
            Text(str(venv_backup_dir), style="bold"),
        )

        failed = []
        for instance_name in self.to_backup:
            console.print(
                "Making a backup of the", Text(instance_name, style="bold"), "instance..."
            )
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "redbot.setup", "backup", instance_name, str(backup_dir)
            )
            if await proc.wait():
                failed.append(instance_name)

        if failed:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The following instances failed during backup: ",
                Text(", ").join(Text(instance_name, style="bold") for instance_name in failed),
                "\nScroll above to find the errors.",
            )
            if not Confirm.ask("Do you want to continue with the update regardless?"):
                raise SystemExit(1)

        return backup_dir

    def _update_with_fresh_venv(self) -> NoReturn:
        console = common.get_console()
        venv_dir = Path(sys.prefix)
        backup_dir = venv_dir / common.OLD_VENV_BACKUP_DIR_NAME
        try:
            backup_dir.mkdir()
        except FileExistsError:
            console.print(
                "Found that a partial backup of a virtual environment from a past failed update"
                " exists at",
                Text(str(backup_dir), style="bold"),
                "\nThe update will not proceed to avoid overriding it. If you are certain that"
                " you don't need to restore anything from it, remove it and try updating again.",
            )
            raise SystemExit(1)

        old_executable = Path(sys.executable)
        rel_executable = old_executable.relative_to(venv_dir)
        new_executable = backup_dir / rel_executable
        wrapper_exe = runner.get_wrapper_executable()

        for path in venv_dir.iterdir():
            if path == backup_dir or path == wrapper_exe:
                continue
            path.rename(backup_dir / path.name)

        console.print()
        runner.make_exec_request(
            str(new_executable),
            "reinstall",
            # base executable for venv creation
            self.interpreter_exe,
            # venv dir
            str(venv_dir),
            # scripts path
            self.interpreter_info.sysconfig_path("scripts", {"base": str(venv_dir)}),
            # Red dependency specifier
            common.get_red_dependency_specifier(self.latest.version),
        )
