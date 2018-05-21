.. debian install guide

================================
Installing Red on Debian Stretch
================================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <https://manpages.debian.org/stretch/adduser/adduser.8.en.html>`_.

---------------------------
Installing pre-requirements
---------------------------

.. code-block:: none

    echo "deb http://httpredir.debian.org/debian stretch-backports main contrib non-free" >> /etc/apt/sources.list
    apt-get update
    apt-get install python3.5-dev python3-pip build-essential libssl-dev libffi-dev git unzip default-jre -y


.. include:: red_install.rst