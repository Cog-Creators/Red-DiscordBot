# This file is retained in it's slimmest form which handles autorestart for users on
# windows and osx until we have proper autorestart docs for theses oses
# no new features will be added to this file
# issues in this file are to be met with removal, not with fixes.
import asyncio
import os
import platform
import subprocess
import sys
import argparse
import aiohttp

import pkg_resources
from redbot import MIN_PYTHON_VERSION
from redbot.core import __version__, version_info as red_version_info, VersionInfo
from redbot.core.utils._internal_utils import expected_version
from redbot.launcher import clear_screen

if sys.platform == "linux":
    import distro  # pylint: disable=import-error

INTERACTIVE_MODE = not len(sys.argv) > 1  # CLI flags = non-interactive

INTRO = "==========================\nRed Discord Bot - Updater\n==========================\n"

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

PYTHON_OK = sys.version_info >= MIN_PYTHON_VERSION or os.getenv("READTHEDOCS", False)


def is_venv():
    """Return True if the process is in a venv or in a virtualenv."""
    # credit to @calebj
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


async def is_outdated():
    red_pypi = "https://pypi.org/pypi/Red-DiscordBot/json"
    current_python = platform.python_version()
    async with aiohttp.ClientSession() as session:
        async with session.get("{}".format(red_pypi)) as r:
            data = await r.json()
            releases = data["releases"]
            valid_releases = sorted(
                [
                    r
                    for i in releases.keys()
                    if (r := VersionInfo.from_str(i))
                    and r.releaselevel == VersionInfo.FINAL
                    and (expected_version(current_python, releases[i][0]["requires_python"]))
                ],
                reverse=True,
            )
            pypi_version = valid_releases[0] if valid_releases else None
            return pypi_version and pypi_version > red_version_info, pypi_version


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Red - Discord Bot's updater (V3)", allow_abbrev=False
    )
    parser.add_argument(
        "--custom",
        type=str,
        nargs="?",
        help=(
            "Updates Red using the specified string "
            "(e.g git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=Red-DiscordBot[style])"
        ),
    )
    parser.add_argument("--dev", help="Updates Red from the Github repo", action="store_true")
    parser.add_argument(
        "--stable", help="Updates Red to the latest release on PyPi", action="store_true"
    )
    return parser.parse_known_args()


def update_red(dev=False, custom=None, stable=True):
    interpreter = sys.executable
    print("Updating Red...")
    # If the user ran redbot-update.exe, updating with pip will fail
    # on windows since the file is open and pip will try to overwrite it.
    # We have to rename redbot-update.exe in this case.
    updater_script = os.path.abspath(sys.argv[0])
    old_name = updater_script + ".exe"
    new_name = updater_script + ".old"
    renamed = False
    skip = False
    if "redbot-update" in updater_script and IS_WINDOWS:
        renamed = True
        if os.path.exists(new_name):
            os.remove(new_name)
        os.rename(old_name, new_name)

    red_pkg = pkg_resources.get_distribution("Red-DiscordBot")
    installed_extras = []
    for extra, reqs in red_pkg._dep_map.items():
        if extra is None:
            continue
        try:
            pkg_resources.require(req.name for req in reqs)
        except pkg_resources.DistributionNotFound:
            pass
        else:
            installed_extras.append(extra)

    if installed_extras:
        package_extras = f"[{','.join(installed_extras)}]"
    else:
        package_extras = ""
    if custom:
        package = custom
    elif dev:
        package = "git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop"
        if package_extras:
            package += "#egg=Red-DiscordBot{}".format(package_extras)
    else:
        loop = asyncio.get_event_loop()
        outdated, new_version = loop.run_until_complete(is_outdated())
        if not outdated:
            print("You are on the latest available release.")
            skip = True
        package = "Red-DiscordBot"
        if package_extras:
            package += "{}".format(package_extras)
    arguments = [
        interpreter,
        "-m",
        "pip",
        "install",
        "-U",
        package,
    ]
    if not skip:
        code = subprocess.call(arguments)
        if code == 0:
            print("Red has been updated")
        else:
            print("Something went wrong while updating!\nError Code: {}".format(code))

    # If redbot wasn't updated, we renamed our .exe file and didn't replace it
    scripts = os.listdir(os.path.dirname(updater_script))
    if renamed and "redbot-update.exe" not in scripts:
        os.rename(new_name, old_name)


def wait():
    if INTERACTIVE_MODE:
        input("Press enter to continue.")


def user_choice():
    return input("> ").lower().strip()


def main_menu():
    if IS_WINDOWS:
        os.system("TITLE Red - Discord Bot V3 Updater")
    clear_screen()
    while True:
        print(INTRO)
        print("\033[4mCurrent version:\033[0m {}".format(__version__))
        print("")
        print("1. Update to latest release")
        print("2. Update to latest dev commit")
        print("3. Custom location")
        print("0. Exit")
        choice = user_choice()
        if choice == "1":
            update_red(stable=True)
            wait()
        elif choice == "2":
            update_red(dev=True)
            wait()
        elif choice == "3":
            print(
                "Enter the location to pass to pip install.\n"
                "(e.g git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=Red-DiscordBot[style])"
            )
            update_red(custom=user_choice())
            wait()
        elif choice == "0":
            break
        clear_screen()


def main():
    if not is_venv():
        print("You are calling me outside of your venv, I will not update Red.")
        sys.exit(1)

    args, _ = parse_cli_args()
    if not PYTHON_OK:
        print(
            "Python {req_ver} is required to run Red, but you have {sys_ver}!".format(
                req_ver=".".join(map(str, MIN_PYTHON_VERSION)), sys_ver=sys.version
            )
        )  # Don't make an f-string, these may not exist on the python version being rejected!
        sys.exit(1)

    if INTERACTIVE_MODE:
        main_menu()
    else:
        update_red(dev=args.dev, custom=args.custom, stable=args.stable)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
