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
 - Python 3.8.1 or greater
 - Pip 18.1 or greater
 - Git
 - Java Runtime Environment 11 or later (for audio support)

We also recommend installing some basic compiler tools, in case our dependencies don't provide
pre-built "wheels" for your architecture.


*****************
Operating systems
*****************

.. contents::
    :local:

----

.. _install-arch:

~~~~~~~~~~
Arch Linux
~~~~~~~~~~

.. code-block:: none

    sudo pacman -Syu python python-pip git jre-openjdk-headless base-devel

Continue by `creating-venv-linux`.

----

.. _install-centos:
.. _install-rhel:

~~~~~~~~~~~~~~~~~
CentOS and RHEL 7
~~~~~~~~~~~~~~~~~

.. code-block:: none

    yum -y groupinstall development
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    sudo yum -y install zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel \
      openssl-devel xz xz-devel libffi-devel findutils git2u java-11-openjdk

Complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

----

.. _install-debian-stretch:

~~~~~~~~~~~~~~
Debian Stretch
~~~~~~~~~~~~~~

.. note::

    This guide is only for Debian Stretch users, these instructions won't work with
    Raspbian Stretch. Raspbian Buster is the only version of Raspbian supported by Red.

We recommend installing pyenv as a method of installing non-native versions of python on
Debian Stretch. This guide will tell you how. First, run the following commands:

.. code-block:: none

    sudo echo "deb http://deb.debian.org/debian stretch-backports main" >> /etc/apt/sources.list.d/red-sources.list
    sudo apt update
    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev \
      libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre
    CXX=/usr/bin/g++

Complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

----

.. _install-debian:
.. _install-raspbian:

~~~~~~~~~~~~~~~~~~~~~~~~~~
Debian and Raspbian Buster
~~~~~~~~~~~~~~~~~~~~~~~~~~

We recommend installing pyenv as a method of installing non-native versions of python on
Debian/Raspbian Buster. This guide will tell you how. First, run the following commands:

.. code-block:: none

    sudo apt update
    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev \
      libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre
    CXX=/usr/bin/g++

Complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

----

.. _install-fedora:

~~~~~~~~~~~~
Fedora Linux
~~~~~~~~~~~~

Fedora Linux 30 and above has all required packages available in official repositories. Install
them with dnf:

.. code-block:: none

    sudo dnf -y install python38 git java-latest-openjdk-headless @development-tools

Continue by `creating-venv-linux`.

----

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
    brew cask install homebrew/cask-versions/adoptopenjdk11

It's possible you will have network issues. If so, go in your Applications folder, inside it, go in
the Python 3.8 folder then double click ``Install certificates.command``.

Continue by `creating-venv-linux`.

----

.. _install-opensuse:

~~~~~~~~
openSUSE
~~~~~~~~

openSUSE Leap
*************

We recommend installing a community package to get Python 3.8 on openSUSE Leap. This package will
be installed to the ``/opt`` directory.

First, add the Opt-Python community repository:

.. code-block:: none

    source /etc/os-release
    sudo zypper ar -f https://download.opensuse.org/repositories/home:/Rotkraut:/Opt-Python/openSUSE_Leap_${VERSION_ID}/ Opt-Python

Now install the pre-requirements with zypper:

.. code-block:: none

    sudo zypper install opt-python38 opt-python38-setuptools git-core java-11-openjdk-headless
    sudo zypper install -t pattern devel_basis

Since Python is now installed to ``/opt/python``, we should add it to PATH. You can add a file in
``/etc/profile.d/`` to do this:

.. code-block:: none

    echo 'export PATH="/opt/python/bin:$PATH"' | sudo tee /etc/profile.d/opt-python.sh
    source /etc/profile.d/opt-python.sh

Now, install pip with easy_install:

.. code-block:: none

    sudo /opt/python/bin/easy_install-3.8 pip

Continue by `creating-venv-linux`.

openSUSE Tumbleweed
*******************

openSUSE Tumbleweed has all required dependencies available in official repositories. Install them
with zypper:

.. code-block:: none

    sudo zypper install python3-base python3-pip git-core java-12-openjdk-headless
    sudo zypper install -t pattern devel_basis

Continue by `creating-venv-linux`.

----

.. _install-ubuntu:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu LTS versions (18.04 and 16.04)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We recommend adding the ``deadsnakes`` ppa to install Python 3.8.1 or greater:

.. code-block:: none

    sudo apt update
    sudo apt install software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. code-block:: none

    sudo apt -y install python3.8 python3.8-dev python3.8-venv python3-pip git default-jre-headless \
      build-essential

Continue by `creating-venv-linux`.

----

.. _install-ubuntu-non-lts:

~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu non-LTS versions
~~~~~~~~~~~~~~~~~~~~~~~

We recommend installing pyenv as a method of installing non-native versions of python on
non-LTS versions of Ubuntu. This guide will tell you how. First, run the following commands:

.. code-block:: none

    sudo apt update
    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev \
      libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre
    CXX=/usr/bin/g++

Complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

----

.. _install-python-pyenv:

****************************
Installing Python with pyenv
****************************

.. note::

    If you followed one of the sections above, and weren't linked here afterwards, you should skip
    this section.

On distributions where Python 3.8 needs to be compiled from source, we recommend the use of pyenv.
This simplifies the compilation process and has the added bonus of simplifying setting up Red in a
virtual environment.

.. code-block:: none

    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

After this command, you may see a warning about 'pyenv' not being in the load path. Follow the
instructions given to fix that, then close and reopen your shell.

Then run the following command:

.. code-block:: none

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.8.1 -v

This may take a long time to complete, depending on your hardware. For some machines (such as
Raspberry Pis and micro-tier VPSes), it may take over an hour; in this case, you may wish to remove
the ``CONFIGURE_OPTS=--enable-optimizations`` part from the front of the command, which will
drastically reduce the install time. However, be aware that this will make Python run about 10%
slower.

After that is finished, run:

.. code-block:: none

    pyenv global 3.8.1

Pyenv is now installed and your system should be configured to run Python 3.8.

.. _creating-venv-linux:

------------------------------
Creating a Virtual Environment
------------------------------

We require installing Red into a virtual environment. Don't be scared, it's very
straightforward. See the section `installing-in-virtual-environment`.

.. _installing-red-linux-mac:

--------------
Installing Red
--------------

Choose one of the following commands to install Red.

To install without additional config backend support:

.. code-block:: none

    python -m pip install -U pip setuptools wheel
    python -m pip install -U Red-DiscordBot

Or, to install with PostgreSQL support:

.. code-block:: none

    python -m pip install -U pip setuptools wheel
    python -m pip install -U Red-DiscordBot[postgres]


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
:dpy_docs:`this guide <discord.html#creating-a-bot-account>`,
section "Creating a Bot Account".

.. tip::
   If it's the first time you're using Red, you should check our `getting-started` guide
   that will walk you through all essential information on how to interact with Red.
