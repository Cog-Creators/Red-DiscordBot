from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import importlib.metadata
import json
import logging
import os
import re
import shutil
import tarfile
import time
import warnings
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tarfile import TarInfo
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Union,
    TypedDict,
    TypeVar,
    TypedDict,
    TYPE_CHECKING,
    Tuple,
    cast,
)

import aiohttp
import discord
import yarl
from packaging.metadata import Metadata
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import parse_sdist_filename
from packaging.version import Version
import rapidfuzz
import rich.progress
from rich.console import Console
from rich.text import Text
from red_commons.logging import VERBOSE, TRACE
from typing_extensions import NotRequired, Self

from redbot import __version__
from redbot.core import data_manager
from redbot.core.utils.chat_formatting import box

if TYPE_CHECKING:
    from redbot.core.bot import Red
    from redbot.core.commands import Command, Context

main_log = logging.getLogger("red")

__all__ = (
    "safe_delete",
    "fuzzy_command_search",
    "format_fuzzy_results",
    "create_backup",
    "send_to_owners_with_preprocessor",
    "send_to_owners_with_prefix_replaced",
    "ReleaseFile",
    "AvailableVersion",
    "fetch_available_red_versions",
    "fetch_latest_red_version",
    "deprecated_removed",
    "RichIndefiniteBarColumn",
    "RichSpeedColumn",
    "detailed_progress",
    "cli_level_to_log_level",
)

_T = TypeVar("_T")

# I guess there's nothing in allowing people to use an alternative index.
_SIMPLE_API_URL = os.getenv("RED_SIMPLE_API_URL") or "https://pypi.org/simple/"
# This variable should only be used for debugging purposes (hence why it starts with `_`).
# You can debug the behavior by e.g. creating a "Red-DiscordBot.json" file,
# starting a server with `python -m http.server` and starting Red with the following env vars:
# RED_SIMPLE_API_URL=http://localhost:8000 _RED_SIMPLE_API_ENDPOINT_PATH=Red-DiscordBot.json
_SIMPLE_API_ENDPOINT_PATH = os.getenv("_RED_SIMPLE_API_ENDPOINT_PATH") or "Red-DiscordBot"


def safe_delete(pth: Path):
    if pth.exists():
        for root, dirs, files in os.walk(str(pth)):
            os.chmod(root, 0o700)

            for d in dirs:
                os.chmod(os.path.join(root, d), 0o700)

            for f in files:
                os.chmod(os.path.join(root, f), 0o700)

        shutil.rmtree(str(pth), ignore_errors=True)


def _fuzzy_log_filter(record):
    return record.funcName != "extractWithoutOrder"


logging.getLogger().addFilter(_fuzzy_log_filter)


async def fuzzy_command_search(
    ctx: Context,
    term: Optional[str] = None,
    *,
    commands: Optional[Union[AsyncIterator[Command], Iterator[Command]]] = None,
    min_score: int = 80,
) -> Optional[List[Command]]:
    """Search for commands which are similar in name to the one invoked.

    Returns a maximum of 5 commands which must all be at least matched
    greater than ``min_score``.

    Parameters
    ----------
    ctx : `commands.Context <redbot.core.commands.Context>`
        The command invocation context.
    term : Optional[str]
        The name of the invoked command. If ``None``,
        `Context.invoked_with` will be used instead.
    commands : Optional[Union[AsyncIterator[commands.Command], Iterator[commands.Command]]]
        The commands available to choose from when doing a fuzzy match.
        When omitted, `Bot.walk_commands` will be used instead.
    min_score : int
        The minimum score for matched commands to reach. Defaults to 80.

    Returns
    -------
    Optional[List[`commands.Command <redbot.core.commands.Command>`]]
        A list of commands which were fuzzily matched with the invoked
        command.

    """
    if ctx.guild is not None:
        enabled = await ctx.bot._config.guild(ctx.guild).fuzzy()
    else:
        enabled = await ctx.bot._config.fuzzy()

    if not enabled:
        return None

    if term is None:
        term = ctx.invoked_with

    # If the term is an alias or CC, we don't want to send a supplementary fuzzy search.
    alias_cog = ctx.bot.get_cog("Alias")
    if alias_cog is not None:
        alias = await alias_cog._aliases.get_alias(ctx.guild, term)

        if alias:
            return None
    customcom_cog = ctx.bot.get_cog("CustomCommands")
    if customcom_cog is not None:
        cmd_obj = customcom_cog.commandobj

        try:
            await cmd_obj.get(ctx.message, term)
        except:
            pass
        else:
            return None

    if commands is None:
        choices = {c: c.qualified_name for c in ctx.bot.walk_commands()}
    elif isinstance(commands, collections.abc.AsyncIterator):
        choices = {c: c.qualified_name async for c in commands}
    else:
        choices = {c: c.qualified_name for c in commands}

    # Do the scoring. `extracted` is a list of tuples in the form `(cmd_name, score, cmd)`
    extracted = rapidfuzz.process.extract(
        term,
        choices,
        limit=5,
        scorer=rapidfuzz.fuzz.QRatio,
        processor=rapidfuzz.utils.default_process,
    )
    if not extracted:
        return None

    # Filter through the fuzzy-matched commands.
    matched_commands = []
    for __, score, command in extracted:
        if score < min_score:
            # Since the list is in decreasing order of score, we can exit early.
            break
        if await command.can_see(ctx):
            matched_commands.append(command)

    return matched_commands


