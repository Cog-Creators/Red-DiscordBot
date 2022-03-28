--------------
Installing Blue
--------------

Choose one of the following commands to install Blue.

To install without additional config backend support:

.. prompt:: bash
    :prompts: (redenv) $

    python -m pip install -U pip setuptools wheel
    python -m pip install -U Blue-DiscordBot

Or, to install with PostgreSQL support:

.. prompt:: bash
    :prompts: (redenv) $

    python -m pip install -U pip setuptools wheel
    python -m pip install -U "Blue-DiscordBot[postgres]"


--------------------------
Setting Up and Running Blue
--------------------------

After installation, set up your instance with the following command:

.. prompt:: bash
    :prompts: (redenv) $

    bluebot-setup

This will set the location where data will be stored, as well as your
storage backend and the name of the instance (which will be used for
running the bot).

Once done setting up the instance, run the following command to run Blue:

.. prompt:: bash
    :prompts: (redenv) $

    bluebot <your instance name>

It will walk through the initial setup, asking for your token and a prefix.
You can find out how to obtain a token with
`this guide <../bot_application_guide>`.

.. tip::
   If it's the first time you're using Blue, you should check our `getting-started` guide
   that will walk you through all essential information on how to interact with Blue.
