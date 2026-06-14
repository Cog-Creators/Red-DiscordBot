.. _install-ubuntu-2204:
.. os-image-location::

    [ubuntu-2204]
    download_type = 'checksum-file'
    url = 'https://cloud-images.ubuntu.com/jammy/current/SHA256SUMS'
    filename_pattern = 'jammy-server-cloudimg-amd64\.img'

    [ubuntu-2204-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://cloud-images.ubuntu.com/jammy/current/SHA256SUMS'
    filename_pattern = 'jammy-server-cloudimg-arm64\.img'

    [ubuntu-2204-arm-raspi]
    download_type = 'checksum-file'
    arch = 'aarch64'
    machine_type = 'raspi3b'
    image_format = 'raw+xz'
    url = 'https://cdimage.ubuntu.com/releases/jammy/release/SHA256SUMS'
    filename_pattern = 'ubuntu-22\.04\.\d+-preinstalled-server-arm64\+raspi\.img\.xz'

==================================
Installing Red on Ubuntu 22.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Ubuntu 22.04 LTS has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3.10 python3.10-dev python3.10-venv git openjdk-25-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.10.rst

.. include:: _includes/install-and-setup-red-unix.rst
