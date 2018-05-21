.. ubuntu install guide

==============================
Installing Red on Ubuntu 16.04
==============================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <http://manpages.ubuntu.com/manpages/artful/man8/adduser.8.html>`_.

-------------------------------
Installing the pre-requirements
-------------------------------

.. code-block:: none

    sudo apt install python3.5-dev python3-pip build-essential libssl-dev libffi-dev git unzip default-jre -y

.. include:: red_install.rst