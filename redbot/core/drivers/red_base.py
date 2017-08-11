from typing import Tuple


class BaseDriver:
    def __init__(self, cog_name):
        self.cog_name = cog_name

    def get_driver(self):
        raise NotImplementedError

    async def get(self, identifiers: Tuple[str]):
        """
        Finds the value indicate by the given identifiers.
        :param identifiers:
            A list of identifiers that correspond to nested dict accesses.
        :return:
            Stored value.
        """
        raise NotImplementedError

    async def set(self, identifiers: Tuple[str], value):
        """
        Sets the value of the key indicated by the given identifiers
        :param identifiers:
            A list of identifiers that correspond to nested dict accesses.
        :param value:
            Any JSON serializable python object.
        """
        raise NotImplementedError
