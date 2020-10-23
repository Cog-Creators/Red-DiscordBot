#!/usr/bin/env python3
import asyncio
import contextlib
import json
import logging
import os
import sys
import re
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Optional, Union

import appdirs
import click

from redbot.core.cli import confirm
from redbot.core.utils._internal_utils import safe_delete, create_backup as red_create_backup
from redbot.core import config, data_manager, drivers
from redbot.core.drivers import BackendType, IdentifierData

conversion_log = logging.getLogger("red.converter")

config_dir = None
appdir = appdirs.AppDirs("Red-DiscordBot")
if sys.platform == "linux":
    if 0 < os.getuid() < 1000:  # pylint: disable=no-member  # Non-exist on win
        config_dir = Path(appdir.site_data_dir)
if not config_dir:
    config_dir = Path(appdir.user_config_dir)
try:
    config_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print("You don't have permission to write to '{}'\nExiting...".format(config_dir))
    sys.exit(1)
config_file = config_dir / "config.json"


def load_existing_config():
    if not config_file.exists():
        return {}

    with config_file.open(encoding="utf-8") as fs:
        return json.load(fs)


instance_data = load_existing_config()
if instance_data is None:
    instance_list = []
else:
    instance_list = list(instance_data.keys())


def save_config(name, data, remove=False):
    _config = load_existing_config()
    if remove and name in _config:
        _config.pop(name)
    else:
        _config[name] = data

    with config_file.open("w", encoding="utf-8") as fs:
        json.dump(_config, fs, indent=4)


def get_data_dir(instance_name: str):
    data_path = Path(appdir.user_data_dir) / "data" / instance_name

    print()
    print(
        "We've attempted to figure out a sane default data location which is printed below."
        " If you don't want to change this default please press [ENTER],"
        " otherwise input your desired data location."
    )
    print()
    print("Default: {}".format(data_path))

    data_path_input = input("> ")

    if data_path_input != "":
        data_path = Path(data_path_input)

    try:
        exists = data_path.exists()
    except OSError:
        print(
            "We were unable to check your chosen directory."
            " Provided path may contain an invalid character."
        )
        sys.exit(1)

    if not exists:
        try:
            data_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            print(
                "We were unable to create your chosen directory."
                " You may need to restart this process with admin"
                " privileges."
            )
            sys.exit(1)

    print("You have chosen {} to be your data directory.".format(data_path))
    if not click.confirm("Please confirm", default=True):
        print("Please start the process over.")
        sys.exit(0)
    return str(data_path.resolve())


def get_storage_type():
    storage_dict = {1: "JSON", 2: "PostgreSQL", 3: "RedisJSON"}
    storage = None
    while storage is None:
        print()
        print("Please choose your storage backend (if you're unsure, just choose 1).")
        print("1. JSON (file storage, requires no database).")
        print("2. PostgreSQL (Requires a database server)")
        print("3. RedisJSON (Requires a redis server with the RedisJSON plugin)")
        storage = input("> ")
        try:
            storage = int(storage)
        except ValueError:
            storage = None
        else:
            if storage not in storage_dict:
                storage = None
    return storage


def get_name() -> str:
    name = ""
    while len(name) == 0:
        print(
            "Please enter a name for your instance,"
            " it will be used to run your bot from here on out.\n"
            "This name is case-sensitive and should only include characters"
            " A-z, numbers, underscores (_) and periods (.)."
        )
        name = input("> ")
        if re.fullmatch(r"[A-Za-z0-9_\.\-]*", name) is None:
            print(
                "ERROR: Instance names can only include characters A-z, numbers, "
                "underscores (_) and periods (.)."
            )
            name = ""
        elif "-" in name and not confirm(
            "Hyphens (-) in instance names may cause issues. Are you sure you want to continue with this instance name?",
            default=False,
        ):
            name = ""

        print()  # new line for aesthetics
    return name


