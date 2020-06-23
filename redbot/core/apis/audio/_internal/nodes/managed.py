from __future__ import annotations

import asyncio
import contextlib
import itertools
import logging
import platform
import shutil
import sys
import tempfile
import time
from typing import ClassVar, Optional, Tuple, List

import aiohttp
from tqdm import tqdm

from redbot.core import Config
from redbot.core.apis.audio import constants, regex, errors

__all__ = [
    "managed_lavalink_connect_task_event",
    "get_latest_lavalink_release",
    "LavalinkServerManager",
]

log = logging.getLogger("red.core.apis.audio.nodes.managed")


managed_lavalink_connect_task_event = asyncio.Event()


async def get_latest_lavalink_release():
    async with aiohttp.ClientSession() as session:
        async with session.get(constants.LAVALINK_JAR_ENDPOINT) as result:
            data = await result.json()
            return (
                data.get("name"),
                data.get("tag_name"),
                next(
                    (
                        i.get("browser_download_url")
                        for i in data.get("assets", [])
                        if i.get("name") == "Lavalink.jar"
                    ),
                    None,
                ),
            )


class LavalinkServerManager:

    _java_available: ClassVar[Optional[bool]] = None
    _java_version: ClassVar[Optional[Tuple[int, int]]] = None
    _up_to_date: ClassVar[Optional[bool]] = None
    _blacklisted_archs: List[str] = []
    _jar_build: ClassVar[int] = constants.JAR_BUILD
    _jar_version: ClassVar[str] = constants.JAR_VERSION
    _jar_name: ClassVar[str] = f"{constants.JAR_VERSION}_{constants.JAR_BUILD}"
    _jar_download_url: ClassVar[str] = constants.LAVALINK_DOWNLOAD_URL

    _lavaplayer: ClassVar[Optional[str]] = None
    _lavalink_build: ClassVar[Optional[int]] = None
    _jvm: ClassVar[Optional[str]] = None
    _lavalink_branch: ClassVar[Optional[str]] = None
    _buildtime: ClassVar[Optional[str]] = None

    _java_exc: ClassVar[str] = "java"

    def __init__(self, config: Config) -> None:
        self.ready: asyncio.Event = asyncio.Event()
        self._proc: Optional[asyncio.subprocess.Process] = None  # pylint:disable=no-member
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown: bool = False
        self._config: Config = config

    @property
    def jvm(self) -> Optional[str]:
        return self._jvm

    @property
    def lavaplayer(self) -> Optional[str]:
        return self._lavaplayer

    @property
    def ll_build(self) -> Optional[int]:
        return self._lavalink_build

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

        if (jar_url := await self._config.lavalink.jar_url()) is not None:
            self._jar_name = jar_url
            self._jar_download_url = jar_url
            self._jar_build = await self._config.lavalink.jar_build() or self._jar_build
        else:
            if await self._config.lavalink.autoupdate():
                with contextlib.suppress(Exception):
                    name, tag, url = await get_latest_lavalink_release()
                    if name and "_" in name:
                        tag = name
                        version, build = name.split("_")
                        build = int(build)
                    elif tag and "_" in tag:
                        name = tag
                        version, build = name.split("_")
                        build = int(build)
                    else:
                        name = tag = version = build = None
                    self._jar_name = name or tag or self._jar_name
                    self._jar_download_url = url or self._jar_download_url
                    self._jar_build = build or self._jar_build
                    self._jar_version = version or self._jar_version

        if self._proc is not None:
            if self._proc.returncode is None:
                raise RuntimeError("Internal Lavalink server is already running")
            elif self._shutdown:
                raise RuntimeError("Server manager has already been used - create another one")

        await self.maybe_download_jar()

        # Copy the application.yml across.
        # For people to customise their Lavalink server configuration they need to run it
        # externally
        shutil.copyfile(str(constants.BUNDLED_APP_YML), str(constants.LAVALINK_APP_YML))

        args = await self._get_jar_args()
        self._proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(constants.LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        log.info("Internal Lavalink server started. PID: %s", self._proc.pid)

        try:
            await asyncio.wait_for(self._wait_for_launcher(), timeout=120)
        except asyncio.TimeoutError:
            log.warning("Timeout occurred whilst waiting for internal Lavalink server to be ready")

        self._monitor_task = asyncio.create_task(self._monitor())

    async def _get_jar_args(self) -> List[str]:
        (java_available, java_version) = await self._has_java()
        if java_version is None:
            raise RuntimeError(
                f"`{self._java_exc}` is not a valid java executable in your machine."
            )
        if not java_available:
            raise RuntimeError("You must install Java 11+ for Lavalink to run.")

        if java_version >= (14, 0):
            raise errors.UnsupportedJavaVersion(version=java_version)
        elif java_version >= (13, 0):
            extra_flags = []
        elif java_version >= (12, 0):
            raise errors.UnsupportedJavaVersion(version=java_version)
        elif java_version >= (11, 0):
            extra_flags = ["-Djdk.tls.client.protocols=TLSv1.2"]
        else:
            raise errors.UnsupportedJavaVersion(version=java_version)

        return [self._java_exc, *extra_flags, "-jar", str(constants.LAVALINK_JAR_FILE)]

    async def _has_java(self) -> Tuple[bool, Optional[Tuple[int, int]]]:
        if self._java_available is not None:
            # Return cached value if we've checked this before
            return self._java_available, self._java_version
        java_available = shutil.which(self._java_exc) is not None
        if not java_available:
            self.java_available = False
            self.java_version = None
        else:
            self._java_version = version = await self._get_java_version()
            self._java_available = (11, 0) <= version < (12, 0) or (13, 0) <= version < (14, 0)
        return self._java_available, self._java_version

    async def _get_java_version(self) -> Tuple[int, int]:
        """This assumes we've already checked that java exists."""
        _proc: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(  # pylint:disable=no-member
            self._java_exc,
            "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # java -version outputs to stderr
        _, err = await _proc.communicate()

        version_info: str = err.decode("utf-8")
        # We expect the output to look something like:
        #     $ java -version
        #     ...
        #     ... version "MAJOR.MINOR.PATCH[_BUILD]" ...
        #     ...
        # We only care about the major and minor parts though.

        lines = version_info.splitlines()
        for line in lines:
            match = regex.JAVA_VERSION_LINE.search(line)
            short_match = regex.JAVA_SHORT_VERSION.search(line)
            if match:
                return int(match["major"]), int(match["minor"])
            elif short_match:
                return int(short_match["major"]), 0

        raise RuntimeError(f"The output of `{self._java_exc} -version` was unexpected.")

    async def _wait_for_launcher(self) -> None:
        log.debug("Waiting for Lavalink server to be ready")
        lastmessage = 0
        for i in itertools.cycle(range(50)):
            line = await self._proc.stdout.readline()
            if regex.LAVALINK_READY_LINE.search(line):
                self.ready.set()
                break
            if regex.LAVALINK_READY_LINE.search(line):
                raise RuntimeError(f"Lavalink failed to start: {line.decode().strip()}")
            if self._proc.returncode is not None and lastmessage + 5 < time.perf_counter():
                # Avoid Console spam only print once every 2 seconds
                lastmessage = time.perf_counter()
                log.critical("Internal lavalink server exited early")
            if i == 49:
                # Sleep after 50 lines to prevent busylooping
                await asyncio.sleep(0.1)

    async def _monitor(self) -> None:
        while self._proc.returncode is None:
            await asyncio.sleep(0.5)

        # This task hasn't been cancelled - Lavalink was shut down by something else
        log.warning("Internal Lavalink jar shutdown unexpectedly")
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
        poss_error_file = constants.LAVALINK_DOWNLOAD_DIR / "hs_err_pid{}.log".format(
            self._proc.pid
        )
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
        async with aiohttp.ClientSession() as session:
            async with session.get(self._jar_download_url) as response:
                if response.status == 404:
                    # A 404 means our LAVALINK_DOWNLOAD_URL is invalid, so likely the jar version
                    # hasn't been published yet
                    raise errors.LavalinkDownloadFailed(
                        f"Lavalink jar version {self._jar_name} hasn't been published " f"yet",
                        response=response,
                        should_retry=False,
                    )
                elif 400 <= response.status < 600:
                    # Other bad responses should be raised but we should retry just incase
                    raise errors.LavalinkDownloadFailed(response=response, should_retry=True)
                fd, path = tempfile.mkstemp()
                file = open(fd, "wb")
                nbytes = 0
                with tqdm(
                    desc="Lavalink.jar",
                    total=response.content_length,
                    file=sys.stdout,
                    unit="B",
                    unit_scale=True,
                    miniters=1,
                    dynamic_ncols=True,
                    leave=False,
                ) as progress_bar:
                    try:
                        chunk = await response.content.read(1024)
                        while chunk:
                            chunk_size = file.write(chunk)
                            nbytes += chunk_size
                            progress_bar.update(chunk_size)
                            chunk = await response.content.read(1024)
                        file.flush()
                    finally:
                        file.close()

                shutil.move(path, str(constants.LAVALINK_JAR_FILE), copy_function=shutil.copyfile)

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
            cwd=str(constants.LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        if (build := regex.LAVALINK_BUILD_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (branch := regex.LAVALINK_BRANCH_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (java := regex.LAVALINK_JAVA_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (lavaplayer := regex.LAVALINK_LAVAPLAYER_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
        if (buildtime := regex.LAVALINK_BUILD_TIME_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False

        build = int(build["build"])
        date = buildtime["build_time"].decode()
        date = date.replace(".", "/")
        self._lavalink_build = build
        self._lavalink_branch = branch["branch"].decode()
        self._jvm = java["jvm"].decode()
        self._lavaplayer = lavaplayer["lavaplayer"].decode()
        self._buildtime = date

        self._up_to_date = build >= self._jar_build
        return self._up_to_date

    async def maybe_download_jar(self):
        if not (constants.LAVALINK_JAR_FILE.exists() and await self._is_up_to_date()):
            await self._download_jar()
            if not await self._is_up_to_date():
                raise errors.LavalinkDownloadFailed(
                    f"Download of Lavalink build {self.ll_build} from {self.ll_branch} "
                    f"({self._jar_download_url}) failed, Excepted build {self._jar_build} "
                    f"But downloaded {self._lavalink_build}",
                    should_retry=False,
                )
