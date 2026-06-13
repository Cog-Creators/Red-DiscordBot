.. _install-ubuntu-2404:
.. os-image-location::

    [ubuntu-2404]
    download_type = 'checksum-file'
    url = 'https://cloud-images.ubuntu.com/noble/current/SHA256SUMS'
    filename_pattern = 'noble-server-cloudimg-amd64\.img'

    [ubuntu-2404-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://cloud-images.ubuntu.com/noble/current/SHA256SUMS'
    filename_pattern = 'noble-server-cloudimg-arm64\.img'

    [ubuntu-2404-arm-raspi]
    download_type = 'checksum-file'
    arch = 'aarch64'
    machine_type = 'raspi3b'
    image_format = 'raw+xz'
    url = 'https://cdimage.ubuntu.com/ubuntu-server/noble/daily-preinstalled/current/SHA256SUMS'
    filename_pattern = 'noble-preinstalled-server-arm64\+raspi\.img\.xz'

==================================
Installing Red on Ubuntu 24.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend adding the ``deadsnakes`` ppa to install Python 3.11:

.. prompt:: bash

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. prompt:: bash

    sudo apt -y install python3.11 python3.11-dev python3.11-venv git openjdk-25-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
