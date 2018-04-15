.. raspbian install guide

==================================
Installing Red on Raspbian Stretch
==================================

---------------------------
Installing pre-requirements
---------------------------

.. code-block:: none

    sudo apt-get install python3.5-dev python3-pip build-essential libssl-dev libffi-dev git unzip default-jre -y


--------------
Installing Red
--------------

Without audio:

:code:`pip3 install -U --process-dependency-links red-discordbot`

With audio:

:code:`pip3 install -U --process-dependency-links red-discordbot[voice]`

To install the development version (without audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot`

To install the development version (with audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[voice]`

----------------------
Setting up an instance
----------------------

Run :code:`redbot-setup` and follow the prompts. It will ask first for where you want to
store the data (the default is :code:`~/.local/share/Red-DiscordBot`) and will then ask
for confirmation of that selection. Next, it will ask you to choose your storage backend
(the default here is JSON). It will then ask for a name for your instance. This can be
anything as long as it does not contain spaces; however, keep in mind that this is the
name you will use to run your bot, and so it should be something you can remember.

-----------
Running Red
-----------

Run :code:`redbot <your instance name>` and run through the initial setup. This will ask for
your token and a prefix.

.. warning:: Audio will not work on Raspberry Pi's **below** 2B. This is a CPU problem and *cannot* be fixed.