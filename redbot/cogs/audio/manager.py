import shlex
import asyncio
from subprocess import Popen, DEVNULL

proc = None
log_fd = None
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

    log_file = LAVALINK_DOWNLOAD_DIR / "lavalink.log"
    global log_fd
    log_fd = log_file.open(mode='a', encoding='utf-8')

    global proc
    proc = Popen(shlex.split(start_cmd), cwd=str(LAVALINK_DOWNLOAD_DIR),
                 stdout=DEVNULL)

    print("Lavalink jar started. PID: {}".format(proc.pid))

    loop.create_task(monitor_lavalink_server(loop))


def shutdown_lavalink_server():
    print("Shutting down lavalink server.")
    SHUTDOWN.set()
    if proc is not None:
        proc.terminate()

    if log_fd is not None:
        log_fd.close()
