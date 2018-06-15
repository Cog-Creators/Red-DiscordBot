.. _economy:

=======
Economy
=======

This is the cog guide for the economy cog. You will
find detailled docs about the usage and the commands.

``[p]`` is considered as your prefix, ``credits`` as
your credits name in your bank.

.. note:: To use this cog, load it by typing this::

        [p]load economy

.. _economy-usage:

-----
Usage
-----

This cog bring useful tools and games that interacts with
the :ref:`bank`.

You will be able to manage accounts, such as :ref:`modifying members
balance <economy-command-bank-set>` or :ref:`make transfer between them
<economy-command-bank-transfer>`. You can also see the :ref:`leaderboard
<economy-command-leaderboard>`.

You can win money with mini games or with a customisable payday
system.

.. _economy-commands:

--------
Commands
--------

.. _economy-command-payday:

^^^^^^
payday
^^^^^^

**Syntax**

.. code-block:: none

    [p]payday

**Description**

Gives you an amount of money. This command can only be used once in
a certain time.

By default, this gives 200 credits, and the command can be used every
5 minuts.

You can edit this using the :ref:`economyset <economy-command-economyset>`
command.

.. _economy-command-slot:

^^^^
slot
^^^^

**Syntax**

.. code-block:: none

    [p]slot <bid>

**Description**

Bet an amount of money and play the slot machine.

3 items will be randomly chosen. If the items on the
middle line match a payout (listed below), you will get some
money.

Possible items: 🍒 🍪 2⃣ 🍀 🌀 🌻 6⃣ 🍄 ❤ ❄

Slot machine payouts:

* 2️⃣ 2️⃣ 6️⃣ Bet * 2500
* 🍀 🍀 🍀 +1000
* 🍒 🍒 🍒 +800
* ️2️⃣ 6️⃣ Bet * 4
* 🍒 🍒 Bet * 3

* Three symbols: +500
* Two symbols: Bet * 2

**Arguments**

* ``<bid>``: The amount of credits you want to bet. If you get nothing,
  it will be lost. Must be between 5 and 100 by default, it can be modified
  using the :ref:`slotmin <economy-command-economyset-slotmin>` and
  :ref:`slotmax <economy-command-economyset-slotmax>` commands.

.. _economy-command-payouts:

^^^^^^^
payouts
^^^^^^^

**Syntax**

.. code-block:: none

    [p]payouts

**Description**

Show the different payouts for the :ref:`slot
<economy-command-slot>` machine.

.. _economy-command-leaderboard:

^^^^^^^^^^^
leaderboard
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]leaderboard [top=10] [show_global=False]

**Description**

Show the leaderboard of the server. Default to the 10
richest members. You can also make it show the global
leaderboard.

**Arguments**

* ``[top=10]``: The number of members to show. Default to 10.

* ``[show_global=False]``: Make the bot show the global leaderboard
  instead of the server-wide one. Specify ``True``, ``yes`` or ``1``
  to make it True.

.. _economy-command-bank:

^^^^
bank
^^^^

**Syntax**

.. code-block:: none

    [p]bank

**Description**

Group command used for managing user accounts.

.. _economy-command-bank-balance:

""""""""""""
bank balance
""""""""""""

**Syntax**

.. code-block:: none

    [p]bank balance [user]

**Description**

Show your own balance. You can see the balance of
an other user by specifying it.

**Arguments**

* ``[user=ctx]`` The user to get the balance from. Defaults
  to the author.

.. _economy-command-bank-set:

""""""""
bank set
""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bank set <to> <creds>

**Description**

Set balance of a user's bank account. You can also add or remove
currency by passing positive or negative values.

Examples:

+-------------------------------+-------------------------------+
|Command                        |Action                         |
+===============================+===============================+
|``[p]bank set @Laggron 26``    | Sets balance to 26            |
+-------------------------------+-------------------------------+
|``[p]bank set @Laggron +2``    |Increases balance by 2         |
+-------------------------------+-------------------------------+
|``[p]bank set @Laggron -6``    |Decreases balance by 6         |
+-------------------------------+-------------------------------+

