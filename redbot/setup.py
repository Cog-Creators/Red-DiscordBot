from __future__ import annotations

from redbot import _early_init

# this needs to be called as early as possible
_early_init()

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
from typing import Any, Dict, IO, List, NoReturn, Optional, Set, Tuple, Union

import click

import redbot.logging
from redbot.core._cli import confirm
from redbot.core.utils._internal_utils import (
    BackupDetails,
    safe_delete,
    create_backup as red_create_backup,
    cli_level_to_log_level,
    detailed_progress,
)
from redbot.core import config, data_manager, _downloader
from redbot.core._cog_manager import CogManager
from redbot.core._config import migrate
from redbot.core._cli import ExitCodes, asyncio_run
from redbot.core.data_manager import appdir, config_dir, config_file
from redbot.core._drivers import (
    BackendType,
    IdentifierData,
    get_driver_class,
    get_driver_class_include_old,
)

conversion_log = logging.getLogger("red.converter")

try:
    config_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print("You don't have permission to write to '{}'\nExiting...".format(config_dir))
    sys.exit(ExitCodes.CONFIGURATION_ERROR)

instance_data = data_manager.load_existing_config()
if instance_data is None:
    instance_list = []
else:
    instance_list = list(instance_data.keys())


def save_config(name, data, remove=False):
    _config = data_manager.load_existing_config()
    if remove and name in _config:
        _config.pop(name)
    else:
        _config[name] = data

    with config_file.open("w", encoding="utf-8") as fs:
        json.dump(_config, fs, indent=4)


def get_default_data_path(instance_name: str) -> Path:
    return Path(appdir.user_data_dir) / "data" / instance_name


def get_data_dir(*, instance_name: str, data_path: Optional[Path], interactive: bool) -> str:
    if data_path is not None:
        return str(data_path.resolve())
    default_data_path = get_default_data_path(instance_name)
    if not interactive:
        return str(default_data_path.resolve())

    print(
        "We've attempted to figure out a sane default data location which is printed below."
        " If you don't want to change this default please press [ENTER],"
        " otherwise input your desired data location."
    )
    print()
    print(f"Default: {default_data_path}")

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
                print(
                    "We were unable to create your chosen directory."
                    " You may need to create the directory and set proper permissions"
                    " for it manually before it can be used as the data directory."
                )
                continue

        print(f"You have chosen {str(data_path)!r} to be your data directory.")
        if click.confirm("Please confirm", default=True):
            break

    return str(data_path.resolve())


def get_storage_type(backend: Optional[str], *, interactive: bool):
    if backend:
        return get_target_backend(backend)
    if not interactive:
        return BackendType.JSON
    storage_dict = {1: BackendType.JSON, 2: BackendType.POSTGRES}
    storage = None
    while storage is None:
        print()
        print("Please choose your storage backend.")
        print("1. JSON (file storage, requires no database).")
        print("2. PostgreSQL (Requires a database server)")
        print("If you're unsure, press [ENTER] to use the recommended default - JSON.")

        storage = input("> ")
        if not storage:
            return BackendType.JSON
        try:
            storage = int(storage)
        except ValueError:
            storage = None
        else:
            if storage not in storage_dict:
                storage = None
    return storage_dict[storage]


INSTANCE_NAME_RE = re.compile(
    r"""
    [a-z0-9]              # starts with letter or digit
    (?:
        (?!.*[_\.\-]{2})  # ensure no consecutive dots, hyphens, or underscores
        [a-z0-9_\.\-]*    # match allowed characters
        [a-z0-9]          # ensure string ends with letter or digit
    )?                    # optional to allow strings of length 1
    """,
    re.VERBOSE | re.IGNORECASE,
)


