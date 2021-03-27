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

.. _modlog-command-case:

^^^^
case
^^^^

**Syntax**

.. code-block:: none

    [p]case <number>

**Description**

Show the specified case.

**Arguments**

* ``<case>``: The case number to get information for.

.. _modlog-command-casesfor:

^^^^^^^^
casesfor
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]casesfor <member>

**Description**

Display cases for the specified member.

**Arguments**

* ``<member>``: The member to get cases for. |member-input|

.. _modlog-command-listcases:

^^^^^^^^^
listcases
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]listcases <member>

**Description**

List cases for the specified member.

**Arguments**

* ``<member>``: The member to get cases for. |member-input|

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

"""""""""""""""
modlogset cases
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset cases [action]

**Description**

Enable or disable case creation for a mod action.

**Arguments**

* ``[action]``: The action to enable or disable case creation for.

.. _modlog-command-modlogset-modlog:

""""""""""""""""
modlogset modlog
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset modlog [channel]

.. tip:: Alias: ``modlogset channel``

**Description**

Set a channel as the modlog.

**Arguments**

* ``[channel]``: The channel to set as the modlog. If omitted, the modlog will be disabled.

.. _modlog-command-modlogset-resetcases:

""""""""""""""""""""
modlogset resetcases
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset resetcases 

**Description**

Reset all modlog cases in this server.

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

**Arguments**

* ``[case]``: The case number to update the reason for.
* ``<reason>``: The new reason for the specified case.

.. note:: If no case number is specified, the latest case will be used.
