from __future__ import print_function  # Used to allow python2 to run this
import os
import sys
import subprocess
from enum import Enum
import argparse
import platform
try:
    import pip
except ImportError:
    pip = None


IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_64BIT = platform.machine().endswith("64")


if IS_WINDOWS:
    PYTHON_OK = (3, 5) <= sys.version_info < (3, 6)
else:
    PYTHON_OK = sys.version_info >= (3, 5)


if not IS_WINDOWS and not IS_MAC:  # On linux, so import distro to help determine distro
    try:
        import distro
    except ImportError:
        distro = None


def parse_cli_args():
    parser = argparse.ArgumentParser(description="Red-DiscordBot's installer")
    parser.add_argument("--install-reqs", "-i",
                        help="Installs the needed prereqs for Red",
                        action="store_true")
    parser.add_argument("--setup-red", "-s",
                        help="Downloads and walks through setting up Red",
                        action="store_true")
    parser.add_argument("--update-red", "-u",
                        help="Updates Red",
                        action="store_true")
    return parser.parse_args()


def do_mac_install():
    homebrew_install = subprocess.call(
        [
            os.path.join("/", "usr", "bin", "ruby"), "-e",
            '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"'
        ]
    )
    if homebrew_install != 0:
        print("Something went wrong while installing Homebrew!")
        exit(InstallerExitCodes.HOMEBREWFAIL)
    brewcommands = {
        "python3": ["brew", "install", "python3", "--with-brewed-openssl"],
        "git": ["brew", "install", "git"],
        "ffmpeg": ["brew", "install", "ffmpeg", "--with-ffplay"],
        "opus": ["brew", "install", "opus"]
    }
    for item in list(brewcommands.keys()):
        attempt = subprocess.call(brewcommands[item])
        if attempt != 0:
            print("Something went wrong while installing {}!".format(item))
            exit(InstallerExitCodes.BREWINSTALLFAIL)
    else:
        print("Successfully installed the necessary requirements")


def ubuntu_install():
    pass


def do_linux_install():
    distro_name = distro.name()
    distro_version = [int(part) for part in distro.version().split(".")]


class InstallerExitCodes(Enum):
    SUCCESS = 0
    IMPROPERPYVER = 1
    NOPIP = 2
    PIPFAILED = 3
    ARGCONFLICT = 4
    HOMEBREWFAIL = 5
    BREWINSTALLFAIL = 6


args = parse_cli_args()

if __name__ == "__main__":
    if args.install_reqs:
        if pip is None:
            print("It appears pip is not installed! I need pip for installing requirements!")
            exit(InstallerExitCodes.NOPIP)
        if not IS_WINDOWS and not IS_MAC and distro is None:
            print("You are missing some requirements for using the launcher!")
            print("Attempting to fix this now...")
            status = pip.main(["install", "-U", "-r", "launcher-requirements.txt"])
            if status == 0:
                print("Launcher requirements installed successfully")
                print("Please relaunch the launcher once it exits")
                exit(InstallerExitCodes.SUCCESS)
            else:
                print("Error with installing requirements, error code {}".format(status))
                exit(InstallerExitCodes.PIPFAILED)
        if IS_WINDOWS:
            print(
                "In order to properly install requirements on Windows, "
                "you need to use the powershell script (launch-install-win.ps1)"
            )
        elif IS_MAC:
            do_mac_install()
        else:
            do_linux_install()
    if args.setup_red and args.update_red:
        print("Conflicting arguments --setup-red and --update-red! I can't do both at the same time!")
        exit(InstallerExitCodes.ARGCONFLICT)

    if args.setup_red:
        pass
    elif args.update_red:
        pass
