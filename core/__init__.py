from core.config import Config
from subprocess import run, PIPE
from collections import namedtuple
from main import determine_main_folder

__all__ = ["Config", "__version__"]
version_info = namedtuple("VersionInfo", "major minor patch")

BASE_VERSION = version_info(3, 0, 0)


def get_latest_version():
    main_folder = determine_main_folder()
    try:
        p = run(
            "git describe --abbrev=0 --tags".split(),
            stdout=PIPE,
            cwd=str(main_folder)
        )
    except FileNotFoundError:
        # No git
        return BASE_VERSION

    if p.returncode != 0:
        return BASE_VERSION

    stdout = p.stdout.strip().decode()
    if stdout.startswith("v"):
        numbers = stdout[1:].split('.')
        args = [0, 0, 0]
        for i in range(3):
            try:
                args[i] = int(numbers[i])
            except (IndexError, ValueError):
                args[i] = 0
        return version_info(*args)
    return BASE_VERSION

__version__ = get_latest_version()

