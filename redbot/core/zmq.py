import asyncio
import sys
from typing import Optional, List, Dict, Callable
import functools
import inspect

import logging
from schema import Schema, SchemaError, Optional as SOptional
import zmq
import zmq.asyncio

from .errors import ZMQError, InvalidRequest, HandlerError

log = logging.getLogger("red.zmq")

__all__ = ["ZMQ", "ZMQMixin", "zmq_handler"]

REQUEST_SCHEMA = Schema({
    "requester": str,
    "cog": str,
    "method": str,
    SOptional("kwargs", default={}): dict
})

def zmq_handler(name: Optional[str] = None):
    def wrapped(func):
        nonlocal name
        if not name:
            name = func.__name__
        setattr(func, "__red_zmq_method__", name)
        return func
    return wrapped


class ZMQRequest:
    """
    ZMQ request
    """

    def __init__(self, manager, address: str, message: List[str]):
        self.manager = manager
        self.address = address
        self.message = b"".join(message)
        self._callback = None
        self.callback_args = None
        self.kwargs = {}

    def parse_message(self):
        try:
            self.message = zmq.utils.jsonapi.loads(self.message)
        except Exception as e:
            raise InvalidRequest(self.message, str(e))
        try:
            self.message = REQUEST_SCHEMA.validate(self.message)
        except SchemaError as e:
            raise InvalidRequest(self.message, str(e))
        
        try:
            self._callback = self.manager.zmq_mapping[self.message["cog"]][self.message["method"]]
        except KeyError as e:
            raise InvalidRequest(self.message, str(e))

        self.parse_args()

    def parse_args(self):
        if self._callback is None:
            raise TypeError("ZMQRequest.parse_message must be called before ZMQRequest.parse_args")
        if self.callback_args:
            raise TypeError("ZMQ Request arguments have already been processed")
        self.callback_args = inspect.signature(self._callback).parameters.copy()
        i = iter(self.callback_args.items())

        if "request" in self.message["kwargs"]:
            raise InvalidRequest(self.message, "ZMQ requests must not contain request keyword argument")

        for name, param in i:
            if name == "request":
                continue
            if name not in self.message["kwargs"]:
                if param.default is param.empty:
                    raise InvalidRequest(self.message, f"Missing required argument {name}")
                else:
                    self.kwargs[name] = param.default
                    continue
            try:
                converted = param.annotation(self.message["kwargs"]["name"])
            except Exception as e:
                raise InvalidRequest(self.message, f"Failed to convert {name} argument to {param.annotation}: {e}")
            self.kwargs[name] = converted

        self.kwargs["request"] = self

    async def __call__(self):
        if not self._callback:
            raise TypeError("ZMQ request has not yet been parsed.")
        if not self.callback_args:
            raise TypeError("ZMQ request arguments have not yet been parsed.")
        try:
            await self._callback(**self.kwargs)
        except Exception as e:
            raise HandlerError(e)

    async def send_message(self, content: Dict, status: int = 200):
        sending = {
            "status": status,
            "message": content
        }
        prepared = zmq.utils.jsonapi.dumps(sending)
        await self.manager.client.send_multipart([self.address, b'', prepared])


class ZMQ:
    """
    ZMQ server manager.
    """

    def __init__(self, bot):
        self.bot = bot

        self.context = zmq.asyncio.Context.instance()
        self.client = self.context.socket(zmq.ROUTER)
        self.zmq_mapping = {}

        self.queue = set()
        self.main_task = None
        self._started = False
        self.zmq_mapping = {}

    async def handle_message(self, request):
        try:
            log.info("Received a message")
            try:
                request.parse_message()
            except InvalidRequest as e:
                await request.send_message(str(e), status=400)
                return
            try:
                await request()
            except HandlerError as e:
                await request.send_message(str(e), status=500)
        except Exception as e:
            await request.send_message(str(e), status=500)


    async def zmq_processor(self):
        while True:
            address, *frames = await self.client.recv_multipart()
            # This shouldn't be processed if there is no empty frame
            if frames[0] != b'':
                continue
            else:
                del frames[0] # Remove empty frame
            r = ZMQRequest(self, address, frames)
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

    def add_method(self, cog: str, name: str, method: Callable):
        if not asyncio.iscoroutinefunction(method):
            raise TypeError("ZMQ methods must be coroutines.")

        if cog not in self.zmq_mapping: # This should not happen, but let's put it in just in case
            self.zmq_mapping[cog] = {}
        
        if name in self.zmq_mapping[cog]:
            raise TypeError(f"A ZMQ method with the name {name} already exists in this cog.")

        callback_args = inspect.signature(method).parameters.copy()
        i = iter(callback_args.items())

        found_request = False
        for pname, param in i:
            if not param.kind is param.KEYWORD_ONLY:
                raise TypeError(f"ZMQ handler {name} must only accept keyword arguments")
            if param.annotation is param.empty:
                raise TypeError(f"ZMQ handler {name}'s {pname} argument is not type-hinted")
            if pname == "request":
                found_request = True
        
        if not found_request:
            raise TypeError(f"ZMQ handler {name} is missing a request keyword argument")
        
        self.zmq_mapping[cog][name] = method

    def remove_method(self, cog: str, name: str):
        if cog not in self.zmq_mapping or name not in self.zmq_mapping[cog]:
            raise TypeError("Cog or method name not registered in ZMQ mapping.")
        
        del self.zmq_mapping[cog][name]

    def remove_cog(self, cog: str):
        if cog not in self.zmq_mapping:
            raise TypeError("Cog not registered in ZMQ mapping.")
    
        del self.zmq_mapping[cog]


class ZMQMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._zmq = ZMQ(self)

    def register_zmq_handler(self, method: Callable, name: Optional[str] = None):
        """
        Registers a method to act as an ZMQ handler if the internal ZMQ server is active.

        When calling this method through the ZMQ server, use the naming scheme
        use the schema defined in the documentation.

        .. important::

            Note that if the __cog_name__ attribute is used instead of commands.Cog inheritance,
            and is under a different name than the cog, you must use bot.unregister_rpc_handler
            yourself.

        .. important::

            All parameters to ZMQ handler methods must be JSON serializable objects.
            The return value of handler methods must also be JSON serializable.

        Parameters
        ----------
        method : coroutine
            The method to register with the internal ZMQ server.
        name : Optional[str]
            The name to register under.  Leave empty for it to be the method name
        """
        try:
            cog = method.__self__.__cog_name__
        except AttributeError:
            raise TypeError("Failed to determine cog name from ZMQ method.  Please use inside a class that inherits commands.Cog or set __cog_name__")
        
        if not name:
            name = method.__name__

        self._zmq.add_method(cog, name, method)

    def unregister_zmq_handler(self, method: Callable = None):
        """
        Unregisters a ZMQ method handler.

        This will be called automatically for you on cog unload and will pass silently if the
        method is not previously registered.

        .. important::

            Note that if you register a ZMQ handler under a name different than the cog you
            are using it with, you must call this function manually.

        Parameters
        ----------
        method : coroutine
            The method to unregister from the internal ZMQ server.
        """
        try:
            cog = method.__self__.__cog_name__
        except AttributeError:
            raise TypeError("Failed to determine cog name from ZMQ method")
        
        name = method.__name__

        self._zmq.remove_method(cog, name)