def basic_setup():
    """
    Creates the data storage folder.
    :return:
    """

    print(
        "Hello! Before we begin, we need to gather some initial information for the new instance."
    )
    name = get_name()

    default_data_dir = get_data_dir(name)

    default_dirs = deepcopy(data_manager.basic_config_default)
    default_dirs["DATA_PATH"] = default_data_dir

    storage = get_storage_type()

    storage_dict = {1: BackendType.JSON, 2: BackendType.POSTGRES, 3: BackendType.REDIS}
    storage_type: BackendType = storage_dict.get(storage, BackendType.JSON)
    default_dirs["STORAGE_TYPE"] = storage_type.value
    driver_cls = drivers.get_driver_class(storage_type)
    default_dirs["STORAGE_DETAILS"] = driver_cls.get_config_details()

    if name in instance_data:
        print(
            "WARNING: An instance already exists with this name. "
            "Continuing will overwrite the existing instance config."
        )
        if not click.confirm("Are you absolutely certain you want to continue?", default=False):
            print("Not continuing")
            sys.exit(0)
    save_config(name, default_dirs)

    print()
    print(
        "Your basic configuration has been saved. Please run `redbot <name>` to"
        " continue your setup process and to run the bot.\n\n"
        "First time? Read the quickstart guide:\n"
        "https://docs.discord.red/en/stable/getting_started.html"
    )


def get_current_backend(instance) -> BackendType:
    return BackendType(instance_data[instance]["STORAGE_TYPE"])


def get_target_backend(backend) -> BackendType:
    if backend == "json":
        return BackendType.JSON
    elif backend == "postgres":
        return BackendType.POSTGRES
    elif backend == "redis":
        return BackendType.REDIS


async def do_migration(
    current_backend: BackendType, target_backend: BackendType
) -> Dict[str, Any]:
    cur_driver_cls = drivers._get_driver_class_include_old(current_backend)
    new_driver_cls = drivers.get_driver_class(target_backend)
    try:
        cur_storage_details = data_manager.storage_details()
        new_storage_details = new_driver_cls.get_config_details()

        await cur_driver_cls.initialize(**cur_storage_details)
        await new_driver_cls.initialize(**new_storage_details)

        await config.migrate(cur_driver_cls, new_driver_cls)
    except Exception as e:
        conversion_log.exception(e, exc_info=e)
        new_storage_details = None

    with contextlib.suppress(Exception):
        await cur_driver_cls.teardown()
    with contextlib.suppress(Exception):
        await new_driver_cls.teardown()

    return new_storage_details


async def create_backup(instance: str, destination_folder: Path = Path.home()) -> None:
    data_manager.load_basic_configuration(instance)
    backend_type = get_current_backend(instance)
    if backend_type != BackendType.JSON:
        await do_migration(backend_type, BackendType.JSON)
    print("Backing up the instance's data...")
    backup_fpath = await red_create_backup(destination_folder)
    if backup_fpath is not None:
        print(f"A backup of {instance} has been made. It is at {backup_fpath}")
    else:
        print("Creating the backup failed.")


async def remove_instance(
    instance,
    interactive: bool = False,
    delete_data: Optional[bool] = None,
    _create_backup: Optional[bool] = None,
    drop_db: Optional[bool] = None,
    remove_datapath: Optional[bool] = None,
):
    data_manager.load_basic_configuration(instance)

    if interactive is True and delete_data is None:
        delete_data = click.confirm(
            "Would you like to delete this instance's data?", default=False
        )

    if interactive is True and _create_backup is None:
        _create_backup = click.confirm(
            "Would you like to make a backup of the data for this instance?", default=False
        )

    if _create_backup is True:
        await create_backup(instance)

    backend = get_current_backend(instance)
    driver_cls = drivers.get_driver_class(backend)
    await driver_cls.initialize(**data_manager.storage_details())
    try:
        if delete_data is True:
            await driver_cls.delete_all_data(interactive=interactive, drop_db=drop_db)

        if interactive is True and remove_datapath is None:
            remove_datapath = click.confirm(
                "Would you like to delete the instance's entire datapath?", default=False
            )

        if remove_datapath is True:
            data_path = data_manager.core_data_path().parent
            safe_delete(data_path)

        save_config(instance, {}, remove=True)
    finally:
        await driver_cls.teardown()
    print("The instance {} has been removed\n".format(instance))


