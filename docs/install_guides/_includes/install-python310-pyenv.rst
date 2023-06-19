----------------------------
Installing Python with pyenv
----------------------------

On distributions where Python 3.10 needs to be compiled from source, we recommend the use of pyenv.
This simplifies the compilation process and has the added bonus of simplifying setting up Red in a
virtual environment.

.. include:: _includes/_install-pyenv-and-setup-path.rst

.. prompt:: bash

    CONFIGURE_OPTS=--enable-optimizations pyenv install 3.10.12 -v

This may take a long time to complete, depending on your hardware. For some machines (such as
Raspberry Pis and micro-tier VPSes), it may take over an hour; in this case, you may wish to remove
the ``CONFIGURE_OPTS=--enable-optimizations`` part from the front of the command, which will
drastically reduce the install time. However, be aware that this will make Python run about 10%
slower.

After that is finished, run:

.. prompt:: bash

    pyenv global 3.10.12

Pyenv is now installed and your system should be configured to run Python 3.10.
