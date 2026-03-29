from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Tuple, Union

from packaging.version import Version

from . import installable
from .log import log

if TYPE_CHECKING:
    from .json_mixins import RepoJSONMixin


__all__ = ("REPO_SCHEMA", "INSTALLABLE_SCHEMA", "update_mixin")


class UseDefault:
    """To be used as sentinel."""


# sentinel value
USE_DEFAULT = UseDefault()
RED_TAG_READY_PATTERN = re.compile(r"^red-(?:[3-9]|[1-9][0-9]+)\.(?:[1-9][0-9]*)-ready$")


def ensure_tuple_of_str(
    info_file: Path, key_name: str, value: Union[Any, UseDefault]
) -> Tuple[str, ...]:
    default: Tuple[str, ...] = ()
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, list):
        log.warning(
            "Invalid value of '%s' key (expected list, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default
    for item in value:
        if not isinstance(item, str):
            log.warning(
                "Invalid item in '%s' list (expected str, got %s)"
                " in JSON information file at path: %s",
                key_name,
                type(item).__name__,
                info_file,
            )
            return default
    return tuple(value)


def ensure_str(info_file: Path, key_name: str, value: Union[Any, UseDefault]) -> str:
    default = ""
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, str):
        log.warning(
            "Invalid value of '%s' key (expected str, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default
    return value


def create_ensure_red_version(default: Version) -> EnsureCallable:
    def ensure_red_version(
        info_file: Path, key_name: str, value: Union[Any, UseDefault]
    ) -> Version:
        if value is USE_DEFAULT:
            return default
        if not isinstance(value, str):
            log.warning(
                "Invalid value of '%s' key (expected str, got %s)"
                " in JSON information file at path: %s",
                key_name,
                type(value).__name__,
                info_file,
            )
            return default
        try:
            version_info = Version(value)
        except ValueError:
            log.warning(
                "Invalid value of '%s' key (given value isn't a valid version string)"
                " in JSON information file at path: %s",
                key_name,
                info_file,
            )
            return default
        return version_info

    return ensure_red_version


def ensure_python_version(
    info_file: Path, key_name: str, value: Union[Any, UseDefault]
) -> Version:
    default = Version("3.5.1")
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, list):
        log.warning(
            "Invalid value of '%s' key (expected list, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default
    count = len(value)
    if count != 3:
        log.warning(
            "Invalid value of '%s' key (expected list with 3 items, got %s items)"
            " in JSON information file at path: %s",
            key_name,
            count,
            info_file,
        )
        return default
    for item in value:
        if not isinstance(item, int):
            log.warning(
                "Invalid item in '%s' list (expected int, got %s)"
                " in JSON information file at path: %s",
                key_name,
                type(item).__name__,
                info_file,
            )
            return default
    return Version(".".join(map(str, value)))


def ensure_bool(
    info_file: Path, key_name: str, value: Union[Any, UseDefault], *, default: bool = False
) -> bool:
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, bool):
        log.warning(
            "Invalid value of '%s' key (expected bool, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default
    return value


def ensure_required_cogs_mapping(
    info_file: Path, key_name: str, value: Union[Any, UseDefault]
) -> Dict[str, str]:
    default: Dict[str, str] = {}
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, dict):
        log.warning(
            "Invalid value of '%s' key (expected dict, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default
    # keys in json dicts are always strings
    for item in value.values():
        if not isinstance(item, str):
            log.warning(
                "Invalid item in '%s' dict (expected str, got %s)"
                " in JSON information file at path: %s",
                key_name,
                type(item).__name__,
                info_file,
            )
            return default
    return value


def ensure_installable_type(
    info_file: Path, key_name: str, value: Union[Any, UseDefault]
) -> installable.InstallableType:
    default = installable.InstallableType.COG
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, str):
        log.warning(
            "Invalid value of '%s' key (expected str, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default  # NOTE: old behavior was to use InstallableType.UNKNOWN
    if value in ("", "COG"):
        return installable.InstallableType.COG
    if value == "SHARED_LIBRARY":
        return installable.InstallableType.SHARED_LIBRARY
    return installable.InstallableType.UNKNOWN


def ensure_tags(info_file: Path, key_name: str, value: Union[Any, UseDefault]) -> Tuple[str, ...]:
    default: Tuple[str, ...] = ()
    if value is USE_DEFAULT:
        return default
    if not isinstance(value, list):
        log.warning(
            "Invalid value of '%s' key (expected list, got %s)"
            " in JSON information file at path: %s",
            key_name,
            type(value).__name__,
            info_file,
        )
        return default
    valid_tags = []
    for item in value:
        if not isinstance(item, str):
            log.warning(
                "Invalid item in '%s' list (expected str, got %s)"
                " in JSON information file at path: %s",
                key_name,
                type(item).__name__,
                info_file,
            )
            return default
        # `red-` tags are reserved for informational metadata we only support a subset of tags
        if not item.startswith("red-"):
            valid_tags.append(item)
            continue
        if RED_TAG_READY_PATTERN.match(item):
            valid_tags.append(item)
        else:
            log.warning(
                "Invalid value in '%s' list (tag starts with the reserved 'red-' prefix"
                " but does not use the only supported reserved tag format: 'red-X.Y-ready')"
                " in JSON information file at path: %s",
                key_name,
                info_file,
            )

    return tuple(value)


EnsureCallable = Callable[[Path, str, Union[Any, UseDefault]], Any]
SchemaType = Dict[str, EnsureCallable]

REPO_SCHEMA: SchemaType = {
    "author": ensure_tuple_of_str,
    "description": ensure_str,
    "install_msg": ensure_str,
    "short": ensure_str,
}
INSTALLABLE_SCHEMA: SchemaType = {
    "min_bot_version": create_ensure_red_version(Version("0.0.dev0")),
    # Using little-known version epoch feature to represent something that,
    # for all practical purposes, will be considered higher than any version number
    # that we may ever have.
    # https://packaging.python.org/en/latest/specifications/version-specifiers/#version-epochs
    "max_bot_version": create_ensure_red_version(Version("99999!99999.99999.post99999+hi.mom")),
    "min_python_version": ensure_python_version,
    "hidden": ensure_bool,
    "disabled": ensure_bool,
    "required_cogs": ensure_required_cogs_mapping,
    "requirements": ensure_tuple_of_str,
    "tags": ensure_tags,
    "type": ensure_installable_type,
    "end_user_data_statement": ensure_str,
}


def update_mixin(repo_or_installable: RepoJSONMixin, schema: SchemaType) -> None:
    info = repo_or_installable._info
    info_file = repo_or_installable._info_file
    for key, callback in schema.items():
        setattr(repo_or_installable, key, callback(info_file, key, info.get(key, USE_DEFAULT)))
