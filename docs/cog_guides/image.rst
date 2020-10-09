.. _image:

=====
Image
=====

This is the cog guide for the image cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load image

.. _image-usage:

-----
Usage
-----

Image related commands.


.. _image-commands:

--------
Commands
--------

.. _image-command-imgur:

^^^^^
imgur
^^^^^

**Syntax**

.. code-block:: none

    [p]imgur 

**Description**

Retrieve pictures from Imgur.

Make sure to set the Client ID using `[p]imgurcreds`.

.. _image-command-imgur-search:

""""""
search
""""""

**Syntax**

.. code-block:: none

    [p]imgur search [count=1] <term>

**Description**

Search Imgur for the specified term.

Use `count` to choose how many images should be returned.
Command can return up to 5 images.

.. _image-command-imgur-subreddit:

"""""""""
subreddit
"""""""""

**Syntax**

.. code-block:: none

    [p]imgur subreddit <subreddit> [count=1] [sort_type=top] [window=day]

**Description**

Get images from a subreddit.

You can customize the search with the following options:
- `<count>`: number of images to return (up to 5)
- `<sort_type>`: new, top
- `<window>`: day, week, month, year, all

.. _image-command-imgurcreds:

^^^^^^^^^^
imgurcreds
^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]imgurcreds 

**Description**

Explain how to set imgur API tokens.

.. _image-command-gif:

^^^
gif
^^^

**Syntax**

.. code-block:: none

    [p]gif [keywords...]

**Description**

Retrieve the first search result from Giphy.

.. _image-command-gifr:

^^^^
gifr
^^^^

**Syntax**

.. code-block:: none

    [p]gifr [keywords...]

**Description**

Retrieve a random GIF from a Giphy search.

.. _image-command-giphycreds:

^^^^^^^^^^
giphycreds
^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]giphycreds 

**Description**

Explains how to set GIPHY API tokens.
