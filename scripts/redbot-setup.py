from pathlib import Path

import appdirs
import sys

from copy import deepcopy

from core.cli import confirm
from core.data_manager import basic_config_default
from core.json_io import JsonIO

appdir = appdirs.AppDirs("Red-DiscordBot")
config_dir = Path(appdir.user_config_dir())
config_dir.mkdir(parents=True, exist_ok=True)
config_file = config_dir / 'config.json'


def load_existing_config():
    if not config_file.exists():
        return {}

    return JsonIO(config_file)._load_json()


def save_config(name, data):
    config = load_existing_config()
    config[name] = data
    JsonIO(config_file)._save_json(config)


def basic_setup():
    """
    Creates the data storage folder.
    :return:
    """

    default_data_dir = Path(appdir.user_data_dir())

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

    default_dirs['STORAGE_TYPE'] = storage_dict[storage]

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
