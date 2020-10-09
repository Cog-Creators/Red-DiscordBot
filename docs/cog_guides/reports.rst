.. _reports:
.. |cogname| replace:: reports.rst

=======
Reports
=======

This is the cog guide for the |cogname| cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load |cogname|

.. _bank-usage:

-----
Usage
-----

This is a general description of what the cog does.
This should be a very basic explanation, addressing
the core purpose of the cog.

This is some additional information about what this
cog can do. Try to answer *the* most frequently
asked question.

.. _reports-commands:

--------
Commands
--------

.. _reports-command-reportset:

^^^^^^^^^
reportset
^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reportset 

**Description**

Manage Reports.

.. _reports-command-reportset-output:

^^^^^^
output
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reportset output <channel>

**Description**

Set the channel where reports will be sent.

.. _reports-command-reportset-toggle:

^^^^^^
toggle
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reportset toggle 

**Description**

Enable or Disable reporting for this server.

.. _reports-command-report:

^^^^^^
report
^^^^^^

**Syntax**

.. code-block:: none

    [p]report [_report]

**Description**

Send a report.

Use without arguments for interactive reporting, or do
`[p]report <text>` to use it non-interactively.

.. _reports-command-report-interact:

^^^^^^^^
interact
^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]report interact <ticket_number>

**Description**

Open a message tunnel.

This tunnel will forward things you say in this channel
to the ticket opener's direct messages.

Tunnels do not persist across bot restarts.
