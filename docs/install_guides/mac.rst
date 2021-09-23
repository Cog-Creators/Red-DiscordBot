.. _install-mac:

=======================
Installing Red on macOS
=======================

-------------------------------
Installing the pre-requirements
-------------------------------

To install pre-requirements, we first have to install Brew.
In Finder or Spotlight, search for and open *Terminal*. In the terminal, paste the
following, then press Enter:

.. prompt:: bash

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

After the installation, install the required packages by pasting the commands and pressing enter,
one-by-one:

.. prompt:: bash

    brew install python@3.9
    echo 'export PATH="$(brew --prefix)/opt/python@3.9/bin:$PATH"' >> ~/.profile
    source ~/.profile
    brew install git
    brew install --cask adoptopenjdk/openjdk/adoptopenjdk11

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
