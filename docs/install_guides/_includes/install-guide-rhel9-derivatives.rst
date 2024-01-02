.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Red Hat Enterprise Linux (RHEL) 9 and its derivatives have all required packages available in official repositories.
Install them with dnf:

.. TODO: Use Python 3.11 once RHEL 9.0 goes EOL in 2024.

.. prompt:: bash

    sudo dnf -y install python39 python3-devel git java-17-openjdk-headless @development nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.9.rst

.. include:: _includes/install-and-setup-red-unix.rst
