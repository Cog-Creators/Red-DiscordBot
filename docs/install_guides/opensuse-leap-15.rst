.. _install-opensuse-leap-15:

=====================================
Installing Red on openSUSE Leap 15.2+
=====================================

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend installing a community package to get Python 3.9 on openSUSE Leap 15.2+. This package will
be installed to the ``/opt`` directory.

First, add the Opt-Python community repository:

.. prompt:: bash

    source /etc/os-release
    sudo zypper -n ar -f https://download.opensuse.org/repositories/home:/Rotkraut:/Opt-Python/openSUSE_Leap_${VERSION_ID}/ Opt-Python
    sudo zypper -n --gpg-auto-import-keys ref

Now install the pre-requirements with zypper:

.. prompt:: bash

    sudo zypper -n install opt-python39 opt-python39-setuptools git-core java-11-openjdk-headless nano
    sudo zypper -n install -t pattern devel_basis

Since Python is now installed to ``/opt/python``, we should add it to PATH. You can add a file in
``/etc/profile.d/`` to do this:

.. prompt:: bash

    echo 'export PATH="/opt/python/bin:$PATH"' | sudo tee /etc/profile.d/opt-python.sh
    source /etc/profile.d/opt-python.sh

Now, bootstrap pip with ensurepip:

.. prompt:: bash

    sudo /opt/python/bin/python3.9 -m ensurepip --altinstall

.. note::

    After this command, a warning about running pip as root might be printed.
    For this specific command, this warning can be safely ignored.

.. Include common instructions:

.. include:: _includes/create-env-with-venv.rst

.. include:: _includes/install-and-setup-red-unix.rst
