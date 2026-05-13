import dataclasses
import enum
import functools
import itertools
import os
import sys
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Set, Tuple

import rich
from packaging.version import Version
from rich.text import Text
from typing_extensions import Self

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


class SimpleCompatibilityStatus(common.OrderedEnum):
    UNSUPPORTED = enum.auto()
    POTENTIALLY_SUPPORTED = enum.auto()
    EXPLICITLY_SUPPORTED = enum.auto()


class CompatibilityStatus(enum.Enum):
    # unsupported is <100, 200)
    UNSUPPORTED_PYTHON_VERSION = 100
    UNSUPPORTED_BOT_VERSION = 101
    # potentially supported is <200, 300)
    POTENTIALLY_SUPPORTED = 200
    # explicitly supported is <300, 400)
    EXPLICITLY_SUPPORTED_NON_BREAKING = 300
    EXPLICITLY_SUPPORTED_MIN_BOT_VERSION = 301
    EXPLICITLY_SUPPORTED_MAX_BOT_VERSION = 302
    EXPLICITLY_SUPPORTED_READY_TAG = 303

    @property
    def simple_status(self) -> SimpleCompatibilityStatus:
        if self.unsupported:
            return SimpleCompatibilityStatus.UNSUPPORTED
        if self.potentially_supported:
            return SimpleCompatibilityStatus.POTENTIALLY_SUPPORTED
        if self.explicitly_supported:
            return SimpleCompatibilityStatus.EXPLICITLY_SUPPORTED
        raise RuntimeError("unreachable")

    @property
    def unsupported(self) -> bool:
        return 100 <= self.value < 200

    @property
    def potentially_supported(self) -> bool:
        return 200 <= self.value < 300

    @property
    def explicitly_supported(self) -> bool:
        return 300 <= self.value < 400

    def __ge__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.simple_status >= other.simple_status
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.simple_status > other.simple_status
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.simple_status <= other.simple_status
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.simple_status < other.simple_status
        return NotImplemented


@dataclasses.dataclass
class CogCompatibilityInfo:
    name: str
    repo_name: str
    min_bot_version: Version
    max_bot_version: Version
    min_python_version: Version
    tags: Tuple[str, ...]
    compatibility_status: CompatibilityStatus = CompatibilityStatus.POTENTIALLY_SUPPORTED

    @classmethod
    def from_installable(cls, installable: _downloader.Installable) -> Self:
        return cls(
            name=installable.name,
            repo_name=installable.repo_name,
            min_bot_version=installable.min_bot_version,
            max_bot_version=installable.max_bot_version,
            min_python_version=installable.min_python_version,
            tags=installable.tags,
        )

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(
            name=data["name"],
            repo_name=data["repo_name"],
            min_bot_version=Version(data["min_bot_version"]),
            max_bot_version=Version(data["max_bot_version"]),
            min_python_version=Version(data["min_python_version"]),
            tags=tuple(data["tags"]),
            compatibility_status=CompatibilityStatus(data["compatibility_status"]),
        )

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "repo_name": self.repo_name,
            "min_bot_version": str(self.min_bot_version),
            "max_bot_version": str(self.max_bot_version),
            "min_python_version": str(self.min_python_version),
            "tags": self.tags,
            "compatibility_status": self.compatibility_status.value,
        }


CogSupportDict = Dict[str, CogCompatibilityInfo]


