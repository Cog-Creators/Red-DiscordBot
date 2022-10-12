.. _install-centos-7:

==========================
Installing Red on CentOS 7
==========================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Install the pre-requirements with yum:

.. prompt:: bash

    sudo yum -y groupinstall development
    sudo yum -y install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel java-11-openjdk-headless nano git

In order to install gcc 8, we'll use SCL repository:

.. prompt:: bash

    sudo yum -y install centos-release-scl
    sudo yum -y install devtoolset-8-gcc devtoolset-8-gcc-c++
    echo "source scl_source enable devtoolset-8" >> ~/.bashrc
    source ~/.bashrc

In order to install Git 2.11 or greater, we recommend adding the IUS repository:

.. prompt:: bash

    sudo yum -y install https://repo.ius.io/ius-release-el7.rpm
    sudo yum -y swap git git236

.. Include common instructions:

.. include:: _includes/install-python-pyenv.rst

.. include:: _includes/create-env-with-pyenv-virtualenv.rst

.. include:: _includes/install-and-setup-red-unix.rst
