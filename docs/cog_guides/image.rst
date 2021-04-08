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

This cog provides commands for retrieving pictures from
websites such as Giphy and Imgur.

.. _image-commands:

--------
Commands
--------

Here's a list of all commands available for this cog.

.. _image-command-gif:

^^^
gif
^^^

**Syntax**

.. code-block:: none

    [p]gif <keywords...>

**Description**

Retrieve the first search result from Giphy. This command requires API tokens
to be set via the :ref:`giphycreds <image-command-giphycreds>` command.

**Arguments**

* ``<keywords...>``: The keywords used to search Giphy.

.. _image-command-gifr:

^^^^
gifr
^^^^

**Syntax**

.. code-block:: none

    [p]gifr <keywords...>

**Description**

Retrieve a random GIF from a Giphy search. This command requires API tokens
to be set via the :ref:`giphycreds <image-command-giphycreds>` command.

**Arguments**

* ``<keywords...>``: The keywords used to generate a random GIF.

.. _image-command-imgur:

^^^^^
imgur
^^^^^

**Syntax**

.. code-block:: none

    [p]imgur

**Description**

Retrieves pictures from Imgur. This command requires API tokens to be set
via the :ref:`imgurcreds <image-command-imgurcreds>` command.

.. _image-command-imgur-search:

""""""""""""
imgur search
""""""""""""

**Syntax**

.. code-block:: none

    [p]imgur search [count=1] <terms...>

**Description**

Search for pictures on Imgur. This command requires API tokens to be set
via the :ref:`imgurcreds <image-command-imgurcreds>` command.

**Arguments**

* ``[count]``: How many images should be returned (maximum 5). Defaults to 1.

* ``<terms...>``: The terms used to search Imgur.

.. _image-command-imgur-subreddit:

"""""""""""""""
imgur subreddit
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]imgur subreddit <subreddit> [count=1] [sort_type=top] [window=day]

**Description**

Get images from a subreddit. This command requires API tokens to be set
via the :ref:`imgurcreds <image-command-imgurcreds>` command.

**Arguments**

* ``<subreddit>``: The subreddit to get images from.

* ``[count]``: The number of images to return (maximum 5). Defaults to 1.

* ``[sort_type]``: New, or top results. Defaults to top.

* ``[window]``: The timeframe, can be the past day, week, month, year or all. Defaults to day.

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

**Getting your API key**

1. Login (or create) a GIPHY account.
2. Visit `this page <https://developers.giphy.com/dashboard>`__.
3. Press 'Create an App'.
4. Click 'Select API', and then 'Next Step'.
5. Add an app name, for example 'Red'.
6. Add an app description, for example 'Used for Red's image cog'.
7. Click 'Create App'. You'll need to agree to the GIPHY API terms.
8. Copy the API Key.
9. In Discord, run the following command::

        [p]set api GIPHY api_key <your_api_key_here>

.. _image-command-imgurcreds:

^^^^^^^^^^
imgurcreds
^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]imgurcreds

**Description**

Explains how to set Imgur API tokens.

**Getting your API key**

1. Login to (or create) an Imgur account.
2. Visit `this page <https://api.imgur.com/oauth2/addclient>`__.
3. Add an app name for your application, for example 'Red'.
4. Select 'Anonymous usage without user authorization' for the auth type.
5. Set the authorization callback URL to ``https://localhost``
6. Leave the app website blank.
7. Enter a valid email address and a description.
8. Check the captcha box and click next.
9. Your Client ID will be on the next page.
10. In Discord, run the following command::

        [p]set api imgur client_id <your_client_id_here>
