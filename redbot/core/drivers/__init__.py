import enum
from typing import Optional, Type

from .base import BaseDriver, ConfigCategory, IdentifierData
from .json import JsonDriver
from .mongo import MongoDriver
from .postgres import PostgresDriver
from .. import data_manager

__all__ = [
    "get_driver",
    "ConfigCategory",
    "IdentifierData",
    "BaseDriver",
    "JsonDriver",
    "MongoDriver",
    "PostgresDriver",
    "BackendType",
]


class BackendType(enum.Enum):
    JSON = "JSON"
    MONGO = "MongoDBV2"
    MONGOV1 = "MongoDB"
    POSTGRES = "Postgres"


_DRIVER_CLASSES = {
    BackendType.JSON: JsonDriver,
    BackendType.MONGO: MongoDriver,
    BackendType.POSTGRES: PostgresDriver,
}


def get_driver_class(storage_type: Optional[BackendType] = None) -> Type[BaseDriver]:
    """Get the driver class for the given storage type.

    Parameters
    ----------
    storage_type : Optional[BackendType]
        The backend you want a driver class for. Omit to try to obtain
        the backend from data manager.

    Returns
    -------
    Type[BaseDriver]
        A subclass of `BaseDriver`.

    Raises
    ------
    ValueError
        If there is no driver for the given storage type.

    """
    if storage_type is None:
        storage_type = BackendType(data_manager.storage_type())
    try:
        return _DRIVER_CLASSES[storage_type]
    except KeyError:
        raise ValueError(f"No driver found for storage type {storage_type}") from None


def get_driver(
    cog_name: str, identifier: str, storage_type: Optional[BackendType] = None, **kwargs
):
    """Get a driver instance.

    Parameters
    ----------
    cog_name : str
        The cog's name.
    identifier : str
        The cog's discriminator.
    storage_type : Optional[BackendType]
        The backend you want a driver for. Omit to try to obtain the
        backend from data manager.
    **kwargs
        Driver-specific keyword arguments.

    Returns
    -------
    BaseDriver
        A driver instance.

    Raises
    ------
    RuntimeError
        If the storage type is MongoV1 or invalid.

    """
    if storage_type is None:
        try:
            storage_type = BackendType(data_manager.storage_type())
        except RuntimeError:
            storage_type = BackendType.JSON

    try:
        driver_cls: Type[BaseDriver] = get_driver_class(storage_type)
    except ValueError:
        if storage_type == BackendType.MONGOV1:
            raise RuntimeError(
                "Please convert to JSON first to continue using the bot."
                " This is a required conversion prior to using the new Mongo driver."
                " This message will be updated with a link to the update docs once those"
                " docs have been created."
            ) from None
        else:
            raise RuntimeError(f"Invalid driver type: '{storage_type}'") from None
    return driver_cls(cog_name, identifier, **kwargs)
