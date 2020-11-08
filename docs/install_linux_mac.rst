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
 - Python 3.8.1 or greater; **Python 3.9 is currently not supported!**
 - Pip 18.1 or greater
 - Git 2.11+
 - Java Runtime Environment 11 (for audio support)

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

    sudo pacman -Syu python python-pip git jre11-openjdk-headless base-devel

Continue by `creating-venv-linux`.

----

.. _install-centos7:
.. _install-rhel7:

~~~~~~~~~~~~~~~~~
CentOS and RHEL 7
~~~~~~~~~~~~~~~~~

.. code-block:: none

    sudo yum -y groupinstall development
    sudo yum -y install zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel xz xz-devel tk-devel libffi-devel findutils java-11-openjdk-headless
    sudo yum -y install centos-release-scl
    sudo yum -y install devtoolset-8-gcc devtoolset-8-gcc-c++
    echo "source scl_source enable devtoolset-8" >> ~/.bashrc
    source ~/.bashrc

In order to install Git 2.11 or greater, we recommend adding the IUS repository:

.. code-block:: none

    sudo yum -y install https://repo.ius.io/ius-release-el7.rpm
    sudo yum -y swap git git224

Complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

----

.. _install-centos:
.. _install-rhel:

~~~~~~~~~~~~~~~~~
CentOS and RHEL 8
~~~~~~~~~~~~~~~~~

.. code-block:: none

    sudo yum -y install epel-release
    sudo yum -y update
    sudo yum -y groupinstall development
    sudo yum -y install git zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel xz xz-devel tk-devel libffi-devel findutils java-11-openjdk-headless

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
    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre-headless
    CXX=/usr/bin/g++

Complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

----

.. _install-fedora:

~~~~~~~~~~~~
Fedora Linux
~~~~~~~~~~~~

Fedora Linux 31 and above has all required packages available in official repositories. Install
them with dnf:

.. code-block:: none

    sudo dnf -y install python38 git java-11-openjdk-headless @development-tools

Continue by `creating-venv-linux`.

----

.. _install-mac:

~~~
Mac
~~~

Install Brew: in Finder or Spotlight, search for and open *Terminal*. In the terminal, paste the
following, then press Enter:

.. code-block:: none

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

After the installation, install the required packages by pasting the commands and pressing enter,
one-by-one:

.. code-block:: none

    brew install python@3.8
    echo 'export PATH="/usr/local/opt/python@3.8/bin:$PATH"' >> ~/.profile
    source ~/.profile
    brew install git
    brew cask install adoptopenjdk/openjdk/adoptopenjdk11

Continue by `creating-venv-linux`.

----

.. _install-opensuse:

~~~~~~~~
openSUSE
~~~~~~~~

openSUSE Leap 15.1+
*******************

We recommend installing a community package to get Python 3.8 on openSUSE Leap 15.1+. This package will
be installed to the ``/opt`` directory.

First, add the Opt-Python community repository:

.. code-block:: none

    source /etc/os-release
    sudo zypper -n ar -f https://download.opensuse.org/repositories/home:/Rotkraut:/Opt-Python/openSUSE_Leap_${VERSION_ID}/ Opt-Python
    sudo zypper -n --gpg-auto-import-keys ref

Now install the pre-requirements with zypper:

.. code-block:: none

    sudo zypper -n install opt-python38 opt-python38-setuptools git-core java-11-openjdk-headless
    sudo zypper -n install -t pattern devel_basis

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

    sudo zypper -n install python3-base python3-pip git-core java-11-openjdk-headless
    sudo zypper -n install -t pattern devel_basis

Continue by `creating-venv-linux`.

----

.. _install-ubuntu-1604:

~~~~~~~~~~~~~~~~
Ubuntu 16.04 LTS
~~~~~~~~~~~~~~~~

We recommend adding the ``openjdk-r`` ppa to install Java 11:

.. code-block:: none

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -yu ppa:openjdk-r/ppa

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. code-block:: none

    sudo add-apt-repository -yu ppa:git-core/ppa

We recommend adding the ``deadsnakes`` ppa to install Python 3.8.1 or greater:

.. code-block:: none

    sudo add-apt-repository -yu ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. code-block:: none

    sudo apt -y install python3.8 python3.8-dev python3.8-venv python3-pip git openjdk-11-jre-headless build-essential

Continue by `creating-venv-linux`.

----

.. _install-ubuntu-1804:

~~~~~~~~~~~~~~~~
Ubuntu 18.04 LTS
~~~~~~~~~~~~~~~~

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. code-block:: none

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:git-core/ppa

We recommend adding the ``deadsnakes`` ppa to install Python 3.8.1 or greater:

.. code-block:: none

    sudo add-apt-repository -y ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. code-block:: none

    sudo apt -y install python3.8 python3.8-dev python3.8-venv python3-pip git openjdk-11-jre-headless build-essential

Continue by `creating-venv-linux`.

----

.. _install-ubuntu:

~~~~~~~~~~~~~~~~
Ubuntu 20.04 LTS
~~~~~~~~~~~~~~~~

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. code-block:: none

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:git-core/ppa

Now install the pre-requirements with apt:

.. code-block:: none

    sudo apt -y install python3.8 python3.8-dev python3.8-venv python3-pip git openjdk-11-jre-headless build-essential

Continue by `creating-venv-linux`.

----

.. _install-ubuntu-non-lts:

~~~~~~~~~~~~~~~~~~~~~~~
Ubuntu non-LTS versions
~~~~~~~~~~~~~~~~~~~~~~~

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. code-block:: none

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -yu ppa:git-core/ppa

Now, to install non-native version of python on non-LTS versions of Ubuntu, we recommend
installing pyenv. To do this, first run the following commands:

.. code-block:: none

    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre-headless
    CXX=/usr/bin/g++

And then complete the rest of the installation by `installing Python 3.8 with pyenv <install-python-pyenv>`.

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

    command -v pyenv && pyenv update || curl https://pyenv.run | bash

**After this command, you may see a warning about 'pyenv' not being in the load path. Follow the
instructions given to fix that, then close and reopen your shell.**

Then run the following command:

.. code-block:: none

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.8.6 -v

This may take a long time to complete, depending on your hardware. For some machines (such as
Raspberry Pis and micro-tier VPSes), it may take over an hour; in this case, you may wish to remove
the ``CONFIGURE_OPTS=--enable-optimizations`` part from the front of the command, which will
drastically reduce the install time. However, be aware that this will make Python run about 10%
slower.

After that is finished, run:

.. code-block:: none

    pyenv global 3.8.6

Pyenv is now installed and your system should be configured to run Python 3.8.

Continue by `creating-venv-linux`.

.. _creating-venv-linux:

------------------------------
Creating a Virtual Environment
------------------------------

.. tip::

    If you want to learn more about virtual environments, see page: `about-venvs`

We require installing Red into a virtual environment. Don't be scared, it's very
straightforward.

You have 2 options:

* :ref:`using-venv` (quick and easy, involves just two commands)
* :ref:`using-pyenv-virtualenv` (only available and recommended when you installed Python with pyenv)

----

.. _using-venv:

**************
Using ``venv``
**************
This is the quickest way to get your virtual environment up and running, as `venv` is shipped with
python.

First, choose a directory where you would like to create your virtual environment. It's a good idea
to keep it in a location which is easy to type out the path to. From now, we'll call it
``redenv`` and it will be located in your home directory.

Create your virtual environment with the following command::

    python3.8 -m venv ~/redenv

And activate it with the following command::

    source ~/redenv/bin/activate

.. important::

    You must activate the virtual environment with the above command every time you open a new
    shell to run, install or update Red.

Continue by `installing-red-linux-mac`.

----

.. _using-pyenv-virtualenv:

**************************
Using ``pyenv virtualenv``
**************************

Using ``pyenv virtualenv`` saves you the headache of remembering where you installed your virtual
environments. This option is only available if you installed Python with pyenv.

First, ensure your pyenv interpreter is set to python 3.8.1 or greater with the following command::

    pyenv version

Now, create a virtual environment with the following command::

    pyenv virtualenv <name>

Replace ``<name>`` with whatever you like. If you ever forget what you named it,
you can always use the command ``pyenv versions`` to list all virtual environments.

Now activate your virtualenv with the following command::

    pyenv shell <name>

.. important::

    You must activate the virtual environment with the above command every time you open a new
    shell to run, install or update Red. You can check out other commands like ``pyenv local`` and
    ``pyenv global`` if you wish to keep the virtualenv activated all the time.

Continue by `installing-red-linux-mac`.

.. _pyenv-installer: https://github.com/pyenv/pyenv-installer/blob/master/README.rst

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


.. note::

    These commands are also used for updating Red

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
`this guide <bot_application_guide>`.

.. tip::
   If it's the first time you're using Red, you should check our `getting-started` guide
   that will walk you through all essential information on how to interact with Red.
