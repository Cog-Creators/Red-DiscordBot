.. _linux-mac-install-guide:

==============================
Installing Red on Linux or Mac
==============================

.. warning::

    For safety reasons, DO NOT install Red with a root user. If you are unsure how to create
    a new user on Linux, see `this guide by DigitalOcean
    <https://www.digitalocean.com/community/tutorials/how-to-create-a-sudo-user-on-ubuntu-quickstart>`_.

-------------------------------
Installing the pre-requirements
-------------------------------

Please install the pre-requirements using the commands listed for your operating system.

The pre-requirements are:
 - Python 3.7.0 or greater
 - pip 9.0 or greater
 - git
 - Java Runtime Environment 8 or later (for audio support)

We also recommend installing some basic compiler tools, in case our dependencies don't provide
pre-built "wheels" for your architecture.

.. _install-arch:

~~~~~~~~~~
Arch Linux
~~~~~~~~~~

.. code-block:: none

    sudo pacman -Syu python python-pip git jre-openjdk-headless base-devel

.. _install-centos:
.. _install-rhel:

~~~~~~~~~~~~~~~~~
CentOS and RHEL 7
~~~~~~~~~~~~~~~~~

.. code-block:: none

    yum -y groupinstall development
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    sudo yum install zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel \
      openssl-devel xz xz-devel libffi-devel findutils git2u java-1.8.0-openjdk

Complete the rest of the installation by `installing Python 3.7 with pyenv <install-python-pyenv>`.

.. _install-debian:
.. _install-raspbian:

~~~~~~~~~~~~~~~~~~~
Debian and Raspbian
~~~~~~~~~~~~~~~~~~~

Debian and Raspbian Buster
**************************

Debian and Raspbian Buster have all required packages available in official repositories. Install
them with apt:

.. code-block:: none

    sudo apt update
    sudo apt install python3 python3-dev python3-venv python3-pip git default-jre-headless \
      build-essential

Debian and Raspbian Stretch
***************************

We recommend installing pyenv as a method of installing non-native versions of python on
Debian/Raspbian Stretch. This guide will tell you how. First, run the following commands:

.. code-block:: none

    sudo apt update
    sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev \
      liblzma-dev python3-openssl git default-jre-headless

Complete the rest of the installation by `installing Python 3.7 with pyenv <install-python-pyenv>`.

.. _install-fedora:

~~~~~~~~~~~~
Fedora Linux
~~~~~~~~~~~~

Fedora Linux 29 and above has all required packages available in official repositories. Install
them with dnf:

.. code-block:: none

    sudo dnf install python3 python3-devel git java-latest-openjdk-headless @development-tools

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
    brew cask install homebrew/cask-versions/adoptopenjdk8

It's possible you will have network issues. If so, go in your Applications folder, inside it, go in
the Python 3.7 folder then double click ``Install certificates.command``.

.. _install-opensuse:

~~~~~~~~
openSUSE
~~~~~~~~

openSUSE Leap
*************

We recommend installing a community package to get Python 3.7 on openSUSE Leap. This package will
be installed to the ``/opt`` directory.

First, add the Opt-Python community repository:

.. code-block:: none

    source /etc/os-release
    sudo zypper ar -f https://download.opensuse.org/repositories/home:/Rotkraut:/Opt-Python/openSUSE_Leap_${VERSION_ID}/ Opt-Python

Now install the pre-requirements with zypper:

.. code-block:: none

    sudo zypper install opt-python37 opt-python37-setuptools git-core java-11-openjdk-headless
    sudo zypper install -t pattern devel_basis

Since Python is now installed to ``/opt/python``, we should add it to PATH. You can add a file in
``/etc/profile.d/`` to do this:

.. code-block:: none

    echo 'export PATH="/opt/python/bin:$PATH"' | sudo tee /etc/profile.d/opt-python.sh
    source /etc/profile.d/opt-python.sh

Now, install pip with easy_install:

.. code-block:: none

    sudo /opt/python/bin/easy_install-3.7 pip

openSUSE Tumbleweed
*******************

openSUSE Tumbleweed has all required dependencies available in official repositories. Install them
with zypper:

.. code-block:: none

    sudo zypper install python3-base python3-pip git-core java-12-openjdk-headless
    sudo zypper install -t pattern devel_basis

.. _install-ubuntu:

~~~~~~
Ubuntu
~~~~~~

.. note:: **Ubuntu 16.04 Users**

    You must add a 3rd-party repository to install Python 3.7 on Ubuntu 16.04 with apt. We
    recommend the ``deadsnakes`` repository:

    .. code-block:: none

        sudo apt install software-properties-common
        sudo add-apt-repository ppa:deadsnakes/ppa

Install the pre-requirements with apt:

.. code-block:: none

    sudo apt update
    sudo apt install python3.7 python3.7-dev python3.7-venv python3-pip git default-jre-headless \
      build-essential

.. _install-python-pyenv:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Installing Python with pyenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    If you followed one of the sections above, and weren't linked here afterwards, you should skip
    this section.

On distributions where Python 3.7 needs to be compiled from source, we recommend the use of pyenv.
This simplifies the compilation process and has the added bonus of simplifying setting up Red in a
virtual environment.

.. code-block:: none

    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

After this command, you may see a warning about 'pyenv' not being in the load path. Follow the
instructions given to fix that, then close and reopen your shell.

Then run the following command:

.. code-block:: none

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.7.4 -v

This may take a long time to complete, depending on your hardware. For some machines (such as
Raspberry Pis and micro-tier VPSes), it may take over an hour; in this case, you may wish to remove
the ``CONFIGURE_OPTS=--enable-optimizations`` part from the front of the command, which will
drastically reduce the install time. However, be aware that this will make Python run about 10%
slower.

After that is finished, run:

.. code-block:: none

    pyenv global 3.7.4

Pyenv is now installed and your system should be configured to run Python 3.7.

------------------------------
Creating a Virtual Environment
------------------------------

We **strongly** recommend installing Red into a virtual environment. Don't be scared, it's very
straightforward. See the section `installing-in-virtual-environment`.

.. _installing-red-linux-mac:

--------------
Installing Red
--------------

Choose one of the following commands to install Red.

.. note::

    If you're not inside an activated virtual environment, include the ``--user`` flag with all
    ``python3.7 -m pip install`` commands, like this:

    .. code-block:: none

        python3.7 -m pip install --user -U Red-DiscordBot

To install without MongoDB support:

.. code-block:: none

    python3.7 -m pip install -U Red-DiscordBot

Or, to install with MongoDB support:

.. code-block:: none

    python3.7 -m pip install -U Red-DiscordBot[mongo]

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
You can find out how to obtain a token with
`this guide <https://discordpy.readthedocs.io/en/v1.0.1/discord.html#creating-a-bot-account>`_,
section "Creating a Bot Account".

You may also run Red via the launcher, which allows you to restart the bot
from discord, and enable auto-restart. You may also update the bot from the
launcher menu. Use the following command to run the launcher:

.. code-block:: none

    redbot-launcher

