import asyncio
import asyncio.subprocess  # disables for # https://github.com/PyCQA/pylint/issues/1469
import itertools
import json
import logging
import pathlib
import platform
import re
import shutil
import sys
import tempfile
import time
from typing import ClassVar, Final, List, Optional, Pattern, Tuple, Union

import aiohttp
import rich.progress

from redbot.core import data_manager
from redbot.core.i18n import Translator

from .errors import LavalinkDownloadFailed
from .utils import task_callback

_ = Translator("Audio", pathlib.Path(__file__))
log = logging.getLogger("red.Audio.manager")
LAVALINK_DOWNLOAD_DIR: Final[pathlib.Path] = data_manager.cog_data_path(raw_name="Audio")
LAVALINK_JAR_FILE: Final[pathlib.Path] = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"
BUNDLED_APP_YML: Final[pathlib.Path] = pathlib.Path(__file__).parent / "data" / "application.yml"
LAVALINK_APP_YML: Final[pathlib.Path] = LAVALINK_DOWNLOAD_DIR / "application.yml"

_FAILED_TO_START: Final[Pattern] = re.compile(rb"Web server failed to start\. (.*)")

# Version regexes
#
# We expect the output to look something like:
#     $ java -version
#     ...
#     ... version "VERSION STRING HERE" ...
#     ...
#
# There are two version formats that we might get here:
#
# - Version scheme pre JEP 223 - used by Java 8 and older
#
# examples:
# 1.8.0
# 1.8.0_275
# 1.8.0_272-b10
# 1.8.0_202-internal-201903130451-b08
# 1.8.0_272-ea-202010231715-b10
# 1.8.0_272-ea-b10
#
# Implementation based on J2SE SDK/JRE Version String Naming Convention document:
# https://www.oracle.com/java/technologies/javase/versioning-naming.html
_RE_JAVA_VERSION_LINE_PRE223: Final[Pattern] = re.compile(
    r'version "1\.(?P<major>[0-8])\.(?P<minor>0)(?:_(?:\d+))?(?:-.*)?"'
)
# - Version scheme introduced by JEP 223 - used by Java 9 and newer
#
# examples:
# 11
# 11.0.9
# 11.0.9.1
# 11.0.9-ea
# 11.0.9-202011050024
#
# Implementation based on JEP 223 document:
# https://openjdk.java.net/jeps/223
_RE_JAVA_VERSION_LINE_223: Final[Pattern] = re.compile(
    r'version "(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.\d+)*(\-[a-zA-Z0-9]+)?"'
)

LAVALINK_BRANCH_LINE: Final[Pattern] = re.compile(rb"^Branch\s+(?P<branch>\S+)$", re.MULTILINE)
LAVALINK_JAVA_LINE: Final[Pattern] = re.compile(rb"^JVM:\s+(?P<jvm>\S+)$", re.MULTILINE)
LAVALINK_LAVAPLAYER_LINE: Final[Pattern] = re.compile(
    rb"^Lavaplayer\s+(?P<lavaplayer>\S+)$", re.MULTILINE
)
LAVALINK_BUILD_TIME_LINE: Final[Pattern] = re.compile(
    rb"^Build time:\s+(?P<build_time>\d+[.\d+]*).*$", re.MULTILINE
)
# present until Lavalink 3.5-rc4
LAVALINK_BUILD_LINE: Final[Pattern] = re.compile(rb"^Build:\s+(?P<build>\d+)$", re.MULTILINE)
# we don't actually care about what the version format before 3.5-rc4 is exactly
# as the comparison is based entirely on the build number
LAVALINK_VERSION_LINE_PRE35: Final[Pattern] = re.compile(
    rb"^Version:\s+(?P<version>\S+)$", re.MULTILINE | re.VERBOSE
)
# used for LL 3.5-rc4 and newer
LAVALINK_VERSION_LINE: Final[Pattern] = re.compile(
    rb"""
    ^
    Version:\s+
    (?P<version>
        (?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)
        # Before LL 3.6, when patch version == 0, it was stripped from the version string
        (?:\.(?P<patch>0|[1-9]\d*))?
        (?:-rc(?P<rc>0|[1-9]\d*))?
        # only used by our downstream Lavalink if we need to make a release before upstream
        (?:_red(?P<red>[1-9]\d*))?
    )
    $
    """,
    re.MULTILINE | re.VERBOSE,
)


