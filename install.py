from __future__ import print_function  # Used to allow python2 to run this
import os
import sys
from subprocess import call, check_output, CalledProcessError, STDOUT
from enum import Enum
import platform
import getpass
import fire
from time import sleep
try:
    import pip
except ImportError:
    pip = None

if sys.version_info.major == 2:
    from urllib import urlretrieve
elif sys.version_info.major == 3:
    from urllib.request import urlretrieve


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
        sleep(120)  # Give enough time to read the above text before exiting
        exit(InstallerExitCodes.UNSUPPORTEDLINUX)


def download_pip():
    urlretrieve("https://bootstrap.pypa.io/get-pip.py", "get-pip.py")


def setup_red():
    raise NotImplementedError


def update_red():
    raise NotImplementedError


def install_requirements():
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
        print(
            "In order to properly install requirements on Windows, "
            "you need to use the powershell script (launch-install-win.ps1)"
        )
        # exit(0)
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
