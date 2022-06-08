.. _install-raspberry-pi-os-10:

====================================================
Installing Red on Raspberry Pi OS (Legacy) 10 Buster
====================================================

.. include:: _includes/supported-arch-armv7l.rst

.. note::

    While we do provide support and install instructions for running Red
    on Raspberry Pi OS (Legacy) 10 Buster, we highly recommend installing/upgrading to
    the new version - Raspberry Pi OS 11 Bullseye.

    If you're not sure what version you are using,
    you can check your version of Raspberry Pi OS by running:

    .. prompt:: bash

        lsb_release -a

    If you're running Bullseye already, read `install-raspberry-pi-os-11` document instead.

    If you're using Buster, please consider upgrading to Bullseye if possible.
    You can read
    `the post about Bullseye release from Raspberry Pi Foundation <https://www.raspberrypi.com/news/raspberry-pi-os-debian-bullseye/>`__
    to learn how you can install/upgrade to the new version.

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend installing pyenv as a method of installing non-native versions of Python on
Raspberry Pi OS. This guide will tell you how. First, run the following commands:

.. prompt:: bash

    sudo apt update
    sudo apt -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev libgdbm-dev uuid-dev python3-openssl git openjdk-11-jre-headless nano
    CXX=/usr/bin/g++

.. Include common instructions:

.. include:: _includes/install-python38-pyenv.rst

.. include:: _includes/create-env-with-pyenv-virtualenv.rst

.. include:: _includes/install-and-setup-red-unix.rst
