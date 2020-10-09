.. _trivia:

======
Trivia
======

This is the cog guide for the trivia cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load trivia

.. _trivia-usage:

-----
Usage
-----

Play trivia with friends!


.. _trivia-commands:

--------
Commands
--------

.. _trivia-command-triviaset:

^^^^^^^^^
triviaset
^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset 

**Description**

Manage Trivia settings.

.. _trivia-command-triviaset-custom:

""""""
custom
""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom 

**Description**

Manage Custom Trivia lists.

.. _trivia-command-triviaset-custom-list:

""""
list
""""

**Syntax**

.. code-block:: none

    [p]triviaset custom list 

**Description**

List uploaded custom trivia.

.. _trivia-command-triviaset-custom-upload:

""""""
upload
""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom upload 

**Description**

Upload a trivia file.

.. _trivia-command-triviaset-custom-delete:

""""""
delete
""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom delete <name>

**Description**

Delete a trivia file.

.. _trivia-command-triviaset-override:

""""""""
override
""""""""

**Syntax**

.. code-block:: none

    [p]triviaset override <enabled>

**Description**

Allow/disallow trivia lists to override settings.

.. _trivia-command-triviaset-revealanswer:

""""""""""""
revealanswer
""""""""""""

**Syntax**

.. code-block:: none

    [p]triviaset revealanswer <true_or_false>

**Description**

Set whether or not the answer is revealed.

If enabled, the bot will reveal the answer if no one guesses correctly
in time.

.. _trivia-command-triviaset-payout:

""""""
payout
""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]triviaset payout <multiplier>

**Description**

Set the payout multiplier.

This can be any positive decimal number. If a user wins trivia when at
least 3 members are playing, they will receive credits. Set to 0 to
disable.

The number of credits is determined by multiplying their total score by
this multiplier.

.. _trivia-command-triviaset-stopafter:

"""""""""
stopafter
"""""""""

**Syntax**

.. code-block:: none

    [p]triviaset stopafter <seconds>

**Description**

Set how long until trivia stops due to no response.

.. _trivia-command-triviaset-botplays:

""""""""
botplays
""""""""

**Syntax**

.. code-block:: none

    [p]triviaset botplays <true_or_false>

**Description**

Set whether or not the bot gains points.

If enabled, the bot will gain a point if no one guesses correctly.

.. _trivia-command-triviaset-maxscore:

""""""""
maxscore
""""""""

**Syntax**

.. code-block:: none

    [p]triviaset maxscore <score>

**Description**

Set the total points required to win.

.. _trivia-command-triviaset-timelimit:

"""""""""
timelimit
"""""""""

**Syntax**

.. code-block:: none

    [p]triviaset timelimit <seconds>

**Description**

Set the maximum seconds permitted to answer a question.

.. _trivia-command-triviaset-showsettings:

""""""""""""
showsettings
""""""""""""

**Syntax**

.. code-block:: none

    [p]triviaset showsettings 

**Description**

Show the current trivia settings.

.. _trivia-command-trivia:

^^^^^^
trivia
^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia [categories...]

**Description**

Start trivia session on the specified category.

You may list multiple categories, in which case the trivia will involve
questions from all of them.

.. _trivia-command-trivia-list:

""""
list
""""

**Syntax**

.. code-block:: none

    [p]trivia list 

**Description**

List available trivia categories.

.. _trivia-command-trivia-leaderboard:

"""""""""""
leaderboard
"""""""""""

**Syntax**

.. code-block:: none

    [p]trivia leaderboard 

**Description**

Leaderboard for trivia.

Defaults to the top 10 of this server, sorted by total wins. Use
subcommands for a more customised leaderboard.

.. _trivia-command-trivia-leaderboard-global:

""""""
global
""""""

**Syntax**

.. code-block:: none

    [p]trivia leaderboard global [sort_by=wins] [top=10]

**Description**

Global trivia leaderboard.

`<sort_by>` can be any of the following fields:
 - `wins`  : total wins
 - `avg`   : average score
 - `total` : total correct answers from all sessions
 - `games` : total games played

`<top>` is the number of ranks to show on the leaderboard.

.. _trivia-command-trivia-leaderboard-server:

""""""
server
""""""

**Syntax**

.. code-block:: none

    [p]trivia leaderboard server [sort_by=wins] [top=10]

**Description**

Leaderboard for this server.

`<sort_by>` can be any of the following fields:
 - `wins`  : total wins
 - `avg`   : average score
 - `total` : total correct answers
 - `games` : total games played

`<top>` is the number of ranks to show on the leaderboard.

.. _trivia-command-trivia-stop:

""""
stop
""""

**Syntax**

.. code-block:: none

    [p]trivia stop 

**Description**

Stop an ongoing trivia session.
