import asyncio
import dataclasses
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Set

import click
from packaging.version import Version
from python_discovery import PythonInfo
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text
from typing_extensions import Self

from redbot.core.utils._internal_utils import (
    AvailableVersion,
    detailed_progress,
    fetch_available_red_versions,
    get_installed_extras,
)

from . import changelog, cmd, common, runner
from .cog_compatibility_checker import CompatibilitySummary
from .tui import ChangelogReaderApp, ChangelogReaderResult


@dataclasses.dataclass
class UpdaterOptions:
    """Update options specified by the user."""

    instances: List[str]
    excluded_instances: Set[str]
    ignore_prefix: bool
    backup_dir: Optional[Path]
    no_backup: bool
    red_version: Optional[Version]
    no_major_updates: bool
    no_full_changelog: bool
    no_cog_compatibility_check: bool
    new_python_interpreter: Optional[PythonInfo]
    update_cogs: Optional[bool]
    force_reinstall: bool
    interactive: bool

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        backup_dir = data["backup_dir"]
        red_version = data["red_version"]
        return cls(
            instances=data["instances"],
            excluded_instances=set(data["excluded_instances"]),
            ignore_prefix=data["ignore_prefix"],
            backup_dir=backup_dir and Path(data["backup_dir"]),
            no_backup=data["no_backup"],
            red_version=red_version and Version(red_version),
            no_major_updates=data["no_major_updates"],
            no_full_changelog=data["no_full_changelog"],
            no_cog_compatibility_check=data["no_cog_compatibility_check"],
            new_python_interpreter=(
                data["new_python_interpreter"]
                and PythonInfo.from_dict(data["new_python_interpreter"])
            ),
            update_cogs=data["update_cogs"],
            force_reinstall=data["force_reinstall"],
            interactive=data["interactive"],
        )

    def to_json_dict(self) -> Dict[str, Any]:
        data = dataclasses.asdict(self)
        data["excluded_instances"] = list(self.excluded_instances)
        data["backup_dir"] = self.backup_dir and str(self.backup_dir)
        data["red_version"] = self.red_version and str(self.red_version)
        data["new_python_interpreter"] = (
            self.new_python_interpreter and self.new_python_interpreter.to_dict()
        )
        return data


@dataclasses.dataclass
class UpdaterCompatibilitySummary:
    checked: Dict[str, CompatibilitySummary]
    failed: List[str]
    skipped: List[str]

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(
            checked={
                instance_name: CompatibilitySummary.from_json_dict(results_data)
                for instance_name, results_data in data["checked"].items()
            },
            failed=data["failed"],
            skipped=data["skipped"],
        )

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "checked": {
                instance_name: results.to_json_dict()
                for instance_name, results in self.checked.items()
            },
            "failed": self.failed,
            "skipped": self.skipped,
        }


@dataclasses.dataclass
class BackupResults:
    checked: List[str]
    failed: List[str]
    skipped: List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_json_dict(cls, data: Dict[str, List[str]]) -> Self:
        return cls(checked=data["checked"], failed=data["failed"], skipped=data["skipped"])

    def to_json_dict(self) -> Dict[str, List[str]]:
        return dataclasses.asdict(self)


_PYTHON_VERSION_PLACEHOLDER = Version("0.0.dev0")


