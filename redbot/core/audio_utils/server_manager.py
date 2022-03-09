import asyncio
import asyncio.subprocess
import itertools
import json
import logging
import pathlib
import platform
import re
import shutil
import tempfile
import time
import aiohttp
import rich
import sys

from typing import Optional, Final, Pattern, List, Tuple

from .api_utils import task_callback
from .errors import LavalinkDownloadFailed, PortAlreadyInUse

from redbot.core import data_manager

log = logging.getLogger("red.core.audio.server_manager")

JAR_VERSION: Final[str] = "3.3.2.3"
JAR_BUILD: Final[int] = 1239
LAVALINK_DOWNLOAD_URL: Final[str] = (
    "https://github.com/Cog-Creators/Lavalink-Jars/releases/download/"
    f"{JAR_VERSION}_{JAR_BUILD}/"
    "Lavalink.jar"
)

# self._lavalink_download_dir: Optional[pathlib.Path]
# self._lavalink_jar_file: Final[pathlib.Path] = self._lavalink_download_dir / "Lavalink.jar"
# BUNDLED_APP_YML: Final[pathlib.Path] = pathlib.Path(__file__).parent / "data" / "application.yml"
# LAVALINK_APP_YML: Final[pathlib.Path] = self._lavalink_download_dir / "application.yml"

_RE_READY_LINE: Final[Pattern] = re.compile(rb"Started Launcher in \S+ seconds")
_FAILED_TO_START: Final[Pattern] = re.compile(rb"Web server failed to start\. (.*)")
_RE_BUILD_LINE: Final[Pattern] = re.compile(rb"Build:\s+(?P<build>\d+)")
_RE_PORT_IN_USE: Final[Pattern] = re.compile(rb"Port \d+ was already in use")

_RE_JAVA_VERSION_LINE_PRE223: Final[Pattern] = re.compile(
    r'version "1\.(?P<major>[0-8])\.(?P<minor>0)(?:_(?:\d+))?(?:-.*)?"'
)
_RE_JAVA_VERSION_LINE_223: Final[Pattern] = re.compile(
    r'version "(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.\d+)*(\-[a-zA-Z0-9]+)?"'
)

LAVALINK_BRANCH_LINE: Final[Pattern] = re.compile(rb"Branch\s+(?P<branch>[\w\-\d_.]+)")
LAVALINK_JAVA_LINE: Final[Pattern] = re.compile(rb"JVM:\s+(?P<jvm>\d+[.\d+]*)")
LAVALINK_LAVAPLAYER_LINE: Final[Pattern] = re.compile(rb"Lavaplayer\s+(?P<lavaplayer>\d+[.\d+]*)")
LAVALINK_BUILD_TIME_LINE: Final[Pattern] = re.compile(rb"Build time:\s+(?P<build_time>\d+[.\d+]*)")


