from typing import Tuple


class BaseDriver:
    def __init__(self, cog_name):
        self.cog_name = cog_name

    def get_driver(self):
        raise NotImplementedError

    async def get(self, identifiers: Tuple[str]):
        raise NotImplementedError

    async def set(self, identifiers: Tuple[str], value):
        raise NotImplementedError
