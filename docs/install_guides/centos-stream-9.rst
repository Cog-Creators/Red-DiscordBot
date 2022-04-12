.. _install-centos-stream-9:

=================================
Installing Red on CentOS Stream 9
=================================

CentOS Stream 9 has all required packages available in official repositories.
Install them with dnf:

.. prompt:: bash

    sudo dnf -y install python39 git java-11-openjdk-headless @development nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
