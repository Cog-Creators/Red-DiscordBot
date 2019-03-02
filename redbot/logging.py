import logging.handlers
import pathlib
import re
import sys

from redbot.core import data_manager

MAX_OLD_LOGS = 9


def init_logging(debug: bool) -> None:
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.WARNING)
    base_logger = logging.getLogger("red")
    if debug is True:
        base_logger.setLevel(logging.DEBUG)
    else:
        base_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    base_logger.addHandler(stdout_handler)
    dpy_logger.addHandler(stdout_handler)

    logs_dir = data_manager.core_data_path() / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
    # Rotate old logs
    paths = []
    for path in logs_dir.iterdir():
        match = re.match(r"red\.(?P<log_num>\d+)\.part(?P<part>\d+)\.log", path.name)
        if match:
            log_num = int(match["log_num"])
            if log_num < MAX_OLD_LOGS:
                paths.append((log_num, match["part"], path))
            else:
                path.unlink()
            continue
        match = re.match(r"latest\.part(?P<part>\d+)\.log", path.name)
        if match:
            paths.append((0, match["part"], path))
    for log_num, part, path in sorted(paths, reverse=True):
        path.replace(path.parent / f"red.{log_num + 1}.part{part}.log")

    fhandler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "latest.part0.log",
        encoding="utf-8",
        mode="a",
        maxBytes=500_000,  # About 500KB per logfile
        backupCount=9,     # Maximum 10 parts to each log
    )
    fhandler.namer = _namer
    fhandler.setFormatter(formatter)

    base_logger.addHandler(fhandler)


def _namer(defaultname: str) -> str:
    # This renames `latest.part0.log` to `latest.part1.log` and so on, when the original gets too
    # large. `defaultname` is in the format `latest.part0.log.X`, where X is the index of the next
    # part.
    # See the `doRollover` method of `logging.handlers.RotatingFileHandler`.
    path = pathlib.Path(defaultname)
    part_num = path.suffix[1:]
    return path.parent / f"latest.part{part_num}.log"
