.. _install-debian-10:

==================================
Installing Red on Debian 10 Buster
==================================

.. include:: _includes/supported-arch-x64+aarch64+armv7l.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend installing pyenv as a method of installing non-native versions of Python on
Debian Buster. This guide will tell you how. First, run the following commands:

.. prompt:: bash

    sudo apt update
    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre-headless nano
    CXX=/usr/bin/g++

.. Include common instructions:

.. include:: _includes/install-python-pyenv.rst

.. include:: _includes/create-env-with-pyenv-virtualenv.rst

.. include:: _includes/install-and-setup-red-unix.rst
