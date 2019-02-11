.. _linux-mac-install-guide:

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
 - Python 3.7.0 or greater
 - pip 9.0 or greater
 - git
 - Java Runtime Environment 8 or later (for audio support)

.. _install-arch:

~~~~~~~~~~
Arch Linux
~~~~~~~~~~

.. code-block:: none

    sudo pacman -Syu python-pip git base-devel jre8-openjdk

.. _install-centos:
.. _install-fedora:
.. _install-rhel:

~~~~~~~~~~~~~~~~~~~~~~~~~~
CentOS 7, Fedora, and RHEL
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

    yum -y groupinstall development
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    sudo yum install zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel \
    openssl-devel xz xz-devel libffi-devel git2u java-1.8.0-openjdk

Complete the rest of the installation by `installing Python 3.7 with pyenv <install-python-pyenv>`.

.. _install-debian:
.. _install-raspbian:

~~~~~~~~~~~~~~~~~~~~~~~~~~~
Debian and Raspbian Stretch
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    Audio will not work on Raspberry Pi's **below** 2B. This is a CPU problem and
    *cannot* be fixed.

We recommend installing pyenv as a method of installing non-native versions of python on
Debian/Raspbian Stretch. This guide will tell you how. First, run the following commands:

.. code-block:: none

    sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git unzip default-jre

Complete the rest of the installation by `installing Python 3.7 with pyenv <install-python-pyenv>`.

.. _install-mac:

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

    brew install python --with-brewed-openssl
    brew install git
    brew tap caskroom/versions
    brew cask install java8

It's possible you will have network issues. If so, go in your Applications folder, inside it, go in the Python 3.7 folder then double click ``Install certificates.command``

.. _install-ubuntu:
.. _install-ubuntu-bionic:
.. _install-ubuntu-cosmic:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu 18.04 Bionic Beaver and 18.10 Cosmic Cuttlefish
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

    sudo apt install python3.7 python3.7-dev python3.7-venv python3-pip build-essential \
    libssl-dev libffi-dev git unzip default-jre -y

.. _install-ubuntu-xenial:

~~~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu 16.04 Xenial Xerus
~~~~~~~~~~~~~~~~~~~~~~~~~

We recommend adding the ``deadsnakes`` apt repository to install Python 3.7 or greater:

.. code-block:: none

    sudo apt install software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update

Now, install python, pip, git and java with the following commands:

.. code-block:: none

    sudo apt install python3.7 python3.7-dev build-essential libssl-dev libffi-dev git \
    unzip default-jre curl -y
    curl https://bootstrap.pypa.io/get-pip.py | sudo python3.7

.. _install-python-pyenv:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Installing Python with pyenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On distributions where Python 3.7 needs to be compiled from source, we recommend the use of pyenv.
This simplifies the compilation process and has the added bonus of simplifying setting up Red in a
virtual environment.

.. code-block:: none

    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

After this command, you may see a warning about 'pyenv' not being in the load path. Follow the
instructions given to fix that, then close and reopen your shell.

Then run the following command:

.. code-block:: none

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.7.2 -v

This may take a long time to complete, depending on your hardware. For some machines (such as
Raspberry Pis and micro-tier VPSes), it may take over an hour; in this case, you may wish to remove
the ``CONFIGURE_OPTS=--enable-optimizations`` part from the front of the command, which will
drastically reduce the install time. However, be aware that this will make Python run about 10%
slower.

After that is finished, run:

.. code-block:: none

    pyenv global 3.7.2

Pyenv is now installed and your system should be configured to run Python 3.7.

------------------------------
Creating a Virtual Environment
------------------------------

We **strongly** recommend installing Red into a virtual environment. See the section
`installing-in-virtual-environment`.

.. _installing-red-linux-mac:

--------------
Installing Red
--------------

Choose one of the following commands to install Red.

.. note::

    If you're not inside an activated virtual environment, include the ``--user`` flag with all
    ``python3.7 -m pip`` commands.

To install without audio support:

.. code-block:: none

    python3.7 -m pip install -U Red-DiscordBot

Or, to install with audio support:

.. code-block:: none

    python3.7 -m pip install -U Red-DiscordBot[voice]

Or, install with audio and MongoDB support:

.. code-block:: none

    python3.7 -m pip install -U Red-DiscordBot[voice,mongo]

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
running the bot).

Once done setting up the instance, run the following command to run Red:

.. code-block:: none

    redbot <your instance name>

It will walk through the initial setup, asking for your token and a prefix.

You may also run Red via the launcher, which allows you to restart the bot
from discord, and enable auto-restart. You may also update the bot from the
launcher menu. Use the following command to run the launcher:

.. code-block:: none

    redbot-launcher

