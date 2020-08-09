.. _bank:

====
Bank
====

This is the cog guide for the bank cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load bank

.. _bank-usage:

-----
Usage
-----

This cog manages the bank. It won't be used often by
users but this is what makes any interaction with the
money possible.

You will be able to switch between a global and a server-
wide bank and choose the bank/currency name.

.. _bank-commands:

--------
Commands
--------

.. _bank-command-bankset:

^^^^^^^
bankset
^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bankset

**Description**

Base command for configuring bank settings.

.. _bank-command-bankset-toggleglobal:

""""""""""""""""""""
bankset toggleglobal
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]bankset toggleglobal [confirm=False]

**Description**

Makes the bank global instead of server-wide. If it
is already global, the command will switch it back
to the server-wide bank.

.. warning:: Using this command will reset **all** accounts.

**Arguments**

* ``[confirm=False]``: Put ``yes`` to confirm.

.. _bank-command-bankset-creditsname:

"""""""""""""""""""
bankset creditsname
"""""""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset creditsname <name>

**Description**

Change the credits name of the bank. It is ``credits`` by default.

For example, if you switch it to ``dollars``, the payday
command will show this:

.. TODO reference the payday command

.. code-block:: none

    Here, take some dollars. Enjoy! (+120 dollars!)

    You currently have 220 dollars.

**Arguments**

* ``<name>``: The new credits name.

.. _bank-command-bankset-bankname:

""""""""""""""""
bankset bankname
""""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset bankname <name>

**Description**

Set bank's name.

**Arguments**

* ``<name>``: The new bank's name.

.. _bank-command-bankset-maxbal:

""""""""""""""
bankset maxbal
""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset maxbal <amount>

**Description**

Defines the maximum amount of money a user can have with the bot.

If an user reaches this limit, he will be unable to gain more money.

**Arguments**

*   ``<amount>``: The maximum amount of money for users.

.. _bank-command-bankset-showsettings:

""""""""""""""""""""
bankset showsettings
""""""""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset showsettings

**Description**

Shows the current settings of your bank.

This will display the following information:

*   Name of the bank
*   Scope of the bank (global or per server)
*   Currency name
*   Default balance
*   Maximum allowed balance