class LavalinkOldVersion:
    def __init__(self, raw_version: str, *, build_number: int) -> None:
        self.raw_version = raw_version
        self.build_number = build_number

    def __str__(self) -> None:
        return f"{self.raw_version}_{self.build_number}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number == other.build_number
        if isinstance(other, LavalinkVersion):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number < other.build_number
        if isinstance(other, LavalinkVersion):
            return True
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number <= other.build_number
        if isinstance(other, LavalinkVersion):
            return True
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number > other.build_number
        if isinstance(other, LavalinkVersion):
            return False
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number >= other.build_number
        if isinstance(other, LavalinkVersion):
            return False
        return NotImplemented


class LavalinkVersion:
    def __init__(
        self,
        major: int,
        minor: int,
        patch: int = 0,
        *,
        rc: Optional[int] = None,
        red: int = 0,
    ) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch
        self.rc = rc
        self.red = red

    def __str__(self) -> None:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.rc is not None:
            version += f"-rc{self.rc}"
        if self.red:
            version += f"_red{self.red}"
        return version

    def _get_comparison_tuple(self) -> Tuple[int, int, int, bool, int, int]:
        return self.major, self.minor, self.patch, self.rc is None, self.rc or 0, self.red

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() == other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() < other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return False
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() <= other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return False
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() > other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return True
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() >= other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return True
        return NotImplemented


