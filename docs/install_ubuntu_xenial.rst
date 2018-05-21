.. ubuntu xenial install guide

==============================
Installing Red on Ubuntu 16.04
==============================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <http://manpages.ubuntu.com/manpages/artful/man8/adduser.8.html>`_.

-------------------------------
Installing the pre-requirements
-------------------------------

.. code-block:: none
    sudo apt install software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install python3.6-dev build-essential libssl-dev libffi-dev git unzip default-jre wget -y
    wget https://bootstrap.pypa.io/get-pip.py
    sudo python3.6 get-pip.py


------------------
Installing the bot
------------------

To install without audio:

:code:`pip3.6 install -U --process-dependency-links red-discordbot --user`

To install with audio:

:code:`pip3.6 install -U --process-dependency-links red-discordbot[voice] --user`

To install the development version (without audio):

:code:`pip3.6 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot --user`

To install the development version (with audio):

:code:`pip3.6 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[voice] --user`

------------------------
Setting up your instance
------------------------

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
