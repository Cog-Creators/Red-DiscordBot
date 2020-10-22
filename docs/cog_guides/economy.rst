.. _economy:

=======
Economy
=======

This is the cog guide for the economy cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load economy

.. _economy-usage:

-----
Usage
-----

Get rich and have fun with imaginary currency!


.. _economy-commands:

--------
Commands
--------

.. _economy-command-bank:

^^^^
bank
^^^^

**Syntax**

.. code-block:: none

    [p]bank 

**Description**

Base command to manage the bank.

.. _economy-command-bank-balance:

""""""""""""
bank balance
""""""""""""

**Syntax**

.. code-block:: none

    [p]bank balance [user]

**Description**

Show the user's account balance.

Example:
- ``[p]bank balance``
- ``[p]bank balance @Twentysix``

**Arguments**

- ``<user>`` The user to check the balance of. If omitted, defaults to your own balance.

.. _economy-command-bank-prune:

""""""""""
bank prune
""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]bank prune 

**Description**

Prune bank accounts.

.. _economy-command-bank-prune-global:

"""""""""""""""""
bank prune global
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]bank prune global [confirmation=False]

**Description**

Prune bank accounts for users who no longer share a server with the bot.

.. _economy-command-bank-prune-server:

"""""""""""""""""
bank prune server
"""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bank prune server [confirmation=False]

.. tip:: Aliases: guild, local

**Description**

Prune bank accounts for users no longer in the server.

.. _economy-command-bank-prune-user:

"""""""""""""""
bank prune user
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]bank prune user <user> [confirmation=False]

**Description**

Delete the bank account of a specified user.

.. _economy-command-bank-reset:

""""""""""
bank reset
""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bank reset [confirmation=False]

**Description**

Delete all bank accounts.

.. _economy-command-bank-set:

""""""""
bank set
""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]bank set <to> <creds>

**Description**

Set the balance of user's bank account.

Passing positive and negative values will add/remove currency instead.

Examples:
- ``[p]bank set @Twentysix 26`` - Sets balance to 26
- ``[p]bank set @Twentysix +2`` - Increases balance by 2
- ``[p]bank set @Twentysix -6`` - Decreases balance by 6

.. _economy-command-bank-transfer:

"""""""""""""
bank transfer
"""""""""""""

**Syntax**

.. code-block:: none

    [p]bank transfer <to> <amount>

**Description**

Transfer currency to other users.

This will come out of your balance, so make sure you have enough.

Example:
- ``[p]bank transfer @Twentysix 500``

**Arguments**

- ``<user>`` The user to give currency to.

.. _economy-command-economyset:

^^^^^^^^^^
economyset
^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]economyset 

**Description**

Manage Economy settings.

.. _economy-command-economyset-paydayamount:

"""""""""""""""""""""""
economyset paydayamount
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset paydayamount <creds>

**Description**

Set the amount earned each payday.

.. _economy-command-economyset-paydaytime:

"""""""""""""""""""""
economyset paydaytime
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset paydaytime <seconds>

**Description**

Set the cooldown for payday.

.. _economy-command-economyset-registeramount:

"""""""""""""""""""""""""
economyset registeramount
"""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset registeramount <creds>

**Description**

Set the initial balance for new bank accounts.

.. _economy-command-economyset-rolepaydayamount:

"""""""""""""""""""""""""""
economyset rolepaydayamount
"""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset rolepaydayamount <role> <creds>

**Description**

Set the amount earned each payday for a role.

.. _economy-command-economyset-showsettings:

"""""""""""""""""""""""
economyset showsettings
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset showsettings 

**Description**

Shows the current economy settings

.. _economy-command-economyset-slotmax:

""""""""""""""""""
economyset slotmax
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset slotmax <bid>

**Description**

Set the maximum slot machine bid.

.. _economy-command-economyset-slotmin:

""""""""""""""""""
economyset slotmin
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset slotmin <bid>

**Description**

Set the minimum slot machine bid.

.. _economy-command-economyset-slottime:

"""""""""""""""""""
economyset slottime
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]economyset slottime <seconds>

**Description**

Set the cooldown for the slot machine.

.. _economy-command-leaderboard:

^^^^^^^^^^^
leaderboard
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]leaderboard [top=10] [show_global=False]

**Description**

Print the leaderboard.

Defaults to top 10.

.. _economy-command-payday:

^^^^^^
payday
^^^^^^

**Syntax**

.. code-block:: none

    [p]payday 

**Description**

Get some free currency.

.. _economy-command-payouts:

^^^^^^^
payouts
^^^^^^^

**Syntax**

.. code-block:: none

    [p]payouts 

**Description**

Show the payouts for the slot machine.

.. _economy-command-slot:

^^^^
slot
^^^^

**Syntax**

.. code-block:: none

    [p]slot <bid>

**Description**

Use the slot machine.