class ServerManager:
    JAR_VERSION: Final[str] = LavalinkVersion(3, 7, 5)
    LAVALINK_DOWNLOAD_URL: Final[str] = (
        "https://github.com/Cog-Creators/Lavalink-Jars/releases/download/"
        f"{JAR_VERSION}/"
        "Lavalink.jar"
    )

    _java_available: ClassVar[Optional[bool]] = None
    _java_version: ClassVar[Optional[Tuple[int, int]]] = None
    _up_to_date: ClassVar[Optional[bool]] = None
    _blacklisted_archs: List[str] = []

    _lavaplayer: ClassVar[Optional[str]] = None
    _lavalink_version: ClassVar[Optional[Union[LavalinkOldVersion, LavalinkVersion]]] = None
    _jvm: ClassVar[Optional[str]] = None
    _lavalink_branch: ClassVar[Optional[str]] = None
    _buildtime: ClassVar[Optional[str]] = None
    _java_exc: ClassVar[str] = "java"

    def __init__(self) -> None:
        self.ready: asyncio.Event = asyncio.Event()

        self._proc: Optional[asyncio.subprocess.Process] = None  # pylint:disable=no-member
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown: bool = False

    @property
    def path(self) -> Optional[str]:
        return self._java_exc

    @property
    def jvm(self) -> Optional[str]:
        return self._jvm

    @property
    def lavaplayer(self) -> Optional[str]:
        return self._lavaplayer

    @property
    def ll_version(self) -> Optional[Union[LavalinkOldVersion, LavalinkVersion]]:
        return self._lavalink_version

    @property
    def ll_branch(self) -> Optional[str]:
        return self._lavalink_branch

    @property
    def build_time(self) -> Optional[str]:
        return self._buildtime

    async def start(self, java_path: str) -> None:
        arch_name = platform.machine()
        self._java_exc = java_path
        if arch_name in self._blacklisted_archs:
            raise asyncio.CancelledError(
                "You are attempting to run Lavalink audio on an unsupported machine architecture."
            )

        if self._proc is not None:
            if self._proc.returncode is None:
                raise RuntimeError("Internal Lavalink server is already running")
            elif self._shutdown:
                raise RuntimeError("Server manager has already been used - create another one")

        await self.maybe_download_jar()

        # Copy the application.yml across.
        # For people to customise their Lavalink server configuration they need to run it
        # externally
        shutil.copyfile(BUNDLED_APP_YML, LAVALINK_APP_YML)

        args = await self._get_jar_args()
        self._proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        log.info("Internal Lavalink server started. PID: %s", self._proc.pid)

        try:
            await asyncio.wait_for(self._wait_for_launcher(), timeout=120)
        except asyncio.TimeoutError:
            log.warning("Timeout occurred whilst waiting for internal Lavalink server to be ready")

        self._monitor_task = asyncio.create_task(self._monitor())
        self._monitor_task.add_done_callback(task_callback)

    async def _get_jar_args(self) -> List[str]:
        (java_available, java_version) = await self._has_java()

        if not java_available:
            raise RuntimeError("You must install Java 11 for Lavalink to run.")

        return [
            self._java_exc,
            "-Djdk.tls.client.protocols=TLSv1.2",
            "-jar",
            str(LAVALINK_JAR_FILE),
        ]

    async def _has_java(self) -> Tuple[bool, Optional[Tuple[int, int]]]:
        if self._java_available is not None:
            # Return cached value if we've checked this before
            return self._java_available, self._java_version
        java_exec = shutil.which(self._java_exc)
        java_available = java_exec is not None
        if not java_available:
            self.java_available = False
            self.java_version = None
        else:
            self._java_version = version = await self._get_java_version()
            self._java_available = (11, 0) <= version < (12, 0)
            self._java_exc = java_exec
        return self._java_available, self._java_version

    async def _get_java_version(self) -> Tuple[int, int]:
        """This assumes we've already checked that java exists."""
        _proc: asyncio.subprocess.Process = (
            await asyncio.create_subprocess_exec(  # pylint:disable=no-member
                self._java_exc,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        )
        # java -version outputs to stderr
        _, err = await _proc.communicate()

        version_info: str = err.decode("utf-8")
        lines = version_info.splitlines()
        for line in lines:
            match = _RE_JAVA_VERSION_LINE_PRE223.search(line)
            if match is None:
                match = _RE_JAVA_VERSION_LINE_223.search(line)
            if match is None:
                continue
            major = int(match["major"])
            minor = 0
            if minor_str := match["minor"]:
                minor = int(minor_str)

            return major, minor

        raise RuntimeError(f"The output of `{self._java_exc} -version` was unexpected.")

    async def _wait_for_launcher(self) -> None:
        log.debug("Waiting for Lavalink server to be ready")
        lastmessage = 0
        for i in itertools.cycle(range(50)):
            line = await self._proc.stdout.readline()
            if b"Lavalink is ready to accept connections." in line:
                self.ready.set()
                log.info("Internal Lavalink server is ready to receive requests.")
                break
            if _FAILED_TO_START.search(line):
                raise RuntimeError(f"Lavalink failed to start: {line.decode().strip()}")
            if self._proc.returncode is not None and lastmessage + 2 < time.time():
                # Avoid Console spam only print once every 2 seconds
                lastmessage = time.time()
                log.critical("Internal lavalink server exited early")
            if i == 49:
                # Sleep after 50 lines to prevent busylooping
                await asyncio.sleep(0.1)

    async def _monitor(self) -> None:
        while self._proc.returncode is None:
            await asyncio.sleep(0.5)

        # This task hasn't been cancelled - Lavalink was shut down by something else
        log.info("Internal Lavalink jar shutdown unexpectedly")
        if not self._has_java_error():
            log.info("Restarting internal Lavalink server")
            await self.start(self._java_exc)
        else:
            log.critical(
                "Your Java is borked. Please find the hs_err_pid%d.log file"
                " in the Audio data folder and report this issue.",
                self._proc.pid,
            )

    def _has_java_error(self) -> bool:
        poss_error_file = LAVALINK_DOWNLOAD_DIR / "hs_err_pid{}.log".format(self._proc.pid)
        return poss_error_file.exists()

    async def shutdown(self) -> None:
        if self._shutdown is True or self._proc is None:
            # For convenience, calling this method more than once or calling it before starting it
            # does nothing.
            return
        log.info("Shutting down internal Lavalink server")
        if self._monitor_task is not None:
            self._monitor_task.cancel()
        self._proc.terminate()
        await self._proc.wait()
        self._shutdown = True

    async def _download_jar(self) -> None:
        log.info("Downloading Lavalink.jar...")
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            async with session.get(self.LAVALINK_DOWNLOAD_URL) as response:
                if response.status == 404:
                    # A 404 means our LAVALINK_DOWNLOAD_URL is invalid, so likely the jar version
                    # hasn't been published yet
                    raise LavalinkDownloadFailed(
                        f"Lavalink jar version {self.JAR_VERSION} hasn't been published yet",
                        response=response,
                        should_retry=False,
                    )
                elif 400 <= response.status < 600:
                    # Other bad responses should be raised but we should retry just incase
                    raise LavalinkDownloadFailed(response=response, should_retry=True)
                fd, path = tempfile.mkstemp()
                file = open(fd, "wb")
                nbytes = 0
                with rich.progress.Progress(
                    rich.progress.SpinnerColumn(),
                    rich.progress.TextColumn("[progress.description]{task.description}"),
                    rich.progress.BarColumn(),
                    rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    rich.progress.TimeRemainingColumn(),
                    rich.progress.TimeElapsedColumn(),
                ) as progress:
                    progress_task_id = progress.add_task(
                        "[red]Downloading Lavalink.jar", total=response.content_length
                    )
                    try:
                        chunk = await response.content.read(1024)
                        while chunk:
                            chunk_size = file.write(chunk)
                            nbytes += chunk_size
                            progress.update(progress_task_id, advance=chunk_size)
                            chunk = await response.content.read(1024)
                        file.flush()
                    finally:
                        file.close()

                shutil.move(path, str(LAVALINK_JAR_FILE), copy_function=shutil.copyfile)

        log.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))
        await self._is_up_to_date()

    async def _is_up_to_date(self):
        if self._up_to_date is True:
            # Return cached value if we've checked this before
            return True
        args = await self._get_jar_args()
        args.append("--version")
        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        if (branch := LAVALINK_BRANCH_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (java := LAVALINK_JAVA_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (lavaplayer := LAVALINK_LAVAPLAYER_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (buildtime := LAVALINK_BUILD_TIME_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False

        if (build := LAVALINK_BUILD_LINE.search(stdout)) is not None:
            if (version := LAVALINK_VERSION_LINE_PRE35.search(stdout)) is None:
                # Output is unexpected, suspect corrupted jarfile
                return False
            self._lavalink_version = LavalinkOldVersion(
                raw_version=version["version"].decode(),
                build_number=int(build["build"]),
            )
        elif (version := LAVALINK_VERSION_LINE.search(stdout)) is not None:
            self._lavalink_version = LavalinkVersion(
                major=int(version["major"]),
                minor=int(version["minor"]),
                patch=int(version["patch"] or 0),
                rc=int(version["rc"]) if version["rc"] is not None else None,
                red=int(version["red"] or 0),
            )
        else:
            # Output is unexpected, suspect corrupted jarfile
            return False
        date = buildtime["build_time"].decode()
        date = date.replace(".", "/")
        self._lavalink_branch = branch["branch"].decode()
        self._jvm = java["jvm"].decode()
        self._lavaplayer = lavaplayer["lavaplayer"].decode()
        self._buildtime = date
        self._up_to_date = self._lavalink_version >= self.JAR_VERSION
        return self._up_to_date

    async def maybe_download_jar(self):
        if not (LAVALINK_JAR_FILE.exists() and await self._is_up_to_date()):
            await self._download_jar()
