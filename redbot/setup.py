#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import sys
import re
import tarfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, IO, List, Optional, Set, Tuple, Union

import appdirs
import click
from tqdm import tqdm

from redbot.core import config, data_manager, drivers
from redbot.cogs.downloader.repo_manager import RepoManager
from redbot.core.drivers import BackendType
from redbot.core.utils._internal_utils import create_backup as red_create_backup, safe_delete

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
    default_data_path = Path(appdir.user_data_dir) / "data" / instance_name

    print()
    print(
        "We've attempted to figure out a sane default data location which is printed below."
        " If you don't want to change this default please press [ENTER],"
        " otherwise input your desired data location."
    )
    print()
    print("Default: {}".format(default_data_path))

    while True:
        data_path_input = input("> ")

        if data_path_input != "":
            data_path = Path(data_path_input)
        else:
            data_path = default_data_path

        try:
            exists = data_path.exists()
        except OSError:
            print(
                "We were unable to check your chosen directory."
                " Provided path may contain an invalid character."
            )
            continue

        if not exists:
            try:
                data_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                print("We were unable to create your chosen directory.")
                continue

        print("You have chosen {} to be your data directory.".format(data_path))
        if not click.confirm("Please confirm", default=True):
            continue
        break

    return str(data_path.resolve())


def get_storage_type():
    storage_dict = {1: BackendType.JSON, 2: BackendType.POSTGRES}
    storage = None
    while storage is None:
        print()
        print("Please choose your storage backend (if you're unsure, just choose 1).")
        print("1. JSON (file storage, requires no database).")
        print("2. PostgreSQL (Requires a database server)")
        storage = input("> ")
        try:
            storage = int(storage)
        except ValueError:
            storage = None
        else:
            if storage not in storage_dict:
                storage = None
    return storage_dict[storage]


def get_name() -> str:
    name = ""
    while not name:
        print(
            "Please enter a name for your instance,"
            " it will be used to run your bot from here on out.\n"
            "This name is case-sensitive and can only include characters"
            " A-z, numbers, underscores, and hyphens."
        )
        name = input("> ")
        if re.fullmatch(r"[a-zA-Z0-9_\-]*", name) is None:
            print(
                "ERROR: Instance name can only include"
                " characters A-z, numbers, underscores, and hyphens!"
            )
            name = ""
        elif name in instance_data:
            print(
                "WARNING: An instance already exists with this name. "
                "Continuing will overwrite the existing instance config."
            )
            if not click.confirm(
                "Are you absolutely certain you want to continue with this instance name?",
                default=False,
            ):
                name = ""
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

    storage_type = get_storage_type()

    default_dirs["STORAGE_TYPE"] = storage_type.value
    driver_cls = drivers.get_driver_class(storage_type)
    default_dirs["STORAGE_DETAILS"] = driver_cls.get_config_details()

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


async def do_migration(
    current_backend: BackendType,
    target_backend: BackendType,
    new_storage_details: Optional[dict] = None,
) -> Dict[str, Any]:
    cur_driver_cls = drivers._get_driver_class_include_old(current_backend)
    new_driver_cls = drivers.get_driver_class(target_backend)
    cur_storage_details = data_manager.storage_details()
    if new_storage_details is None:
        new_storage_details = new_driver_cls.get_config_details()

    await cur_driver_cls.initialize(**cur_storage_details)
    await new_driver_cls.initialize(**new_storage_details)

    await config.migrate(cur_driver_cls, new_driver_cls)

    await cur_driver_cls.teardown()
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

    if delete_data is True:
        backend = get_current_backend(instance)
        driver_cls = drivers.get_driver_class(backend)
        await driver_cls.initialize(**data_manager.storage_details())
        try:
            await driver_cls.delete_all_data(interactive=interactive, drop_db=drop_db)
        finally:
            await driver_cls.teardown()

    if interactive is True and remove_datapath is None:
        remove_datapath = click.confirm(
            "Would you like to delete the instance's entire datapath?", default=False
        )

    if remove_datapath is True:
        data_path = data_manager.core_data_path().parent
        safe_delete(data_path)

    save_config(instance, {}, remove=True)
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


def open_file_from_tar(tar: tarfile.TarFile, arcname: str) -> Optional[IO[bytes]]:
    try:
        fp = tar.extractfile(arcname)
    except (KeyError, tarfile.StreamError):
        return None
    return fp


