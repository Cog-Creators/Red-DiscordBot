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

It's designed as a moderator tool and offers many convenient use cases.
All cleanup commands only apply to the channel the command is executed in


.. _cleanup-commands:

--------
Commands
--------

.. _cleanup-command-cleanup:

^^^^^^^
cleanup
^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]cleanup 

**Description**

Base command for deleting messages.

.. _cleanup-command-cleanup-before:

""""""""""""""
cleanup before
""""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup before <message_id> <number> [delete_pinned=False]

**Description**

Deletes X messages before specified message.

To get a message id, enable developer mode in Discord's
settings, 'appearance' tab. Then right click a message
and copy its id.

.. _cleanup-command-cleanup-self:

""""""""""""
cleanup self
""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup self <number> [match_pattern] [delete_pinned=False]

**Description**

Clean up messages owned by the bot.

By default, all messages are cleaned. If a third argument is specified,
it is used for pattern matching - only messages containing the given text will be deleted.

.. _cleanup-command-cleanup-text:

""""""""""""
cleanup text
""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup text <text> <number> [delete_pinned=False]

**Description**

Delete the last X messages matching the specified text.

Example:
    ``[p]cleanup text "test" 5``

Remember to use double quotes.

.. _cleanup-command-cleanup-between:

"""""""""""""""
cleanup between
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup between <one> <two> [delete_pinned=False]

**Description**

Delete the messages between Messsage One and Message Two, providing the messages IDs.

The first message ID should be the older message and the second one the newer.

Example:
    ``[p]cleanup between 123456789123456789 987654321987654321``

.. _cleanup-command-cleanup-spam:

""""""""""""
cleanup spam
""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup spam [number=50]

**Description**

Deletes duplicate messages in the channel from the last X messages and keeps only one copy.

Defaults to 50.

.. _cleanup-command-cleanup-user:

""""""""""""
cleanup user
""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup user <user> <number> [delete_pinned=False]

**Description**

Delete the last X messages from a specified user.

Examples:
    ``[p]cleanup user @Twentysix 2``
    ``[p]cleanup user Red 6``

.. _cleanup-command-cleanup-messages:

""""""""""""""""
cleanup messages
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup messages <number> [delete_pinned=False]

**Description**

Delete the last X messages.

Example:
    ``[p]cleanup messages 26``

.. _cleanup-command-cleanup-after:

"""""""""""""
cleanup after
"""""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup after <message_id> [delete_pinned=False]

**Description**

Delete all messages after a specified message.

To get a message id, enable developer mode in Discord's
settings, 'appearance' tab. Then right click a message
and copy its id.

.. _cleanup-command-cleanup-bot:

"""""""""""
cleanup bot
"""""""""""

**Syntax**

.. code-block:: none

    [p]cleanup bot <number> [delete_pinned=False]

**Description**

Clean up command messages and messages from the bot.
