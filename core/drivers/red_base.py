from typing import Tuple


class BaseDriver:
    def get_driver(self):
        raise NotImplementedError

    def get(self, identifiers: Tuple[str]):
        raise NotImplementedError

    async def set(self, identifiers: Tuple[str], value):
        raise NotImplementedError