async def format_fuzzy_results(
    ctx: Context, matched_commands: List[Command], *, embed: Optional[bool] = None
) -> Union[str, discord.Embed]:
    """Format the result of a fuzzy command search.

    Parameters
    ----------
    ctx : `commands.Context <redbot.core.commands.Context>`
        The context in which this result is being displayed.
    matched_commands : List[`commands.Command <redbot.core.commands.Command>`]
        A list of commands which have been matched by the fuzzy search, sorted
        in order of decreasing similarity.
    embed : bool
        Whether or not the result should be an embed. If set to ``None``, this
        will default to the result of `ctx.embed_requested`.

    Returns
    -------
    Union[str, discord.Embed]
        The formatted results.

    """
    if embed is not False and (embed is True or await ctx.embed_requested()):
        lines = []
        for cmd in matched_commands:
            short_doc = cmd.format_shortdoc_for_context(ctx)
            lines.append(f"**{ctx.clean_prefix}{cmd.qualified_name}** {short_doc}")
        return discord.Embed(
            title="Perhaps you wanted one of these?",
            colour=await ctx.embed_colour(),
            description="\n".join(lines),
        )
    else:
        lines = []
        for cmd in matched_commands:
            short_doc = cmd.format_shortdoc_for_context(ctx)
            lines.append(f"{ctx.clean_prefix}{cmd.qualified_name} -- {short_doc}")
        return "Perhaps you wanted one of these? " + box("\n".join(lines), lang="vhdl")


def _tar_addfile_from_string(tar: tarfile.TarFile, name: str, string: str) -> None:
    encoded = string.encode("utf-8")
    fp = BytesIO(encoded)

    # TarInfo needs `mtime` and `size`
    # https://stackoverflow.com/q/53306000
    tar_info = tarfile.TarInfo(name)
    tar_info.mtime = time.time()
    tar_info.size = len(encoded)

    tar.addfile(tar_info, fp)


class BackupDetails(TypedDict):
    backup_version: int


