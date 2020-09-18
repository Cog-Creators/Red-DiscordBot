import asyncio
import sys
from typing import Optional, List, Dict

import logging
from schema import Schema, SchemaError, Optional as SOptional
import zmq
import zmq.asyncio

from .errors import ZMQError, InvalidRequest

log = logging.getLogger("red.zmq")

__all__ = ["ZMQ", "ZMQMixin"]

REQUEST_SCHEMA = Schema({
    "requester": str,
    "cog": str,
    "method": str,
    SOptional("args", default=[]): list,
    SOptional("kwargs", default={}): dict
})


class ZMQRequest:
    """
    ZMQ request
    """

    def __init__(self, client: zmq.Socket, address: str, message: List[str]):
        self.client = client
        self.address = address
        self.message = b"".join(message)

    def parse_message(self):
        try:
            self.message = zmq.utils.jsonapi.loads(self.message)
        except Exception as e:
            raise InvalidRequest(self.message, str(e))
        try:
            REQUEST_SCHEMA.validate(self.message)
        except SchemaError as e:
            raise InvalidRequest(self.message, str(e))

    async def send_message(self, content: Dict, status: int = 200):
        sending = {
            "status": status,
            "message": content
        }
        prepared = zmq.utils.jsonapi.dumps(sending)
        await self.client.send_multipart([self.address, b'', prepared])


class ZMQ:
    """
    ZMQ server manager.
    """

    def __init__(self, bot):
        self.context = zmq.asyncio.Context.instance()
        self.client = self.context.socket(zmq.ROUTER)
        self._started = False
        self.bot = bot

        self.queue = set()
        self.main_task = None

    async def handle_message(self, request):
        log.info("Received a message")
        try:
            request.parse_message()
        except InvalidRequest as e:
            await request.send_message(str(e), status=400)
            return
        await request.send_message(f"Hi, requester {request.message['requester']}")


    async def zmq_processor(self):
        while True:
            address, *frames = await self.client.recv_multipart()
            # This shouldn't be processed if there is no empty frame
            if frames[0] != b'':
                continue
            else:
                del frames[0] # Remove empty frame
            r = ZMQRequest(self.client, address, frames)
            self.queue.add(self.bot.loop.create_task(self.handle_message(r)))

    async def initialize(self, port: int):
        """
        Finalizes the initialization of the ZMQ server and allows it to begin
        accepting queries.
        """
        try:
            self.client.bind(f"tcp://127.0.0.1:{port}")
        except Exception as exc:
            log.exception("ZMQ setup failure", exc_info=exc)
            sys.exit(1)
        else:
            self._started = True
            log.debug("Created ZMQ server listener on port %s", port)
            await asyncio.sleep(.3) # Give time for the server to initialize
            self.main_task = self.bot.loop.create_task(self.zmq_processor())

    async def close(self):
        """
        Closes the ZMQ server.
        """
        if self._started:
            self.main_task.cancel()
            for request in self.queue:
                request.cancel()
            self.client.close()

    def add_method(self, method, prefix: str = None):
        if prefix is None:
            prefix = method.__self__.__class__.__name__.lower()

        if not asyncio.iscoroutinefunction(method):
            raise TypeError("RPC methods must be coroutines.")

        self._rpc.add_methods((prefix, method))

    def add_multi_method(self, *methods, prefix: str = None):
        if not all(asyncio.iscoroutinefunction(m) for m in methods):
            raise TypeError("RPC methods must be coroutines.")

        for method in methods:
            self.add_method(method, prefix=prefix)

    def remove_method(self, method):
        self._rpc.remove_method(method)

    def remove_methods(self, prefix: str):
        self._rpc.remove_methods(prefix)


class ZMQMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._zmq = ZMQ(self)

        self.zmq_handlers = {}  # Uppercase cog name to method

    def register_rpc_handler(self, method):
        """
        Registers a method to act as an ZMQ handler if the internal ZMQ server is active.

        When calling this method through the ZMQ server, use the naming scheme
        "cogname__methodname".

        .. important::

            All parameters to ZMQ handler methods must be JSON serializable objects.
            The return value of handler methods must also be JSON serializable.

        .. important::
            ZMQ support is included in Red on a provisional basis. Backwards incompatible changes (up to and including removal of the ZMQ) may occur if deemed necessary.

        Parameters
        ----------
        method : coroutine
            The method to register with the internal ZMQ server.
        """
        return
        self._zmq.add_method(method)

        cog_name = method.__self__.__class__.__name__.upper()

        if cog_name not in self.rpc_handlers:
            self.zmq_handlers[cog_name] = []

        self.zmq_handlers[cog_name].append(method)

    def unregister_rpc_handler(self, method):
        """
        Unregisters an RPC method handler.

        This will be called automatically for you on cog unload and will pass silently if the
        method is not previously registered.

        .. important::
            RPC support is included in Red on a provisional basis. Backwards incompatible changes (up to and including removal of the RPC) may occur if deemed necessary.

        Parameters
        ----------
        method : coroutine
            The method to unregister from the internal RPC server.
        """
        return
        self._zmq.remove_method(method)

        name = get_name(method)
        cog_name = name.split("__")[0]

        if cog_name in self.zmq_handlers:
            try:
                self.zmq_handlers[cog_name].remove(method)
            except ValueError:
                pass