@dataclasses.dataclass(frozen=True)
class CompatibilityResults(Mapping[str, CogCompatibilityInfo]):
    latest_version: Version
    interpreter_version: Version

    explicitly_supported: CogSupportDict = dataclasses.field(default_factory=dict)
    potentially_supported: CogSupportDict = dataclasses.field(default_factory=dict)
    incompatible_python_version: CogSupportDict = dataclasses.field(default_factory=dict)
    incompatible_bot_version: CogSupportDict = dataclasses.field(default_factory=dict)

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(
            latest_version=Version(data["latest_version"]),
            interpreter_version=Version(data["interpreter_version"]),
            explicitly_supported={
                cog_name: CogCompatibilityInfo.from_json_dict(info_data)
                for cog_name, info_data in data["explicitly_supported"].items()
            },
            potentially_supported={
                cog_name: CogCompatibilityInfo.from_json_dict(info_data)
                for cog_name, info_data in data["potentially_supported"].items()
            },
            incompatible_python_version={
                cog_name: CogCompatibilityInfo.from_json_dict(info_data)
                for cog_name, info_data in data["incompatible_python_version"].items()
            },
            incompatible_bot_version={
                cog_name: CogCompatibilityInfo.from_json_dict(info_data)
                for cog_name, info_data in data["incompatible_bot_version"].items()
            },
        )

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "latest_version": str(self.latest_version),
            "interpreter_version": str(self.interpreter_version),
            "explicitly_supported": {
                cog_name: info.to_json_dict()
                for cog_name, info in self.explicitly_supported.items()
            },
            "potentially_supported": {
                cog_name: info.to_json_dict()
                for cog_name, info in self.potentially_supported.items()
            },
            "incompatible_python_version": {
                cog_name: info.to_json_dict()
                for cog_name, info in self.incompatible_python_version.items()
            },
            "incompatible_bot_version": {
                cog_name: info.to_json_dict()
                for cog_name, info in self.incompatible_bot_version.items()
            },
        }

    def __getitem__(self, key: str) -> CogCompatibilityInfo:
        for data in (
            self.explicitly_supported,
            self.potentially_supported,
            self.incompatible_python_version,
            self.incompatible_bot_version,
        ):
            try:
                return data[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return itertools.chain(
            self.explicitly_supported.keys(),
            self.potentially_supported.keys(),
            self.incompatible_python_version.keys(),
            self.incompatible_bot_version.keys(),
        )

    def __len__(self) -> int:
        count = 0
        for data in (
            self.explicitly_supported,
            self.potentially_supported,
            self.incompatible_python_version,
            self.incompatible_bot_version,
        ):
            count += len(data)
        return count

    def __bool__(self) -> bool:
        return any(
            (
                self.explicitly_supported,
                self.potentially_supported,
                self.incompatible_python_version,
                self.incompatible_bot_version,
            )
        )

    def print(self) -> None:
        major_version = Text(f"{self.latest_version.major}.{self.latest_version.minor}")
        if self.explicitly_supported:
            common.print_with_prefix_column(
                common.ICON_SUCCESS,
                "The following cogs are explicitly marked as supporting Red ",
                major_version,
                ":\n",
                Text(", ").join(Text(cog, style="bold") for cog in self.explicitly_supported),
            )
        if self.potentially_supported:
            common.print_with_prefix_column(
                common.ICON_WARN,
                "The following cogs may support Red ",
                major_version,
                " but they haven't been explicitly marked as such:\n",
                Text(", ").join(Text(cog, style="bold") for cog in self.potentially_supported),
            )
        if self.incompatible_bot_version:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The following cogs do not support Red ",
                Text(str(self.latest_version)),
                ":\n",
                Text(", ").join(Text(cog, style="bold") for cog in self.incompatible_bot_version),
            )
        if self.incompatible_python_version:
            common.print_with_prefix_column(
                common.ICON_ERROR,
                "The following cogs do not support Python ",
                Text(str(self.interpreter_version)),
                ":\n",
                Text(", ").join(
                    Text(cog, style="bold") for cog in self.incompatible_python_version
                ),
            )
        if not self.explicitly_supported and (
            self.potentially_supported
            or self.incompatible_bot_version
            or self.incompatible_python_version
        ):
            common.print_with_prefix_column(
                common.ICON_INFO,
                "None of the checked cogs were explicitly marked as supporting Red ",
                major_version,
                ".",
            )


