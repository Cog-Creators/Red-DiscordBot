.. _general:

=======
General
=======

This is the cog guide for the general cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load general

.. _general-usage:

-----
Usage
-----

General commands.


.. _general-commands:

--------
Commands
--------

.. _general-command-choose:

^^^^^^
choose
^^^^^^

**Syntax**

.. code-block:: none

    [p]choose [choices...]

**Description**

Choose between multiple options.

To denote options which include whitespace, you should use
double quotes.

.. _general-command-roll:

^^^^
roll
^^^^

**Syntax**

.. code-block:: none

    [p]roll [number=100]

**Description**

Roll a random number.

The result will be between 1 and `<number>`.

`<number>` defaults to 100.

.. _general-command-flip:

^^^^
flip
^^^^

**Syntax**

.. code-block:: none

    [p]flip [user]

**Description**

Flip a coin... or a user.

Defaults to a coin.

.. _general-command-rps:

^^^
rps
^^^

**Syntax**

.. code-block:: none

    [p]rps <your_choice>

**Description**

Play Rock Paper Scissors.

.. _general-command-8:

^
8
^

**Syntax**

.. code-block:: none

    [p]8 <question>

**Description**

Ask 8 ball a question.

Question must end with a question mark.

.. _general-command-stopwatch:

^^^^^^^^^
stopwatch
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]stopwatch 

**Description**

Start or stop the stopwatch.

.. _general-command-lmgtfy:

^^^^^^
lmgtfy
^^^^^^

**Syntax**

.. code-block:: none

    [p]lmgtfy <search_terms>

**Description**

Create a lmgtfy link.

.. _general-command-hug:

^^^
hug
^^^

**Syntax**

.. code-block:: none

    [p]hug <user> [intensity=1]

**Description**

Because everyone likes hugs!

Up to 10 intensity levels.

.. _general-command-serverinfo:

^^^^^^^^^^
serverinfo
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]serverinfo [details=False]

**Description**

Show server information.

`details`: Shows more information when set to `True`.
Default to False.

.. _general-command-urban:

^^^^^
urban
^^^^^

**Syntax**

.. code-block:: none

    [p]urban <word>

**Description**

Search the Urban Dictionary.

This uses the unofficial Urban Dictionary API.
