import argparse
import asyncio
import getpass
import os
import platform
import subprocess
import sys

import aiohttp
import pkg_resources

from redbot import MIN_PYTHON_VERSION
from redbot.core import VersionInfo, __version__, version_info as red_version_info
from redbot.core.cli import confirm
from redbot.setup import (
    basic_setup,
    create_backup,
    load_existing_config,
    remove_instance,
    remove_instance_interaction,
)

if sys.platform == "linux":
    import distro  # pylint: disable=import-error

INTERACTIVE_MODE = not len(sys.argv) > 1  # CLI flags = non-interactive

INTRO = "==========================\nRed Discord Bot - Launcher\n==========================\n"

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"

PYTHON_OK = sys.version_info >= MIN_PYTHON_VERSION


def is_venv():
    """Return True if the process is in a venv or in a virtualenv."""
    # credit to @calebj
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Red - Discord Bot's launcher (V3)", allow_abbrev=False
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
    parser.add_argument("--start", "-s", help="Starts Red", action="store_true")
    parser.add_argument(
        "--auto-restart", help="Autorestarts Red in case of issues", action="store_true"
    )
    parser.add_argument("--update", help="Updates Red", action="store_true")
    parser.add_argument(
        "--update-dev", help="Updates Red from the Github repo", action="store_true"
    )
    parser.add_argument("--docs", help="Installs extra 'docs' when updating", action="store_true")
    parser.add_argument("--test", help="Installs extra 'test' when updating", action="store_true")
    parser.add_argument(
        "--style", help="Installs extra 'style' when updating", action="store_true"
    )
    parser.add_argument(
        "--mongo", help="Installs extra 'mongo' when updating", action="store_true"
    )
    parser.add_argument(
        "--debuginfo",
        help="Prints basic debug info that would be useful for support",
        action="store_true",
    )
    return parser.parse_known_args()


def update_red(dev=False, style=False, mongo=False, docs=False, test=False):
    interpreter = sys.executable
    print("Updating Red...")
    # If the user ran redbot-launcher.exe, updating with pip will fail
    # on windows since the file is open and pip will try to overwrite it.
    # We have to rename redbot-launcher.exe in this case.
    launcher_script = os.path.abspath(sys.argv[0])
    old_name = launcher_script + ".exe"
    new_name = launcher_script + ".old"
    renamed = False
    if "redbot-launcher" in launcher_script and IS_WINDOWS:
        renamed = True
        print("Renaming {} to {}".format(old_name, new_name))
        if os.path.exists(new_name):
            os.remove(new_name)
        os.rename(old_name, new_name)
    egg_l = []
    if style:
        egg_l.append("style")
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
    arguments = [interpreter, "-m", "pip", "install", "-U", package]
    if not is_venv():
        arguments.append("--user")
    code = subprocess.call(arguments)
    if code == 0:
        print("Red has been updated")
    else:
        print("Something went wrong while updating!")

    # If redbot wasn't updated, we renamed our .exe file and didn't replace it
    scripts = os.listdir(os.path.dirname(launcher_script))
    if renamed and "redbot-launcher.exe" not in scripts:
        print("Renaming {} to {}".format(new_name, old_name))
        os.rename(new_name, old_name)


def run_red(selected_instance, autorestart: bool = False, cliflags=None):
    interpreter = sys.executable
    while True:
        print("Starting {}...".format(selected_instance))
        cmd_list = [interpreter, "-m", "redbot", selected_instance]
        if cliflags:
            cmd_list += cliflags
        status = subprocess.call(cmd_list)
        if (not autorestart) or (autorestart and status != 26):
            break


