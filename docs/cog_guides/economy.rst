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

Manage the bank.

.. _economy-command-bank-prune:

^^^^^
prune
^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]bank prune 

**Description**

Prune bank accounts.

.. _economy-command-bank-prune-global:

^^^^^^
global
^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]bank prune global [confirmation=False]

**Description**

Prune bank accounts for users who no longer share a server with the bot.

.. _economy-command-bank-prune-server:

^^^^^^
server
^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bank prune server [confirmation=False]

**Description**

Prune bank accounts for users no longer in the server.

.. _economy-command-bank-prune-user:

^^^^
user
^^^^

**Syntax**

.. code-block:: none

    [p]bank prune user <user> [confirmation=False]

**Description**

Delete the bank account of a specified user.

.. _economy-command-bank-transfer:

^^^^^^^^
transfer
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]bank transfer <to> <amount>

**Description**

Transfer currency to other users.

.. _economy-command-bank-set:

^^^
set
^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]bank set <to> <creds>

**Description**

Set the balance of user's bank account.

Passing positive and negative values will add/remove currency instead.

Examples:
- `[p]bank set @Twentysix 26` - Sets balance to 26
- `[p]bank set @Twentysix +2` - Increases balance by 2
- `[p]bank set @Twentysix -6` - Decreases balance by 6

.. _economy-command-bank-reset:

^^^^^
reset
^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bank reset [confirmation=False]

**Description**

Delete all bank accounts.

.. _economy-command-bank-balance:

^^^^^^^
balance
^^^^^^^

**Syntax**

.. code-block:: none

    [p]bank balance [user]

**Description**

Show the user's account balance.

Defaults to yours.

.. _economy-command-payday:

^^^^^^
payday
^^^^^^

**Syntax**

.. code-block:: none

    [p]payday 

**Description**

Get some free currency.

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

.. _economy-command-economyset-slotmin:

^^^^^^^
slotmin
^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset slotmin <bid>

**Description**

Set the minimum slot machine bid.

.. _economy-command-economyset-paydayamount:

^^^^^^^^^^^^
paydayamount
^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset paydayamount <creds>

**Description**

Set the amount earned each payday.

.. _economy-command-economyset-slotmax:

^^^^^^^
slotmax
^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset slotmax <bid>

**Description**

Set the maximum slot machine bid.

.. _economy-command-economyset-rolepaydayamount:

^^^^^^^^^^^^^^^^
rolepaydayamount
^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset rolepaydayamount <role> <creds>

**Description**

Set the amount earned each payday for a role.

.. _economy-command-economyset-slottime:

^^^^^^^^
slottime
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset slottime <seconds>

**Description**

Set the cooldown for the slot machine.

.. _economy-command-economyset-registeramount:

^^^^^^^^^^^^^^
registeramount
^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset registeramount <creds>

**Description**

Set the initial balance for new bank accounts.

.. _economy-command-economyset-showsettings:

^^^^^^^^^^^^
showsettings
^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset showsettings 

**Description**

Shows the current economy settings

.. _economy-command-economyset-paydaytime:

^^^^^^^^^^
paydaytime
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]economyset paydaytime <seconds>

**Description**

Set the cooldown for payday.