def get_name(name: str = "", *, confirm_overwrite: bool = False) -> str:
    if name:
        if INSTANCE_NAME_RE.fullmatch(name) is None:
            print(
                "ERROR: Instance names need to start and end with a letter or a number"
                " and can only include characters A-z, numbers,"
                " and non-consecutive underscores (_) and periods (.)."
            )
            sys.exit(ExitCodes.INVALID_CLI_USAGE)
        if name in instance_data and not confirm_overwrite:
            print(
                "An instance with this name already exists.\n"
                "If you want to remove the existing instance and replace it with this one,"
                " run this command with --overwrite-existing-instance flag."
            )
            sys.exit(ExitCodes.INVALID_CLI_USAGE)
        return name

    name = ""
    while not name:
        print(
            "Please enter a name for your instance,"
            " it will be used to run your bot from here on out.\n"
            "This name is case-sensitive, needs to start and end with a letter or a number"
            " and should only include characters A-z, numbers,"
            " and non-consecutive underscores (_) and periods (.)."
        )
        name = input("> ")
        if not name:
            pass
        elif INSTANCE_NAME_RE.fullmatch(name) is None:
            print(
                "ERROR: Instance names need to start and end with a letter or a number"
                " and can only include characters A-z, numbers,"
                " and non-consecutive underscores (_) and periods (.)."
            )
            name = ""
        elif "-" in name and not confirm(
            "Hyphens (-) in instance names may cause issues. Are you sure you want to continue with this instance name?",
            default=False,
        ):
            name = ""
        elif name in instance_data and not confirm_overwrite:
            print(
                "WARNING: An instance already exists with this name."
                " Continuing will overwrite the existing instance config."
            )
            if not click.confirm(
                "Are you absolutely certain you want to continue with this instance name?",
                default=False,
            ):
                name = ""

        print()  # new line for aesthetics
    return name


def basic_setup(
    *,
    name: str,
    data_path: Optional[Path],
    backend: Optional[str],
    interactive: bool,
    overwrite_existing_instance: bool,
):
    """
    Creates the data storage folder.
    :return:
    """
    if not interactive and not name:
        print(
            "Providing instance name through --instance-name is required"
            " when using non-interactive mode."
        )
        sys.exit(ExitCodes.INVALID_CLI_USAGE)

    if interactive:
        print(
            "Hello! Before we begin, we need to gather some initial information"
            " for the new instance."
        )
    name = get_name(name, confirm_overwrite=overwrite_existing_instance)

    default_data_dir = get_data_dir(
        instance_name=name, data_path=data_path, interactive=interactive
    )

    default_dirs = deepcopy(data_manager.basic_config_default)
    default_dirs["DATA_PATH"] = default_data_dir

    storage_type = get_storage_type(backend, interactive=interactive)

    default_dirs["STORAGE_TYPE"] = storage_type.value
    driver_cls = get_driver_class(storage_type)
    default_dirs["STORAGE_DETAILS"] = driver_cls.get_config_details()

    save_config(name, default_dirs)

    if interactive:
        print()
        print(
            f"Your basic configuration has been saved. Please run `redbot {name}` to"
            " continue your setup process and to run the bot.\n\n"
            "First time? Read the quickstart guide:\n"
            "https://docs.discord.red/en/stable/getting_started.html"
        )
    else:
        print("Your basic configuration has been saved.")


def get_current_backend(instance: str) -> BackendType:
    return BackendType(instance_data[instance]["STORAGE_TYPE"])


def get_target_backend(backend: str) -> BackendType:
    if backend == "json":
        return BackendType.JSON
    elif backend == "postgres":
        return BackendType.POSTGRES


async def do_migration(
    current_backend: BackendType,
    target_backend: BackendType,
    new_storage_details: Optional[dict] = None,
) -> Dict[str, Any]:
    cur_driver_cls = get_driver_class_include_old(current_backend)
    new_driver_cls = get_driver_class(target_backend)
    cur_storage_details = data_manager.storage_details()
    if new_storage_details is None:
        new_storage_details = new_driver_cls.get_config_details()

    await cur_driver_cls.initialize(**cur_storage_details)
    await new_driver_cls.initialize(**new_storage_details)

    await migrate(cur_driver_cls, new_driver_cls)

    await cur_driver_cls.teardown()
    await new_driver_cls.teardown()

    return new_storage_details


async def create_backup(instance: str, destination_folder: Path = Path.home()) -> None:
    data_manager.load_basic_configuration(instance)
    backend_type = get_current_backend(instance)
    if backend_type != BackendType.JSON:
        await do_migration(backend_type, BackendType.JSON)
    print("Backing up the instance's data...")
    driver_cls = get_driver_class()
    await driver_cls.initialize(**data_manager.storage_details())
    backup_fpath = await red_create_backup(destination_folder)
    await driver_cls.teardown()
    if backup_fpath is not None:
        print(f"A backup of {instance} has been made. It is at {backup_fpath}")
    else:
        print("Creating the backup failed.")


