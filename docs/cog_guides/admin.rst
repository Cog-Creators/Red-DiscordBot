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

It also provides tools for bot owner such as server locking (once enabled,
the bot will instantly leave new servers he joins) and announcements, which
will tell something in all servers he's in.

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
by admins.

**Arguments**

* ``<selfrole>``: The role you want to attribute to yourself. Please give
  **the exact role name or ID**, or it won't be detected.

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

* ``<selfrole>``: The role you want to remove from yourself. Please give
  **the exact role name or ID**, or it won't be detected.

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

This command is locked to the ``Manage roles`` permission.

**Syntax**

.. code-block:: none

    [p]selfrole add <role>

**Description**

Add a role to the available selfroles list.

.. warning:: Members will be able to assign themselves the role.
    Make sure it doesn't give extra perms or anything that can break
    your servers' security.

**Arguments**

* ``<role>``: The role to add to the list. Please give 
  **the exact role name or ID**, or it won't be detected.

.. _admin-command-selfrole-delete:

"""""""""""""""
selfrole delete
"""""""""""""""

This command is locked to the ``Manage roles`` permission.

**Syntax**

.. code-block:: none

    [p]selfrole add <role>

**Description**

Removes a role from the available selfroles list.

**Arguments**

* ``<role>``: The role to remove from the list. Please give
  **the exact role name or ID**, or it won't be detected.

.. _admin-command-addrole:

^^^^^^^
addrole
^^^^^^^

|admin-lock|

**Syntax**

.. code-block:: none

    [p]addrole <rolename> [user]

**Description**

Add a role to a member. If ``user`` is not given, it will be considered
as yourself, the command author.

**Arguments**

* ``<role>``: The role to add to the member. Please give
  **the exact role name or ID**, or it won't be detected. If the role
  name has spaces, give it between quotes like this: ``[p]addrole "my
  role with spaces"``

* ``[user=ctx]``: Member you want to add the role to. Default to the
  command author.

.. _admin-command-removerole:

^^^^^^^^^^
removerole
^^^^^^^^^^

|admin-lock|

**Syntax**

.. code-block:: none

    [p]removerole

**Description**

Remove a role from a member. If ``user`` is not given, it will be considered
as yourself, the command author.

**Arguments**

* ``<role>``: The role to remove. Please give
  **the exact role name or ID**, or it won't be detected. If the role
  name has spaces, give it between quotes like this: ``[p]removerole "my
  role with spaces"``

* ``[user=ctx]``: The member to remove the role from. Default to the
  command author.

.. _admin-command-editrole:

^^^^^^^^
editrole
^^^^^^^^

|admin-lock|

**Syntax**

.. code-block:: none

    [p]editrole

**Description**

Edits a role from the server.

.. _admin-command-editrole-name:

"""""""""""""
editrole name
"""""""""""""

**Syntax**

.. code-block:: none

    [p]editrole name <role> <name>

**Description**

Edit a role name from the guild.

**Arguments**

* ``<role>``: The role name to edit. Please give
  **the exact role name or ID**, or it won't be detected. If the role
  name has spaces, give it between quotes like this: ``[p]removerole "my
  role with spaces"``

* ``<name>``: The new role name

.. _admin-command-editrole-color:

""""""""""""""
editrole color
""""""""""""""

**Syntax**

.. code-block:: none

    [p]editrole color <role> <color>

**Description**

Edit a role color from the guild. You can give an hexadecimal code or a color
name for the color. For a complete list of the available color names, 
check :class:`~discord.Color`.

Examples:

* ``[p]editrole color "My role" #ff0000``

* ``[p]editrole color "My role" dark_blue``

**Arguments**

* ``<role>``: The role name to edit. Please give
  **the exact role name or ID**, or it won't be detected. If the role
  name has spaces, give it between quotes like this: ``[p]removerole "my
  role with spaces"``

* ``<color>``: The new color to assign. Can be a name (e.g. ``green``) or
  an hexadecimal code (e.g. ``#ff0000``)

.. _admin-command-announce:

^^^^^^^^
announce
^^^^^^^^

|owner-lock|

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

|guildowner-lock|

**Syntax**

.. code-block:: none

    [p]announce channel [channel]

**Description**

Set the channel where the bot owner announcements will be done.

**Arguments**

* ``[channel=ctx]``: The channel that will be used for bot announcements.
  Default to where you typed the command.

.. _admin-command-announce-ignore:

"""""""""""""""
announce ignore
"""""""""""""""

|guildowner-lock|

**Syntax**

.. code-block:: none

    [p]announce ignore [guild]

**Description**

Enable or disable the announcements on the selected guild.

**Arguments**

* ``[guild=ctx]``: The guild where the announcements will be enabled/disabled.

.. warning:: You need proper permissions if you're trying to edit a guild
    setting from another one.

.. _admin-command-announce-cancel:

"""""""""""""""
announce cancel
"""""""""""""""

|owner-lock|

**Syntax**

.. code-block:: none

    [p]announce cancel

**Description**

Cancel a running announcement.
