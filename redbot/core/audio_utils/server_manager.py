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

from typing import ClassVar, Optional, Final, Pattern, List, Tuple

from .api_utils import task_callback
from .errors import LavalinkDownloadFailed

from redbot.core import data_manager, config

log = logging.getLogger("red.core.audio.server_manager")

JAR_VERSION: Final[str] = "3.3.2.3"
JAR_BUILD: Final[int] = 1236
LAVALINK_DOWNLOAD_URL: Final[str] = (
    "https://github.com/Cog-Creators/Lavalink-Jars/releases/download/"
    f"{JAR_VERSION}_{JAR_BUILD}/"
    "Lavalink.jar"
)

# cls._lavalink_download_dir: Optional[pathlib.Path]
# cls._lavalink_jar_file: Final[pathlib.Path] = cls._lavalink_download_dir / "Lavalink.jar"
# BUNDLED_APP_YML: Final[pathlib.Path] = pathlib.Path(__file__).parent / "data" / "application.yml"
# LAVALINK_APP_YML: Final[pathlib.Path] = cls._lavalink_download_dir / "application.yml"

_RE_READY_LINE: Final[Pattern] = re.compile(rb"Started Launcher in \S+ seconds")
_FAILED_TO_START: Final[Pattern] = re.compile(rb"Web server failed to start\. (.*)")
_RE_BUILD_LINE: Final[Pattern] = re.compile(rb"Build:\s+(?P<build>\d+)")

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
    data_manager.load_basic_configuration("bot")
    _lavalink_download_dir : ClassVar[pathlib.Path] = data_manager.cog_data_path(raw_name="Audio")
    _lavalink_jar_file: Final[pathlib.Path] = _lavalink_download_dir / "Lavalink.jar"
    _bundled_app_yml: Final[pathlib.Path] = pathlib.Path(__file__).parent / "data" / "application.yml"
    _lavalink_app_yml: Final[pathlib.Path] = _lavalink_download_dir / "application.yml"
    
    _java_available: ClassVar[Optional[bool]] = None
    _java_version: ClassVar[Optional[Tuple[int, int]]] = None
    _up_to_date: ClassVar[Optional[bool]] = None
    _blacklisted_archs: ClassVar[List[str]] = []

    _lavaplayer: ClassVar[Optional[str]] = None
    _lavalink_build: ClassVar[Optional[int]] = None
    _jvm: ClassVar[Optional[str]] = None
    _lavalink_branch: ClassVar[Optional[str]] = None
    _buildtime: ClassVar[Optional[str]] = None
    _java_exc: ClassVar[str] = "java"

    _ready: ClassVar[asyncio.Event] = asyncio.Event()
    _proc: ClassVar[Optional[asyncio.subprocess.Process]] = None
    _monitor_task: ClassVar[Optional[asyncio.Task]] = None
    _shutdown: ClassVar[bool] = False

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
    def ll_build(self) -> Optional[int]:
        return self._lavalink_build

    @property
    def ll_branch(self) -> Optional[str]:
        return self._lavalink_branch

    @property
    def build_time(self) -> Optional[str]:
        return self._buildtime

    @classmethod
    async def start(cls, java_path: str):
        cls._shutdown = False
        arch_name = platform.machine()
        if arch_name in cls._blacklisted_archs:
            raise asyncio.CancelledError(
                "You are attempting to run Lavalink audio on an unsupported machine architecture."
            )
        cls._java_exc = java_path

        if cls._proc:
            if cls._proc.returncode is None:
                raise RuntimeError("Internal Lavalink server is already running")

        await cls.maybe_download_jar()

        #handle application.yml copying

        args = await cls._get_jar_args()
        cls._proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=str(cls._lavalink_download_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        log.info(f"Internal Lavalink server started. Pid: {cls._proc.pid}")

        try:
            await asyncio.wait_for(cls._wait_for_launcher(), timeout=120)
        except asyncio.TimeoutError:
            log.warning("Timeout occured whilst waiting for internal Lavalink server to become ready")

        cls._monitor_task = asyncio.create_task(cls._monitor())
        cls._monitor_task.add_done_callback(task_callback)

    @classmethod
    async def shutdown(cls) -> None:
        if cls._shutdown or not cls._proc:
            # For convenience, calling this method more than once or calling it before starting it
            # does nothing.
            return
        log.info("Shutting down internal Lavalink server")
        if cls._monitor_task is not None:
            cls._monitor_task.cancel()
        cls._proc.terminate()
        await cls._proc.wait()
        cls._shutdown = True

    @classmethod
    def is_running(cls) -> bool:
        if cls._shutdown or not cls._proc:
            return False
        return True

    @classmethod
    async def _monitor(cls) -> None:
        while cls._proc.returncode is None:
            await asyncio.sleep(0.5)

        # This task hasn't been cancelled - Lavalink was shut down by something else
        log.info("Internal Lavalink jar shutdown unexpectedly")
        if not cls._has_java_error():
            log.info("Restarting internal Lavalink server")
            await cls.start(cls._java_exc)
        else:
            log.critical(
                "Your Java is borked. Please find the hs_err_pid%d.log file"
                " in the Audio data folder and report this issue.",
                cls._proc.pid,
            )

    @classmethod
    async def _wait_for_launcher(cls) -> None:
        log.debug("Waiting for Lavalink server to be ready")
        lastmessage = 0
        for i in itertools.cycle(range(50)):
            line = await cls._proc.stdout.readline()
            if _RE_READY_LINE.search(line):
                cls._ready.set()
                log.info("Internal Lavalink server is ready to receive requests.")
                break
            if _FAILED_TO_START.search(line):
                raise RuntimeError(f"Lavalink failed to start: {line.decode().strip()}")
            if cls._proc.returncode is not None and lastmessage + 2 < time.time():
                # Avoid Console spam only print once every 2 seconds
                lastmessage = time.time()
                log.critical("Internal lavalink server exited early")
            if i == 49:
                # Sleep after 50 lines to prevent busylooping
                await asyncio.sleep(0.1)

    @classmethod
    def _has_java_error(cls) -> bool:
        poss_error_file = cls._lavalink_download_dir / "hs_err_pid{}.log".format(cls._proc.pid)
        return poss_error_file.exists()

    @classmethod
    async def _get_java_version(cls) -> Tuple[int, int]:
        """This assumes we've already checked that java exists."""
        _proc: asyncio.subprocess.Process = (
            await asyncio.create_subprocess_exec(  # pylint:disable=no-member
                cls._java_exc,
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

        raise RuntimeError(f"The output of `{cls._java_exc} -version` was unexpected.")

    @classmethod
    async def _has_java(cls) -> Tuple[bool, Optional[Tuple[int, int]]]:
        java_exc = shutil.which(cls._java_exc)
        java_available = java_exc is not None
        if not java_available:
            cls._java_available = False
            cls._java_version = None
        else:
            cls._java_version = version = await cls._get_java_version()
            cls._java_available = (11, 0) <= version < (12, 0)
            cls._java_exc = java_exc
        return cls._java_available, cls._java_version

    @classmethod
    async def _get_jar_args(cls) -> List[str]:
        java_available, java_version = await cls._has_java()

        if not java_available:
            raise RuntimeError("You must install Java 11 for Lavalink to run.")

        return [
            cls._java_exc,
            "-Djdk.tls.client.protocols=TLSv1.2",
            "-jar",
            str(cls._lavalink_jar_file),
        ]

    @classmethod
    async def _is_up_to_date(cls) -> None:
        args = await cls._get_jar_args()
        args.append("--version")

        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(cls._lavalink_download_dir),
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
        cls._lavalink_build = build
        cls._lavalink_branch = branch["branch"].decode()
        cls._jvm = java["jvm"].decode()
        cls._lavaplayer = lavaplayer["lavaplayer"].decode()
        cls._buildtime = date
        cls._up_to_date = build >= JAR_BUILD

        return cls._up_to_date

    @classmethod
    async def _download_jar(cls) -> None:
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

                shutil.move(path, str(cls._lavalink_jar_file), copy_function=shutil.copyfile)

        log.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))
        await cls._is_up_to_date()

    @classmethod
    async def maybe_download_jar(cls) -> None:
        if not (cls._lavalink_jar_file.exists() and await cls._is_up_to_date()):
            await cls._download_jar()