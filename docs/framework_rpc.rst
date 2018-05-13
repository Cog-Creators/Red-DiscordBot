.. rpc docs

===
RPC
===

.. currentmodule:: redbot.core.rpc

V3 comes default with an internal RPC server that may be used to remotely control the bot in various ways.
Cogs must register functions to be exposed to RPC clients.
Each of those functions must only take JSON serializable parameters and must return JSON serializable objects.

To begin, register all methods using individual calls to the :func:`Methods.add` method.

********
Examples
********

Coming soon to a docs page near you!

*************
API Reference
*************

.. py:attribute:: redbot.core.rpc.methods

    An instance of the :class:`Methods` class.
    All attempts to register new RPC methods **MUST** use this object.
    You should never create a new instance of the :class:`Methods` class!

RPC
^^^
.. autoclass:: redbot.core.rpc.RPC
    :members:

Methods
^^^^^^^
.. autoclass:: redbot.core.rpc.Methods
    :members:
