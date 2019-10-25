.. _alias:

=====
Alias
=====

This is the cog guide for the alias cog. You will
find detailed docs about the usage and the commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load alias

.. _alias-usage:

-----
Usage
-----

This cog allows to create shortcuts for commands.

You can do things like this:

.. code-block:: none

    [p]cleanup messages 42
    equals to
    [p]clean 42

or even this:

.. code-block:: none

    [p]playlist append daftpunk One more time
    equals to
    [p]dp One more time

In the first example, we made an alias named ``clean`` that will
invoke the ``cleanup messages`` command.

In the second example, we made an alias called ``dp`` that will
invoke the ``playlist append daftpunk`` command. As you can see,
you can also add arguments to your alias.

Then you can add the arguments you want after your alias.

.. _alias-commands:

--------
Commands
--------

.. _alias-command-alias:

^^^^^
alias
^^^^^

**Syntax**

.. code-block:: none

    [p]alias

**Description**

This is the main command used for setting up the cog.
It will be used for all other commands.

.. _alias-command-alias-add:

"""""""""
alias add
"""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]alias add <alias_name> <command>

**Description**

Creates an alias. It will be used like this ``[p]alias_name <arguments>``
and will be equal to this ``[p]command <arguments>``.

Click :ref:`here <alias-usage>` for examples.

**Arguments**

* ``<alias_name>``: The new command name.

* ``<command>``: The command to execute when ``[p]alias_name`` is invoked.

.. _alias-command-alias-delete:

""""""""""""
alias delete
""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]alias [delete|remove|del] <alias_name>

**Description**

Removes an alias from the list. Check the list with
the :ref:`alias list <alias-command-alias-list>` command.

**Arguments**

* ``<alias_name>``: The alias' name to delete.

.. _alias-command-alias-list:

""""""""""
alias list
""""""""""

**Syntax**

.. code-block:: none

    [p]alias list

**Description**

Shows all of the existing aliases on the current server.

.. _alias-command-alias-show:

""""""""""
alias show
""""""""""

**Syntax**

.. code-block:: none

    [p]alias show <alias_name>

**Description**

Shows the command associated to the alias.

**Arguments**

* ``<alias_name>``: The alias you want information from.

.. _alias-command-alias-help:

""""""""""
alias help
""""""""""

**Syntax**

.. code-block:: none

    [p]alias help <alias_name>

**Description**

Shows help message for an alias.

**Arguments**

* ``<alias_name>``: Alias you want to get help from.

.. _alias-command-alias-global:

""""""""""""
alias global
""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]alias global

**Description**

Another group command which contains the :ref:`add
<alias-command-alias-add>`, :ref:`del
<alias-command-alias-delete>` and :ref:`list
<alias-command-alias-list>` commands.

They work the same, except the created aliases will be
global instead of being server-wide.

Please refer to these commands for the docs, they work with the
same arguments. For example, if you want to add a global alias,
instead of doing ``[p]alias add <arguments>``, do ``[p]alias
global add <arguments>``.
