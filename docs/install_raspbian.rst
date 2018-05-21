.. raspbian install guide

==================================
Installing Red on Raspbian Stretch
==================================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <https://www.raspberrypi.org/documentation/linux/usage/users.md>`_.

---------------------------
Installing pre-requirements
---------------------------

.. code-block:: none

    sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev git unzip default-jre
    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

After that last command, you may see a warning about 'pyenv' not being in the load path. Follow the instructions given to fix that, then close and reopen your shell

Then run the following command:

.. code-block:: none

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.6.5 -v

This may take a long time to complete.

After that is finished, run:

.. code-block:: none

    pyenv global 3.6.5

--------------
Installing Red
--------------

Without audio:

:code:`pip3 install -U --process-dependency-links red-discordbot --user`

With audio:

:code:`pip3 install -U --process-dependency-links red-discordbot[voice] --user`

To install the development version (without audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot --user`

To install the development version (with audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[voice] --user`

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
