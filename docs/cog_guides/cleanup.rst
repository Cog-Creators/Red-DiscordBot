.. _cleanup:

=======
Cleanup
=======

This is the cog guide for the cleanup cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load cleanup

.. _cleanup-usage:

-----
Usage
-----

This cog contains commands used for "cleaning up" (deleting) messages.

This is designed as a moderator tool and offers many convenient use cases.
All cleanup commands only apply to the channel the command is executed in.

Messages older than two weeks cannot be mass deleted.
This is a limitation of the API.


.. _cleanup-commands:

--------
Commands
--------

.. _cleanup-command-cleanup:

^^^^^^^
cleanup
^^^^^^^

**Syntax**

.. code-block:: none

    [p]cleanup 

**Description**

Base command for deleting messages.

.. _cleanup-command-cleanup-after:

"""""""""""""
cleanup after
"""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup after <message_id> [delete_pinned=False]

**Description**

Delete all messages after a specified message.

To get a message id, enable developer mode in Discord's
settings, 'appearance' tab. Then right click a message
and copy its id.

**Arguments:**

- ``<message_id>`` The id of the message to cleanup after. This message won't be deleted.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-before:

""""""""""""""
cleanup before
""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup before <message_id> <number> [delete_pinned=False]

**Description**

Deletes X messages before the specified message.

To get a message id, enable developer mode in Discord's
settings, 'appearance' tab. Then right click a message
and copy its id.

**Arguments:**

- ``<message_id>`` The id of the message to cleanup before. This message won't be deleted.
- ``<number>`` The max number of messages to cleanup. Must be a positive integer.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-between:

"""""""""""""""
cleanup between
"""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup between <one> <two> [delete_pinned=False]

**Description**

Delete the messages between Message One and Message Two, providing the messages IDs.

The first message ID should be the older message and the second one the newer.

Example:
    - ``[p]cleanup between 123456789123456789 987654321987654321``

**Arguments:**

- ``<one>`` The id of the message to cleanup after. This message won't be deleted.
- ``<two>`` The id of the message to cleanup before. This message won't be deleted.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-bot:

"""""""""""
cleanup bot
"""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup bot <number> [delete_pinned=False]

**Description**

Clean up command messages and messages from the bot.

Can only cleanup custom commands and alias commands if those cogs are loaded.

**Arguments:**

- ``<number>`` The max number of messages to cleanup. Must be a positive integer.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-messages:

""""""""""""""""
cleanup messages
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup messages <number> [delete_pinned=False]

**Description**

Delete the last X messages.

Example:
    - ``[p]cleanup messages 26``

**Arguments:**

- ``<number>`` The max number of messages to cleanup. Must be a positive integer.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-self:

""""""""""""
cleanup self
""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup self <number> [match_pattern] [delete_pinned=False]

**Description**

Clean up messages owned by the bot.

By default, all messages are cleaned. If a second argument is specified,
it is used for pattern matching - only messages containing the given text will be deleted.

Examples:
    - ``[p]cleanup self 6``
    - ``[p]cleanup self 10 Pong``
    - ``[p]cleanup self 7 "" True``

**Arguments:**

- ``<number>`` The max number of messages to cleanup. Must be a positive integer.
- ``<match_pattern>`` The text that messages must contain to be deleted. Use "" to skip this.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-spam:

""""""""""""
cleanup spam
""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup spam [number=50]

**Description**

Deletes duplicate messages in the channel from the last X messages and keeps only one copy.

Defaults to 50.

**Arguments:**

- ``<number>`` The number of messages to check for duplicates. Must be a positive integer.

.. _cleanup-command-cleanup-text:

""""""""""""
cleanup text
""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup text <text> <number> [delete_pinned=False]

**Description**

Delete the last X messages matching the specified text.

Example:
    - ``[p]cleanup text "test" 5``

Remember to use double quotes.

**Arguments:**

- ``<number>`` The max number of messages to cleanup. Must be a positive integer.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False

.. _cleanup-command-cleanup-user:

""""""""""""
cleanup user
""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup user <user> <number> [delete_pinned=False]

**Description**

Delete the last X messages from a specified user.

Examples:
    - ``[p]cleanup user @Twentysix 2``
    - ``[p]cleanup user Red 6``

**Arguments:**

- ``<user>`` The user whose messages are to be cleaned up.
- ``<number>`` The max number of messages to cleanup. Must be a positive integer.
- ``<delete_pinned>`` Whether to delete pinned messages or not. Defaults to False