async def create_backup(dest: Path = Path.home()) -> Optional[Path]:
    # version of backup
    BACKUP_VERSION = 2

    data_path = Path(data_manager.core_data_path().parent)
    if not data_path.exists():
        return None

    dest.mkdir(parents=True, exist_ok=True)
    timestr = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    backup_fpath = dest / f"redv3_{data_manager.instance_name()}_{timestr}.tar.gz"

    to_backup = []
    # we need trailing separator to not exclude files and folders that only start with these names
    exclusions = [
        "__pycache__",
        # Lavalink will be downloaded on Audio load
        "Lavalink.jar",
        # cogs and repos installed through Downloader can be reinstalled using restore command
        os.path.join("Downloader", "lib", ""),
        os.path.join("CogManager", "cogs", ""),
        os.path.join("RepoManager", "repos", ""),
        os.path.join("Audio", "logs", ""),
        # these files are created during backup so we exclude them from data path backup
        os.path.join("RepoManager", "repos.json"),
        "instance.json",
        "backup_details.json",
    ]

    # Avoiding circular imports
    from redbot.core._downloader.repo_manager import RepoManager

    repo_mgr = RepoManager()
    await repo_mgr.initialize()
    repo_output = []
    for repo in repo_mgr.repos:
        repo_output.append({"url": repo.url, "name": repo.name, "branch": repo.branch})

    with rich.progress.Progress(
        rich.progress.SpinnerColumn(),
        rich.progress.TextColumn("[progress.description]{task.description}"),
        RichIndefiniteBarColumn(),
        rich.progress.TextColumn("{task.completed} files processed"),
        rich.progress.TimeElapsedColumn(),
    ) as progress:
        for f in progress.track(
            data_path.glob("**/*"), description="Preparing files for backup..."
        ):
            if not any(ex in str(f) for ex in exclusions) and f.is_file():
                to_backup.append(f)

    backup_details: BackupDetails = {
        "backup_version": BACKUP_VERSION,
    }

    with tarfile.open(str(backup_fpath), "w:gz", dereference=True) as tar:
        with detailed_progress(unit="files") as progress:
            progress_tracker = progress.track(to_backup, description="Compressing data")
            for f in progress_tracker:
                tar.add(str(f), arcname=str(f.relative_to(data_path)), recursive=False)

        # add repos backup
        repos_data = json.dumps(repo_output, indent=4)
        _tar_addfile_from_string(tar, "cogs/RepoManager/repos.json", repos_data)

        # add instance's original data
        instance_data = json.dumps(
            {data_manager.instance_name(): data_manager.basic_config}, indent=4
        )
        _tar_addfile_from_string(tar, "instance.json", instance_data)

        # add info about backup version
        _tar_addfile_from_string(tar, "backup_details.json", json.dumps(backup_details))
    return backup_fpath


# this might be worth moving to `bot.send_to_owners` at later date


async def send_to_owners_with_preprocessor(
    bot: Red,
    content: str,
    *,
    content_preprocessor: Optional[
        Callable[[Red, discord.abc.Messageable, str], Awaitable[str]]
    ] = None,
    **kwargs,
):
    """
    This sends something to all owners and their configured extra destinations.

    This acts the same as `Red.send_to_owners`, with
    one added keyword argument as detailed below in *Other Parameters*.

    Other Parameters
    ----------------
    content_preprocessor: Optional[Callable[[Red, discord.abc.Messageable, str], Awaitable[str]]]
        Optional async function that takes
        bot object, owner notification destination and message content
        and returns the content that should be sent to given location.
    """
    destinations = await bot.get_owner_notification_destinations()

    async def wrapped_send(bot, location, content=None, preprocessor=None, **kwargs):
        try:
            if preprocessor is not None:
                content = await preprocessor(bot, location, content)
            await location.send(content, **kwargs)
        except Exception as _exc:
            main_log.error(
                "I could not send an owner notification to %s (%s)",
                location,
                location.id,
                exc_info=_exc,
            )

    sends = [wrapped_send(bot, d, content, content_preprocessor, **kwargs) for d in destinations]
    await asyncio.gather(*sends)


async def send_to_owners_with_prefix_replaced(bot: Red, content: str, **kwargs):
    """
    This sends something to all owners and their configured extra destinations.

    This acts the same as `Red.send_to_owners`, with one addition - `[p]` in ``content`` argument
    is replaced with a clean prefix for each specific destination.
    """

    async def preprocessor(bot: Red, destination: discord.abc.Messageable, content: str) -> str:
        prefixes = await bot.get_valid_prefixes(getattr(destination, "guild", None))
        prefix = re.sub(
            rf"<@!?{bot.user.id}>", f"@{bot.user.name}".replace("\\", r"\\"), prefixes[0]
        )
        return content.replace("[p]", prefix)

    await send_to_owners_with_preprocessor(bot, content, content_preprocessor=preprocessor)


