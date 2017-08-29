from __future__ import print_function  # Used to allow python2 to run this
import os
import sys
from subprocess import check_output, CalledProcessError, STDOUT
from enum import Enum
import platform
import shutil
import tarfile
import zipfile
from time import sleep
try:
    import pip
except ImportError:
    pip = None
try:
    import requests
except ImportError:
    requests = None
try:
    import fire
except ImportError:
    fire = None


IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_64BIT = platform.machine().endswith("64")


if IS_WINDOWS:
    PYTHON_OK = (3, 5) <= sys.version_info < (3, 6)
else:
    PYTHON_OK = sys.version_info >= (3, 5)

if IS_WINDOWS and PYTHON_OK:
    from winreg import *
if not IS_WINDOWS and not IS_MAC:  # need distro to determine distro
    try:
        import distro
    except ImportError:
        distro = None


UNSUPPORTED_LINUX_TEXT = (
    """
    Your distro (or version) is not supported by this installer. It may have\n
    a page that walks through the installation manually which is located at\n
    http://twentysix26.github.io/Red-Docs/red_install_linux/\n
    If it is not listed there, you are probably on your own.\n
    However, to run Red, one needs to install:\n\n
    - Git\n
    - Python (3.5 or greater)\n
    - ffmpeg or avconv\n
    - libsodium\n
    - pip\n
    - libssl\n
    - libffi\n
    - unzip\n
    - libopus\n\n
    Please be aware that if your package manager doesn't provide a package\n
    for some of these, you may need to compile them on\ your own which means\n
    you would need to install the necessary tools to allow you to compile\n
    source code; therefore if you are not comfortable doing this, you should\n
    select a different distro to use for running an instance of Red. Please\n
    do not ask for help with this in the support channel in Red's official\n
    server as we may not be able to assist you with this process. If you\n
    choose to carry on using an unsupported distro, you may wish to use\n
    Google to assist you in answering any questions you may have. Your\n
    distro's website may also contain documentation that may help you\n
    """
)


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
        "libffi-dev", "git", "ffmpeg",
        "libopus-dev", "unzip"
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


def raspbian_install():
    print("Installing prerequisite packages...")
    print("If prompted for your password, enter it.")
    package_list = [
        'libbz2-dev', 'libopus-dev', 'liblzma-dev', 'libsqlite3-dev',
        'libncurses5-dev', 'libgdbm-dev', 'zlib1g-dev', 'libreadline-dev',
        'git', 'unzip', 'libssl-dev', 'tk-dev', 'build-essential',
        'libffi-dev', 'libav-tools'
    ]
    try:
        aptupres = check_output(
            ["sudo", "-K", "apt-get", "update"],
            stderr=STDOUT
        )
    except CalledProcessError as e:
        print("Error while doing apt-get update! Output:\n\n")
        print(e.output.decode())
        print("\n\nProcess returned code {}".format(e.returncode))
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(aptupres.decode())

    try:
        aptugres = check_output(
            ["sudo", "-K", "apt-get", "upgrade"],
            stderr=STDOUT
        )
    except CalledProcessError as e:
        print("Error while upgrading packages! Output:\n\n")
        print(e.output.decode())
        print("\n\nProcess returned code {}".format(e.returncode))
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(aptugres.decode())

    try:
        aptres = check_output(
            ["sudo", "-K", "apt-get", "install", " ".join(package_list), "-y"],
            stderr=STDOUT
        )
    except CalledProcessError as e:
        print("Error while installing requirements! Output:\n\n")
        print(e.output.decode())
        print("\n\nProcess returned code {}".format(e.returncode))
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(aptres.decode())
        print("\n\nRequirements installed successfully.\n")


def debian_install():
    try:
        aar_install = check_output(["sudo", "apt", "install", "software-properties-common"], stderr=STDOUT)
    except CalledProcessError as e:
        print("Error while installing software-properties-common! Output:\n\n")
        print(e.output.decode())
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(aar_install.decode())
    sources_list_add = "deb http://httpredir.debian.org/debian stretch-backports main contrib non-free"

    try:
        add_backports = check_output(["sudo", "add-apt-repository", sources_list_add], stderr=STDOUT)
    except CalledProcessError as e:
        print("Error while adding stretch-backports to sources! Output:\n\n")
        print(e.output.decode())
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(add_backports.decode())

    try:
        apt_update = check_output(["sudo", "apt", "update"], stderr=STDOUT)
    except CalledProcessError as e:
        print("Error doing apt update! Output:\n\n")
        print(e.output.decode())
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(apt_update.decode())

    package_list = ["python3", ""]


def amazon_linux_install():
    pass


def do_linux_install():
    distro_id = distro.id()
    distro_version = [int(part) for part in distro.version().split(".")]
    if distro_id == "ubuntu" and distro_version[0] == 16 and distro_version[1] == 4:
        pass
    elif distro_id == "debian" and distro_version[0] == 9:
        pass
    elif distro_id == "raspbian":
        pass
    elif distro_id == "amazon":
        pass
    else:
        print(UNSUPPORTED_LINUX_TEXT)
        sleep(5)
        while input("Press enter after reading the above text: "):
            pass
        exit(InstallerExitCodes.UNSUPPORTEDLINUX)


