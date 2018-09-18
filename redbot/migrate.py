"""Migration script for data backends.

This script operates by first loading all data of an instance
into memory, and dumping it all onto whatever data backend is
specified afterwards - so this could be quite a memory-intensive
script.
"""
import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from redbot.core import data_manager, drivers

log = logging.getLogger(__name__)


async def load_json_data() -> Tuple[Dict, Dict]:
    log.info("JSON load starting...")
    core_data, cog_data = {}, {}
    core_data_path = data_manager.core_data_path()
    json_path = core_data_path / "settings.json"
    if json_path.is_file():
        with json_path.open() as file:
            core_data = json.load(file)
    else:
        log.warning("Core settings.json seems to be missing, it should be at %s", json_path)

    cog_data_path = data_manager.cog_data_path()
    for path in cog_data_path.iterdir():
        if not path.is_dir():
            log.info("Skipping %s as it is not a directory", path)
            continue
        json_path = path / "settings.json"
        if not json_path.is_file():
            log.info("Skipping directory %s as it does not contain a settings.json.", path)
            continue

        with json_path.open() as file:
            cog_data[path.stem] = json.load(file)

    log.info("JSON load complete!")
    return core_data, cog_data


class BaseDumper:
    DriverCls: type
    START_MSG: str = "Starting data dump..."

    def __init__(self, core_data: Dict[str, Any], cog_data: Dict[str, Any]) -> None:
        log.info(self.START_MSG)
        self.core_data: Dict[str, Any] = core_data
        self.cog_data: Dict[str, Any] = cog_data
        # noinspection PyUnresolvedReferences
        storage_details = self.DriverCls.get_config_details()
        self._core_driver: drivers.BaseDriver = self.DriverCls(
            "Core", "0", data_path_override=data_manager.core_data_path(), **storage_details
        )
        self._cog_drivers: List[drivers.BaseDriver] = []
        for cog_name, data in cog_data.items():
            for identifier, cog_data in data.items():
                self._cog_drivers.append(
                    self.DriverCls(
                        cog_name,
                        identifier,
                        data_path_override=data_manager.cog_data_path(raw_name=cog_name),
                        **storage_details,
                    )
                )

    async def _dump(self) -> None:
        inner_core_data = self.core_data.get("0", {})
        for key, value in inner_core_data.items():
            await self._core_driver.set(key, value=value)
        for cog_driver in self._cog_drivers:
            cog_data = self.cog_data[cog_driver.cog_name][cog_driver.unique_cog_identifier]
            for key, value in cog_data.items():
                await cog_driver.set(key, value=value)
        log.info("Dump complete!")

    def __await__(self):
        return self._dump().__await__()


class MongoDumper(BaseDumper):
    DriverCls = drivers.Mongo
    START_MSG = "Starting MongoDB data dump..."


LOADERS: Dict[str, Callable[[], Awaitable[Tuple[Dict, Dict]]]] = {"JSON": load_json_data}

DUMPERS: Dict[str, Callable[[Dict, Dict], Awaitable[None]]] = {"Mongo": MongoDumper}

AVAILABLE_LOADERS_STR = ", ".join(LOADERS)
AVAILABLE_DUMPERS_STR = ", ".join(DUMPERS)


def main(args: Optional[Sequence[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]

    options = _parse_cli_args(args)

    try:
        return _do_migration(options)
    except KeyboardInterrupt:
        print("Migration aborted.")
        return 1


def _parse_cli_args(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", help="The name of the instance to migrate data from.")
    parser.add_argument(
        "migrate_to",
        help=(
            "The name of the storage backend to migrate to. Valid backends: "
            + AVAILABLE_DUMPERS_STR
        ),
    )
    return parser.parse_args(args)


def _do_migration(options: argparse.Namespace) -> int:

    data_manager.load_basic_configuration(options.instance)
    cur_storage_type = data_manager.storage_type()

    if cur_storage_type not in LOADERS:
        print(
            f"Migration from the current storage backend for the {options.instance} instance is "
            f"not yet supported. Available backends for migrating from: {AVAILABLE_LOADERS_STR}"
        )
        return 1
    if options.migrate_to not in DUMPERS:
        print(
            f"Migration to the storage backend {options.migrate_to} is not yet supported. "
            f"Available backends for migrating to: {AVAILABLE_DUMPERS_STR}"
        )
        return 1

    load = LOADERS[cur_storage_type]
    dump = DUMPERS[options.migrate_to]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_migrate(load, dump))
    print(
        "Migration complete. You may now set up a new instance using redbot-setup "
        "which utilises the migrated data."
    )
    return 0


async def _migrate(load, dump) -> None:
    await dump(*(await load()))


if __name__ == "__main__":
    sys.exit(main())
