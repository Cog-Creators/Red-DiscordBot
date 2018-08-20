import shlex
import shutil
import asyncio
import asyncio.subprocess
import os
import logging
import re
from subprocess import Popen, DEVNULL
from typing import Optional, Tuple

_JavaVersion = Tuple[int, int]

log = logging.getLogger("red.audio.manager")

proc = None
SHUTDOWN = asyncio.Event()


def has_java_error(pid):
    from . import LAVALINK_DOWNLOAD_DIR

    poss_error_file = LAVALINK_DOWNLOAD_DIR / "hs_err_pid{}.log".format(pid)
    return poss_error_file.exists()


async def monitor_lavalink_server(loop):
    while not SHUTDOWN.is_set():
        if proc.poll() is not None:
            break
        await asyncio.sleep(0.5)

    if not SHUTDOWN.is_set():
        log.info("Lavalink jar shutdown.")
        if not has_java_error(proc.pid):
            log.info("Restarting Lavalink jar.")
            await start_lavalink_server(loop)
        else:
            log.error(
                "Your Java is borked. Please find the hs_err_pid{}.log file"
                " in the Audio data folder and report this issue.".format(proc.pid)
            )


async def has_java(loop) -> Tuple[bool, Optional[_JavaVersion]]:
    java_available = shutil.which("java") is not None
    if not java_available:
        return False, None

    version = await get_java_version(loop)
    return (2, 0) > version >= (1, 8) or version >= (8, 0), version


async def get_java_version(loop) -> _JavaVersion:
    """
    This assumes we've already checked that java exists.
    """
    _proc: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
        "java",
        "-version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        loop=loop,
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
    version_line_re = re.compile(r'version "(?P<major>\d+).(?P<minor>\d+).\d+(?:_\d+)?"')

    lines = version_info.splitlines()
    for line in lines:
        match = version_line_re.search(line)
        if match:
            return int(match["major"]), int(match["minor"])

    raise RuntimeError(
        "The output of `java -version` was unexpected. Please report this issue on Red's "
        "issue tracker."
    )


async def start_lavalink_server(loop):
    java_available, java_version = await has_java(loop)
    if not java_available:
        raise RuntimeError("You must install Java 1.8+ for Lavalink to run.")

    extra_flags = ""
    if java_version == (1, 8):
        extra_flags = "-Dsun.zip.disableMemoryMapping=true"

    from . import LAVALINK_DOWNLOAD_DIR, LAVALINK_JAR_FILE

    start_cmd = "java {} -jar {}".format(extra_flags, LAVALINK_JAR_FILE.resolve())

    global proc
    proc = Popen(
        shlex.split(start_cmd, posix=os.name == "posix"),
        cwd=str(LAVALINK_DOWNLOAD_DIR),
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    log.info("Lavalink jar started. PID: {}".format(proc.pid))

    loop.create_task(monitor_lavalink_server(loop))


def shutdown_lavalink_server():
    log.info("Shutting down lavalink server.")
    SHUTDOWN.set()
    global proc
    if proc is not None:
        proc.terminate()
        proc.wait()
        proc = None