def cli_flag_getter():
    print("Would you like to enter any cli flags to pass to redbot? (y/n)")
    resp = user_choice()
    if resp == "n":
        return None
    elif resp == "y":
        flags = []
        print("Ok, we will now walk through choosing cli flags")
        print("Would you like to specify an owner? (y/n)")
        print(
            "Please note that the owner is normally determined automatically from "
            "the bot's token, so you should only use that if you want to specify a "
            "user other than that one as the owner."
        )
        choice = user_choice()
        if choice == "y":
            print("Enter the user id for the owner")
            owner_id = user_choice()
            flags.append("--owner {}".format(owner_id))
        print("Would you like to specify any prefixes? (y/n)")
        choice = user_choice()
        if choice == "y":
            print(
                "Enter the prefixes, separated by a space (please note "
                "that prefixes containing a space will need to be added with [p]set prefix)"
            )
            prefixes = user_choice().split()
            for p in prefixes:
                flags.append("-p {}".format(p))
        print("Would you like mentioning the bot to be a prefix? (y/n)")
        choice = user_choice()
        if choice == "y":
            flags.append("--mentionable")
        print(
            "Would you like to disable console input? Please note that features "
            "requiring console interaction may fail to work (y/n)"
        )
        choice = user_choice()
        if choice == "y":
            flags.append("--no-prompt")
        print("Would you like to start with no cogs loaded? (y/n)")
        choice = user_choice()
        if choice == "y":
            flags.append("--no-cogs")
        print("Do you want to do a dry run? (y/n)")
        choice = user_choice()
        if choice == "y":
            flags.append("--dry-run")
        print("Do you want to set the log level to debug? (y/n)")
        choice = user_choice()
        if choice == "y":
            flags.append("--debug")
        print(
            "Do you want the Dev cog loaded (thus enabling commands such as debug and repl)? (y/n)"
        )
        choice = user_choice()
        if choice == "y":
            flags.append("--dev")
        print("Do you want to enable RPC? (y/n)")
        choice = user_choice()
        if choice == "y":
            flags.append("--rpc")
        print("You have selected the following cli flags:\n\n")
        print("\n".join(flags))
        print("\nIf this looks good to you, type y. If you wish to start over, type n")
        choice = user_choice()
        if choice == "y":
            print("Done selecting cli flags")
            return flags
        else:
            print("Starting over")
            return cli_flag_getter()
    else:
        print("Invalid response! Let's try again")
        return cli_flag_getter()


def instance_menu():
    instances = load_existing_config()
    if not instances:
        print("No instances found!")
        return None
    counter = 0
    print("Red instance menu\n")

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


async def reset_red():
    instances = load_existing_config()

    if not instances:
        print("No instance to delete.\n")
        return
    print("WARNING: You are about to remove ALL Red instances on this computer.")
    print(
        "If you want to reset data of only one instance, "
        "please select option 5 in the launcher."
    )
    await asyncio.sleep(2)
    print("\nIf you continue you will remove these instances.\n")
    for instance in list(instances.keys()):
        print("    - {}".format(instance))
    await asyncio.sleep(3)
    print('\nIf you want to reset all instances, type "I agree".')
    response = input("> ").strip()
    if response != "I agree":
        print("Cancelling...")
        return

    if confirm("\nDo you want to create a backup for an instance? (y/n) "):
        for index, instance in instances.items():
            print("\nRemoving {}...".format(index))
            await create_backup(index)
            await remove_instance(index)
    else:
        for index, instance in instances.items():
            await remove_instance(index)
    print("All instances have been removed.")


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


def extras_selector():
    print("Enter any extra requirements you want installed\n")
    print("Options are: style, docs, test, mongo\n")
    selected = user_choice()
    selected = selected.split()
    return selected


def development_choice(can_go_back=True):
    while True:
        print("\n")
        print("Do you want to install stable or development version?")
        print("1. Stable version")
        print("2. Development version")
        if can_go_back:
            print("\n")
            print("0. Go back")
        choice = user_choice()
        print("\n")

        if choice == "1":
            selected = extras_selector()
            update_red(
                dev=False,
                style=True if "style" in selected else False,
                docs=True if "docs" in selected else False,
                test=True if "test" in selected else False,
                mongo=True if "mongo" in selected else False,
            )
            break
        elif choice == "2":
            selected = extras_selector()
            update_red(
                dev=True,
                style=True if "style" in selected else False,
                docs=True if "docs" in selected else False,
                test=True if "test" in selected else False,
                mongo=True if "mongo" in selected else False,
            )
            break
        elif choice == "0" and can_go_back:
            return False
        clear_screen()
    return True


