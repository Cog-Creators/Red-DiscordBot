#!/usr/bin/env python

import argparse
import os
import shutil
import sys
import tarfile
from copy import deepcopy
from datetime import datetime as dt
from pathlib import Path

import appdirs
from redbot.core.cli import confirm
from redbot.core.data_manager import basic_config_default
from redbot.core.json_io import JsonIO

config_dir = None
appdir = appdirs.AppDirs("Red-DiscordBot")
if sys.platform == 'linux':
    if 0 < os.getuid() < 1000:
        config_dir = Path(appdir.site_data_dir)
if not config_dir:
    config_dir = Path(appdir.user_config_dir)
try:
    config_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print(
        "You don't have permission to write to "
        "'{}'\nExiting...".format(config_dir))
    sys.exit(1)
config_file = config_dir / 'config.json'


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Red - Discord Bot's instance manager (V3)"
    )
    parser.add_argument(
        "--delete", "-d",
        help="Interactively delete an instance",
        action="store_true"
    )
    return parser.parse_known_args()


def load_existing_config():
    if not config_file.exists():
        return {}

    return JsonIO(config_file)._load_json()


def save_config(name, data, remove=False):
    config = load_existing_config()
    if remove and name in config:
        config.pop(name)
    else:
        config[name] = data
    JsonIO(config_file)._save_json(config)


def basic_setup():
    """
    Creates the data storage folder.
    :return:
    """

    default_data_dir = Path(appdir.user_data_dir)

    print("Hello! Before we begin the full configuration process we need to"
          " gather some initial information about where you'd like us"
          " to store your bot's data. We've attempted to figure out a"
          " sane default data location which is printed below. If you don't"
          " want to change this default please press [ENTER], otherwise"
          " input your desired data location.")
    print()
    print("Default: {}".format(default_data_dir))

    new_path = input('> ')

    if new_path != '':
        new_path = Path(new_path)
        default_data_dir = new_path

    if not default_data_dir.exists():
        try:
            default_data_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            print("We were unable to create your chosen directory."
                  " You may need to restart this process with admin"
                  " privileges.")
            sys.exit(1)

    print("You have chosen {} to be your data directory."
          "".format(default_data_dir))
    if not confirm("Please confirm (y/n):"):
        print("Please start the process over.")
        sys.exit(0)

    default_dirs = deepcopy(basic_config_default)
    default_dirs['DATA_PATH'] = str(default_data_dir.resolve())

    storage_dict = {
        1: "JSON",
        2: "MongoDB"
    }
    storage = None
    while storage is None:
        print()
        print("Please choose your storage backend (if you're unsure, choose 1).")
        print("1. JSON (file storage, requires no database).")
        print("2. MongoDB")
        storage = input("> ")
        try:
            storage = int(storage)
        except ValueError:
            storage = None
        else:
            if storage not in storage_dict:
                storage = None

    default_dirs['STORAGE_TYPE'] = storage_dict.get(storage, 1)

    if storage_dict.get(storage, 1) == "MongoDB":
        from redbot.core.drivers.red_mongo import get_config_details
        default_dirs['STORAGE_DETAILS'] = get_config_details()
    else:
        default_dirs['STORAGE_DETAILS'] = {}

    name = ""
    while len(name) == 0:
        print()
        print("Please enter a name for your instance, this name cannot include spaces"
              " and it will be used to run your bot from here on out.")
        name = input("> ")
        if " " in name:
            name = ""

    save_config(name, default_dirs)

    print()
    print("Your basic configuration has been saved. Please run `redbot <name>` to"
          " continue your setup process and to run the bot.")


def remove_instance():
    instance_list = load_existing_config()
    if not instance_list:
        print("No instances have been set up!")
        return

    print(
        "You have chosen to remove an instance. The following "
        "is a list of instances that currently exist:\n"
    )
    for instance in instance_list.keys():
        print("{}\n".format(instance))
    print("Please select one of the above by entering its name")
    selected = input("> ")
    
    if selected not in instance_list.keys():
        print("That isn't a valid instance!")
        return
    instance_data = instance_list[selected]
    print(
        "Would you like to make a backup of "
        "the data for this instance (y/n)?"
    )
    yesno = input("> ")
    if yesno.lower() == "y":
        if instance_data["STORAGE_TYPE"] == "MongoDB":
            raise NotImplementedError(
                "Support for removing instances with MongoDB as the storage "
                "is not implemented at this time due to backup support."
            )
        else:
            print("Backing up the instance's data...")
            backup_filename = "redv3-{}-{}.tar.gz".format(
                selected, dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            )
            pth = Path(instance_data["DATA_PATH"])
            home = pth.home()
            backup_file = home / backup_filename
            os.chdir(str(pth.parent))  # str is used here because 3.5 support
            with tarfile.open(str(backup_file), "w:gz") as tar:
                tar.add(pth.stem)  # add all files in that directory
            print(
                "A backup of {} has been made. It is at {}".format(
                    selected, backup_file
                )
            )
            print("Removing the instance...")
            try:
                shutil.rmtree(str(pth))
            except FileNotFoundError:
                pass  # data dir was removed manually
            save_config(selected, {}, remove=True)
            print("The instance has been removed")
            return
    elif yesno.lower() == "n":
        pth = Path(instance_data["DATA_PATH"])
        print("Removing the instance...")
        try:
            shutil.rmtree(str(pth))
        except FileNotFoundError:
            pass  # data dir was removed manually
        save_config(selected, {}, remove=True)
        print("The instance has been removed")
        return
    else:
        print("That's not a valid option!")
        return


def main():
    if args.delete:
        try:
            remove_instance()
        except NotImplementedError as e:
            print(str(e))
    else:
        basic_setup()

args, _ = parse_cli_args()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
    else:
        print("Exiting...")
