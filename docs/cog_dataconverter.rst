.. Importing data from a V2 install

================================
Importing data from a V2 install
================================

----------------
What you'll need
----------------

1. A Running V3 bot
2. The path where your V2 bot is installed

--------------
Importing data
--------------

.. important::

    Unless otherwise specified, the V2 data will take priority over V3 data for the same entires

.. important::

    For the purposes of this guide, your prefix will be denoted as 
    [p]

    You should swap whatever you made your prefix in for this.
    All of the below are commands to be entered in discord where the bot can
    see them.

The dataconverter cog is not loaded by default. To start, load it with

.. code-block:: none

    [p]load dataconverter

Next, you'll need to give it the path where your V2 install is.

On linux and OSX, it may look something like:

.. code-block:: none

    /home/username/Red-DiscordBot/

On Windows it will look something like:

.. code-block:: none

    C:\Users\yourusername\Red-DiscordBot

Once you have that path, give it to the bot with the following command
(make sure to swap your own path in)

.. code-block:: none

    [p]convertdata /home/username/Red-DiscordBot/


From here, if the path is correct, you will be prompted with an interactive menu asking you
what data you would like to import

You can select an entry by number, or quit with any of 'quit', 'exit', 'q', '-1', or 'cancel'
