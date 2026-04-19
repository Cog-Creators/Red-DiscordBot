.. _install-opensuse-tumbleweed:

=====================================
Installing Red on openSUSE Tumbleweed
=====================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

openSUSE Tumbleweed has all required dependencies available in official repositories. Install them
with zypper:

.. prompt:: bash

    sudo zypper -n install python314 python314-devel git-core java-17-openjdk-headless nano
    sudo zypper -n install -t pattern devel_basis

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.14.rst

.. include:: _includes/install-and-setup-red-unix.rst
