.. _install-raspberry-pi-os-11:

=============================================
Installing Red on Raspberry Pi OS 11 Bullseye
=============================================

.. include:: _includes/supported-arch-aarch64+armv7l.rst

.. note::

    This guide can only be used with Raspberry Pi OS 11 Bullseye,
    it will not work with any older (e.g. Raspberry Pi OS 10 Buster)
    or newer (e.g. Raspberry Pi OS 12 Bookworm) releases.
    You can check your version of Raspberry Pi OS by running:

    .. prompt:: bash

        lsb_release -a

    If you're not running Bullseye, you should read
    `the post about Bullseye release from Raspberry Pi Foundation <https://www.raspberrypi.com/news/raspberry-pi-os-debian-bullseye/>`__
    to learn how you can install/upgrade to the new version.

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Raspberry Pi OS "Bullseye" has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3 python3-dev python3-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.9.rst

.. include:: _includes/install-and-setup-red-unix.rst
