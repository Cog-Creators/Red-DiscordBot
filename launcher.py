# pylint: disable=missing-docstring
from __future__ import print_function

import getpass
import json
import os
import platform
import subprocess
import sys
import argparse
import appdirs
from pathlib import Path

import pkg_resources
# from redbot.setup import basic_setup

config_dir = Path(appdirs.AppDirs("Red-DiscordBot").user_config_dir)
config_file = config_dir / 'config.json'

PYTHON_OK = sys.version_info >= (3, 5)
INTERACTIVE_MODE = not len(sys.argv) > 1  # CLI flags = non-interactive

INTRO = ("==========================\n"
         "Red Discord Bot - Launcher\n"
         "==========================\n")

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"

def parse_cli_args():
    parser = argparse.ArgumentParser(description="Red - Discord Bot's launcher (V3)")
    with config_file.open("r") as fin:
        instances = json.loads(fin.read())
    parser.add_argument("instancename", metavar="instancename", type=str,
                        nargs="?", help="The instance to run", choices=list(instances.keys()))
    parser.add_argument("--start", "-s",
                        help="Starts Red",
                        action="store_true")
    parser.add_argument("--auto-restart",
                        help="Autorestarts Red in case of issues",
                        action="store_true")
    parser.add_argument("--update",
                        help="Updates Red",
                        action="store_true")
    parser.add_argument("--update-dev",
                        help="Updates Red from the Github repo",
                        action="store_true")
    parser.add_argument("--voice",
                        help="Installs extra 'voice' when updating",
                        action="store_true")
    parser.add_argument("--docs",
                        help="Installs extra 'docs' when updating",
                        action="store_true")
    parser.add_argument("--test",
                        help="Installs extra 'test' when updating",
                        action="store_true")
    parser.add_argument("--mongo",
                        help="Installs extra 'mongo' when updating",
                        action="store_true")
    parser.add_argument("--debug",
                        help="Prints basic debug info that would be useful for support",
                        action="store_true")
    return parser.parse_args()


def update_red(dev=False, voice=False, mongo=False, docs=False, test=False):
    interpreter = sys.executable
    print("Updating Red...")
    eggs = ""  # for installing extras (e.g. voice, docs, test, mongo)
    egg_l = []
    if voice:
        egg_l.append("voice")
    if mongo:
        egg_l.append("mongo")
    if docs:
        egg_l.append("docs")
    if test:
        egg_l.append("test")
    if dev:
        package = "git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop"
        if egg_l:
            package += "#egg=Red-DiscordBot[{}]".format(", ".join(egg_l))
    else:
        package = "Red-DiscordBot"
        if egg_l:
            package += "[{}]".format(", ".join(egg_l))
    code = subprocess.call([
        interpreter, "-m",
        "pip", "install", "-U",
        "--process-dependency-links",
        package
    ])
    if code == 0:
        print("Red has been updated")
    else:
        print("Something went wrong while updating!")


def run_red(selected_instance, autorestart=False):
    while True:
        print("Starting {}...".format(selected_instance))
        status = subprocess.call(["redbot", selected_instance])
        if (not autorestart) or (autorestart and status != 26):
            break


def instance_menu():
    with config_file.open("r") as fin:
        instances = json.loads(fin.read())
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
        return None
    else:
        if selection not in list(range(1, counter+1)):
            print("Invalid selection! Please try again")
            return None
        else:
            return name_num_map[str(selection)]


def clear_screen():
    if IS_WINDOWS:
        os.system("cls")
    else:
        os.system("clear")


def wait():
    if INTERACTIVE_MODE:
        input("Press enter to continue.")


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
    if IS_WINDOWS:
        os.system("TITLE Red - Discord Bot V3 Launcher")
    while True:
        print(INTRO)
        print("1. Run Red w/ autorestart in case of issues")
        print("2. Run Red")
        print("3. Update Red")
        # print("4. Create Instance")
        print("5. Debug information (use this if having issues with the launcher or bot)")
        print("0. Exit")
        choice = user_choice()
        if choice == "1":
            instance = instance_menu()
            if instance:
                run_red(instance, autorestart=True)
            wait()
        elif choice == "2":
            instance = instance_menu()
            if instance:
                run_red(instance, autorestart=False)
            wait()
        elif choice == "3":
            update_red()
            wait()
        elif choice == "5":
            debug_info()
        elif choice == "0":
            break
        clear_screen()

args = parse_cli_args()

if __name__ == "__main__":
    if not PYTHON_OK:
        raise RuntimeError(
            "Red requires Python 3.5 or greater. "
            "Please install the correct version!"
        )
    if args.debug:  # Check first since the function triggers an exit
        debug_info()
    
    if args.update and args.update_dev:  # Conflicting args, so error out
        raise RuntimeError(
            "\nUpdate requested but conflicting arguments provided.\n\n"
            "Please try again using only one of --update or --update-dev"
        )
    if args.update:
        update_red(
            voice=args.voice, docs=args.docs, 
            test=args.test, mongo=args.mongo
        )
    elif args.update_dev:
        update_red(
            dev=True, voice=args.voice, docs=args.docs, 
            test=args.test, mongo=args.mongo
        )

    if INTERACTIVE_MODE:
        main()
    elif args.start:
        print("Starting Red...")
        run_red(args.instancename, autorestart=args.auto_restart)
