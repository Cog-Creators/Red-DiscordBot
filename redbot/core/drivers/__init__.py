__all__ = ["get_driver"]


def get_driver(type, *args, **kwargs):
    """
    Selectively import/load driver classes based on the selected type. This
    is required so that dependencies can differ between installs (e.g. so that
    you don't need to install a mongo dependency if you will just be running a
    json data backend).

    .. note::

        See the respective classes for information on what ``args`` and ``kwargs``
        should be.

    :param str type:
        One of: json, mongo
    :param args:
        Dependent on driver type.
    :param kwargs:
        Dependent on driver type.
    :return:
        Subclass of :py:class:`.red_base.BaseDriver`.
    """
    if type == "JSON":
        from .red_json import JSON

        return JSON(*args, **kwargs)
    elif type == "MongoDB":
        from .red_mongo import Mongo

        return Mongo(*args, **kwargs)
    raise RuntimeError("Invalid driver type: '{}'".format(type))
