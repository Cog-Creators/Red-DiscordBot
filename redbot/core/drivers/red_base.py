from typing import Tuple

__all__ = ["BaseDriver"]

class BaseDriver:
    def get_driver(self):
        raise NotImplementedError

    async def get(self, identifiers: Tuple[str]):
        raise NotImplementedError

    async def set(self, identifiers: Tuple[str], value):
        raise NotImplementedError