class RestoreInfo:
    def __init__(
        self,
        tar: tarfile.TarFile,
        backup_version: int,
        name: str,
        data_path: Path,
        storage_type: BackendType,
        storage_details: dict,
    ):
        self.tar = tar
        self.backup_version = backup_version
        self.name = name
        self.data_path = data_path
        self.storage_type = storage_type
        self.storage_details = storage_details

    @classmethod
    def from_tar(cls, tar: tarfile.TarFile) -> RestoreInfo:
        instance_name, raw_data = cls.get_instance_from_backup(tar)
        backup_version = cls.get_backup_version(tar)

        return cls(
            tar=tar,
            backup_version=backup_version,
            name=instance_name,
            data_path=Path(raw_data["DATA_PATH"]),
            storage_type=BackendType(raw_data["STORAGE_TYPE"]),
            storage_details=raw_data["STORAGE_DETAILS"],
        )

    @staticmethod
    def get_instance_from_backup(tar: tarfile.TarFile) -> Tuple[str, dict]:
        if (fp := open_file_from_tar(tar, "instance.json")) is None:
            print("This isn't a valid backup file!")
            sys.exit(1)
        with fp:
            return json.load(fp).popitem()

    @staticmethod
    def get_backup_version(tar: tarfile.TarFile) -> int:
        if (fp := open_file_from_tar(tar, "backup.version")) is None:
            # backup version 1 doesn't have the version file
            return 1
        with fp:
            backup_version = int(fp.read())
        if backup_version > 2:
            print("This backup was created using newer version of Red. Update Red to restore it.")
            sys.exit(1)
        return backup_version

    @property
    def name_used(self) -> bool:
        return self.name in instance_list

    @property
    def data_path_not_empty(self) -> bool:
        return self.data_path.exists() and next(self.data_path.glob("*"), None) is not None

    @property
    def backend_unavailable(self) -> bool:
        return self.storage_type in (BackendType.MONGOV1, BackendType.MONGO)

    @functools.cached_property
    def restore_downloader(self) -> bool:
        return "cogs/RepoManager/repos.json" in self.all_tar_member_names and click.confirm(
            "Do you want to restore 3rd-party repos and cogs installed through Downloader?\n"
            "Full offline restore process for this hasn't been made yet, so after it's done"
            " you will have to load Downloader and run `[p]cog update` command "
            " to reinstall all cogs you had installed before.",
            default=True,
        )

    @functools.cached_property
    def all_tar_members(self) -> List[tarfile.TarInfo]:
        return self.tar.getmembers()

    @functools.cached_property
    def all_tar_member_names(self) -> List[str]:
        return [tarinfo.name for tarinfo in self.all_tar_members]

    @functools.cached_property
    def tar_members_to_extract(self) -> List[tarfile.TarInfo]:
        ignored_members: Set[str] = {"backup.version", "instance.json"}
        if not self.restore_downloader:
            ignored_members |= {
                "cogs/RepoManager/repos.json",
                "cogs/RepoManager/settings.json",
                "cogs/Downloader/settings.json",
            }
        return [member for member in self.all_tar_members if member.name not in ignored_members]

    def print_instance_data(self) -> None:
        print("\nWhen the instance was backuped, it was using these settings:")
        print("  Original instance name:", self.name)
        print("  Original data path:", self.data_path)
        storage_backends = {
            BackendType.JSON: "JSON",
            BackendType.POSTGRES: "PostgreSQL",
            BackendType.MONGOV1: "MongoDB (unavailable)",
            BackendType.MONGO: "MongoDB (unavailable)",
        }
        print("  Original storage backend:", storage_backends[self.storage_type])
        if self.storage_type is BackendType.POSTGRES:
            print("  Original storage details:")
            for key in ("host", "port", "database", "user"):
                print(f"    - DB {key}:", self.storage_details[key])
            print("    - DB password: ***")

    def ask_for_changes(self) -> None:
        self._ask_for_optional_changes()
        self._ask_for_required_changes()

    def _ask_for_optional_changes(self) -> None:
        if click.confirm("\nWould you like to change anything?"):
            if not self.name_used and click.confirm("Do you want to use different instance name?"):
                self._ask_for_name()
            if not self.data_path_not_empty and click.confirm(
                "Do you want to use different data path?"
            ):
                self._ask_for_data_path()
            if not self.backend_unavailable and click.confirm(
                "Do you want to use different storage backend or change storage details?"
            ):
                self._ask_for_storage()

    def _ask_for_required_changes(self) -> None:
        if self.name_used:
            print(
                "WARNING: Original instance name is already used by a different instance."
                " Continuing will overwrite the existing instance config."
            )
            if click.confirm("Do you want to use different instance name?", default=True):
                self._ask_for_name()
        if self.data_path_not_empty:
            print(
                "Original data path can't be used as it's not empty."
                " You have to choose a different path."
            )
            self._ask_for_data_path()
        if self.backend_unavailable:
            print(
                "Original storage backend is no longer available in Red."
                " You have to choose a different backend."
            )
            self._ask_for_storage()

    def _ask_for_name(self) -> None:
        self.name = get_name()

    def _ask_for_data_path(self) -> None:
        while True:
            self.data_path = Path(get_data_dir(self.name))
            if not self.data_path_not_empty:
                return
            print("Given path can't be used as it's not empty.")

    def _ask_for_storage(self) -> None:
        self.storage_type = get_storage_type()
        driver_cls = drivers.get_driver_class(self.storage_type)
        self.storage_details = driver_cls.get_config_details()

    def extractall(self) -> None:
        progress_bar = tqdm(
            self.tar_members_to_extract, desc="Extracting data", unit=" files", dynamic_ncols=True
        )
        # tar.errorlevel == 0 so errors are printed to stderr
        self.tar.extractall(path=self.data_path, members=progress_bar)

    def get_basic_config(self, use_json: bool = False) -> dict:
        default_dirs = deepcopy(data_manager.basic_config_default)
        default_dirs["DATA_PATH"] = str(self.data_path)
        if use_json:
            default_dirs["STORAGE_TYPE"] = BackendType.JSON.value
            default_dirs["STORAGE_DETAILS"] = {}
        else:
            default_dirs["STORAGE_TYPE"] = self.storage_type.value
            default_dirs["STORAGE_DETAILS"] = self.storage_details
        return default_dirs

    async def restore_data(self) -> None:
        self.extractall()

        # data in backup file is using json
        save_config(self.name, self.get_basic_config(use_json=True))
        data_manager.load_basic_configuration(self.name)

        if self.storage_type is not BackendType.JSON:
            await do_migration(BackendType.JSON, self.storage_type, self.storage_details)
            save_config(self.name, self.get_basic_config())
            data_manager.load_basic_configuration(self.name)

        if self.restore_downloader:
            driver_cls = drivers.get_driver_class(self.storage_type)
            await driver_cls.initialize(**self.storage_details)
            try:
                repo_mgr = RepoManager()
                # this line shouldn't be needed since there are no repos:
                # await repo_mgr.initialize()
                await repo_mgr._restore_from_backup()
            finally:
                await driver_cls.teardown()
        elif self.backup_version == 1:
            print(
                "INFO: Downloader's data isn't included in the backup file"
                " - this backup was created with Red 3.3.7 or older."
            )
        else:
            print("WARNING: Downloader's data isn't included in the backup file.")

    async def run(self) -> None:
        self.print_instance_data()
        self.ask_for_changes()
        await self.restore_data()

        print("Restore process has been completed.")
        if self.restore_downloader:
            print(
                "Remember to run these commands after you start Red"
                " to complete restoring of 3rd-party cogs:\n"
                "[p]load downloader\n"
                "[p]cog update"
            )


