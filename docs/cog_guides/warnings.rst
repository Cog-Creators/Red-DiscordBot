.. _warnings:

========
Warnings
========

This is the cog guide for the warnings cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load warnings

.. _warnings-usage:

-----
Usage
-----

Warn misbehaving users and take automated actions.


.. _warnings-commands:

--------
Commands
--------

.. _warnings-command-actionlist:

^^^^^^^^^^
actionlist
^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]actionlist 

**Description**

List all configured automated actions for Warnings.

.. _warnings-command-mywarnings:

^^^^^^^^^^
mywarnings
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]mywarnings 

**Description**

List warnings for yourself.

.. _warnings-command-reasonlist:

^^^^^^^^^^
reasonlist
^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reasonlist 

**Description**

List all configured reasons for Warnings.

.. _warnings-command-unwarn:

^^^^^^
unwarn
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unwarn <member> <warn_id> [reason]

**Description**

Remove a warning from a member.

**Arguments**

* ``<member>``: The member to remove the warning from. |member-input-quotes|
* ``<warn_id>``: The warning ID to remove from the member.
* ``[reason]``: The reason for unwarning this member.

.. _warnings-command-warn:

^^^^
warn
^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]warn <member> [points=1] <reason>

**Description**

Warn the user for the specified reason.

**Arguments**

* ``<member>``: The member to warn. |member-input-quotes|
* ``[points]``: The number of points the warning should be for. If no number is supplied, 1 point will be given. Pre-set warnings disregard this.
* ``<reason>``: The reason for the warning. This can be a registered reason, or a custom reason if ``[p]warningset allowcustomreasons`` is set.

.. _warnings-command-warnaction:

^^^^^^^^^^
warnaction
^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]warnaction 

**Description**

Manage automated actions for Warnings.

Actions are essentially command macros. Any command can be run
when the action is initially triggered, and/or when the action
is lifted.

Actions must be given a name and a points threshold. When a
user is warned enough so that their points go over this
threshold, the action will be executed.

.. _warnings-command-warnaction-add:

""""""""""""""
warnaction add
""""""""""""""

**Syntax**

.. code-block:: none

    [p]warnaction add <name> <points>

**Description**

Create an automated action.

Duplicate action names are not allowed.

**Arguments**

* ``<name>``: The name of the action.
* ``<points>``: The number of points for this action.

.. _warnings-command-warnaction-delete:

"""""""""""""""""
warnaction delete
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warnaction delete <action_name>

**Description**

Delete the action with the specified name.

**Arguments**

* ``<action_name>``: The name of the action to delete.

.. _warnings-command-warnings:

^^^^^^^^
warnings
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]warnings <member>

**Description**

List the warnings for the specified member.

**Arguments**

* ``<member>``: The member to get the warnings for. |member-input|

.. _warnings-command-warningset:

^^^^^^^^^^
warningset
^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]warningset 

**Description**

Manage settings for Warnings.

.. _warnings-command-warningset-allowcustomreasons:

"""""""""""""""""""""""""""""
warningset allowcustomreasons
"""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warningset allowcustomreasons <true_or_false>

**Description**

Enable or disable custom reasons for a warning.

**Arguments**

* ``<true_or_false>``: |bool-input|

.. _warnings-command-warningset-senddm:

"""""""""""""""""
warningset senddm
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warningset senddm <true_or_false>

**Description**

Set whether warnings should be sent to users in DMs.

**Arguments**

* ``<true_or_false>``: |bool-input|

.. _warnings-command-warningset-showmoderator:

""""""""""""""""""""""""
warningset showmoderator
""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warningset showmoderator <true_or_false>

**Description**

Decide whether the name of the moderator warning a user should be included in the DM to that user.

**Arguments**

* ``<true_or_false>``: |bool-input|

.. _warnings-command-warningset-usewarnchannel:

"""""""""""""""""""""""""
warningset usewarnchannel
"""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warningset usewarnchannel <true_or_false>

**Description**

Set if warnings should be sent to a channel set with ``[p]warningset warnchannel``.

**Arguments**

* ``<true_or_false>``: |bool-input|

.. _warnings-command-warningset-warnchannel:

""""""""""""""""""""""
warningset warnchannel
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warningset warnchannel [channel]

**Description**

Set the channel where warnings should be sent to.

**Arguments**

* ``[channel]``: |channel-input| Leave empty to use the channel ``[p]warn`` command was called in.

.. _warnings-command-warnreason:

^^^^^^^^^^
warnreason
^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]warnreason 

**Description**

Manage warning reasons.

Reasons must be given a name, description and points value. The
name of the reason must be given when a user is warned.

.. _warnings-command-warnreason-create:

"""""""""""""""""
warnreason create
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warnreason create <name> <points> <description>

.. tip:: Alias: ``warnreason add``

**Description**

Create a warning reason.

**Arguments**

* ``<name>``: The name for the new reason.
* ``<points>``: The number of points with the new reason.
* ``<description>``: The description of the new warn reason.

.. _warnings-command-warnreason-delete:

"""""""""""""""""
warnreason delete
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]warnreason delete <reason_name>
    
**Description**

Delete a warning reason.

**Arguments**

* ``<reason_name>``: The name of the reason to delete.
