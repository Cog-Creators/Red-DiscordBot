.. _dev:

===
Dev
===

This is the cog guide for the dev cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load dev

.. _dev-usage:

-----
Usage
-----

Various development focused utilities.


.. _dev-commands:

--------
Commands
--------

.. _dev-command-debug:

^^^^^
debug
^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]debug <code>

**Description**

Evaluate a statement of python code.

The bot will always respond with the return value of the code.
If the return value of the code is a coroutine, it will be awaited,
and the result of that will be the bot's response.

Note: Only one statement may be evaluated. Using certain restricted
keywords, e.g. yield, will result in a syntax error. For multiple
lines or asynchronous code, see [p]repl or [p]eval.

Environment Variables:
    ctx      - command invocation context
    bot      - bot object
    channel  - the current channel object
    author   - command author's member object
    message  - the command's message object
    discord  - discord.py library
    commands - redbot.core.commands
    _        - The result of the last dev command.

.. _dev-command-eval:

^^^^
eval
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]eval <body>

**Description**

Execute asynchronous code.

This command wraps code into the body of an async function and then
calls and awaits it. The bot will respond with anything printed to
stdout, as well as the return value of the function.

The code can be within a codeblock, inline code or neither, as long
as they are not mixed and they are formatted correctly.

Environment Variables:
    ctx      - command invocation context
    bot      - bot object
    channel  - the current channel object
    author   - command author's member object
    message  - the command's message object
    discord  - discord.py library
    commands - redbot.core.commands
    _        - The result of the last dev command.

.. _dev-command-mock:

^^^^
mock
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]mock <user> <command>

**Description**

Mock another user invoking a command.

The prefix must not be entered.

.. _dev-command-mockmsg:

^^^^^^^
mockmsg
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]mockmsg <user> <content>

**Description**

Dispatch a message event as if it were sent by a different user.

Only reads the raw content of the message. Attachments, embeds etc. are
ignored.

.. _dev-command-repl:

^^^^
repl
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]repl 

**Description**

Open an interactive REPL.

The REPL will only recognise code as messages which start with a
backtick. This includes codeblocks, and as such multiple lines can be
evaluated.

.. _dev-command-repl-pause:

""""""""""
repl pause
""""""""""

**Syntax**

.. code-block:: none

    [p]repl pause [toggle]

.. tip:: Alias: ``repl resume``

**Description**

Pauses/resumes the REPL running in the current channel
