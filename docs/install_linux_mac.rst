.. _linux-install-guide:

==============================
Installing Red on Linux or Mac
==============================

.. warning::

    For safety reasons, DO NOT install Red with a root user. If you are unsure how to create
    a new user, see the man page for the ``useradd`` command.

-------------------------------
Installing the pre-requirements
-------------------------------

Please install the pre-requirements using the commands listed for your operating system.

The pre-requirements are:
 - Python 3.6 or greater
 - pip 9.0 or greater
 - git
 - Java Runtime Environment 8 or later (for audio support)

~~~~~~~~~~
Arch Linux
~~~~~~~~~~

.. code-block:: none

    sudo pacman -Syu python-pip git base-devel jre8-openjdk

~~~~~~~~
CentOS 7
~~~~~~~~

.. code-block:: none

    yum -y groupinstall development
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    yum -y install yum-utils wget which python36u python36u-pip python36u-devel openssl-devel libffi-devel git java-1.8.0-openjdk

~~~~~~~~~~~~~~~~~~~~~~~~~~~
Debian and Raspbian Stretch
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    Audio will not work on Raspberry Pi's **below** 2B. This is a CPU problem and
    *cannot* be fixed.

We recommend installing pyenv as a method of installing non-native versions of python on
Debian/Raspbian Stretch. This guide will tell you how. First, run the following commands:

.. code-block:: none

    sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev git unzip default-jre
    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

After that last command, you may see a warning about 'pyenv' not being in the load path. Follow the
instructions given to fix that, then close and reopen your shell.

Then run the following command:

.. code-block:: none

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.7.0 -v

This may take a long time to complete.

After that is finished, run:

.. code-block:: none

    pyenv global 3.7.0

Pyenv is now installed and your system should be configured to run Python 3.7.

~~~
Mac
~~~

Install Brew: in Finder or Spotlight, search for and open *Terminal*. In the terminal, paste the
following, then press Enter:

.. code-block:: none

    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

After the installation, install the required packages by pasting the commands and pressing enter,
one-by-one:

.. code-block:: none

    brew install python3 --with-brewed-openssl
    brew install git
    brew tap caskroom/versions
    brew cask install java8

~~~~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu 18.04 Bionic Beaver
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

    sudo apt install python3.6-dev python3-pip build-essential libssl-dev libffi-dev git unzip default-jre -y

~~~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu 16.04 Xenial Xerus
~~~~~~~~~~~~~~~~~~~~~~~~~

We recommend adding the ``deadsnakes`` apt repository to install Python 3.6 or greater:

.. code-block:: none

    sudo apt install software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update

Now, install python, pip, git and java with the following commands:

.. code-block:: none

    sudo apt install python3.6-dev build-essential libssl-dev libffi-dev git unzip default-jre wget -y
    wget https://bootstrap.pypa.io/get-pip.py
    sudo python3.6 get-pip.py

------------------------------
Creating a virtual environment
------------------------------

We **strongly** recommend installing Red into a virtual environment. See the section
`installing-in-virtual-environment`.

------------------
Installing the bot
------------------

Choose one of the following commands to install Red.

.. note::

    If you're not inside an activated virtual environment, include the ``--user`` flag with all
    ``pip3`` commands.

To install without audio support:

.. code-block:: none

    pip3 install -U --process-dependency-links --no-cache-dir Red-DiscordBot

Or, to install with audio support:

.. code-block:: none

    pip3 install -U --process-dependency-links --no-cache-dir Red-DiscordBot[voice]

Or, install with audio and MongoDB support:

.. code-block:: none

    pip3 install -U --process-dependency-links --no-cache-dir Red-DiscordBot[voice,mongo]

.. note::

  To install the development version, replace ``Red-DiscordBot`` in the above commands with the
  following link:

  .. code-block:: none

      git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=Red-DiscordBot

--------------------------
Setting Up and Running Red
--------------------------

After installation, set up your instance with the following command:

.. code-block:: none

    redbot-setup

This will set the location where data will be stored, as well as your
storage backend and the name of the instance (which will be used for
running the bot)

Once done setting up the instance, run the following command to run Red:

.. code-block:: none

    redbot <your instance name>

It will walk through the initial setup, asking for your token and a prefix.
