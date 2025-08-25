.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Red Hat Enterprise Linux (RHEL) 10.2-10.x and its derivatives have all required packages available in official repositories.
Install them with dnf:

.. prompt:: bash

    sudo dnf -y install python3.13 python3.13-devel git java-17-openjdk-headless @development nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.13.rst

.. include:: _includes/install-and-setup-red-unix.rst