class ServerManager:
    def __init__(self, bot, config):
        self._lavalink_download_dir: Optional[pathlib.Path] = None
        self._lavalink_jar_file: Optional[pathlib.Path] = None
        self._bundled_app_yml: Optional[pathlib.Path] = None
        self._lavalink_app_yml: Optional[pathlib.Path] = None

        self._java_available: Optional[bool] = None
        self._java_version: Optional[Tuple[int, int]] = None
        self._up_to_date: Optional[bool] = None
        self._blacklisted_archs: List[str] = []

        self._lavaplayer: Optional[str] = None
        self._lavalink_build: Optional[int] = None
        self._jvm: Optional[str] = None
        self._lavalink_branch: Optional[str] = None
        self._buildtime: Optional[str] = None
        self._java_exc: str = "java"

        self._ready: asyncio.Event = asyncio.Event()
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown: bool = False

        self._bot = bot
        self._config = config

    @property
    def path(self) -> Optional[str]:
        """str: java path"""
        return self._java_exc

    @property
    def jvm(self) -> Optional[str]:
        """str: java version"""
        return self._jvm

    @property
    def lavaplayer(self) -> Optional[str]:
        """str: lavaplayer version"""
        return self._lavaplayer

    @property
    def ll_build(self) -> Optional[int]:
        """str: lavalink build"""
        return self._lavalink_build

    @property
    def ll_branch(self) -> Optional[str]:
        """str: lavalink branch"""
        return self._lavalink_branch

    @property
    def build_time(self) -> Optional[str]:
        """str: lavalink build time"""
        return self._buildtime

    @property
    def is_running(self) -> bool:
        """bool: whether or not the ll server is running"""
        if self._shutdown or not self._proc:
            return False
        return True

    async def start_ll_server(self, java_path: str):
        """Starts the internal lavalink server and handles jar downloading

        Parameters
        ----------
        bot: Red
            The bot object to start the connection from
        java_path: str
            the java path to use
        """
        self._lavalink_download_dir = data_manager.cog_data_path(raw_name="Audio")
        self._lavalink_jar_file = self._lavalink_download_dir / "Lavalink.jar"
        self._bundled_app_yml = (
            pathlib.Path(sys.modules["redbot"].__file__).parent
            / "cogs"
            / "audio"
            / "data"
            / "application.yml"
        )
        self._lavalink_app_yml = self._lavalink_download_dir / "application.yml"

        self._shutdown = False
        arch_name = platform.machine()
        if arch_name in self._blacklisted_archs:
            raise asyncio.CancelledError(
                "You are attempting to run Lavalink audio on an unsupported machine architecture."
            )
        self._java_exc = java_path

        if self._proc:
            if self._proc.returncode is None:
                raise RuntimeError("Internal Lavalink server is already running")

        await self.maybe_download_jar()

        shutil.copy(self._bundled_app_yml, self._lavalink_app_yml)

        args = await self._get_jar_args()
        self._proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=str(self._lavalink_download_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        log.info(f"Internal Lavalink server started. Pid: {self._proc.pid}")

        try:
            await asyncio.wait_for(self._wait_for_launcher(), timeout=120)
            self._bot.dispatch("red_lavalink_server_started", java_path)
        except asyncio.TimeoutError:
            log.warning(
                "Timeout occured whilst waiting for internal Lavalink server to become ready"
            )

        self._monitor_task = asyncio.create_task(self._monitor())
        self._monitor_task.add_done_callback(task_callback)

    async def shutdown_ll_server(self) -> None:
        """Stops the internal lavalink server"""
        if self._shutdown or not self._proc:
            # For convenience, calling this method more than once or calling it before starting it
            # does nothing.
            return
        log.info("Shutting down internal Lavalink server")
        if self._monitor_task is not None:
            self._monitor_task.cancel()

        self._proc.terminate()
        await self._proc.wait()
        # self._bot.dispatch("lavalink_server_stopped")
        self._shutdown = True

    async def _monitor(self) -> None:
        try:
            while self._proc.returncode is None:
                await asyncio.sleep(0.5)

            # This task hasn't been cancelled - Lavalink was shut down by something else
            log.info("Internal Lavalink jar shutdown unexpectedly")
            if not self._has_java_error():
                log.info("Restarting internal Lavalink server")
                await self.start_ll_server(self._java_exc)
            else:
                log.critical(
                    "Your Java is borked. Please find the hs_err_pid%d.log file"
                    " in the Audio data folder and report this issue.",
                    self._proc.pid,
                )
        except asyncio.CancelledError:
            self._bot.dispatch("red_lavalink_server_stopped")

    async def _wait_for_launcher(self) -> None:
        log.debug("Waiting for Lavalink server to be ready")
        lastmessage = 0
        for i in itertools.cycle(range(50)):
            line = await self._proc.stdout.readline()
            if _RE_READY_LINE.search(line):
                self._ready.set()
                log.info("Internal Lavalink server is ready to receive requests.")
                break
            if _FAILED_TO_START.search(line):
                # if _RE_PORT_IN_USE.search(line):
                #     raise PortAlreadyInUse
                raise RuntimeError(f"Lavalink failed to start: {line.decode().strip()}")
            if self._proc.returncode is not None and lastmessage + 2 < time.time():
                # Avoid Console spam only print once every 2 seconds
                lastmessage = time.time()
                log.critical("Internal lavalink server exited early")
            if i == 49:
                # Sleep after 50 lines to prevent busylooping
                await asyncio.sleep(0.1)

    def _has_java_error(self) -> bool:
        poss_error_file = self._lavalink_download_dir / "hs_err_pid{}.log".format(self._proc.pid)
        return poss_error_file.exists()

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

    async def _has_java(self) -> Tuple[bool, Optional[Tuple[int, int]]]:
        java_exc = shutil.which(self._java_exc)
        java_available = java_exc is not None
        if not java_available:
            self._java_available = False
            self._java_version = None
        else:
            self._java_version = version = await self._get_java_version()
            self._java_available = (
                (11, 0) <= version < (12, 0)
            )  # or ((13, 0) <= version < (14, 0))
            self._java_exc = java_exc
        return self._java_available, self._java_version

    async def _get_jar_args(self) -> List[str]:
        java_available, java_version = await self._has_java()

        if not java_available:
            raise RuntimeError("You must install Java 11 for Lavalink to run.")

        return [
            self._java_exc,
            "-Djdk.tls.client.protocols=TLSv1.2",
            "-jar",
            str(self._lavalink_jar_file),
        ]

    async def _is_up_to_date(self) -> None:
        args = await self._get_jar_args()
        args.append("--version")

        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(self._lavalink_download_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        if (build := _RE_BUILD_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            return False
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

        build = int(build["build"])
        date = buildtime["build_time"].decode()
        date = date.replace(".", "/")
        self._lavalink_build = build
        self._lavalink_branch = branch["branch"].decode()
        self._jvm = java["jvm"].decode()
        self._lavaplayer = lavaplayer["lavaplayer"].decode()
        self._buildtime = date
        self._up_to_date = build >= JAR_BUILD

        return self._up_to_date

    async def _download_jar(self) -> None:
        log.info("Downloading Lavalink.jar...")
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            async with session.get(LAVALINK_DOWNLOAD_URL) as response:
                if response.status == 404:
                    # A 404 means our LAVALINK_DOWNLOAD_URL is invalid, so likely the jar version
                    # hasn't been published yet
                    raise LavalinkDownloadFailed(
                        f"Lavalink jar version {JAR_VERSION}_{JAR_BUILD} hasn't been published "
                        "yet",
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

                shutil.move(path, str(self._lavalink_jar_file), copy_function=shutil.copyfile)

        log.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))
        await self._is_up_to_date()

    async def maybe_download_jar(self) -> None:
        """Checks jar version and redownloads if outdated"""
        if not (self._lavalink_jar_file.exists() and await self._is_up_to_date()):
            await self._download_jar()
