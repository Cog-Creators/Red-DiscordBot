.. _filter:

======
Filter
======

This is the cog guide for the filter cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load filter

.. _filter-usage:

-----
Usage
-----

Filter unwanted words and phrases from text channels.


.. _filter-commands:

--------
Commands
--------

.. _filter-command-filter:

^^^^^^
filter
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]filter 

**Description**

Add or remove words from server filter.

Use double quotes to add or remove sentences.

.. _filter-command-filter-add:

""""""""""
filter add
""""""""""

**Syntax**

.. code-block:: none

    [p]filter add [words...]

**Description**

Add words to the filter.

Use double quotes to add sentences.

Examples:
    - ``[p]filter add word1 word2 word3``
    - ``[p]filter add "This is a sentence"``

.. _filter-command-filter-channel:

""""""""""""""
filter channel
""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel 

**Description**

Add or remove words from channel filter.

Use double quotes to add or remove sentences.

.. _filter-command-filter-channel-add:

""""""""""""""""""
filter channel add
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel add [words...]

**Description**

Add words to the filter.

Use double quotes to add sentences.

Examples:
    - ``[p]filter channel add word1 word2 word3``
    - ``[p]filter channel add "This is a sentence"``

.. _filter-command-filter-channel-list:

"""""""""""""""""""
filter channel list
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel list 

**Description**

Send the list of the channel's filtered words.

.. _filter-command-filter-channel-remove:

"""""""""""""""""""""
filter channel remove
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel remove [words...]

**Description**

Remove words from the filter.

Use double quotes to remove sentences.

Examples:
    - ``[p]filter channel remove word1 word2 word3``
    - ``[p]filter channel remove "This is a sentence"``

.. _filter-command-filter-delete:

"""""""""""""
filter delete
"""""""""""""

**Syntax**

.. code-block:: none

    [p]filter delete [words...]

.. tip:: Aliases: ``filter remove``, ``filter del``

**Description**

Remove words from the filter.

Use double quotes to remove sentences.

Examples:
    - ``[p]filter remove word1 word2 word3``
    - ``[p]filter remove "This is a sentence"``

.. _filter-command-filter-list:

"""""""""""
filter list
"""""""""""

**Syntax**

.. code-block:: none

    [p]filter list 

**Description**

Send a list of this servers filtered words.

.. _filter-command-filter-names:

""""""""""""
filter names
""""""""""""

**Syntax**

.. code-block:: none

    [p]filter names 

**Description**

Toggle name and nickname filtering.

This is disabled by default.

.. _filter-command-filterset:

^^^^^^^^^
filterset
^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]filterset 

**Description**

Base command to manage filter settings.

.. _filter-command-filterset-ban:

"""""""""""""
filterset ban
"""""""""""""

**Syntax**

.. code-block:: none

    [p]filterset ban <count> <timeframe>

**Description**

Set the filter's autoban conditions.

Users will be banned if they send ``<count>`` filtered words in
``<timeframe>`` seconds.

Set both to zero to disable autoban.

.. _filter-command-filterset-defaultname:

"""""""""""""""""""""
filterset defaultname
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filterset defaultname <name>

**Description**

Set the nickname for users with a filtered name.

Note that this has no effect if filtering names is disabled
(to toggle, run ``[p]filter names``).

The default name used is *John Doe*.
