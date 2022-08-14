.. _install-opensuse-leap-15:

=====================================
Installing Red on openSUSE Leap 15.3+
=====================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

openSUSE Leap 15.3+ has all required dependencies available in official repositories. Install them
with zypper:

.. prompt:: bash

    sudo zypper -n install python39-base python39-pip git-core java-11-openjdk-headless nano
    sudo zypper -n install -t pattern devel_basis

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
