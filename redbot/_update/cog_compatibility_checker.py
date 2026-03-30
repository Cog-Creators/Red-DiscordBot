import dataclasses
import functools
import os
import sys
from typing import Iterable, Optional, Set

import rich
from packaging.version import Version
from rich.text import Text
from redbot.core import _downloader, _drivers, data_manager
from redbot.core._cli import parse_cli_flags
from redbot.core.bot import Red
from redbot.core.utils._internal_utils import detailed_progress

from . import common


class InstanceSitePrefixMismatchError(Exception):
    """The instance's last known sys.prefix is different from the current one."""

    def __init__(self, instance_name: str, last_known_prefix: Optional[str]) -> None:
        self.instance_name = instance_name
        self.last_known_prefix = last_known_prefix
        super().__init__(
            f"The last known sys.prefix of {instance_name!r} is different from"
            " current process's sys.prefix.",
        )


@dataclasses.dataclass(frozen=True)
class CompatibilityResults:
    latest_version: Version
    interpreter_version: Version

    explicitly_supported: Set[_downloader.Installable]
    potentially_supported: Set[_downloader.Installable]
    incompatible_python: Set[_downloader.Installable]
    incompatible_red: Set[_downloader.Installable]

    def print(self) -> None:
        major_version = Text(f"{self.latest_version.major}.{self.latest_version.minor}")
        if self.explicitly_supported:
            common.print_with_prefix_column(
                common.ICON_SUCCESS,
                "The following cogs are explicitly marked as supporting Red ",
                major_version,
                ":\n",
                Text(", ").join(Text(cog.name, style="bold") for cog in self.explicitly_supported),
            )
        if self.potentially_supported:
            common.print_with_prefix_column(
                common.ICON_WARN,
                "The following cogs may support Red ",
                major_version,
                " but they haven't been explicitly marked as such:\n",
                Text(", ").join(
                    Text(cog.name, style="bold") for cog in self.potentially_supported
                ),
            )
        if self.incompatible_red:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The following cogs do not support Red ",
                Text(str(self.latest_version)),
                ":\n",
                Text(", ").join(Text(cog.name, style="bold") for cog in self.incompatible_red),
            )
        if self.incompatible_python:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The following cogs do not support Python ",
                Text(str(self.interpreter_version)),
                ":\n",
                Text(", ").join(Text(cog.name, style="bold") for cog in self.incompatible_python),
            )
        if not self.explicitly_supported and (
            self.potentially_supported or self.incompatible_red or self.incompatible_python
        ):
            common.print_with_prefix_column(
                common.ICON_INFO,
                "None of the checked cogs were explicitly marked as supporting Red ",
                major_version,
                ".",
            )


