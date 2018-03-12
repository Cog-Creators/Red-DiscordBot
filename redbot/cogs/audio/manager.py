import shlex
import asyncio
from subprocess import Popen, DEVNULL
import os

proc = None
SHUTDOWN = asyncio.Event()


async def monitor_lavalink_server(loop):
    while not SHUTDOWN.is_set():
        if proc.poll() is not None:
            break
        await asyncio.sleep(0.5)

    if not SHUTDOWN.is_set():
        print("Lavalink jar shutdown, restarting.")
        await start_lavalink_server(loop)


async def start_lavalink_server(loop):
    from . import LAVALINK_DOWNLOAD_DIR, LAVALINK_JAR_FILE
    start_cmd = "java -jar {}".format(LAVALINK_JAR_FILE.resolve())

    global proc
    proc = Popen(
        shlex.split(start_cmd, posix=os.name == 'posix'),
        cwd=str(LAVALINK_DOWNLOAD_DIR),
        stdout=DEVNULL, stderr=DEVNULL
    )

    print("Lavalink jar started. PID: {}".format(proc.pid))

    loop.create_task(monitor_lavalink_server(loop))


def shutdown_lavalink_server():
    print("Shutting down lavalink server.")
    SHUTDOWN.set()
    if proc is not None:
        proc.terminate()