# gotta use functional TypedDict syntax due to hyphens in keys
ReleaseFile = TypedDict(
    "ReleaseFile",
    {
        "filename": str,
        "url": str,
        "hashes": Dict[str, str],
        "requires-python": NotRequired[str],
        "core-metadata": NotRequired[Union[bool, Dict[str, str]]],
        "yanked": bool,
        "size": int,
        "upload-time": NotRequired[str],
        "provenance": NotRequired[Optional[str]],
    },
)


class AvailableVersion:
    def __init__(self, version: Version, files: Dict[str, ReleaseFile]) -> None:
        self.version = version
        self.files = files
        required_pythons = {f.get("requires-python") or "" for f in files.values()}
        if len(required_pythons) > 1:
            raise ValueError("found multiple files with different Requires-Python values")
        self.requires_python = SpecifierSet(required_pythons.pop())

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        ret = cls(Version(data["version"]), data["files"])
        if str(ret.requires_python) != data["requires_python"]:
            raise ValueError("requires_python key in given data is inconsistent with files")
        return ret

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "version": str(self.version),
            "requires_python": str(self.requires_python),
            "files": self.files,
        }

    async def fetch_core_metadata(self) -> Metadata:
        for release_file in self.files.values():
            core_metadata_hashes = release_file.get("core-metadata", False)
            if core_metadata_hashes is False:
                continue
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{release_file['url']}.metadata") as resp:
                    return Metadata.from_email(await resp.read(), validate=False)
        raise TypeError("Could not find core metadata for any of the release files.")

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.version == other.version
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.version != other.version
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.version < other.version
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.version <= other.version
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.version > other.version
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.version >= other.version
        return NotImplemented


async def fetch_available_red_versions(
    *, include_prereleases: Optional[bool] = None
) -> List[AvailableVersion]:
    """
    Fetch information about Red releases available on PyPI,
    sorted by version (latest first).

    Parameters
    ----------
    include_prereleases : bool, optional
        Whether the pre-releases should be included in the list.
        If ``None`` (the default), the pre-releases will only be included,
        if the currently running Red version is considered a pre-release.

    Raises
    ------
    aiohttp.ClientError
        An error occurred during request to PyPI.
    TimeoutError
        The request to PyPI timed out.
    ValueError
        Some part of the response was considered invalid.
        This includes issues such as incorrect response content type,
        invalid version strings, inability to find files for a release,
        and mismatching Requires-Python values.
    KeyError
        The PyPI metadata is missing some of the required information.
    """
    if include_prereleases is None:
        include_prereleases = Version(__version__).is_prerelease
    expected_content_type = "application/vnd.pypi.simple.v1+json"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            yarl.URL(_SIMPLE_API_URL) / _SIMPLE_API_ENDPOINT_PATH,
            headers={"Accept": expected_content_type},
        ) as resp:
            data = await resp.json()
            content_type = resp.headers["Content-Type"]
            if not (
                content_type.startswith(expected_content_type)
                or (
                    content_type.startswith("application/json")
                    and data["meta"]["api-version"].startswith("1.")
                )
            ):
                raise ValueError("got unexpected response from Simple Repository API")

    files: Dict[Version, Dict[str, ReleaseFile]] = {}
    f: ReleaseFile
    for f in data["files"]:
        if f.get("yanked"):
            continue
        filename = f["filename"]
        if filename.endswith((".tar.gz", ".zip")):
            _, version = parse_sdist_filename(filename)
        elif filename.endswith(".whl"):
            # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
            _, raw_version, _ = filename.split("-", 2)
            version = Version(raw_version)
        else:
            continue
        if version.is_prerelease and not include_prereleases:
            continue
        version_files = files.setdefault(version, {})
        version_files[f["filename"]] = f

    if not files:
        raise ValueError("could not find any files")

    available_versions = [
        AvailableVersion(version, version_files) for version, version_files in files.items()
    ]
    available_versions.sort(reverse=True)

    return available_versions


