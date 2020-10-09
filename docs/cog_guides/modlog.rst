.. _modlog:

======
ModLog
======

This is the cog guide for the modlog cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load modlog

.. _modlog-usage:

-----
Usage
-----

Manage log channels for moderation actions.


.. _modlog-commands:

--------
Commands
--------

.. _modlog-command-modlogset:

^^^^^^^^^
modlogset
^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]modlogset 

**Description**

Manage modlog settings.

.. _modlog-command-modlogset-cases:

"""""
cases
"""""

**Syntax**

.. code-block:: none

    [p]modlogset cases [action]

**Description**

Enable or disable case creation for a mod action.

.. _modlog-command-modlogset-modlog:

""""""
modlog
""""""

**Syntax**

.. code-block:: none

    [p]modlogset modlog [channel]

**Description**

Set a channel as the modlog.

Omit `<channel>` to disable the modlog.

.. _modlog-command-modlogset-fixcasetypes:

""""""""""""
fixcasetypes
""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]modlogset fixcasetypes 

**Description**

Command to fix misbehaving casetypes.

.. _modlog-command-modlogset-resetcases:

""""""""""
resetcases
""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset resetcases 

**Description**

Reset all modlog cases in this server.

.. _modlog-command-case:

^^^^
case
^^^^

**Syntax**

.. code-block:: none

    [p]case <number>

**Description**

Show the specified case.

.. _modlog-command-casesfor:

^^^^^^^^
casesfor
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]casesfor <member>

**Description**

Display cases for the specified member.

.. _modlog-command-reason:

^^^^^^
reason
^^^^^^

**Syntax**

.. code-block:: none

    [p]reason [case] <reason>

**Description**

Specify a reason for a modlog case.

Please note that you can only edit cases you are
the owner of unless you are a mod, admin or server owner.

If no case number is specified, the latest case will be used.