def do_windows_install():
    print("Installing Windows requirements")
    which = shutil.which
    if not PYTHON_OK:
        print("You do not have the correct version of Python installed!")
        print("Please use the Powershell script (launch-install-win.ps1) "
              "to install the correct version of Python and try again.")
        exit(InstallerExitCodes.IMPROPERPYVER)

    if not which("git.exe"):
        print("Downloading Git")
        download_git()

    if not which("ffmpeg.exe")\
            or not which("ffplay.exe")\
            or not which("ffprobe.exe"):
        print("Downloading ffmpeg")
        download_ffmpeg()
    print("\n")
    print("Finished installing necessary requirements. You may now run:\n")
    print("python install.py setup\n")
    print("to continue with setting up Red")


def download_git():
    print("Finding the latest git download")
    ver_r = requests.get("https://api.github.com/repos/git-for-windows/git/releases/latest")
    ver_data = ver_r.json()
    git_url = ""
    filename = ""
    file_ending = "64-bit.exe" if IS_64BIT else "32-bit.exe"
    for item in ver_data["assets"]:
        if item["name"].endswith(file_ending):
            git_url = item["browser_download_url"]
            filename = item["name"]
            break
    else:
        print("Something went wrong while finding a git download!")
        exit(InstallerExitCodes.REQFAIL)
    print("Downloading Git. This may take a while "
          "depending on your connection speed")
    git_r = requests.get(git_url)
    with open(filename, "wb") as fout:
        fout.write(git_r.content)
    print("Finished downloading Git. Installing...")
    try:
        git_inst = check_output([filename, "/VERYSILENT", "/NORESTART", "/NOCANCEL", "/NOCLOSEAPPLICATIONS"], stderr=STDOUT)
    except CalledProcessError as e:
        print(e.output.decode())
        exit(InstallerExitCodes.REQFAIL)
    else:
        print(git_inst.decode())
    print("Done installing git")
    os.remove(filename)


def download_ffmpeg():
    ffurl = ("https://ffmpeg.zeranoe.com/builds"
             "/{0}/static/ffmpeg-latest-{0}-static.zip"
             "").format("win64" if IS_64BIT else "win32")
    ff_file =\
        "ffmpeg-latest-{}-static.zip".format("win64" if IS_64BIT else "win32")
    ff_r = requests.get(ffurl)
    with open(ff_file, "wb") as fout:
        fout.write(ff_r.content)
    print("Finished downloading ffmpeg. Extracting...")
    target_path = os.path.join(os.getenv("LOCALAPPDATA"), "Programs")
    with zipfile.ZipFile(ff_file, "r") as ff_zip:
        ff_zip.extractall(target_path)
    cur_dir = os.getcwd()
    os.chdir(target_path)
    os.rename(ff_file[:-4], "ffmpeg")
    os.chdir(cur_dir)
    bin_path = os.path.join(target_path, "ffmpeg", "bin")
    path = os.environ["Path"]
    if bin_path not in path:
        print("Adding ffmpeg to the path")
        key = OpenKey(HKEY_CURRENT_USER, "Environment", 0, KEY_ALL_ACCESS)
        current_path = QueryValueEx(key, "Path")[0]
        new_path = "{}{}{};".format(current_path, ";" if not current_path.endswith(";") else "", bin_path)
        SetValueEx(key, "Path", 0, REG_SZ, new_path)
        CloseKey(key)
    print("Done installing ffmpeg")
    os.remove(ff_file)


def download_pip():
    print("Downloading pip, please wait...")
    r = requests.get("https://bootstrap.pypa.io/get-pip.py")
    with open("get-pip.py", "w") as fout:
        fout.write(r.text)
    try:
        pip_install = check_output([sys.executable, "get-pip.py"], stderr=STDOUT)
    except CalledProcessError as e:
        print(e.output.decode())
    else:
        print(pip_install.decode())
        print("\n\nDone installing pip!")


def setup_red():
    raise NotImplementedError


def update_red():
    raise NotImplementedError


def install_requirements():
    print("Launching requirements install")
    if not IS_WINDOWS and not IS_MAC and distro is None:
        if distro is None:
            if pip is None:  # Installer requirements on Linux need pip
                print("Pip is not installed!")
                print("Attempting to install pip...")

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
        if requests is None:
            if pip is None:
                raise RuntimeError("Pip is not installed!")
            else:
                pip.main(["install", "requests"])
        do_windows_install()
    elif IS_MAC:
        do_mac_install()
    else:
        do_linux_install()


def installer_welcome_message():
    print(
        (
            """
            ===========================\n
            Red Discord Bot - Installer\n
            ===========================\n
            """
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
    UNSUPPORTEDLINUX = 8


if __name__ == "__main__":
    installer_welcome_message()

    fire.Fire(
        {
            "install": install_requirements,
            "setup": setup_red,
            "update": update_red
        }
    )