@dataclasses.dataclass
class UpdaterMetadata:
    """Metadata about the update process."""

    # options specified by the user
    options: UpdaterOptions
    # info about Red version to update to (latest available or latest non-major update)
    latest: AvailableVersion
    latest_major: AvailableVersion
    # info about Red/Python versions that we're updating from
    current_version: Version = dataclasses.field(default_factory=common.get_current_red_version)
    current_python_version: Version = dataclasses.field(
        default_factory=common.get_current_python_version
    )
    # details about the interpreter that will be used for the new venv
    interpreter_info: PythonInfo = dataclasses.field(default_factory=PythonInfo.current_system)
    interpreter_version: Version = _PYTHON_VERSION_PLACEHOLDER
    interpreter_exe: str = ""
    # changelogs for version in (current_version, latest> range
    changelogs: changelog.Changelogs = dataclasses.field(default_factory=dict)
    # cog compatibility check results
    cog_compatibility: Optional[UpdaterCompatibilitySummary] = None
    # backup info
    to_backup: List[str] = dataclasses.field(default_factory=list)
    backup_dir: Optional[Path] = None
    backup_results: Optional[BackupResults] = None

    def __post_init__(self) -> None:
        if self.interpreter_version is _PYTHON_VERSION_PLACEHOLDER:
            self.interpreter_version = Version(
                ".".join(map(str, self.interpreter_info.version_info[:3]))
            )
        if not self.interpreter_exe:
            self.interpreter_exe = self.interpreter_info.system_executable

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        """
        Make an instance of this class from a dictionary,
        as returned by the `to_json_dict()` method.

        This aims to maintain backwards compatibility with data generated by
        earlier Red versions as it may be called with such data
        after the last update step.
        """
        backup_dir = data.get("backup_dir")
        return cls(
            options=UpdaterOptions.from_json_dict(data["options"]),
            latest=AvailableVersion.from_json_dict(data["latest"]),
            latest_major=AvailableVersion.from_json_dict(data["latest_major"]),
            current_version=Version(data["current_version"]),
            current_python_version=Version(data["current_python_version"]),
            interpreter_version=Version(data["interpreter_version"]),
            interpreter_info=PythonInfo.from_dict(data["interpreter_info"]),
            interpreter_exe=data["interpreter_exe"],
            changelogs={
                Version(raw_version): changelog.VersionChangelog.from_json_dict(raw_changelog)
                for raw_version, raw_changelog in data["changelogs"].items()
            },
            cog_compatibility=UpdaterCompatibilitySummary.from_json_dict(
                data["cog_compatibility"]
            ),
            to_backup=data["to_backup"],
            backup_dir=backup_dir and Path(backup_dir),
            backup_results=BackupResults.from_json_dict(data["backup_results"]),
        )

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "options": self.options.to_json_dict(),
            "latest": self.latest.to_json_dict(),
            "latest_major": self.latest_major.to_json_dict(),
            "current_version": str(self.current_version),
            "current_python_version": str(self.current_python_version),
            "interpreter_version": str(self.interpreter_version),
            "interpreter_info": self.interpreter_info.to_dict(),
            "interpreter_exe": self.interpreter_exe,
            "changelogs": {str(v): c.to_json_dict() for v, c in self.changelogs.items()},
            "cog_compatibility": self.cog_compatibility and self.cog_compatibility.to_json_dict(),
            "to_backup": self.to_backup,
            "backup_dir": self.backup_dir and str(self.backup_dir),
            "backup_results": self.backup_results and self.backup_results.to_json_dict(),
        }

    @property
    def breaking_update(self) -> bool:
        return self.current_version.release[:2] != self.latest.version.release[:2]


