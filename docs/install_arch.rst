.. arch install guide

==============================
Installing Red on Arch Linux
==============================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, make a new one.

:code:`https://wiki.archlinux.org/index.php/Users_and_groups`

-------------------------------
Installing the pre-requirements
-------------------------------

.. code-block:: none

    sudo pacman -Syu python-pip git base-devel jre8-openjdk

.. include:: red_install.rst