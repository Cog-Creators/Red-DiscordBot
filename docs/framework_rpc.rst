.. rpc docs

===
RPC
===

V3 comes default with an internal RPC server that may be used to remotely control the bot in various ways.
Cogs must register functions to be exposed to RPC clients.
Each of those functions must only take JSON serializable parameters and must return JSON serializable objects.

To enable the internal RPC server you must start the bot with the ``--rpc`` flag.

*******************************
Interacting with the RPC Server
*******************************

The RPC server opens a websocket bound to port ``6133`` on ``127.0.0.1``.
This may be configured by the use of the ``--rpc-port `` flag.
To access the server you must find a library that implements websocket based JSONRPC in the language of your choice.
Red uses ``aiohttp-json-rpc`` for the RPC server, and so code examples from now on will be using that library.

There are a few built-in RPC methods to note:

* ``GET_METHODS`` - Returns a list of available RPC methods.
* ``GET_METHOD_INFO`` - Will return the docstring for an available RPC method. Useful for finding information about the method's parameters and return values.
* ``GET_TOPIC`` - Returns a list of available RPC message topics.
* ``GET_SUBSCRIPTIONS`` - Returns a list of RPC subscriptions.
* ``SUBSCRIBE`` - Subscribes to an available RPC message topic.
* ``UNSUBSCRIBE`` - Unsubscribes from an RPC message topic.

All RPC methods accept a list of parameters.
The built-in methods above expect their parameters to be in list format.

All cog-based methods expect their parameter list to take one argument, a JSON object, in the following format::

    params = [
        {
            "args": [],  # A list of positional arguments
            "kwargs": {},  # A dictionary of keyword arguments
        }
    ]

    # As an example, here's a call to "get_method_info"
    rpc_call("GET_METHOD_INFO", ["get_methods",])

    # And here's a call to "core__load"
    rpc_call("CORE__LOAD", {"args": [["general", "economy", "downloader"],], "kwargs": {}})

As seen above with the core load function, cog RPC handlers will follow the template of cog name, two underscores,
then the name of the RPC handler, like this: :code:`COGNAME__RPC_METHOD_NAME`.

********
Tutorial
********

This tutorial will teach you how to use basic RPC in a cog.  In this example cog, a command will send a message over
RPC, supplying a channel ID (destination) and a message to send to that channel.  When finished, we will send back a
JSON object detailing whether or not it succeeded, and a message attribute explaining what happened if it failed.  The
client can also be a different python process if you wish, but to keep it simple, a command will just be used in this
tutorial.

First, let's create the handler that will take care of actually sending the message.  In your class, create a function
like the one below:

.. code-block:: Python

    async def _rpc_method(self, channel_id: int, message: str) -> dict:
      channel = self.bot.get_channel(channel_id)
      if channel is None:
          return {"success": False, "message": "Channel not found"}
      try:
          await channel.send(message)
      except Exception as e:
          return {"success": False, "message": str(e)}
      return {"success": True, "message": None}

Then, in your class's :code:`__init__` function, include the following:

.. code-block:: Python

    self.bot.register_rpc_handler(self._rpc_method)

That's it for the RPC handler.  Next, let's write the client.  At the top of your cog file, include the following import
statement:

.. code-block:: Python

    from aiohttp_json_rpc import JsonRpcClient

Then, in your class's :code:`__init__` function, add this line:

.. code-block:: Python

    self.client = JsonRpcClient()

After that, create two new function in your class to handle the connecting and disconnecting of the RPC client:

.. code-block:: Python

    def cog_unload(self):
      self.bot.loop.create_task(self.client.disconnect())

    async def task(self):
      await self.client.connect("127.0.0.1", 6133)

To make sure that's called, let's change the :code:`__init__.py` file in the cog folder to the following:

.. important::

  Make sure to change ``RPCCog`` below to the name of your class if it is different.

.. code-block:: Python

    from .rpccog import RPCCog

    async def setup(bot):
        cog = RPCCog(bot)
        await cog.task()
        bot.add_cog(cog)

Finally, create a new command in your cog's class, like the following:

.. important::

  Again, ake sure to change RPCCOG to your class's name if it is different, and that you convert it to uppercase.

.. code-block:: Python

    @checks.is_owner() # Not necessary, but recommended.  If included, make sure to import redbot.core.checks
    @commands.command()
    async def sendrpcmessage(self, ctx, channel: discord.TextChannel, *, message):
      """Send a message to a channel over RPC"""
      result = await self.client.call("RPCCOG__RPC_METHOD", [channel.id, message])
      if result["success"]:
          await ctx.send("Message sent!")
      else:
          await ctx.send(f"Something went wrong:\n{result['message']}")

It should now be working!  Load up your cog with :code:`[p]load`, and run :code:`[p]sendrpcmessage` to see it work.  If
it isn't, check your code against the code below:

:code:`rpccog.py`

.. code-block:: Python

    from redbot.core import commands, checks
    from aiohttp_json_rpc import JsonRpcClient
    import discord

    class RPCCog(commands.Cog):
        """Send a message with RPC"""

        def __init__(self, bot):
            self.bot = bot

            # RPC
            self.bot.register_rpc_handler(self._rpc_method)
            self.client = JsonRpcClient()

        def cog_unload(self):
            self.bot.loop.create_task(self.client.disconnect())

        async def task(self):
            await self.client.connect("127.0.0.1", 6133)

        async def _rpc_method(self, channel_id: int, message: str):
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                return {"success": False, "message": "Channel not found"}
            try:
                await channel.send(message)
            except Exception as e:
                return {"success": False, "message": str(e)}
            return {"success": True, "message": None}

        @checks.is_owner()  # Not necessary, but recommended.  If included, make sure to import redbot.core.checks
        @commands.command()
        async def sendrpcmessage(self, ctx, channel: discord.TextChannel, *, message):
            """Send a message to a channel over RPC"""
            result = await self.client.call("RPCCOG__RPC_METHOD", [channel.id, message])
            if result["success"]:
                await ctx.send("Message sent!")
            else:
                await ctx.send(f"Something went wrong:\n{result['message']}")

:code:`__init__.py`

.. code-block:: Python

    from .rpccog import RPCCog


    async def setup(bot):
        cog = RPCCog(bot)
        await cog.task()
        bot.add_cog(cog)

***********************
Converted RPC functions
***********************

Below is a list of all commands that have RPC functions attached to them.  You can call them by doing :code:`COGNAME_` +
:code:`METHOD_NAME`.

.. automodule:: redbot.core.core_commands

Core
^^^^

.. autoclass:: CoreLogic
    :special-members: _load, _unload, _reload, _name, _prefixes, _invite_url

*************
API Reference
*************

Please see the :class:`redbot.core.bot.RedBase` class for details on the RPC handler register and unregister methods.
