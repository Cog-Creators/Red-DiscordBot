.. _install-fedora:

==============================
Installing Red on Fedora Linux
==============================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Fedora Linux 35 and above has all required packages available in official repositories. Install
them with dnf:

.. prompt:: bash

    sudo dnf -y install python39 git java-11-openjdk-headless @development-tools nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
