.. _install-fedora:

==============================
Installing Red on Fedora Linux
==============================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Fedora Linux 41 and above has all required packages available in official repositories. Install
them with dnf:

.. prompt:: bash

    sudo dnf -y install python3.11 python3.11-devel git adoptium-temurin-java-repository @development-tools nano
    sudo dnf config-manager setopt adoptium-temurin-java-repository.enabled=1
    sudo dnf -y install temurin-17-jre

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
