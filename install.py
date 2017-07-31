from __future__ import print_function  # Used to allow python2 to run this
import os
import sys
from subprocess import check_output, CalledProcessError, STDOUT
from enum import Enum
import argparse
import platform
try:
    import pip
except ImportError:
    pip = None

try:
    import requests
except ImportError:
    requests = None


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
    try:
        homebrew_install = check_output(
            [
                os.path.join("/", "usr", "bin", "ruby"), "-e",
                '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"'
            ],
            stderr=STDOUT
        )
    except CalledProcessError as e:
        print("Something went wrong while installing Homebrew!\n\n")
        print(e.output.decode())
        print("Process returned code {}".format(e.returncode))
        exit(InstallerExitCodes.HOMEBREWFAIL)
    else:
        print("Successfully installed Homebrew!\n")
        print(homebrew_install.decode())

    brewcommands = {
        "python3": ["brew", "install", "python3", "--with-brewed-openssl"],
        "git": ["brew", "install", "git"],
        "ffmpeg": ["brew", "install", "ffmpeg", "--with-ffplay"],
        "opus": ["brew", "install", "opus"]
    }

    for item in list(brewcommands.keys()):
        try:
            attempt = check_output(brewcommands[item], stderr=STDOUT)
        except CalledProcessError as e:
            print("Something went wrong while installing {}!\n\n".format(item))
            print(e.output.decode())
            print("\n\nStatus code: {}".format(e.returncode))
            exit(InstallerExitCodes.BREWINSTALLFAIL)
        else:
            print("Installed {}\n\n".format(item))
            print(attempt.decode())
    else:
        print("Successfully installed the necessary requirements")


def ubuntu_install():
    print("Installing prerequisite packages...")
    print("If prompted for your password, enter it.")
    package_list = [
        "python3.5-dev", "python3-pip",
        "build-essential", "libssl-dev",
        "libffi-dev", "git", "unzip"
    ]
    # Use -K here so we ask the user to
    # enter their password every time it is needed
    try:
        aptresult = check_output(
            ["sudo", "-K", "apt-get", "install", " ".join(package_list), "-y"],
            stderr=STDOUT
        )
    except CalledProcessError as e:
        print("Error while installing requirements! Output:\n\n")
        print(e.output.decode())
        print("\n\nProcess returned code {}".format(e.returncode))
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(aptresult.decode())
        print("\n\nRequirements installed successfully.\n")
        if sys.version_info < (3, 5) and args.setup_red:
            print("Please note that the script will give an error\n"
                  "message regarding the version of python used to\n"
                  "run this installer and will then exit. You can do\n\n"
                  "python3 install.py --setup-red\n\n"
                  "to continue with setting up Red"
                  )


def do_linux_install():
    distro_name = distro.name()
    distro_version = [int(part) for part in distro.version().split(".")]


def installer_welcome_message():
    print(
        (
            "===========================\n"
            "Red Discord Bot - Installer\n"
            "===========================\n"
        )
    )


class InstallerExitCodes(Enum):
    SUCCESS = 0
    IMPROPERPYVER = 1
    NOPIP = 2
    PIPFAILED = 3
    ARGCONFLICT = 4
    HOMEBREWFAIL = 5
    BREWINSTALLFAIL = 6
    REQFAIL = 7


args = parse_cli_args()

if __name__ == "__main__":
    installer_welcome_message()
    if args.install_reqs:
        if not IS_WINDOWS and not IS_MAC and distro is None:
            if requests is None or distro is None:
                if pip is None:  # For installing requirements, we only need pip on Linux
                    print("It appears pip is not installed! I need pip for installing requirements!")
                    exit(InstallerExitCodes.NOPIP)
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
            exit(0)
        elif IS_MAC:
            do_mac_install()
        else:
            do_linux_install()
    if args.setup_red and args.update_red:
        print("Conflicting arguments --setup-red and --update-red! I can't do both at the same time!")
        exit(InstallerExitCodes.ARGCONFLICT)

    if args.setup_red:
        if not PYTHON_OK:
            print("Improper Python version detected!")
            if IS_WINDOWS:
                print("I require Python 3.5.x to work properly.")
                print("Please use the powershell script to ensure "
                      "the correct version is installed")
            else:
                print("I require at least Python 3.5.x to work properly")
            exit(InstallerExitCodes.IMPROPERPYVER)
    elif args.update_red:
        pass
