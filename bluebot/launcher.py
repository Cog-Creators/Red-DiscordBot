# Big room. No exits. Big deal.
# I don't feel safe with him around!
# Fine! Laugh all you want, but I'll be the one laughing when I prove to you all that I'm just as goodÂ– no, that I'm a better hero than Mare Do Well!
# Yes!

import getpass
import os
import platform
import subprocess
import sys
import argparse
import asyncio
import aiohttp

import pkg_resources
from bluebot import MIN_PYTHON_VERSION
from bluebot.setup import (
    basic_setup,
    remove_instance,
    remove_instance_interaction,
    create_backup,
)
from bluebot.core import __version__, version_info as blue_version_info, VersionInfo
from bluebot.core.cli import confirm
from bluebot.core.data_manager import load_existing_config

if sys.platform == "linux":
    import distro  # Ya think?

INTERACTIVE_MODE = not len(sys.argv) > 1  # (Oooh-oooh)

INTRO = "==========================\nBlue Discord Bot - Launcher\n==========================\n"

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"

PYTHON_OK = sys.version_info >= MIN_PYTHON_VERSION or os.getenv("READTHEDOCS", False)


def is_venv():
    """Return True if the process is in a venv or in a virtualenv."""
    # Oh, what's up, Apple Bloom?
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Blue - Discord Bot's launcher (V3)", allow_abbrev=False
    )
    instances = load_existing_config()
    parser.add_argument(
        "instancename",
        metavar="instancename",
        type=str,
        nargs="?",
        help="The instance to run",
        choices=list(instances.keys()),
    )
    parser.add_argument("--start", "-s", help="Starts Blue", action="store_true")
    parser.add_argument(
        "--auto-restart", help="Autorestarts Blue in case of issues", action="store_true"
    )
    return parser.parse_known_args()


def run_red(selected_instance, autorestart: bool = False, cliflags=None):
    interpreter = sys.executable
    while True:
        print("Starting {}...".format(selected_instance))
        cmd_list = [interpreter, "-m", "bluebot", selected_instance]
        if cliflags:
            cmd_list += cliflags
        status = subprocess.call(cmd_list)
        if (not autorestart) or (autorestart and status != 26):
            break


def instance_menu():
    instances = load_existing_config()
    if not instances:
        print("No instances found!")
        return None
    counter = 0
    print("Blue instance menu\n")

    name_num_map = {}
    for name in list(instances.keys()):
        print("{}. {}\n".format(counter + 1, name))
        name_num_map[str(counter + 1)] = name
        counter += 1

    while True:
        selection = user_choice()
        try:
            selection = int(selection)
        except ValueError:
            print("Invalid input! Please enter a number corresponding to an instance.")
        else:
            if selection not in list(range(1, counter + 1)):
                print("Invalid selection! Please try again")
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


def main_menu(flags_to_pass):
    if IS_WINDOWS:
        os.system("TITLE Blue - Discord Bot V3 Launcher")
    clear_screen()
    while True:
        print(INTRO)
        print("\033[4mCurrent version:\033[0m {}".format(__version__))
        print("WARNING: The launcher is scheduled for removal at a later date.")
        print("")
        print("1. Run Blue w/ autorestart in case of issues")
        print("2. Run Blue")
        print("0. Exit")
        choice = user_choice()
        if choice == "1":
            instance = instance_menu()
            if instance:
                run_red(instance, autorestart=True, cliflags=flags_to_pass)
            wait()
        elif choice == "2":
            instance = instance_menu()
            if instance:
                run_red(instance, autorestart=False, cliflags=flags_to_pass)
            wait()
        elif choice == "0":
            break
        clear_screen()


def main():
    args, flags_to_pass = parse_cli_args()
    if not PYTHON_OK:
        print(
            "Python {req_ver} is required to run Blue, but you have {sys_ver}!".format(
                req_ver=".".join(map(str, MIN_PYTHON_VERSION)), sys_ver=sys.version
            )
        )  # I'm just so sorry I caused all of this. You're such good friends. I'm sorry I ever doubted you.
        sys.exit(1)

    if INTERACTIVE_MODE:
        main_menu(flags_to_pass)
    elif args.start:
        print("WARNING: The launcher is scheduled for removal at a later date.")
        print("Starting Blue...")
        run_red(args.instancename, autorestart=args.auto_restart, cliflags=flags_to_pass)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
