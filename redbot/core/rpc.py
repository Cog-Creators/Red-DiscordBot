from typing import NewType, TYPE_CHECKING

import asyncio
from aiohttp.web import Application
from aiohttp_json_rpc import JsonRpc

import logging

if TYPE_CHECKING:
    from .bot import Red

log = logging.getLogger('red.rpc')
JsonSerializable = NewType('JsonSerializable', dict)

rpc = None  # type: JsonRpc

server = None  # type: asyncio.AbstractServer


async def initialize(bot: "Red"):
    global rpc
    global server
    rpc = JsonRpc(logger=log)

    app = Application(loop=bot.loop)
    app.router.add_route('*', '/rpc', rpc)

    handler = app.make_handler()

    server = await bot.loop.create_server(handler, '127.0.0.1', 8080)

    log.debug('Created RPC server listener.')

    bot.register_rpc_methods(rpc)

    log.debug('Registered bot RPC methods.')

    bot.add_listener(on_shutdown)


def _ensure_initialized(func):
    def partial(*args, **kwargs):
        if rpc is None:
            raise IOError("RPC server not initalized.")
        return func(*args, **kwargs)
    return partial


@_ensure_initialized
def add_topic(topic_name: str):
    """
    Adds a topic for clients to listen to.

    :param topic_name:
    """
    rpc.add_topics(topic_name)


@_ensure_initialized
def notify(topic_name: str, data: JsonSerializable):
    """
    Publishes a notification for the given topic name to all listening clients.

    data MUST be json serializable.

    note::

        This method will fail silently.

    :param topic_name:
    :param data:
    """
    rpc.notify(topic_name, data)


@_ensure_initialized
def add_method(prefix, method):
    """
    Makes a method available to RPC clients. The name given to clients will be as
    follows::

        "{}__{}".format(prefix, method.__name__)

    note::

        This method will fail silently.

    :param prefix:
    :param method:
        MUST BE A COROUTINE OR OBJECT.
    :return:
    """
    rpc.add_methods(
        ('', method),
        prefix=prefix
    )


async def on_shutdown():
    server.close()
