# pylint: disable=missing-docstring
from __future__ import print_function

import getpass
import json
import os
import platform
import subprocess
import sys

import pkg_resources
from redbot.core.data_manager import config_file
from redbot.setup import basic_setup

PYTHON_OK = sys.version_info >= (3, 5)

INTRO = ("==========================\n"
         "Red Discord Bot - Launcher\n"
         "==========================\n")

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"


def update_red():
    interpreter = sys.executable
    print("Updating Red...")
    code = subprocess.call([
        interpreter, "-m",
        "pip", "install", "-U",
        "Red-DiscordBot"
    ])
    print("Red has been updated")


def run_red(autorestart=False):
    with open(config_file, "r") as fin:
        instances = json.loads(fin.read())
    selected_instance = instance_menu(instances)
    if not selected_instance:
        return None
    while True:
        print("Starting {}...".format(selected_instance))
        status = subprocess.call(["redbot", selected_instance])
        if (not autorestart) or (autorestart and status != 26):
            break


def instance_menu(instances):
    if not instances:
        print("No instances found!")
        return None
    counter = 0
    print("Red instance menu\n")
   
    name_num_map = {}
    for name in list(instances.keys()):
        print("{}. {}\n".format(counter+1, name))
        name_num_map[str(counter+1)] = name
        counter += 1
    selection = user_choice()
    try:
        selection = int(selection)
    except ValueError:
        print("Invalid input! Try again.")
        return instance_menu(instances)
    else:
        if selection not in list(range(1, counter+1)):
            print("Invalid selection! Please try again")
            return instance_menu(instances)
        else:
            return name_num_map[str(selection)]


def clear_screen():
    if IS_WINDOWS:
        os.system("cls")
    else:
        os.system("clear")


def user_choice():
    return input("> ").lower().strip()


def debug_info():
    pyver = sys.version
    redver = pkg_resources.get_distribution("Red-DiscordBot").version
    osver = ""
    if IS_WINDOWS:
        os_info = platform.uname()
        osver = "{} {} (version {}) {}".format(
            os_info.system, os_info.release, os_info.version, os_info.machine
        )
    elif IS_MAC:
        os_info = platform.mac_ver()
        osver = "Mac OSX {} {}".format(os_info[0], os_info[2])
    else:
        os_info = platform.linux_distribution()  # pylint: disable=deprecated-method
        osver = "{} {} {}".format(os_info[0], os_info[1], platform.machine())
    user_who_ran = getpass.getuser()
    info = "Debug Info for Red\n\n" +\
        "Python version: {}\n".format(pyver) +\
        "Red version: {}\n".format(redver) +\
        "OS version: {}\n".format(osver) +\
        "User: {}\n".format(user_who_ran)
    print(info)
    exit(0)


def main():
    while True:
        print(INTRO)
        print("1. Run Red w/ autorestart in case of issues")
        print("2. Run Red")
        print("3. Update Red")
        print("4. Create Instance")
        print("5. Debug information (use this if having issues with the launcher or bot)")
        print("0. Exit")
        choice = user_choice()
        if choice == "1":
            run_red(autorestart=True)
        elif choice == "2":
            run_red(autorestart=False)
        elif choice == "3":
            update_red()
        elif choice == "4":
            basic_setup()
        elif choice == "5":
            debug_info()
        elif choice == "0":
            break
        clear_screen()


if __name__ == "__main__":
    if not PYTHON_OK:
        raise RuntimeError(
            "Red requires Python 3.5 or greater. "
            "Please install the correct version!"
        )
    main()
