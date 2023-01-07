.. _install-ubuntu-1804:

==================================
Installing Red on Ubuntu 18.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

.. Git 2.17.0-2.22.0 have an issue with partial clone which is used in pip for git installs.
.. Not incredibly important perhaps but this ppa is recommended by git-scm.com/download/linux
.. so it should be fine.

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. prompt:: bash

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:git-core/ppa

We recommend adding the ``deadsnakes`` ppa to install Python 3.11:

.. prompt:: bash

    sudo add-apt-repository -y ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. prompt:: bash

    sudo apt -y install python3.11 python3.11-dev python3.11-venv git openjdk-11-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