@dataclasses.dataclass(frozen=True)
class CompatibilitySummary:
    instance_name: str
    before_update: CompatibilityResults
    after_update: CompatibilityResults

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(
            instance_name=data["instance_name"],
            before_update=CompatibilityResults.from_json_dict(data["before_update"]),
            after_update=CompatibilityResults.from_json_dict(data["after_update"]),
        )

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "instance_name": self.instance_name,
            "before_update": self.before_update.to_json_dict(),
            "after_update": self.after_update.to_json_dict(),
        }


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

    async def check(self) -> CompatibilitySummary:
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

            summary = CompatibilitySummary(
                instance_name=instance_name,
                before_update=self._evaluate_before_update_compatibility(to_check),
                after_update=self._evaluate_after_update_compatibility(
                    to_check, update_check_result
                ),
            )

        common.print_with_prefix_column(
            common.ICON_INFO,
            "Finished checking cog compatibility for the ",
            Text(instance_name, style="bold"),
            " instance.",
            console=self._console,
        )

        self._stdout_console.print()

        # Note that when a cog can be updated
        # and its up-to-date version does not support the Red version we're updating to,
        # we don't check whether currently installed version of the cog supports that Red version.
        # This is intentional - we want to allow cog creators to mark something incompatible
        # after the fact.
        summary.after_update.print()

        return summary

    async def _update_repos(self) -> None:
        with detailed_progress(unit="repos", console=self._console) as progress:
            task_id = progress.add_task(
                "Updating repos", total=len(_downloader._repo_manager.repos)
            )
            updated_count = 0
            already_up_to_date_count = 0
            failed_count = 0
            for repo in _downloader._repo_manager.repos:
                progress.update(task_id, description=f"Updating {repo.name!r} repo")
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
                progress.advance(task_id)

        self._stdout_console.print(
            f"Successfully updated {updated_count} repos, failed to update {failed_count} repos.\n"
            f"{already_up_to_date_count} repos were already up-to-date.",
            highlight=True,
        )

    def _fill_compatibility_results(
        self, results: CompatibilityResults, cogs: Iterable[_downloader.Installable]
    ) -> None:
        latest_version = self.latest_version
        interpreter_version = self.interpreter_version
        breaking_update = self.current_version.release[:2] != self.latest_version.release[:2]

        for cog in cogs:
            info = CogCompatibilityInfo.from_installable(cog)
            if cog.min_python_version > interpreter_version:
                info.compatibility_status = CompatibilityStatus.UNSUPPORTED_PYTHON_VERSION
                results.incompatible_python_version[cog.name] = info
            elif cog.min_bot_version > latest_version or (
                # max version should be ignored when it's lower than min version
                cog.min_bot_version <= cog.max_bot_version
                and cog.max_bot_version < latest_version
            ):
                info.compatibility_status = CompatibilityStatus.UNSUPPORTED_BOT_VERSION
                results.incompatible_bot_version[cog.name] = info
            elif not breaking_update:
                info.compatibility_status = CompatibilityStatus.EXPLICITLY_SUPPORTED_NON_BREAKING
                results.explicitly_supported[cog.name] = info
            elif latest_version.release[:2] == cog.min_bot_version.release[:2]:
                # If cog creator explicitly set min_bot_version to 3.x.y,
                # then 3.x is explicitly supported.
                info.compatibility_status = (
                    CompatibilityStatus.EXPLICITLY_SUPPORTED_MIN_BOT_VERSION
                )
                results.explicitly_supported[cog.name] = info
            elif latest_version.release[:2] == cog.max_bot_version.release[:2]:
                # If cog creator explicitly set max_bot_version to 3.x.y,
                # then 3.x is explicitly supported.
                info.compatibility_status = (
                    CompatibilityStatus.EXPLICITLY_SUPPORTED_MAX_BOT_VERSION
                )
                results.explicitly_supported[cog.name] = info
            elif f"red-{latest_version.major}-{latest_version.minor}-ready" in cog.tags:
                # If cog creator explicitly added a "red-3.x-ready" tag,
                # then 3.x is explicitly supported.
                # This is similar to the meaning of "Programming Language :: Python :: 3.x"
                # classifiers in Python packaging.
                info.compatibility_status = CompatibilityStatus.EXPLICITLY_SUPPORTED_READY_TAG
                results.explicitly_supported[cog.name] = info
            else:
                # If we don't have any explicit signals from the cog's metadata that
                # Red 3.x is supported, the cog is only *potentially* supported by that version.
                info.compatibility_status = CompatibilityStatus.POTENTIALLY_SUPPORTED
                results.potentially_supported[cog.name] = info

    def _evaluate_before_update_compatibility(
        self, to_check: Iterable[_downloader.Installable]
    ) -> CompatibilityResults:
        results = CompatibilityResults(
            latest_version=self.latest_version, interpreter_version=self.interpreter_version
        )

        self._fill_compatibility_results(results, to_check)

        return results

    def _evaluate_after_update_compatibility(
        self,
        to_check: Iterable[_downloader.Installable],
        update_check_result: _downloader.CogUpdateCheckResult,
    ) -> CompatibilityResults:
        not_updatable = set(to_check)
        results = CompatibilityResults(
            latest_version=self.latest_version, interpreter_version=self.interpreter_version
        )

        not_updatable.difference_update(update_check_result.incompatible_python_version)
        not_updatable.difference_update(update_check_result.incompatible_bot_version)
        not_updatable.difference_update(update_check_result.updatable_cogs)

        self._fill_compatibility_results(results, update_check_result.incompatible_python_version)
        self._fill_compatibility_results(results, update_check_result.incompatible_bot_version)
        self._fill_compatibility_results(results, update_check_result.updatable_cogs)

        # not_updatable should now only have cogs that were not updateable. Those cogs
        # are filled based on metadata of the currently installed ("before update") version.
        self._fill_compatibility_results(results, not_updatable)

        return results


async def check_instance(
    instance: str,
    *,
    latest_version: Version,
    interpreter_version: Version,
    ignore_prefix: bool = False,
) -> CompatibilitySummary:
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
        return await checker.check()
    finally:
        await driver_cls.teardown()