**Arguments**

* ``<to>``: The user to get the balance from.

* ``<creds>``: The new amount to set. Can also increase/decrease
  the current balance by adding +/- before the number.

.. _economy-command-bank-transfer:

"""""""""""""
bank transfer
"""""""""""""

**Syntax**

.. code-block:: none

    [p]bank transfer <to> <amount>

**Description**

Transfer credits from your balance to an user.

**Arguments**

* ``<to>``: The user to give credits to.

* ``<amount>``: The amount of money to give.

.. _economy-command-bank-reset:

""""""""""
bank reset
""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bank reset [confirmation=False]

**Description**

Reset the bank, global or server-wide depending on the bank type.

You need to pass a security check before resetting the bank.

.. warning:: This action cannot be undone.

**Arguments**

* ``[confirmation=False]``: The confirmation for the reset. Put ``yes``
  if you want to reset the bank.

.. _economy-command-economyset:

^^^^^^^^^^
economyset
^^^^^^^^^^

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]economyset

**Description**

Group command used for setting up the economy settings.

.. note::

    If you use this command without a subcommand, the current settings
    will be shown.

.. _economy-command-economyset-paydayamount:

"""""""""""""""""""""""
economyset paydayamount
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset paydayamount <creds>

**Description**

Set the amount of credits given when using the :ref:`payday
<economy-command-payday>` command.

**Arguments**

* ``<creds>``: The new amount of credits to set.

.. _economy-command-economyset-rolepaydayamount:

"""""""""""""""""""""""""""
economyset rolepaydayamount
"""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset rolepaydayamount <role> <creds>

**Description** 

Set the amount of credits given when using the :ref:`payday
<economy-command-payday>` command for a specific role.

**Arguments**

* ``<role>``: The role that will get the specific payday amount.
  Please give **the exact role name or ID**, or it won't be detected.

  If the role name has spaces in it, put in enclosed in quotes like this:
  ``"My role name"``.

* ``<creds>``: The new amount of credits to set.

.. _economy-command-economyset-paydaytime:

"""""""""""""""""""""
economyset paydaytime
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset paydaytime <seconds>

**Description**

Set the cooldown of the :ref:`payday <economy-command-payday>`
command in seconds.

.. tip:: 30 minuts = 1800 seconds
    1 hour = 3600 seconds
    12 hours = 43200 seconds
    24 hours = 84400 seconds
    7 days = 604800 seconds

**Arguments**

* ``<seconds>``: The cooldown to set.

.. _economy-command-economyset-registeramount:

"""""""""""""""""""""""""
economyset registeramount
"""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset registeramount <creds>

**Description**

Set the amount of credits given on account creation (default user balance).

**Arguments**

* ``<creds>``: The default amount of credits to set.

.. _economy-command-economyset-slotmin:

""""""""""""""""""
economyset slotmin
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset slotmin <bid>

**Description**

Set the minimum bid for the :ref:`slot machine <economy-command-slot>`.

Default to 5.

**Arguments**

* ``<bid>``: The minimum amount of credits to set.

.. _economy-command-economyset-slotmax:

""""""""""""""""""
economyset slotmax
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset slotmax <bid>

**Description**

Set the maximum bid for the :ref:`slot machine <economy-command-slot>`.

Default to 100.

**Arguments**

* ``<bid>``: The maximum amount of credits to set.

.. _economy-command-economyset-slottime:

"""""""""""""""""""
economyset slottime
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset slottime <seconds>

**Description**

Set the cooldown of the :ref:`slot <economy-command-slot>`
command in seconds.

.. tip:: 30 minuts = 1800 seconds
    1 hour = 3600 seconds
    12 hours = 43200 seconds
    24 hours = 84400 seconds
    7 days = 604800 seconds

**Arguments**

* ``<seconds>``: The cooldown to set.
