.. _install-ubuntu-non-lts:

=========================================
Installing Red on Ubuntu non-LTS versions
=========================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. prompt:: bash

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -yu ppa:git-core/ppa

Now, to install non-native version of python on non-LTS versions of Ubuntu, we recommend
installing pyenv. To do this, first run the following commands:

.. prompt:: bash

    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre-headless nano
    CXX=/usr/bin/g++

.. Include common instructions:

.. include:: _includes/install-python-pyenv.rst

.. include:: _includes/create-env-with-pyenv-virtualenv.rst

.. include:: _includes/install-and-setup-red-unix.rst
