import weakref

from aiohttp import web
import jsonrpcserver.aio

import inspect
import logging

__all__ = ["methods", "RPC", "Methods"]

log = logging.getLogger("red.rpc")


class Methods(jsonrpcserver.aio.AsyncMethods):
    """
    Container class for all registered RPC methods, please use the existing `methods`
    attribute rather than creating a new instance of this class.

    .. warning::

        **NEVER** create a new instance of this class!
    """

    def __init__(self):
        super().__init__()

        self._items = weakref.WeakValueDictionary()

    def add(self, method, name: str = None):
        """
        Registers a method to the internal RPC server making it available for
        RPC users to call.

        .. important::

            Any method added here must take ONLY JSON serializable parameters and
            MUST return a JSON serializable object.

        Parameters
        ----------
        method : function
            A reference to the function to register.

        name : str
            Name of the function as seen by the RPC clients.
        """
        if not inspect.iscoroutinefunction(method):
            raise TypeError("Method must be a coroutine.")

        if name is None:
            name = method.__qualname__

        self._items[str(name)] = method

    def remove(self, *, name: str = None, method=None):
        """
        Unregisters an RPC method. Either a name or reference to the method must
        be provided and name will take priority.

        Parameters
        ----------
        name : str
        method : function
        """
        if name and name in self._items:
            del self._items[name]

        elif method and method in self._items.values():
            to_remove = []
            for name, val in self._items.items():
                if method == val:
                    to_remove.append(name)

            for name in to_remove:
                del self._items[name]

    def all_methods(self):
        """
        Lists all available method names.

        Returns
        -------
        list of str
        """
        return self._items.keys()


methods = Methods()


class BaseRPCMethodMixin:

    def __init__(self):
        methods.add(self.all_methods, name="all_methods")

    async def all_methods(self):
        return list(methods.all_methods())


class RPC(BaseRPCMethodMixin):
    """
    RPC server manager.
    """

    def __init__(self, bot):
        self.app = web.Application(loop=bot.loop)
        self.app.router.add_post("/rpc", self.handle)

        self.app_handler = self.app.make_handler()

        self.server = None

        super().__init__()

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

    async def handle(self, request):
        request = await request.text()
        response = await methods.dispatch(request)
        if response.is_notification:
            return web.Response()
        else:
            return web.json_response(response, status=response.http_status)
