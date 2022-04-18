.. _install-ubuntu-2004:

==================================
Installing Red on Ubuntu 20.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend adding the ``git-core`` ppa to install Git 2.11 or greater:

.. prompt:: bash

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:git-core/ppa

Now install the pre-requirements with apt:

.. prompt:: bash

    sudo apt -y install python3.9 python3.9-dev python3.9-venv python3-pip git openjdk-11-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
