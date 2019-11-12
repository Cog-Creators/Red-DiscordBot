# -*- coding: utf-8 -*-
# Standard Library
import logging.handlers
import pathlib
import re
import sys

from typing import List, Optional, Tuple

MAX_OLD_LOGS = 8


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Custom rotating file handler.

    This file handler rotates a bit differently to the one in stdlib.

    For a start, this works off of a "stem" and a "directory". The stem
    is the base name of the log file, without the extension. The
    directory is where all log files (including backups) will be placed.

    Secondly, this logger rotates files downwards, and new logs are
    *started* with the backup number incremented. The stdlib handler
    rotates files upwards, and this leaves the logs in reverse order.

    Thirdly, naming conventions are not customisable with this class.
    Logs will initially be named in the format "{stem}.log", and after
    rotating, the first log file will be renamed "{stem}-part1.log",
    and a new file "{stem}-part2.log" will be created for logging to
    continue.

    A few things can't be modified in this handler: it must use append
    mode, it doesn't support use of the `delay` arg, and it will ignore
    custom namers and rotators.

    When this handler is instantiated, it will search through the
    directory for logs from previous runtimes, and will open the file
    with the highest backup number to append to.
    """

    def __init__(
        self,
        stem: str,
        directory: pathlib.Path,
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = None,
    ) -> None:
        self.baseStem = stem
        self.directory = directory.resolve()
        # Scan for existing files in directory, append to last part of existing log
        log_part_re = re.compile(rf"{stem}-part(?P<partnum>\d+).log")
        highest_part = 0
        for path in directory.iterdir():
            match = log_part_re.match(path.name)
            if match and int(match["partnum"]) > highest_part:
                highest_part = int(match["partnum"])
        if highest_part:
            filename = directory / f"{stem}-part{highest_part}.log"
        else:
            filename = directory / f"{stem}.log"
        super().__init__(
            filename,
            mode="a",
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=False,
        )

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        initial_path = self.directory / f"{self.baseStem}.log"
        if self.backupCount > 0 and initial_path.exists():
            initial_path.replace(self.directory / f"{self.baseStem}-part1.log")

        match = re.match(
            rf"{self.baseStem}(?:-part(?P<part>\d+)?)?.log", pathlib.Path(self.baseFilename).name
        )
        latest_part_num = int(match.groupdict(default="1").get("part", "1"))
        if self.backupCount < 1:
            # No backups, just delete the existing log and start again
            pathlib.Path(self.baseFilename).unlink()
        elif latest_part_num > self.backupCount:
            # Rotate files down one
            # red-part2.log becomes red-part1.log etc, a new log is added at the end.
            for i in range(1, self.backupCount):
                next_log = self.directory / f"{self.baseStem}-part{i + 1}.log"
                if next_log.exists():
                    prev_log = self.directory / f"{self.baseStem}-part{i}.log"
                    next_log.replace(prev_log)
        else:
            # Simply start a new file
            self.baseFilename = str(
                self.directory / f"{self.baseStem}-part{latest_part_num + 1}.log"
            )

        self.stream = self._open()


def init_logging(level: int, location: pathlib.Path) -> None:
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.WARNING)
    base_logger = logging.getLogger("red")
    base_logger.setLevel(level)

    formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    base_logger.addHandler(stdout_handler)
    dpy_logger.addHandler(stdout_handler)

    if not location.exists():
        location.mkdir(parents=True, exist_ok=True)
    # Rotate latest logs to previous logs
    previous_logs: List[pathlib.Path] = []
    latest_logs: List[Tuple[pathlib.Path, str]] = []
    for path in location.iterdir():
        match = re.match(r"latest(?P<part>-part\d+)?\.log", path.name)
        if match:
            part = match.groupdict(default="")["part"]
            latest_logs.append((path, part))
        match = re.match(r"previous(?:-part\d+)?.log", path.name)
        if match:
            previous_logs.append(path)
    # Delete all previous.log files
    for path in previous_logs:
        path.unlink()
    # Rename latest.log files to previous.log
    for path, part in latest_logs:
        path.replace(location / f"previous{part}.log")

    latest_fhandler = RotatingFileHandler(
        stem="latest",
        directory=location,
        maxBytes=1_000_000,  # About 1MB per logfile
        backupCount=MAX_OLD_LOGS,
        encoding="utf-8",
    )
    all_fhandler = RotatingFileHandler(
        stem="red",
        directory=location,
        maxBytes=1_000_000,
        backupCount=MAX_OLD_LOGS,
        encoding="utf-8",
    )
    for fhandler in (latest_fhandler, all_fhandler):
        fhandler.setFormatter(formatter)
        base_logger.addHandler(fhandler)