class Updater:
    metadata: UpdaterMetadata

    def __init__(self, options: UpdaterOptions) -> None:
        self.options = options
        self.console = common.get_console()

    @property
    def latest(self) -> AvailableVersion:
        return self.metadata.latest

    @property
    def current_version(self) -> Version:
        return self.metadata.current_version

    async def run(self) -> None:
        await self._prepare_metadata()

        new_version_available = self.current_version < self.latest.version
        if not self.options.force_reinstall and not new_version_available:
            if self.current_version >= self.metadata.latest_major.version:
                common.print_with_prefix_column(
                    common.ICON_SUCCESS,
                    "You are already running the latest available version of Red.",
                )
            else:
                common.print_with_prefix_column(
                    common.ICON_INFO,
                    "There are no non-major updates available.\n",
                    "There is a new major version available: ",
                    Text(str(self.metadata.latest_major.version), style="bold"),
                )
            return

        if new_version_available:
            common.print_with_prefix_column(
                common.ICON_SUCCESS,
                "New version available: ",
                Text(str(self.latest.version), style="bold"),
            )

        await self._show_changelog()
        self._check_python_requires()
        if self.options.no_cog_compatibility_check:
            self.console.print(
                "Will not make backups as --no-cog-compatibility-check option was passed."
            )
        else:
            await self._check_cog_compatibility()

        if self.options.no_backup:
            common.print_with_prefix_column(
                common.ICON_INFO, "Will not make backups as --no-backup option was passed."
            )
        else:
            common.print_with_prefix_column(
                common.ICON_INFO,
                "The following instances will be backed up before performing the update: ",
                Text(", ").join(
                    Text(instance_name, style="bold") for instance_name in self.metadata.to_backup
                ),
            )
        if self.metadata.breaking_update:
            self.console.print(
                "[b]Remember that this is a major release and it may have some breaking changes"
                " that the bot or its cogs may be affected by.[/]"
            )
        if self.options.interactive and not Confirm.ask(
            f"Do you want to continue with the update to [b]Red {self.latest.version}[/]?"
        ):
            return
        self.console.print()

        if self.options.no_backup:
            self.console.print("Will not make backups as --no-backup option was passed.")
        else:
            await self._make_backups()

        await self._update_with_fresh_venv()

    async def _prepare_metadata(self) -> None:
        interpreter_info = self.options.new_python_interpreter or PythonInfo.current_system()
        with self.console.status("Checking latest version..."):
            available_versions = await fetch_available_red_versions(
                include_prereleases=common.get_current_red_version().is_prerelease
            )
            latest_major = available_versions[0]

        self.metadata = UpdaterMetadata(
            self.options,
            latest=latest_major,
            latest_major=latest_major,
            interpreter_info=interpreter_info,
        )

        if self.options.red_version:
            if self.options.red_version <= self.current_version:
                common.print_with_prefix_column(
                    common.ICON_ERROR, "You can only update to a newer version of Red."
                )
                raise SystemExit(2)
            if (
                self.options.no_major_updates
                and self.options.red_version.release[:2] != self.current_version.release[:2]
            ):
                common.print_with_prefix_column(
                    common.ICON_ERROR,
                    "Updating to the specified version would be a major update"
                    " but --no-major-updates option was specified.",
                )
                raise SystemExit(2)
            for available_version in available_versions:
                if available_version.version == self.options.red_version:
                    break
            else:
                common.print_with_prefix_column(
                    common.ICON_ERROR, "The provided version does not seem to exist."
                )
                raise SystemExit(2)
            self.metadata.latest = available_version
        elif self.options.no_major_updates:
            for available_version in available_versions:
                if available_version.version.release[:2] == self.current_version.release[:2]:
                    self.metadata.latest = available_version
                    break
            else:
                if self.current_version < latest_major.version:
                    common.print_with_prefix_column(
                        common.ICON_ERROR,
                        "Could not find any version of Red that would not be a major update.",
                    )
                    raise SystemExit(1)

    async def _show_changelog(self) -> None:
        with self.console.status("Fetching changelogs..."):
            changelogs = await changelog.fetch_changelogs()
            self.metadata.changelogs = changelogs = changelog.get_changelogs_between(
                changelogs, self.current_version, self.latest.version
            )
        common.print_with_prefix_column(common.ICON_SUCCESS, "Changelogs fetched.")

        if not changelogs:
            return

        if not self.options.interactive or self.options.no_full_changelog:
            self.console.print(Panel(Markdown(changelog.render_markdown(changelogs))))
            if self.options.interactive and not Confirm.ask("Do you want to continue?"):
                raise click.Abort()
            return

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
        if self.metadata.breaking_update:
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

        viewer = ChangelogReaderApp.from_changelogs(changelogs)
        result = await viewer.run_async()
        if result is None:
            raise RuntimeError("Unexpected state")
        if result is ChangelogReaderResult.QUIT:
            raise click.Abort()

        self.console.print("Changelog has been closed.\n")

    def _check_python_requires(self) -> None:
        if self.metadata.interpreter_version in self.latest.requires_python:
            return
        if self.options.new_python_interpreter:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The latest version of Red requires a different Python version (",
                Text(str(self.latest.requires_python), style="bold"),
                ") from the version of the interpreter passed to with the --new-python-interpreter"
                " option (",
                Text(str(self.metadata.interpreter_version), style="bold"),
                ")",
            )
            raise SystemExit(1)
        common.print_with_prefix_column(
            common.ICON_WARN if self.options.interactive else common.ICON_ERROR,
            "The latest version of Red requires a different Python version (",
            Text(str(self.latest.requires_python), style="bold"),
            ") from the one that you are currently using (",
            Text(str(self.metadata.interpreter_version), style="bold"),
            ")",
            (
                "\nredbot-update will have to recreate the virtual environment"
                " with a compatible version of Python."
                if self.options.interactive
                else ""
            ),
        )
        if not self.options.interactive:
            raise SystemExit(1)
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
                info = PythonInfo.from_exe(response)
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
                self.metadata.interpreter_version = interpreter_version
                self.metadata.interpreter_info = info
                self.metadata.interpreter_exe = info.executable
            else:
                (
                    self.metadata.interpreter_exe,
                    self.metadata.interpreter_version,
                    self.metadata.interpreter_info,
                ) = interpreters[result - 1]

            self.console.print(
                "\n[b]You selected:[/]",
                _render_interpreter(
                    self.metadata.interpreter_exe, self.metadata.interpreter_version
                ),
            )
            if Confirm.ask("Do you want to continue with this choice?"):
                self.console.print()
                break

    async def _check_cog_compatibility(self) -> None:
        outputs = {}
        checked_instances = {}
        skipped_instances = []
        failed_instances = []
        unsupported_storage_instances = []
        for instance_name in self.options.instances:
            if instance_name in self.options.excluded_instances:
                skipped_instances.append(instance_name)
                continue
            exit_code, stdout, results = await cmd.cog_compatibility.call(
                instance_name,
                red_version=self.latest.version,
                python_version=self.metadata.interpreter_version,
                ignore_prefix=self.options.ignore_prefix,
                return_results=True,
                stdout=asyncio.subprocess.PIPE,
            )
            if exit_code == cmd.cog_compatibility.EXIT_INSTANCE_BACKEND_UNSUPPORTED:
                skipped_instances.append(instance_name)
                unsupported_storage_instances.append(instance_name)
            elif exit_code == cmd.cog_compatibility.EXIT_INSTANCE_SITE_PREFIX_MISMATCH:
                skipped_instances.append(instance_name)
            elif exit_code:
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
                assert results is not None
                outputs[instance_name] = stdout
                checked_instances[instance_name] = results
            if stdout:
                self.console.print()
        self.console.print()
        if not self.options.no_backup:
            self.metadata.to_backup = [*checked_instances, *failed_instances]

        if outputs:
            for instance_name, stdout in outputs.items():
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
                " instances to check cog compatibility for.",
            )
        self.console.print()

        self.metadata.cog_compatibility = UpdaterCompatibilitySummary(
            checked=checked_instances, failed=failed_instances, skipped=skipped_instances
        )

    async def _make_backups(self) -> None:
        self.metadata.backup_dir = backup_dir = self.options.backup_dir or Path(
            tempfile.mkdtemp(prefix="redbot-update-backup-")
        )
        console = common.get_console()
        console.print("Backups will be created at:", Text(str(backup_dir), style="bold"))
        venv_archive = backup_dir / "venv.tar.gz"
        with console.status("Making a backup of the virtual environment directory..."):
            venv_dir = Path(sys.prefix)
            venv_files = []
            for current_dir, _, filenames in os.walk(venv_dir):
                target_dir = os.path.relpath(current_dir, venv_dir)
                if target_dir == ".":
                    target_dir = ""
                for name in filenames:
                    venv_files.append(
                        (os.path.join(current_dir, name), os.path.join(target_dir, name))
                    )
            with tarfile.open(venv_archive, "w:gz", compresslevel=6) as tar:
                with detailed_progress(unit="files") as progress:
                    for src, arcname in progress.track(venv_files, description="Compressing..."):
                        tar.add(src, arcname=arcname, recursive=False)
        console.print(
            "Created a backup of the virtual environment directory at:",
            Text(str(venv_archive), style="bold"),
        )

        checked = []
        failed = []
        instance_backups_dir = backup_dir / "instance_backups"
        instance_backups_dir.mkdir()
        for instance_name in self.metadata.to_backup:
            console.print(
                "Making a backup of the", Text(instance_name, style="bold"), "instance..."
            )
            debug_args = (cmd.arg_names.DEBUG,) * common.get_log_cli_level()
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "redbot.setup",
                "backup",
                *debug_args,
                instance_name,
                str(instance_backups_dir),
            )
            if await proc.wait():
                failed.append(instance_name)
            else:
                checked.append(instance_name)

        self.metadata.backup_results = BackupResults(checked=checked, failed=failed)
        if self.metadata.cog_compatibility:
            self.metadata.backup_results.skipped.extend(self.metadata.cog_compatibility.skipped)

        if failed:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The following instances failed during backup: ",
                Text(", ").join(Text(instance_name, style="bold") for instance_name in failed),
                "\nScroll above to find the errors.",
            )
            # If a backup fails, we cannot allow non-interactive update to continue.
            # The user can choose to use options such as `--no-backup`, `--instance`,
            # and `--exclude-instance` to not have the backup step try to backup something
            # that it can't.
            if not self.options.interactive or not Confirm.ask(
                "Do you want to continue with the update regardless?"
            ):
                raise SystemExit(1)

    async def _update_with_fresh_venv(self) -> NoReturn:
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

        with console.status("Determining extras to install..."):
            try:
                metadata = await self.latest.fetch_core_metadata()
            except TypeError:
                extras = get_installed_extras()
            else:
                known_extras = metadata.provides_extra or []
                extras = [extra for extra in get_installed_extras() if extra in known_extras]
        console.print("Extras to install have been determined.")

        old_executable = Path(sys.executable)
        rel_executable = old_executable.relative_to(venv_dir)
        new_executable = backup_dir / rel_executable
        wrapper_exe = runner.get_wrapper_executable()

        with console.status("Moving old virtual environment..."):
            for path in venv_dir.iterdir():
                if path == backup_dir or path == wrapper_exe:
                    continue
                path.rename(backup_dir / path.name)
        console.print("Old virtual environment moved.")

        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", prefix="redbot-update-metadata-", suffix=".json", delete=False
        ) as metadata_file:
            json.dump(self.metadata.to_json_dict(), metadata_file)

        console.print()
        runner.make_exec_request(
            str(new_executable),
            "reinstall",
            # base executable for venv creation
            self.metadata.interpreter_exe,
            # venv dir
            str(venv_dir),
            # scripts path
            self.metadata.interpreter_info.sysconfig_path("scripts", {"base": str(venv_dir)}),
            # Red dependency specifier
            common.get_red_dependency_specifier(self.latest.version, extras),
            set_env_vars={common.INTERNAL_UPDATER_METADATA_ENV_VAR: metadata_file.name},
        )


def get_updater_metadata() -> UpdaterMetadata:
    with open(os.environ[common.INTERNAL_UPDATER_METADATA_ENV_VAR], encoding="utf-8") as fp:
        return UpdaterMetadata.from_json_dict(json.load(fp))
