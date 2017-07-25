from __future__ import print_function  # Used to allow python2 to run this
import os
import sys
import subprocess
from enum import Enum
try:
    import requests
except ImportError:
    requests = None
import platform
try:
    import pip
except ImportError:
    pip = None


FFMPEG_32 = "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.zip"
FFMPEG_64 = "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.zip"
GFW_LATEST_RELEASE = "https://api.github.com/repos/git-for-windows/git/releases/latest"
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


def do_windows_install():
    good_to_continue = True
    # Python 3.5 install confirmation
    if not PYTHON_OK:
        print("I need Python 3.5 to work properly!")
        good_to_continue = False

    # ffmpeg install confirmation
    ffmpegdir = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "ffmpeg", "bin")
    try:
        ffmpegdircontents = os.listdir(ffmpegdir)
    except FileNotFoundError:
        print("I need ffmpeg in order for audio to work properly!")
        good_to_continue = False
    else:
        if "ffmpeg.exe" not in ffmpegdircontents \
                or "ffplay.exe" not in ffmpegdircontents \
                or "ffprobe.exe" not in ffmpegdircontents:
            print("I need ffmpeg in order for audio to work properly!")
            good_to_continue = False

    # git install confirmation
    gitdir = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Git", "bin")
    try:
        gitcontents = os.listdir(gitdir)
    except FileNotFoundError:
        print("I need git in order for Downloader to work properly!")
        good_to_continue = False
    else:
        if "git.exe" not in gitcontents:
            print("I need git in order for Downloader to work properly!")
            good_to_continue = False

    # Print out a message directing the user to run the powershell script and then exit
    if not good_to_continue:
        print("Please run the powershell script to install requirements")
        exit(InstallerExitCodes.WINFAIL)
    else:
        print("All requirements appear to be installed properly!")


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
    WINFAIL = 4
    HOMEBREWFAIL = 5
    BREWINSTALLFAIL = 6


if __name__ == "__main__":
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
        do_windows_install()
    elif IS_MAC:
        do_mac_install()
    else:
        do_linux_install()
