.. zmq docs

===
ZMQ
===

Red comes with an internal IPC communication server that allows for outside programs to interact with Red and call functions remotely.
This allows for cog creators to develop applications such as external dashboards or interfaces and be able to interact easily with Red.
Red uses the fast networking library ZeroMQ for the backend, and as a result requires applications interacting with the server to use ZMQ.
ZMQ provides support in multiple languages, allowing for external programs to be written in any language.  By default, the internal ZMQ server
binds to port 6133, but this can be changed using a flag at launch.

.. important::

    For security reasons, the internal ZMQ server binds to localhost, and this cannot be changed.  This ensures that outside applications cannot
    interact with your bot and take control.

In this tutorial, we will guide you through setting up your own ZMQ methods and and client to interact with Red, but for simplicity reasons,
we will incorporate the client into the cog.  However, be aware that the client can be implemented in other languages as well.

************
ZMQ Tutorial
************

Start off by starting your bot with the ``--zmq``, which enables the internal ZMQ server.  For example, ``redbot mybot --zmq``.  If you wish to change the port as well (by default, binds to port 6133), you can change this by use of the ``--zmq-port`` flag.

Next, let's start off with a basic template, importing the necessary libraries to start writing ZMQ methods.  We'll start with this code:

``zmqexample.py``

.. code-block:: python

    from redbot.core import checks, commands
    from redbot.core.zmq import zmq_handler, ZMQRequest
    from redbot.core.commands.converter import ZMQUserConverter
    import discord

    import zmq, zmq.asyncio

    class ZMQExample(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

We'll use ``zmq_handler`` for registering our ZMQ method handler, and then ``ZMQRequest`` and ``ZMQUserConverter`` as type hints for our arguments, but we'll get to that later.  Finally, we import ``zmq`` and ``zmq.asyncio`` for when we will send a request.  For this example, you can use a default cog ``__init__.py`` with nothing special.

Alright, now let's get to writing our ZMQ handler.  An important thing to note is that **all arguments must be keyword-only and type hinted, and all ZMQ handlers must have a request argument.**  This means that when writing the function declaration, you must include an asterisk after the ``self`` argument, and you must specify the type of every variable.  Here's the signature for the ZMQ method we are writing:

.. code-block:: python

    async def say_hello(self, *, user: ZMQUserConverter, request: ZMQRequest)

Notice that after the ``self`` argument we put an asterisk, meaning that any non-keyword arguments are bundled into that.  For more structure, this is enforced, and all parameters must be after the asterisk, and only ``self`` is allowed before.  Each parameter is also type-hinted, which Red's ZMQ manager will attempt to automatically convert the argument to.

Now let's get into writing the function.  What we want is when the ZMQ method is called with the passed user, it will return a message saying "Hi {user.name}."  Since user will already be converted into a discord.User type by the ZMQUserConverter, we won't have to worry about doing that manually.

.. code-block:: python

    @zmq_handler()
    async def say_hello(self, *, user: ZMQUserConverter, request: ZMQRequest):
        await request.send_message(f"Hi {user.display_name}!")

Let's walk through this line by line.

Line 1: This marks the method as a ZMQ method, which will be recognized on cog load.  If you wish to have a different name than the function, you can pass that to the decorator as such: ``@zmq_handler("sayhello")``.

Line 2: We went over this in the previous code, it tells ZMQ what paramaters to expect.

Line 3: This uses the ZMQRequest object, which is unique to the request that was made and called this method, to send a message back to the caller with the message that is passed, which in this case is ``Hi {user.display_name}``.

You should now be able to load the cog without errors.  If you have the Dev cog enabled, you can check by running ``[p]debug bot._zmq.zmq_mapping["ZMQExample"]``.  If you receive an error doing either, make sure you typed your code exactly as above.

Next, we will write a command that will call this handler.  As said before, ZMQ has bindings in a large amount of popular languages, so this will work with a caller in any language.  We are only using Python here for simplicity.  Here's the code for the command, and then we'll walk through it line by line.

.. code-block:: python

    @checks.is_owner()
    @commands.command()
    async def zmqsayhello(self, ctx, user: discord.User):
        worker = zmq.asyncio.Context.instance().socket(zmq.REQ)
        worker.connect(f"tcp://127.0.0.1:{self.bot.zmq_port}")
        await worker.send_json({
            "requester": "ZMQExample",
            "cog": "ZMQExample",
            "method": "say_hello",
            "id": 123,
            "kwargs": {
                "user": user.id
            }
        })
        result = await worker.recv_json()
        await ctx.send(result["message"])

Lines 1 - 3: First few lines are standard command declarations, we limit this to owner only for testing purposes (but you can change this if you want), and we take a user argument.

Line 4: Here, we initialize a new asynchronous ZMQ context, and create a socket from it using the REQ protocol.  Red's ZMQ server manager uses ROUTER protocol, which allows for multiple sockets to connect and request.

Line 5: Here we connect to the ZMQ server manager that is running on the port set over 127.0.0.1 using TCP.

Line 6 - 14: This makes a request to Red's ZMQ server manager, telling it that ``ZMQExample`` is making a request (``requester``), and attempting to call the ``say_hello`` method (``method``) under the ``ZMQExample`` cog (``cog``).  Note that ``requester`` should be changed to the name of whatever program is interacting with the method.  We also give ZMQ and ``id`` argument, which we can use for tracking the responses and to ensure that race conditions to not affect it, but since we are only making one request, we do not need to check when getting the result.  Lastly, we pass ``kwargs`` which tells ZMQ what arguments we are supplying values for, and in this case, we are giving the passed user's ID to the ``user`` argument.

Line 15: We wait until we get a response back from the ZMQ server, and store that in result.

Line 16: We send the returned message into channel.

This should be ready for use now.  Reload the cog, and try running ``[p]zmqsayhello @User#1234`` and it should reply back with "Hi User!."

**************
Advanced Usage
**************

---------------------
Custom ZMQ converters
---------------------

Red's ZMQ argument parser allows for custom converters to be made.  When using this converter, Red will call ``ConverterClass.zmq_convert``, passing two arguments: ``argument`` which contains the data that was passed in the request, matched with the respective parameter, and ``request``, which will pass the ZMQRequest object.  The ``zmq_convert`` function may be asynchronous or synchronous.  If any invalid data is received, raise ``redbot.core.errors.InvalidRequest`` and the ZMQ manager will handle it for you.  Here's an example that is in ``redbot.core.commands.converter`` and is used for translating an ID to a User object:

.. code-block:: python

    class ZMQGuildConverter:
        """Converts an ID to a `discord.Guild` object.
        This is here primarily as a convenient converter for ZMQ methods,
        but can be used for other purposes, however discouraged."""

        @staticmethod
        def zmq_convert(argument: int, request: "ZMQRequest"):
            if not type(argument) is int:
                raise TypeError("Guild ID must be an integer")

            guild = request.manager.bot.get_guild(argument)
            if not guild:
                raise InvalidRequest(request.message, f"Failed to find Guild with ID {argument}")
            return guild

-------------------
Request Status Code
-------------------

Red's ZMQ manager also allows for status codes to be sent with ``request.send_message``, via the ``status`` parameter.  On the client side, this will be available in ``request["status"]``, at the same depth as message.  Note that any error raised while converting arguments will return status code ``400`` and errors while running the command will return status code ``500``.