async def remove_instance(
    instance: str,
    interactive: bool = False,
    delete_data: Optional[bool] = None,
    _create_backup: Optional[bool] = None,
    drop_db: Optional[bool] = None,
    remove_datapath: Optional[bool] = None,
) -> None:
    data_manager.load_basic_configuration(instance)
    backend = get_current_backend(instance)

    if interactive is True and delete_data is None:
        msg = "Would you like to delete this instance's data?"
        if backend != BackendType.JSON:
            msg += " The database server must be running for this to work."
        delete_data = click.confirm(msg, default=False)

    if interactive is True and _create_backup is None:
        msg = "Would you like to make a backup of the data for this instance?"
        if backend != BackendType.JSON:
            msg += " The database server must be running for this to work."
        _create_backup = click.confirm(msg, default=False)

    if _create_backup is True:
        await create_backup(instance)

    driver_cls = get_driver_class(backend)
    if delete_data is True:
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
    print("The instance {} has been removed.".format(instance))


async def remove_instance_interaction() -> None:
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
    STORAGE_BACKENDS = {
        BackendType.JSON: "JSON",
        BackendType.POSTGRES: "PostgreSQL",
        BackendType.MONGOV1: "MongoDB (unavailable)",
        BackendType.MONGO: "MongoDB (unavailable)",
    }

    def __init__(
        self,
        tar: tarfile.TarFile,
        backup_details: BackupDetails,
        name: str,
        data_path: Path,
        storage_type: BackendType,
        storage_details: dict,
        restore_downloader: Optional[bool] = None,
    ):
        self.tar = tar
        self.backup_details = backup_details
        self.backup_version = backup_details["backup_version"]
        self.name = name
        self._data_path = data_path
        self.storage_type = storage_type
        self.storage_details = storage_details
        self._restore_downloader: Optional[bool] = restore_downloader
        self._data_path_ensure_result: Optional[bool] = None

    @classmethod
    def from_tar(
        cls, tar: tarfile.TarFile, *, restore_downloader: Optional[bool] = None
    ) -> RestoreInfo:
        instance_name, raw_data = cls.get_instance_from_backup(tar)
        backup_details = cls.get_backup_details(tar)

        return cls(
            tar=tar,
            backup_details=backup_details,
            name=instance_name,
            data_path=Path(raw_data["DATA_PATH"]),
            storage_type=BackendType(raw_data["STORAGE_TYPE"]),
            storage_details=raw_data["STORAGE_DETAILS"],
            restore_downloader=restore_downloader,
        )

    @staticmethod
    def get_instance_from_backup(tar: tarfile.TarFile) -> Tuple[str, dict]:
        if (fp := open_file_from_tar(tar, "instance.json")) is None:
            print("This isn't a valid backup file!")
            sys.exit(1)
        with fp:
            return json.load(fp).popitem()

    @staticmethod
    def get_backup_details(tar: tarfile.TarFile) -> BackupDetails:
        if (fp := open_file_from_tar(tar, "backup_details.json")) is None:
            # backup version 1 doesn't have the details file
            return {"backup_version": 1}
        with fp:
            backup_details = json.load(fp)
        backup_version = backup_details.get("backup_version")
        if not isinstance(backup_version, int):
            print("This does not appear to be a valid backup.")
            sys.exit(1)
        if backup_version > 2:
            print("This backup was created using newer version of Red. Update Red to restore it.")
            sys.exit(1)
        return backup_details

    @property
    def data_path(self) -> Path:
        return self._data_path

    @data_path.setter
    def data_path(self, value: Path) -> None:
        self._data_path_ensure_result = None
        self._data_path = value

    @property
    def name_used(self) -> bool:
        return self.name in instance_list

    def ensure_data_path(self) -> bool:
        if self._data_path_ensure_result is not None:
            return self._data_path_ensure_result
        if self.data_path.is_absolute():
            try:
                # try making the dir since that's most reliant access check, if path does not exist
                self.data_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                self._data_path_ensure_result = False
            else:
                # if path exists, mkdir above is a no-op so we still have to check for write access
                self._data_path_ensure_result = os.access(self.data_path, os.W_OK)
        else:
            # if path is not absolute, it's not valid on the current OS, e.g.
            # Path('D:\\data').is_absolute() is False on Linux/macOS
            # Path('/some/path').is_absolute() is False on Windows
            self._data_path_ensure_result = False
        return self._data_path_ensure_result

    @property
    def data_path_not_empty(self) -> bool:
        if not self.ensure_data_path():
            return True
        try:
            return next(self.data_path.glob("*"), None) is not None
        except OSError:
            return True

    @property
    def backend_unavailable(self) -> bool:
        return self.storage_type in (BackendType.MONGOV1, BackendType.MONGO)

    @functools.cached_property
    def can_restore_downloader(self) -> bool:
        return "cogs/RepoManager/repos.json" in self.all_tar_member_names

    @functools.cached_property
    def restore_downloader(self) -> bool:
        if self._restore_downloader is not None:
            return self.can_restore_downloader
        return self.can_restore_downloader and click.confirm(
            "Do you want to restore 3rd-party repos and cogs installed through Downloader?",
            default=True,
        )

    @functools.cached_property
    def all_tar_members(self) -> List[tarfile.TarInfo]:
        return self.tar.getmembers()

    @functools.cached_property
    def all_tar_member_names(self) -> List[str]:
        return [tarinfo.name for tarinfo in self.all_tar_members]

    def get_tar_members_to_extract(self) -> List[tarfile.TarInfo]:
        ignored_members: Set[str] = {"backup_details.json", "instance.json"}
        if not self.restore_downloader:
            ignored_members |= {
                "cogs/RepoManager/repos.json",
                "cogs/RepoManager/settings.json",
                "cogs/Downloader/settings.json",
            }
        return [member for member in self.all_tar_members if member.name not in ignored_members]

    def print_instance_data(self) -> None:
        print("\nWhen the instance was backed up, it was using these settings:")
        print("  Original instance name:", self.name)
        print("  Original data path:", self.data_path)
        print("  Original storage backend:", self.STORAGE_BACKENDS[self.storage_type])
        self.print_storage_details()

    def print_storage_details(self, *, original: bool = True) -> None:
        if self.storage_type is BackendType.POSTGRES:
            if original:
                print("  Original storage details:")
            else:
                print("  Storage details:")
            for key in ("host", "port", "database", "user"):
                print(f"    - DB {key}:", self.storage_details[key])
            print("    - DB password: ***")

    def ask_for_changes(self, *, interactive: bool) -> None:
        if interactive:
            self._ask_for_optional_changes()
        self._ask_for_required_changes(interactive=interactive)

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

    @staticmethod
    def _error_and_exit(message: str) -> NoReturn:
        print(f"ERROR: {message}")
        sys.exit(1)

    @staticmethod
    def _warning(message: str) -> None:
        print(f"WARNING: {message}")

    @staticmethod
    def _info(message: str) -> None:
        print(f"INFO: {message}")

    def _ask_for_required_changes(self, interactive: bool) -> None:
        p = self._warning if interactive else self._error_and_exit
        if self.name_used:
            p("Original instance name is already used by a different instance.")
            p("Continuing will overwrite the existing instance config.")
            if click.confirm("Do you want to use different instance name?", default=True):
                self._ask_for_name()
        if not self.ensure_data_path():
            p(
                "Original data path can't be used as it cannot be written to by the current user."
                " You have to choose a different path."
            )
            self._ask_for_data_path()
        elif self.data_path_not_empty:
            p(
                "Original data path can't be used as it's not empty."
                " You have to choose a different path."
            )
            self._ask_for_data_path()
        if self.backend_unavailable:
            p(
                "Original storage backend is no longer available in Red."
                " You have to choose a different backend."
            )
            self._ask_for_storage()

    def _ask_for_name(self) -> None:
        self.name = get_name("")

    def _ask_for_data_path(self) -> None:
        while True:
            self.data_path = Path(
                get_data_dir(instance_name=self.name, data_path=None, interactive=True)
            )
            if not self.ensure_data_path():
                print("Given path can't be used as it cannot be written to by the current user.")
            elif self.data_path_not_empty:
                print("Given path can't be used as it's not empty.")
            else:
                return

    def _ask_for_storage(self) -> None:
        self.storage_type = get_storage_type(None, interactive=True)
        driver_cls = get_driver_class(self.storage_type)
        self.storage_details = driver_cls.get_config_details()

    def extractall(self) -> None:
        to_extract = self.get_tar_members_to_extract()
        with detailed_progress(unit="files") as progress:
            progress_tracker = progress.track(to_extract, description="Extracting data")
            # tar.errorlevel == 0 so errors are printed to stderr
            self.tar.extractall(path=self.data_path, members=progress_tracker)

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
            driver_cls = get_driver_class(self.storage_type)
            await driver_cls.initialize(**self.storage_details)
            try:
                await _downloader._init_without_bot(CogManager())
                await _downloader._restore_from_backup()
            finally:
                await driver_cls.teardown()
        elif self.backup_version == 1:
            self._info(
                "Downloader's data isn't included in the backup file"
                " - this backup was created with Red 3.5.24 or older."
            )
        elif not self.can_restore_downloader:
            self._warning("Downloader's data isn't included in the backup file.")

    async def run(
        self,
        *,
        interactive: bool,
        instance_name: str = "",
        data_path: Optional[Path] = None,
        backend: Optional[BackendType] = None,
        use_sane_default_data_path: bool = False,
    ) -> None:
        storage_details = {}
        if backend:
            driver_cls = get_driver_class(backend)
            storage_details = driver_cls.get_config_details()
            print("\n---")
        self.print_instance_data()

        if use_sane_default_data_path:
            data_path = get_default_data_path(instance_name or self.name)
        if instance_name or data_path or backend:
            print("\nThe following settings have been overridden with command options:")
        if instance_name:
            self.name = instance_name
            print("  Instance name:", instance_name)
        if data_path:
            self.data_path = data_path
            print("  Data path:", data_path)
        if backend:
            self.storage_type = backend
            self.storage_details = storage_details
            print("  Storage backend:", self.STORAGE_BACKENDS[backend])
            self.print_storage_details(original=False)

        self.ask_for_changes(interactive=interactive)
        await self.restore_data()

        print("Restore process has been completed.")