async def fetch_latest_red_version(
    *, include_prereleases: Optional[bool] = None
) -> AvailableVersion:
    """
    Fetch information about latest Red release on PyPI.

    Parameters
    ----------
    include_prereleases : bool, optional
        Whether the pre-releases should be considered when finding the latest version.
        If ``None`` (the default), the pre-releases will only be considered,
        if the currently running Red version is considered a pre-release.

    Raises
    ------
    aiohttp.ClientError
        An error occurred during request to PyPI.
    TimeoutError
        The request to PyPI timed out.
    ValueError
        Some part of the response was considered invalid.
        This includes issues such as incorrect response content type,
        invalid version strings, inability to find files for a release,
        and mismatching Requires-Python values.
    KeyError
        The PyPI metadata is missing some of the required information.
    """
    available_versions = await fetch_available_red_versions(
        include_prereleases=include_prereleases
    )
    return available_versions[0]


def get_installed_extras() -> List[str]:
    red_dist = importlib.metadata.distribution("Red-DiscordBot")
    installed_extras = red_dist.metadata.get_all("Provides-Extra")
    if installed_extras is None:
        return []
    installed_extras.remove("dev")
    installed_extras.remove("all")
    distributions: Dict[str, Optional[importlib.metadata.Distribution]] = {}
    for req_str in red_dist.requires or []:
        req = Requirement(req_str)
        if req.marker is None or req.marker.evaluate():
            continue
        for extra in reversed(installed_extras):
            if not req.marker.evaluate({"extra": extra}):
                continue

            # Check that the requirement is met.
            # This is a bit simplified for our purposes and does not check
            # whether the requirements of our requirements are met as well.
            # This could potentially be an issue if we'll ever depend on
            # a dependency's extra in our extra when we already depend on that
            # in our base dependencies. However, considering that right now, all
            # our dependencies are also fully pinned, this should not ever matter.
            if req.name in distributions:
                dist = distributions[req.name]
            else:
                try:
                    dist = importlib.metadata.distribution(req.name)
                except importlib.metadata.PackageNotFoundError:
                    dist = None
                distributions[req.name] = dist
            if dist is None or not req.specifier.contains(dist.version, prereleases=True):
                installed_extras.remove(extra)

    return installed_extras


def deprecated_removed(
    deprecation_target: str,
    deprecation_version: str,
    minimum_days: int,
    message: str = "",
    stacklevel: int = 1,
) -> None:
    warnings.warn(
        f"{deprecation_target} is deprecated since version {deprecation_version}"
        " and will be removed in the first minor version that gets released"
        f" after {minimum_days} days since deprecation. {message}",
        DeprecationWarning,
        stacklevel=stacklevel + 1,
    )


class RichIndefiniteBarColumn(rich.progress.ProgressColumn):
    def render(self, task: rich.progress.Task) -> rich.progress.ProgressBar:
        return rich.progress.ProgressBar(
            pulse=task.completed < task.total if task.total is not None else True,
            animation_time=task.get_time(),
            width=40,
            total=task.total,
            completed=task.completed,
        )


class RichSpeedColumn(rich.progress.ProgressColumn):
    def __init__(self, *, unit: str) -> None:
        self.unit = unit
        super().__init__()

    def render(self, task: rich.progress.Task) -> Text:
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed")
        return Text(f"{int(speed)} {self.unit}/s", style="progress.data.speed")


def detailed_progress(*, unit: str, console: Optional[Console] = None) -> rich.progress.Progress:
    return rich.progress.Progress(
        rich.progress.SpinnerColumn(),
        rich.progress.TextColumn("[progress.description]{task.description}"),
        rich.progress.BarColumn(bar_width=None),
        RichSpeedColumn(unit=unit),
        rich.progress.TaskProgressColumn(),
        rich.progress.TextColumn("eta"),
        rich.progress.TimeRemainingColumn(),
        rich.progress.TextColumn("elapsed"),
        rich.progress.TimeElapsedColumn(),
        console=console,
    )


def cli_level_to_log_level(level: int) -> int:
    if level == 0:
        log_level = logging.INFO
    elif level == 1:
        log_level = logging.DEBUG
    elif level == 2:
        log_level = VERBOSE
    else:
        log_level = TRACE
    return log_level


def log_level_to_cli_level(log_level: int) -> int:
    if log_level == TRACE:
        level = 3
    elif log_level == VERBOSE:
        level = 2
    elif log_level == logging.DEBUG:
        level = 1
    else:
        level = 0
    return level
