import asyncio

from aiohttp import web
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.rpc import unpack_request_args

import logging

log = logging.getLogger("red.rpc")

__all__ = ["RPC", "get_name"]


def get_name(func, prefix=None):
    class_name = prefix or func.__self__.__class__.__name__.lower()
    func_name = func.__name__.strip("_")
    return f"{class_name}__{func_name}"


class RedRpc(JsonRpc):
    def _add_method(self, method, prefix=""):
        if not asyncio.iscoroutinefunction(method):
            return

        name = get_name(method, prefix)

        self.methods[name] = method

    def remove_method(self, method):
        meth_name = get_name(method)
        new_methods = {}
        for name, meth in self.methods.items():
            if name != meth_name:
                new_methods[name] = meth
        self.methods = new_methods

    def remove_methods(self, prefix: str):
        new_methods = {}
        for name, meth in self.methods.items():
            splitted = name.split("__")
            if len(splitted) < 2 or splitted[0] != prefix:
                new_methods[name] = meth
        self.methods = new_methods


class RPC:
    """
    RPC server manager.
    """

    def __init__(self, bot):
        self.app = web.Application(loop=bot.loop)
        self._rpc = RedRpc()
        self.app.router.add_route("*", "/", self._rpc)

        self.app_handler = self.app.make_handler()

        self.server = None

    async def initialize(self):
        """
        Finalizes the initialization of the RPC server and allows it to begin
        accepting queries.
        """
        self.server = await self.app.loop.create_server(self.app_handler, "127.0.0.1", 6133)
        log.debug("Created RPC server listener.")

    def close(self):
        """
        Closes the RPC server.
        """
        self.server.close()

    def add_method(self, method, prefix: str = None):
        if prefix is None:
            prefix = method.__self__.__class__.__name__.lower()

        if not asyncio.iscoroutinefunction(method):
            raise TypeError("RPC methods must be coroutines.")

        self._rpc.add_methods((prefix, unpack_request_args(method)))

    def add_multi_method(self, *methods, prefix: str = None):
        if not all(asyncio.iscoroutinefunction(m) for m in methods):
            raise TypeError("RPC methods must be coroutines.")

        for method in methods:
            self.add_method(method, prefix=prefix)

    def remove_method(self, method):
        self._rpc.remove_method(method)

    def remove_methods(self, prefix: str):
        self._rpc.remove_methods(prefix)
