import asyncio
import asyncio.subprocess  # disables for # https://github.com/PyCQA/pylint/issues/1469
import itertools
import logging
import pathlib
import platform
import re
import shutil
import sys
import tempfile
import time
from typing import ClassVar, List, Optional, Tuple

import aiohttp
from tqdm import tqdm

from redbot.core import data_manager
from .errors import LavalinkDownloadFailed

JAR_VERSION = "3.2.1"
JAR_BUILD = 823
LAVALINK_DOWNLOAD_URL = (
    f"https://github.com/Cog-Creators/Lavalink-Jars/releases/download/{JAR_VERSION}_{JAR_BUILD}/"
    f"Lavalink.jar"
)
LAVALINK_DOWNLOAD_DIR = data_manager.cog_data_path(raw_name="Audio")
LAVALINK_JAR_FILE = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"

BUNDLED_APP_YML = pathlib.Path(__file__).parent / "data" / "application.yml"
LAVALINK_APP_YML = LAVALINK_DOWNLOAD_DIR / "application.yml"

READY_LINE_RE = re.compile(rb"Started Launcher in \S+ seconds")
BUILD_LINE_RE = re.compile(rb"Build:\s+(?P<build>\d+)")

log = logging.getLogger("red.audio.manager")


class ServerManager:

    _java_available: ClassVar[Optional[bool]] = None
    _java_version: ClassVar[Optional[Tuple[int, int]]] = None
    _up_to_date: ClassVar[Optional[bool]] = None
    _blacklisted_archs = []

    def __init__(self) -> None:
        self.ready = asyncio.Event()

        self._proc: Optional[asyncio.subprocess.Process] = None  # pylint:disable=no-member
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown: bool = False

    async def start(self) -> None:
        arch_name = platform.machine()
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

    @classmethod
    async def _get_jar_args(cls) -> List[str]:
        java_available, java_version = await cls._has_java()
        if not java_available:
            raise RuntimeError("You must install Java 1.8+ for Lavalink to run.")

        if java_version == (1, 8):
            extra_flags = ["-Dsun.zip.disableMemoryMapping=true"]
        elif java_version >= (11, 0):
            extra_flags = ["-Djdk.tls.client.protocols=TLSv1.2"]
        else:
            extra_flags = []

        return ["java", *extra_flags, "-jar", str(LAVALINK_JAR_FILE)]

    @classmethod
    async def _has_java(cls) -> Tuple[bool, Optional[Tuple[int, int]]]:
        if cls._java_available is not None:
            # Return cached value if we've checked this before
            return cls._java_available, cls._java_version
        java_available = shutil.which("java") is not None
        if not java_available:
            cls.java_available = False
            cls.java_version = None
        else:
            cls._java_version = version = await cls._get_java_version()
            cls._java_available = (2, 0) > version >= (1, 8) or version >= (8, 0)
        return cls._java_available, cls._java_version

    @staticmethod
    async def _get_java_version() -> Tuple[int, int]:
        """
        This assumes we've already checked that java exists.
        """
        _proc: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(  # pylint:disable=no-member
            "java", "-version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
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
        version_line_re = re.compile(
            r'version "(?P<major>\d+).(?P<minor>\d+).\d+(?:_\d+)?(?:-[A-Za-z0-9]+)?"'
        )
        short_version_re = re.compile(r'version "(?P<major>\d+)"')

        lines = version_info.splitlines()
        for line in lines:
            match = version_line_re.search(line)
            short_match = short_version_re.search(line)
            if match:
                return int(match["major"]), int(match["minor"])
            elif short_match:
                return int(short_match["major"]), 0

        raise RuntimeError(
            "The output of `java -version` was unexpected. Please report this issue on Red's "
            "issue tracker."
        )

    async def _wait_for_launcher(self) -> None:
        log.debug("Waiting for Lavalink server to be ready")
        lastmessage = 0
        for i in itertools.cycle(range(50)):
            line = await self._proc.stdout.readline()
            if READY_LINE_RE.search(line):
                self.ready.set()
                break
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
            await self.start()
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

    @staticmethod
    async def _download_jar() -> None:
        log.info("Downloading Lavalink.jar...")
        async with aiohttp.ClientSession() as session:
            async with session.get(LAVALINK_DOWNLOAD_URL) as response:
                if response.status == 404:
                    # A 404 means our LAVALINK_DOWNLOAD_URL is invalid, so likely the jar version
                    # hasn't been published yet
                    raise LavalinkDownloadFailed(
                        f"Lavalink jar version {JAR_VERSION}_{JAR_BUILD} hasn't been published "
                        f"yet",
                        response=response,
                        should_retry=False,
                    )
                elif 400 <= response.status < 600:
                    # Other bad responses should be raised but we should retry just incase
                    raise LavalinkDownloadFailed(response=response, should_retry=True)
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

                shutil.move(path, str(LAVALINK_JAR_FILE), copy_function=shutil.copyfile)

        log.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))

    @classmethod
    async def _is_up_to_date(cls):
        if cls._up_to_date is True:
            # Return cached value if we've checked this before
            return True
        args = await cls._get_jar_args()
        args.append("--version")
        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        match = BUILD_LINE_RE.search(stdout)
        if not match:
            # Output is unexpected, suspect corrupted jarfile
            return False
        build = int(match["build"])
        cls._up_to_date = build >= JAR_BUILD
        return cls._up_to_date

    @classmethod
    async def maybe_download_jar(cls):
        if not (LAVALINK_JAR_FILE.exists() and await cls._is_up_to_date()):
            await cls._download_jar()
