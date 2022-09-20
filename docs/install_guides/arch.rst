.. _install-arch:

============================
Installing Red on Arch Linux
============================

.. include:: _includes/supported-arch-x64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Install the pre-requirements with pacman:

.. prompt:: bash

    sudo pacman -Syu python python-pip git jre11-openjdk-headless base-devel nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