async def remove_instance_interaction():
    if not instance_list:
        print("No instances have been set up!")
        return

    print(
        "You have chosen to remove an instance. The following "
        "is a list of instances that currently exist:\n"
    )
    for instance in instance_data.keys():
        print("{}\n".format(instance))
    print("Please select one of the above by entering its name")
    selected = input("> ")

    if selected not in instance_data.keys():
        print("That isn't a valid instance!")
        return

    await remove_instance(selected, interactive=True)


@click.group(invoke_without_command=True)
@click.option("--debug", type=bool)
@click.pass_context
def cli(ctx, debug):
    """Create a new instance."""
    level = logging.DEBUG if debug else logging.INFO
    base_logger = logging.getLogger("red")
    base_logger.setLevel(level)
    formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    base_logger.addHandler(stdout_handler)

    if ctx.invoked_subcommand is None:
        basic_setup()


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.option(
    "--no-prompt",
    "interactive",
    is_flag=True,
    default=True,
    help="Don't ask for user input during the process.",
)
@click.option(
    "--delete-data/--no-delete-data",
    "delete_data",
    is_flag=True,
    default=None,
    help=(
        "Delete this instance's data. "
        "If these options and --no-prompt are omitted, you will be asked about this."
    ),
)
@click.option(
    "--backup/--no-backup",
    "_create_backup",
    is_flag=True,
    default=None,
    help=(
        "Create backup of this instance's data. "
        "If these options and --no-prompt are omitted, you will be asked about this."
    ),
)
@click.option(
    "--drop-db/--no-drop-db",
    is_flag=True,
    default=None,
    help=(
        "Drop the entire database containing this instance's data. Has no effect on JSON "
        "instances, or if --no-delete-data is set. If these options and --no-prompt are omitted,"
        "you will be asked about this."
    ),
)
@click.option(
    "--remove-datapath/--no-remove-datapath",
    is_flag=True,
    default=None,
    help=(
        "Remove this entire instance's datapath. If these options and --no-prompt are omitted, "
        "you will be asked about this. NOTE: --remove-datapath will override --no-delete-data "
        "for JSON instances."
    ),
)
def delete(
    instance: str,
    interactive: bool,
    delete_data: Optional[bool],
    _create_backup: Optional[bool],
    drop_db: Optional[bool],
    remove_datapath: Optional[bool],
):
    """Removes an instance."""
    asyncio.run(
        remove_instance(
            instance, interactive, delete_data, _create_backup, drop_db, remove_datapath
        )
    )


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.argument("backend", type=click.Choice(["json", "postgres", "redis"]))
def convert(instance, backend):
    """Convert data backend of an instance."""
    current_backend = get_current_backend(instance)
    target = get_target_backend(backend)
    data_manager.load_basic_configuration(instance)

    default_dirs = deepcopy(data_manager.basic_config_default)
    default_dirs["DATA_PATH"] = str(Path(instance_data[instance]["DATA_PATH"]))

    if current_backend == BackendType.MONGOV1:
        raise RuntimeError("Please see the 3.2 release notes for upgrading a bot using mongo.")
    else:
        loop = asyncio.get_event_loop()
        new_storage_details = loop.run_until_complete(do_migration(current_backend, target))

    if new_storage_details is not None:
        default_dirs["STORAGE_TYPE"] = target.value
        default_dirs["STORAGE_DETAILS"] = new_storage_details
        save_config(instance, default_dirs)
        conversion_log.info(f"Conversion to {target} complete.")
    else:
        conversion_log.info(
            f"Cannot convert {current_backend.value} to {target.value} at this time."
        )


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.argument(
    "destination_folder",
    type=click.Path(
        exists=False, dir_okay=True, file_okay=False, resolve_path=True, writable=True
    ),
    default=Path.home(),
)
def backup(instance: str, destination_folder: Union[str, Path]) -> None:
    """Backup instance's data."""
    asyncio.run(create_backup(instance, Path(destination_folder)))


def run_cli():
    # Setuptools entry point script stuff...
    try:
        cli()  # pylint: disable=no-value-for-parameter  # click
    except KeyboardInterrupt:
        print("Exiting...")
    else:
        print("Exiting...")


if __name__ == "__main__":
    run_cli()
