.. _customcommands:

==============
CustomCommands
==============

This is the cog guide for the customcommands cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load customcom

.. _customcommands-usage:

-----
Usage
-----

Creates commands used to display text.


.. _customcommands-commands:

--------
Commands
--------

.. _customcommands-command-customcom:

^^^^^^^^^
customcom
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]customcom 

**Description**

Custom commands management.

.. _customcommands-command-customcom-show:

""""
show
""""

**Syntax**

.. code-block:: none

    [p]customcom show <command_name>

**Description**

Shows a custom command's responses and its settings.

.. _customcommands-command-customcom-search:

""""""
search
""""""

**Syntax**

.. code-block:: none

    [p]customcom search <query>

**Description**

Searches through custom commands, according to the query.

.. _customcommands-command-customcom-raw:

"""
raw
"""

**Syntax**

.. code-block:: none

    [p]customcom raw <command>

**Description**

Get the raw response of a custom command, to get the proper markdown.

This is helpful for copy and pasting.

.. _customcommands-command-customcom-cooldown:

""""""""
cooldown
""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom cooldown <command> [cooldown] [per=member]

**Description**

Set, edit, or view the cooldown for a custom command.

You may set cooldowns per member, channel, or guild. Multiple
cooldowns may be set. All cooldowns must be cooled to call the
custom command.

Example:
- `[p]customcom cooldown yourcommand 30`

.. _customcommands-command-customcom-list:

""""
list
""""

**Syntax**

.. code-block:: none

    [p]customcom list 

**Description**

List all available custom commands.

The list displays a preview of each command's response, with
markdown escaped and newlines replaced with spaces.

.. _customcommands-command-customcom-delete:

""""""
delete
""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom delete <command>

**Description**

Delete a custom command.

Example:
- `[p]customcom delete yourcommand`

.. _customcommands-command-customcom-create:

""""""
create
""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom create <command> <text>

**Description**

Create custom commands.

If a type is not specified, a simple CC will be created.
CCs can be enhanced with arguments, see the guide
[here](https://docs.discord.red/en/stable/cog_customcom.html).

.. _customcommands-command-customcom-create-simple:

""""""
simple
""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom create simple <command> <text>

**Description**

Add a simple custom command.

Example:
- `[p]customcom create simple yourcommand Text you want`

.. _customcommands-command-customcom-create-random:

""""""
random
""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom create random <command>

**Description**

Create a CC where it will randomly choose a response!

Note: This command is interactive.

.. _customcommands-command-customcom-edit:

""""
edit
""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom edit <command> [text]

**Description**

Edit a custom command.

Example:
- `[p]customcom edit yourcommand Text you want`
