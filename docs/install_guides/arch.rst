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

    sudo pacman -Syu git jre17-openjdk-headless base-devel nano

On Arch Linux, Python 3.13 can be installed from the Arch User Repository (AUR) from the ``python313`` package.

The manual build process is the Arch-supported install method for AUR packages. You can install ``python313`` package with the following commands:

.. prompt:: bash

    git clone https://aur.archlinux.org/python313.git /tmp/python313
    cd /tmp/python313
    makepkg -sicL
    cd -
    rm -rf /tmp/python313

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.13.rst

.. include:: _includes/install-and-setup-red-unix.rst
