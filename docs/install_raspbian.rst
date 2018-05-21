.. raspbian install guide

==================================
Installing Red on Raspbian Stretch
==================================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <https://www.raspberrypi.org/documentation/linux/usage/users.md>`_.

---------------------------
Installing pre-requirements
---------------------------

.. code-block:: none

    sudo apt-get install python3.5-dev python3-pip build-essential libssl-dev libffi-dev git unzip default-jre -y

.. include:: red_install.rst