from __future__ import print_function  # Used to allow python2 to run this
import os
import sys
import subprocess
from enum import Enum
from zipfile import ZipFile
try:
    import requests
except ImportError:
    requests = None
import platform
import tarfile
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

if IS_WINDOWS:  # Import winreg to help handle adding git/ffmpeg to path
    if sys.version_info.major < 3:  # Using python 2, winreg is actually _winreg there
        import _winreg as winreg
    else:
        import winreg

if not IS_WINDOWS and not IS_MAC:  # On linux, so import distro to help determine distro
    try:
        import distro
    except ImportError:
        distro = None


def download_ffmpeg(is64bit: bool=True):
    dir_contents = os.listdir(".")
    # Remove old files so we can get updated versions
    if "ffmpeg.exe" in dir_contents:
        os.remove("ffmpeg.exe")
    if "ffplay.exe" in dir_contents:
        os.remove("ffplay.exe")
    if "ffprobe.exe" in dir_contents:
        os.remove("ffprobe.exe")

    if is64bit:
        filename = FFMPEG_64.split("/")[-1]
        print("Downloading {}".format(filename))
        data = requests.get(FFMPEG_64)
        with open(filename, "wb") as f:
            f.write(data.content)
        print("Done downloading. Extracting needed files")
        with ZipFile(filename, "r") as zf:
            pathname = filename.split(".")[0]
            zf.extract("{}/bin/ffmpeg.exe".format(pathname), path="ffmpeg.exe")
            zf.extract("{}/bin/ffplay.exe".format(pathname), path="ffplay.exe")
            zf.extract("{}/bin/ffprobe.exe".format(pathname), path="ffprobe.exe")
        print("Done extracting files. Removing downloaded zip file")
        os.remove(filename)
        print("FFmpeg has now been installed. Installation will continue")

    else:
        filename = FFMPEG_32.split("/")[-1]
        print("Downloading {}".format(filename))
        data = requests.get(FFMPEG_32)
        with open(filename, "wb") as f:
            f.write(data.content)
        print("Done downloading. Extracting needed files")
        with ZipFile(filename, "r") as zf:
            pathname = filename.split(".")[0]
            zf.extract("{}/bin/ffmpeg.exe".format(pathname), path="ffmpeg.exe")
            zf.extract("{}/bin/ffplay.exe".format(pathname), path="ffplay.exe")
            zf.extract("{}/bin/ffprobe.exe".format(pathname), path="ffprobe.exe")
        print("Done extracting files. Removing downloaded zip file")
        os.remove(filename)
        print("FFmpeg has now been installed. Installation will continue")


def download_git(is64bit: bool=True):
    headers = {"User-Agent": "Twentysix26/Red-DiscordBot installer"}
    GIT_INSTALLPATH = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Git")
    if not os.path.isdir(GIT_INSTALLPATH):
        os.makedirs(GIT_INSTALLPATH)

    if is64bit:
        print("Finding current Git for Windows release...")
        r = requests.get(GFW_LATEST_RELEASE, headers=headers)
        data = r.json()
        download_url = None
        filename = None
        for asset in data["assets"]:
            if asset["name"].endswith("64-bit.tar.bz2"):
                download_url = asset["browser_download_url"]
                filename = asset["name"]
                break
        else:
            raise RuntimeError("Failed to find a valid git installer!")
        print("Downloading Git for Windows...")
        git_r = requests.get(download_url)
        with open(filename, "wb") as f:
            f.write(git_r.content)
        print("Finished downloading Git for Windows.")
        print("Extracting Git for Windows...")
        with tarfile.open(filename, "r:bz2") as gittar:
            gittar.extractall(GIT_INSTALLPATH)
    else:
        print("Finding current Git for Windows release...")
        r = requests.get(GFW_LATEST_RELEASE, headers=headers)
        data = r.json()
        download_url = None
        filename = None
        for asset in data["assets"]:
            if asset["name"].endswith("32-bit.tar.bz2"):
                download_url = asset["browser_download_url"]
                filename = asset["name"]
                break
        else:
            raise RuntimeError("Failed to find a valid git installer!")
        print("Downloading Git for Windows...")
        git_r = requests.get(download_url)
        with open(filename, "wb") as f:
            f.write(git_r.content)
        print("Finished downloading Git for Windows.")
        print("Extracting Git for Windows...")
        with tarfile.open(filename, "r:bz2") as gittar:
            gittar.extractall(GIT_INSTALLPATH)
    print("Finished extracting. Adding git to path")
    envreg = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
    value, regtype = winreg.QueryValueEx(envreg, "Path")
    toappend = ";{}".format(GIT_INSTALLPATH)
    value += toappend
    winreg.SetValueEx(envreg, "Path", 0, regtype, value)
    print("Added git to the path!")
    print(
        "Please note that you will need to log out and back\n"
        "into your account for this change to take effect"
    )


def do_windows_install():
    if "ffmpeg.exe" not in os.listdir(os.getcwd())\
            or "ffprobe.exe" not in os.listdir(os.getcwd())\
            or "ffplay.exe" not in os.listdir(os.getcwd()):
        download_ffmpeg(True if IS_64BIT else False)
    if not os.path.isdir(os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Git")):
        download_git(True if IS_64BIT else False)


def do_mac_install():
    pass


def do_linux_install():
    distro_name = distro.name()
    distro_version = [int(part) for part in distro.version().split(".")]


class InstallerExitCodes(Enum):
    SUCCESS = 0
    IMPROPERPYVER = 1
    NOPIP = 2
    PIPFAILED = 3
    NOGIT = 4


if __name__ == "__main__":
    # Python version checks
    if not PYTHON_OK and IS_WINDOWS:
        # For Windows, we'll attempt to install the correct
        # version, telling the user to rerun the script using
        # the newly installed version
        print("Red needs Python 3.5 or superior. Please run "
              "launch-install-win.ps1 using powershell to "
              "install the correct version")
        exit(InstallerExitCodes.IMPROPERPYVER)
    elif not PYTHON_OK and not IS_WINDOWS and not IS_MAC:  # Improper python version and on Linux
        print("Red needs Python 3.5 or superior. Please install the required version.\n")
        exit(InstallerExitCodes.IMPROPERPYVER)
    #end Python version checks

    if IS_WINDOWS and sys.version_info >= (3, 6):
        print("Please download and install Python 3.5 instead. 3.6 has issues on Windows")
        exit(InstallerExitCodes.IMPROPERPYVER)

    if pip is None:
        print("It appears pip isn't installed!")
        if IS_WINDOWS:
            print("Reinstall python and be sure to not uncheck any boxes!")
        elif not IS_WINDOWS and not IS_MAC:
            print("Please install pip using your distro's package manager")
        exit(InstallerExitCodes.NOPIP)
    if not IS_WINDOWS:
        try:
            subprocess.call(["git"])
        except FileNotFoundError:
            print("\nError: Git not found. It's either not installed or not in "
                  "the PATH environment variable like requested in the guide.")
            exit(InstallerExitCodes.NOGIT)

    if not IS_WINDOWS and not IS_MAC:
        pass

    if (IS_WINDOWS and requests is None) or (not IS_WINDOWS and not IS_MAC and distro is None):
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
