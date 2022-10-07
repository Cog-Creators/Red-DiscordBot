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

Various development focused utilities. All commands in this cog are
restricted to the bot owners.

.. note::

    Unlike other built-in cogs, the Dev cog requires the ``--dev`` flag.

    .. warning::

        It is not suggested that you run Dev in production. Many
        of these cog's commands may cause down-the-line complications if
        not used appropriately.

        For example, cooldowns are often implemented by cog developers to prevent
        the rate-limiting of a resource, or to prevent other complications caused by
        excessive repetitive use of the command. By using ``[p]bypasscooldowns``,
        you could be directly damaging your bot or a significant resource.

.. _dev-commands:

--------
Commands
--------

.. _dev-command-bypasscooldowns:

^^^^^^^^^^^^^^^
bypasscooldowns
^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]debug [toggle]

**Description**

Give bot owners the ability to bypass cooldowns. Note that this bypass
does not persist through restarts/shutdowns.

**Arguments**

* ``[toggle]``: |bool-input| Otherwise, defaults to the inverse of the current setting.

.. _dev-command-debug:

^^^^^
debug
^^^^^

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

**Environment Variables**

* ``ctx``: command invocation context
* ``bot``: the bot object
* ``channel``: the current channel object
* ``author``: the current author's member object
* ``message``: the command's message object
* ``discord``: the discord.py library
* ``commands``: the redbot.core.commands module
* ``_``: The result from the last dev command.

**Arguments**

* ``<code>``: The code to debug.

.. _dev-command-eval:

^^^^
eval
^^^^

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

**Environment Variables**

* ``ctx``: command invocation context
* ``bot``: the bot object
* ``channel``: the current channel object
* ``author``: the current author's member object
* ``message``: the command's message object
* ``discord``: the discord.py library
* ``commands``: the redbot.core.commands module
* ``_``: The result from the last dev command.

**Arguments**

* ``<body>``: The code to evaluate.

.. _dev-command-mock:

^^^^
mock
^^^^

**Syntax**

.. code-block:: none

    [p]mock <member> <command>

**Description**

Mock another member invoking a command. The prefix must not be entered.

**Arguments**

* ``<member>``: The member to mock. |member-input-quotes|
* ``<command>``: The command to invoke.

.. _dev-command-mockmsg:

^^^^^^^
mockmsg
^^^^^^^

**Syntax**

.. code-block:: none

    [p]mockmsg <member> <content>

**Description**

Dispatch a message event as if it were sent by a different member.

Only reads the raw content of the message. Attachments, embeds etc. are
ignored.

**Arguments**

* ``<member>``: The member to mock. |member-input-quotes|
* ``<content>``: The content used for the message.

.. note:: 

        If ``content`` isn't passed, the message needs to contain embeds, attachments,
        or anything else that makes the message non-empty.

.. _dev-command-repl:

^^^^
repl
^^^^

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

**Description**

Pauses/resumes the REPL running in the current channel.

**Arguments**

* ``[toggle]``: |bool-input| Otherwise, defaults to the inverse of the current setting.
