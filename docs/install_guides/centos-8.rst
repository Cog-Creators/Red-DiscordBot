.. _install-centos-8:
.. _install-rhel-8:

===================================
Installing Red on CentOS and RHEL 8
===================================

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Install the pre-requirements with yum:

.. prompt:: bash

    sudo yum -y install epel-release
    sudo yum -y update
    sudo yum -y groupinstall development
    sudo yum -y install git zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel xz xz-devel tk-devel libffi-devel findutils java-11-openjdk-headless nano

.. Include common instructions:

.. include:: _includes/install-python-pyenv.rst

.. include:: _includes/create-env-with-pyenv-virtualenv.rst

.. include:: _includes/install-and-setup-red-unix.rst