class CogCompatibilityChecker:
    def __init__(
        self,
        bot: Red,
        *,
        latest_version: Version,
        interpreter_version: Version,
        ignore_prefix: bool = False,
    ) -> None:
        self.bot = bot
        self.latest_version = latest_version
        self.interpreter_version = interpreter_version
        self.ignore_prefix = ignore_prefix
        self._console = common.get_console(stderr=True)
        self._stdout_console = common.get_console()

    @functools.cached_property
    def current_version(self) -> Version:
        return common.get_current_red_version()

    async def check(self) -> None:
        instance_name = data_manager.instance_name()
        if not self.ignore_prefix:
            last_known_prefix = await self.bot._config.last_system_info.python_prefix()
            same_install = False
            if last_known_prefix is not None:
                try:
                    same_install = os.path.samefile(last_known_prefix, sys.prefix)
                except OSError:
                    pass
            if not same_install:
                raise InstanceSitePrefixMismatchError(instance_name, last_known_prefix)

        common.print_with_prefix_column(
            common.ICON_INFO,
            "Started checking cog compatibility for the ",
            Text(instance_name, style="bold"),
            " instance.",
            console=self._console,
        )
        status = Text.assemble(
            "Checking compatibility of cogs installed on the ",
            (instance_name, "bold"),
            " instance...",
        )
        with self._console.status(status):
            await _downloader._init_without_bot(self.bot._cog_mgr)

            await self._update_repos()

            installed_cogs = await _downloader.installed_cogs()
            repo_unknown = []
            to_check = set()

            for cog in installed_cogs:
                if cog.repo is None:
                    repo_unknown.append(cog)
                else:
                    to_check.add(cog)

            with self._console.status("Checking available cog updates..."):
                update_check_result = await _downloader.check_cog_updates(
                    cogs=to_check,
                    update_repos=False,
                    env=_downloader.Environment(
                        red_version=self.latest_version, python_version=self.interpreter_version
                    ),
                )
            self._console.print("Available cog updates checked.")

            compatibility_results = self._evaluate_compatibility(to_check, update_check_result)

        common.print_with_prefix_column(
            common.ICON_INFO,
            "Finished checking cog compatibility for the ",
            Text(instance_name, style="bold"),
            " instance.",
            console=self._console,
        )

        self._stdout_console.print()
        compatibility_results.print()

    async def _update_repos(self) -> None:
        with detailed_progress(unit="repos", console=self._console) as progress:
            task_id = progress.add_task(
                "Updating repos", total=len(_downloader._repo_manager.repos)
            )
            updated_count = 0
            already_up_to_date_count = 0
            failed_count = 0
            for idx, repo in enumerate(_downloader._repo_manager.repos):
                progress.update(task_id, completed=idx, description=f"Updating {repo.name!r} repo")
                try:
                    old, new = await repo.update()
                except _downloader.errors.UpdateError:
                    common.print_with_prefix_column(
                        common.ICON_WARN,
                        "Could not update repo ",
                        Text(repo.name, style="bold"),
                        ", the results for cogs from it may be inaccurate.",
                        console=self._console,
                    )
                    failed_count += 1
                else:
                    if old != new:
                        updated_count += 1
                        self._console.print("Updated repo", Text(repo.name, style="bold"))
                    else:
                        already_up_to_date_count += 1
                        self._console.print(
                            "Repo", Text(repo.name, style="bold"), "is already up-to-date."
                        )

        self._stdout_console.print(
            f"Successfully updated {updated_count} repos, failed to update {failed_count} repos.\n"
            f"{already_up_to_date_count} repos were already up-to-date.",
            highlight=True,
        )

    def _evaluate_compatibility(
        self,
        to_check: Iterable[_downloader.Installable],
        update_check_result: _downloader.CogUpdateCheckResult,
    ) -> CompatibilityResults:
        not_updatable = set(to_check)
        latest_version = self.latest_version
        breaking_update = self.current_version.release[:2] != latest_version.release[:2]

        # Explicitly unsupported cogs. Note that when a cog can be updated
        # and its up-to-date version does not support the Red version we're updating to,
        # we don't check whether currently installed version of the cog supports that Red version.
        # This is intentional - we want to allow cog creators to mark something incompatible
        # after the fact.
        incompatible_python = set(update_check_result.incompatible_python_version)
        incompatible_red = set(update_check_result.incompatible_bot_version)

        explicitly_supported = set()
        potentially_supported = set()

        def _handle_cog(cog: _downloader.Installable) -> None:
            if not breaking_update:
                # If we're not performing an update from 3.x -> 3.y, we have no reason
                # to check anything here.
                explicitly_supported.add(cog)
            elif latest_version.release[:2] in (
                cog.min_bot_version.release[:2],
                cog.max_bot_version.release[:2],
            ):
                # If cog creator explicitly set min/max_bot_version to 3.x.y,
                # then 3.x is explicitly supported.
                explicitly_supported.add(cog)
            elif f"red-{latest_version.major}-{latest_version.minor}-ready" in cog.tags:
                # If cog creator explicitly added a "red-3.x-ready" tag,
                # then 3.x is explicitly supported.
                # This is similar to the meaning of "Programming Language :: Python :: 3.x"
                # classifiers in Python packaging.
                explicitly_supported.add(cog)
            else:
                # If we don't have any explicit signals from the cog's metadata that
                # Red 3.x is supported, the cog is only *potentially* supported by that version.
                potentially_supported.add(cog)

        not_updatable -= incompatible_python
        not_updatable -= incompatible_red

        for cog in update_check_result.updatable_cogs:
            not_updatable.discard(cog)
            _handle_cog(cog)

        # not_updatable should now only have cogs that were not updateable.
        for cog in not_updatable:
            _handle_cog(cog)

        return CompatibilityResults(
            latest_version=latest_version,
            interpreter_version=self.interpreter_version,
            explicitly_supported=explicitly_supported,
            potentially_supported=potentially_supported,
            incompatible_python=incompatible_python,
            incompatible_red=incompatible_red,
        )


async def check_instance(
    instance: str,
    *,
    latest_version: Version,
    interpreter_version: Version,
    ignore_prefix: bool = False,
) -> None:
    data_manager.load_basic_configuration(instance)
    red = Red(cli_flags=parse_cli_flags([instance]))
    driver_cls = _drivers.get_driver_class()
    await driver_cls.initialize(**data_manager.storage_details())
    try:
        checker = CogCompatibilityChecker(
            red,
            latest_version=latest_version,
            interpreter_version=interpreter_version,
            ignore_prefix=ignore_prefix,
        )
        await checker.check()
    finally:
        await driver_cls.teardown()