async def restore_instance(
    backup_path: Path,
    *,
    interactive: bool,
    skip_downloader_restore: bool,
    instance_name: str,
    data_path: Optional[Path],
    use_sane_default_data_path: bool = False,
    backend: Optional[str],
) -> None:
    try:
        tar = tarfile.open(backup_path)
    except tarfile.ReadError:
        print(
            "We couldn't open the given backup file. Make sure that you're passing correct file."
        )
        return

    print("Hello! This command will guide you through restore process.")
    if interactive:
        restore_downloader = False if skip_downloader_restore else None
    else:
        restore_downloader = not skip_downloader_restore
    with tar:
        # The filter functionality exists on Python 3.11.4+.
        # We'll use the value consistent with the 3.11's default
        # since there's no reason we shouldn't trust the archive
        # that we generated ourselves.
        tar.extraction_filter = getattr(tarfile, "fully_trusted_filter", None)
        restore_info = RestoreInfo.from_tar(
            tar,
            restore_downloader=restore_downloader,
        )
        await restore_info.run(
            interactive=interactive,
            instance_name=instance_name,
            data_path=data_path,
            use_sane_default_data_path=use_sane_default_data_path,
            backend=get_target_backend(backend) if backend else None,
        )


@click.group(invoke_without_command=True)
@click.option(
    "--debug",
    "--verbose",
    "-v",
    count=True,
    help=(
        "Increase the verbosity of the logs, each usage of this flag increases the verbosity"
        " level by 1."
    ),
)
@click.option(
    "--no-prompt",
    "interactive",
    type=bool,
    is_flag=True,
    default=True,
    help=(
        "Don't ask for user input during the process (non-interactive mode)."
        " This makes `--instance-name` required."
    ),
)
@click.option(
    "--instance-name",
    type=str,
    default="",
    help="Name of the new instance. Required if --no-prompt is passed.",
)
@click.option(
    "--data-path",
    type=click.Path(exists=False, dir_okay=True, file_okay=False, writable=True, path_type=Path),
    default=None,
    help=(
        "Data path of the new instance. If this option and --no-prompt are omitted,"
        " you will be asked for this."
    ),
)
@click.option(
    "--backend",
    type=click.Choice(["json", "postgres"]),
    default=None,
    help=(
        "Choose a backend type for the new instance."
        " If this option is omitted, you will be asked for this."
        " Defaults to JSON in non-interactive mode.\n"
        "Note: Choosing PostgreSQL will prevent the setup from being completely non-interactive."
    ),
)
@click.option(
    "--overwrite-existing-instance",
    type=bool,
    is_flag=True,
    help=(
        "Confirm overwriting of existing instance.\n"
        "Note: This removes *metadata* about the existing instance with that name."
    ),
)
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    interactive: bool,
    instance_name: str,
    data_path: Optional[Path],
    backend: Optional[str],
    overwrite_existing_instance: bool,
) -> None:
    """Create a new instance."""

    level = cli_level_to_log_level(debug)
    redbot.logging.init_logging(level)

    if ctx.invoked_subcommand is None:
        basic_setup(
            name=instance_name,
            data_path=data_path,
            backend=backend,
            overwrite_existing_instance=overwrite_existing_instance,
            interactive=interactive,
        )


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
) -> None:
    """Removes an instance."""
    asyncio_run(
        remove_instance(
            instance, interactive, delete_data, _create_backup, drop_db, remove_datapath
        )
    )


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.argument("backend", type=click.Choice(["json", "postgres"]))
def convert(instance: str, backend: str) -> None:
    """Convert data backend of an instance."""
    current_backend = get_current_backend(instance)
    target = get_target_backend(backend)
    data_manager.load_basic_configuration(instance)

    default_dirs = deepcopy(data_manager.basic_config_default)
    default_dirs["DATA_PATH"] = str(Path(instance_data[instance]["DATA_PATH"]))

    if current_backend == BackendType.MONGOV1:
        raise RuntimeError("Please see the 3.2 release notes for upgrading a bot using mongo.")
    else:
        new_storage_details = asyncio_run(do_migration(current_backend, target))

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
        dir_okay=True, file_okay=False, resolve_path=True, writable=True, path_type=Path
    ),
    default=Path.home(),
)
def backup(instance: str, destination_folder: Path) -> None:
    """Backup instance's data."""
    asyncio_run(create_backup(instance, destination_folder))


