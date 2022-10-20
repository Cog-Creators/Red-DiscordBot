.. _install-mac:

=======================
Installing Red on macOS
=======================

.. include:: _includes/supported-arch-x64+aarch64.rst

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
    brew install git
    brew tap homebrew/cask-versions
    brew install --cask temurin11

By default, Python installed through Homebrew is not added to the load path.
To fix this, you should run these commands:

.. prompt:: bash

    profile=$([ -n "$ZSH_VERSION" ] && echo ~/.zprofile || ([ -f ~/.bash_profile ] && echo ~/.bash_profile || echo ~/.profile))
    echo 'export PATH="$(brew --prefix)/opt/python@3.9/bin:$PATH"' >> "$profile"
    source "$profile"

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