async def restore_instance():
    print("Hello! This command will guide you through restore process.\n")
    backup_path_input = ""
    while not backup_path_input:
        print("Please enter the path to instance's backup:")
        backup_path_input = input("> ")
        backup_path = Path(backup_path_input)
        try:
            backup_path = backup_path.resolve()
        except OSError:
            print("This doesn't look like a valid path.")
            backup_path_input = ""
        else:
            if not backup_path.is_file():
                print("This path doesn't exist or it's not a file.")
                backup_path_input = ""

    try:
        tar = tarfile.open(backup_path)
    except tarfile.ReadError:
        print(
            "We couldn't open the given backup file. Make sure that you're passing correct file."
        )
        return
    with tar:
        restore_info = RestoreInfo.from_tar(tar)
        await restore_info.run()


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True)
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
@click.argument("instance", type=click.Choice(instance_list))
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
        "Drop the entire database constaining this instance's data. Has no effect on JSON "
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
@click.argument("instance", type=click.Choice(instance_list))
@click.argument("backend", type=click.Choice(["json", "postgres"]))
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
        new_storage_details = asyncio.run(do_migration(current_backend, target))

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
@click.argument("instance", type=click.Choice(instance_list))
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


@cli.command()
def restore() -> None:
    """Restore instance."""
    asyncio.run(restore_instance())


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
