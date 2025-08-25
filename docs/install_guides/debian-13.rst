.. _install-debian-13:

==================================
Installing Red on Debian 13 Trixie
==================================

.. include:: _includes/supported-arch-x64+aarch64+armv7l.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Debian 13 "Trixie" has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3 python3-dev python3-venv git openjdk-21-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.13.rst

.. include:: _includes/install-and-setup-red-unix.rst