def debug_info():
    pyver = sys.version
    redver = pkg_resources.get_distribution("Red-DiscordBot").version
    if IS_WINDOWS:
        os_info = platform.uname()
        osver = "{} {} (version {}) {}".format(
            os_info.system, os_info.release, os_info.version, os_info.machine
        )
    elif IS_MAC:
        os_info = platform.mac_ver()
        osver = "Mac OSX {} {}".format(os_info[0], os_info[2])
    else:
        os_info = distro.linux_distribution()
        osver = "{} {}".format(os_info[0], os_info[1]).strip()
    user_who_ran = getpass.getuser()
    info = (
        "Debug Info for Red\n\n"
        + "Python version: {}\n".format(pyver)
        + "Red version: {}\n".format(redver)
        + "OS version: {}\n".format(osver)
        + "System arch: {}\n".format(platform.machine())
        + "User: {}\n".format(user_who_ran)
    )
    print(info)
    sys.exit(0)


async def is_outdated():
    red_pypi = "https://pypi.python.org/pypi/Red-DiscordBot"
    async with aiohttp.ClientSession() as session:
        async with session.get("{}/json".format(red_pypi)) as r:
            data = await r.json()
            new_version = data["info"]["version"]
    return VersionInfo.from_str(new_version) > red_version_info, new_version


def main_menu():
    if IS_WINDOWS:
        os.system("TITLE Red - Discord Bot V3 Launcher")
    clear_screen()
    loop = asyncio.get_event_loop()
    outdated, new_version = loop.run_until_complete(is_outdated())
    while True:
        print(INTRO)
        print("\033[4mCurrent version:\033[0m {}".format(__version__))
        if outdated:
            print("Red is outdated. {} is available.".format(new_version))
        print("")
        print("1. Run Red w/ autorestart in case of issues")
        print("2. Run Red")
        print("3. Update Red")
        print("4. Create Instance")
        print("5. Remove Instance")
        print("6. Debug information (use this if having issues with the launcher or bot)")
        print("7. Reinstall Red")
        print("0. Exit")
        choice = user_choice()
        if choice == "1":
            instance = instance_menu()
            if instance:
                cli_flags = cli_flag_getter()
                run_red(instance, autorestart=True, cliflags=cli_flags)
            wait()
        elif choice == "2":
            instance = instance_menu()
            if instance:
                cli_flags = cli_flag_getter()
                run_red(instance, autorestart=False, cliflags=cli_flags)
            wait()
        elif choice == "3":
            if development_choice():
                wait()
        elif choice == "4":
            basic_setup()
            wait()
        elif choice == "5":
            loop.run_until_complete(remove_instance_interaction())
            wait()
        elif choice == "6":
            debug_info()
        elif choice == "7":
            while True:
                clear_screen()
                print("==== Reinstall Red ====")
                print(
                    "1. Reinstall Red requirements "
                    "(discard code changes, keep data and 3rd party cogs)"
                )
                print("2. Reset all data")
                print("3. Factory reset (discard code changes, reset all data)")
                print("\n")
                print("0. Back")
                choice = user_choice()
                if choice == "1":
                    if development_choice():
                        wait()
                elif choice == "2":
                    loop.run_until_complete(reset_red())
                    wait()
                elif choice == "3":
                    loop.run_until_complete(reset_red())
                    development_choice(can_go_back=False)
                    wait()
                elif choice == "0":
                    break
        elif choice == "0":
            break
        clear_screen()


def main():
    args, flags_to_pass = parse_cli_args()
    if not PYTHON_OK:
        print(
            f"Python {'.'.join(map(str, MIN_PYTHON_VERSION))} is required to run Red, but you "
            f"have {sys.version}! Please update Python."
        )
        sys.exit(1)
    if args.debuginfo:  # Check first since the function triggers an exit
        debug_info()

    if args.update and args.update_dev:  # Conflicting args, so error out
        raise RuntimeError(
            "\nUpdate requested but conflicting arguments provided.\n\n"
            "Please try again using only one of --update or --update-dev"
        )
    if args.update:
        update_red(style=args.style, docs=args.docs, test=args.test, mongo=args.mongo)
    elif args.update_dev:
        update_red(dev=True, style=args.style, docs=args.docs, test=args.test, mongo=args.mongo)

    if INTERACTIVE_MODE:
        main_menu()
    elif args.start:
        print("Starting Red...")
        run_red(args.instancename, autorestart=args.auto_restart, cliflags=flags_to_pass)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
