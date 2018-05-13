from aiohttp import web
import jsonrpcserver.aio

import inspect
import logging

log = logging.getLogger('red.rpc')


class Methods(jsonrpcserver.aio.AsyncMethods):
    # noinspection PyMethodOverriding
    def add(self, method, name=None):
        if not inspect.iscoroutinefunction(method):
            raise TypeError("Method must be a coroutine.")

        if name is None:
            name = method.__qualname__

        super(Methods, self).add(method, name=name)

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
        methods.add(self.all_methods, name='all_methods')

    async def all_methods(self):
        return list(methods.all_methods())


class RPC(BaseRPCMethodMixin):
    def __init__(self, bot):
        self.app = web.Application(loop=bot.loop)
        self.app.router.add_post('/rpc', self.handle)

        self.app_handler = self.app.make_handler()

        self.server = None

        super().__init__()

    async def initialize(self):
        self.server = await self.app.loop.create_server(self.app_handler, '127.0.0.1', 6133)
        log.debug('Created RPC server listener.')

    def close(self):
        self.server.close()

    async def handle(self, request):
        request = await request.text()
        response = await methods.dispatch(request)
        if response.is_notification:
            return web.Response()
        else:
            return web.json_response(response, status=response.http_status)
