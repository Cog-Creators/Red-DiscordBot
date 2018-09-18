from typing import Type as _Type

from .red_base import *
from .red_json import *
from .red_mongo import *


__all__ = ["BaseDriver", "JSON", "Mongo", "get_driver", "get_driver_cls"]

_DRIVER_CLASSES = {"json": JSON, "mongo": Mongo}


def get_driver(storage_type: str, *args, **kwargs) -> BaseDriver:
    """Get a new driver instance.

    .. note::

        See the respective classes for information on what ``args``
        and ``kwargs`` should be.

    Parameters
    ----------
    storage_type : str
        The type of storage backend being used.
    *args
        Positional arguments passed to driver constructor.
    **kwargs
        Keyword arguments passed to driver constructor.

    Returns
    -------
    BaseDriver
        A new driver instance.

    """
    return get_driver_cls(storage_type)(*args, **kwargs)


def get_driver_cls(storage_type: str) -> _Type[BaseDriver]:
    """Get the class for the driver used by the given storage type.

    Parameters
    ----------
    storage_type : str
        The type of storage backend being used.

    Returns
    -------
    Type[BaseDriver]
        A class which subclasses `BaseDriver`.

    """
    try:
        return _DRIVER_CLASSES[storage_type.lower()]
    except KeyError:
        raise RuntimeError(f"Invalid driver type: '{storage_type}'")
