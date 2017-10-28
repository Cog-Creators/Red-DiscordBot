from typing import NewType, TYPE_CHECKING

import asyncio

from aiohttp.web import Application
from aiohttp_json_rpc import JsonRpc

import logging

if TYPE_CHECKING:
    from .bot import Red

log = logging.getLogger('red.rpc')
JsonSerializable = NewType('JsonSerializable', dict)

_rpc = JsonRpc(logger=log)

_rpc_server = None  # type: asyncio.AbstractServer


async def initialize(bot: "Red"):
    global _rpc_server

    app = Application(loop=bot.loop)
    app.router.add_route('*', '/rpc', _rpc)

    handler = app.make_handler()

    _rpc_server = await bot.loop.create_server(handler, '127.0.0.1', 8080)

    log.debug('Created RPC _rpc_server listener.')


def add_topic(topic_name: str):
    """
    Adds a topic for clients to listen to.

    :param topic_name:
    """
    _rpc.add_topics(topic_name)


def notify(topic_name: str, data: JsonSerializable):
    """
    Publishes a notification for the given topic name to all listening clients.

    data MUST be json serializable.

    note::

        This method will fail silently.

    :param topic_name:
    :param data:
    """
    _rpc.notify(topic_name, data)


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
    _rpc.add_methods(
        ('', method),
        prefix=prefix
    )


def clean_up():
    _rpc_server.close()
