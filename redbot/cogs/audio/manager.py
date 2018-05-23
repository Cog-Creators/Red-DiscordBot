import shlex
import shutil
import asyncio
from subprocess import Popen, DEVNULL, PIPE
import os
import logging

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


async def has_java(loop):
    java_available = shutil.which("java") is not None
    if not java_available:
        return False

    version = await get_java_version(loop)
    return version >= (1, 8), version


async def get_java_version(loop):
    """
    This assumes we've already checked that java exists.
    """
    proc = Popen(shlex.split("java -version", posix=os.name == "posix"), stdout=PIPE, stderr=PIPE)
    _, err = proc.communicate()

    version_info = str(err, encoding="utf-8")

    version_line = version_info.split("\n")[0]
    version_start = version_line.find('"')
    version_string = version_line[version_start + 1 : -1]
    major, minor = version_string.split(".")[:2]
    return int(major), int(minor)


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
