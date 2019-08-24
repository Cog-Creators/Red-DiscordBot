.. _admin:

=====
Admin
=====

This is the cog guide for the admin cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load admin

.. _admin-usage:

-----
Usage
-----

This cog will provide tools for server admins and bot owner.

It can add or remove a role to a member, edit one, make some available
for members so they can self-assign them as they wish.

It also provides tools for the bot owner such as server locking (once enabled,
the bot will instantly leave new servers he joins) and announcements, which
will tell something in all the servers of the bot.

.. _admin-commands:

--------
Commands
--------

Here's a list of all commands available for this cog.

.. _admin-command-selfrole:

^^^^^^^^
selfrole
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]selfrole <selfrole>

**Description**

Add a role to yourself. It must have been configured as user settable
by admins using the :ref:`selfrole add command <admin-command-selfrole-add>`.

**Arguments**

* ``<selfrole>``: The role you want to attribute to yourself. |role-input|

.. _admin-command-selfrole-remove:

"""""""""""""""
selfrole remove
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]selfrole remove <role>

**Description**

Remove a role from yourself. It must have been configured as user settable
by admins.

**Arguments**

* ``<selfrole>``: The role you want to remove from yourself. |role-input|

.. _admin-command-selfrole-list:

"""""""""""""
selfrole list
"""""""""""""

**Syntax**

.. code-block:: none

    [p]selfrole list

**Description**

List all of the available roles you can assign to yourself.

.. _admin-command-selfrole-add:

""""""""""""
selfrole add
""""""""""""

.. note:: This command is locked to the members with the ``Manage roles``
    permission.

**Syntax**

.. code-block:: none

    [p]selfrole add <role>

**Description**

Add a role to the list of selfroles.

.. warning:: Members will be able to assign themselves the role.
    Make sure it doesn't give extra perms or anything that can break
    your servers' security.

**Arguments**

* ``<role>``: The role to add to the list. |role-input|

.. _admin-command-selfrole-delete:

"""""""""""""""
selfrole delete
"""""""""""""""

.. note:: This command is locked to the member with the ``Manage roles``
    permission.

**Syntax**

.. code-block:: none

    [p]selfrole add <role>

**Description**

Removes a role from the list of selfroles.

**Arguments**

* ``<role>``: The role to remove from the list. |role-input|

.. _admin-command-addrole:

^^^^^^^
addrole
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]addrole <rolename> [user]

**Description**

Adds a role to a member. If ``user`` is not given, it will be considered
as yourself, the command author.

**Arguments**

* ``<role>``: The role to add to the member. |role-input|

* ``[user=ctx]``: The member you want to add the role to. Default to the
  command author. |member-input|

.. _admin-command-removerole:

^^^^^^^^^^
removerole
^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]removerole

**Description**

Removes a role from a member. If ``user`` is not given, it will be considered
as yourself, the command author.

**Arguments**

* ``<role>``: The role to remove. |role-input|

* ``[user=ctx]``: The member to remove the role from. |member-input| Default to
  the command author.

.. _admin-command-editrole:

^^^^^^^^
editrole
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]editrole

**Description**

Edits a setting of a role.

.. _admin-command-editrole-name:

"""""""""""""
editrole name
"""""""""""""

**Syntax**

.. code-block:: none

    [p]editrole name <role> <name>

**Description**

Edits the name of a role.

**Arguments**

* ``<role>``: The role name to edit. |role-input|

* ``<name>``: The new role name.

.. _admin-command-editrole-color:

""""""""""""""
editrole color
""""""""""""""

**Syntax**

.. code-block:: none

    [p]editrole color <role> <color>

**Description**

Edits the color of a role.

**Arguments**

* ``<role>``: The role name to edit. |role-input|

* ``<color>``: The new color to assign. |color-input|

**Examples**

* ``[p]editrole color "My role" #ff0000``

* ``[p]editrole color "My role" dark_blue``

.. _admin-command-announce:

^^^^^^^^
announce
^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]announce <message>

**Description**

Announce your message to all of the servers the bot is in.

The bot will announce the message in the guild's announcements channel
if set, else he will try the system channel (where the new members are
welcomed with the Discord announcer). If none of these channels are found,
the bot will use the first one.

**Arguments**

* ``<message>``: The message to send.

.. _admin-command-announce-channel:

""""""""""""""""
announce channel
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]announce channel [channel]

**Description**

Sets the channel where the bot owner announcements will be done.

**Arguments**

* ``[channel=ctx]``: The channel that will be used for bot announcements.
  |channel-input| Default to where you typed the command.

.. _admin-command-announce-ignore:

"""""""""""""""
announce ignore
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]announce ignore [guild]

**Description**

Enables or disables the announcements on the selected guild.

**Arguments**

* ``[guild=ctx]``: The server where the announcements will be enabled/disabled.
    Defaults to the current server.

.. warning:: You need the appropriate permissions if you're trying to edit a
    server setting from a different one.

.. _admin-command-announce-cancel:

"""""""""""""""
announce cancel
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]announce cancel

**Description**

Cancels an active announcement.