@cli.command()
@click.argument(
    "backup_file",
    type=click.Path(file_okay=True, resolve_path=True, readable=True, path_type=Path),
    metavar="<BACKUP_FILE>",
)
@click.option(
    "--no-prompt",
    "interactive",
    is_flag=True,
    default=True,
    help="Don't ask for user input during the process. Most of the values",
)
@click.option(
    "--no-restore-downloader",
    "skip_downloader_restore",
    is_flag=True,
    default=False,
    help="Skip restoring of 3rd-party repos and cogs installed through Downloader.",
)
@click.option(
    "--instance-name",
    type=str,
    default="",
    help=(
        "Name of the new instance. By default, the name stored in the backup will be used"
        " and, if the --no-prompt option was not specified, you will be able to change this"
        " before restoring"
    ),
)
@click.option(
    "--data-path",
    type=click.Path(exists=False, dir_okay=True, file_okay=False, writable=True, path_type=Path),
    default=None,
    help=(
        "Data path of the new instance. If this option and --no-prompt are omitted,"
        " you will be asked for this."
    ),
)
@click.option(
    "--use-sane-default-data-path",
    is_flag=True,
    default=False,
    help=(
        "Use the sane default data path derived from the instance name instead of using data path"
        " from the backup or specifying --data-path option."
    ),
)
@click.option(
    "--backend",
    type=click.Choice(["json", "postgres"]),
    default=None,
    help=(
        "Choose a backend type for the new instance."
        " By default, the backend of the backed up instance will be used"
        " and, if the --no-prompt option was not specified, you will be able to change this"
        " before restoring.\n"
        "Note: Choosing PostgreSQL will prevent the setup from being completely non-interactive."
    ),
)
def restore(
    backup_file: Path,
    interactive: bool,
    skip_downloader_restore: bool,
    instance_name: str,
    data_path: Optional[Path],
    use_sane_default_data_path: bool,
    backend: Optional[str],
) -> None:
    """Restore instance."""
    asyncio.run(
        restore_instance(
            backup_file,
            interactive=interactive,
            skip_downloader_restore=skip_downloader_restore,
            instance_name=instance_name,
            data_path=data_path,
            use_sane_default_data_path=use_sane_default_data_path,
            backend=backend,
        )
    )


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
