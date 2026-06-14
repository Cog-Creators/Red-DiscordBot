.. _install-debian-12:
.. os-image-location::

    [debian-12]
    download_type = 'checksum-file'
    url = 'https://cloud.debian.org/images/cloud/bookworm/latest/SHA512SUMS'
    checksum_type = 'sha512'
    filename_pattern = 'debian-12-generic-amd64\.qcow2'
    expected_java_version = 17

    [debian-12-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://cloud.debian.org/images/cloud/bookworm/latest/SHA512SUMS'
    checksum_type = 'sha512'
    filename_pattern = 'debian-12-genericcloud-arm64\.qcow2'
    expected_java_version = 17

====================================
Installing Red on Debian 12 Bookworm
====================================

.. include:: _includes/supported-arch-x64+aarch64+armv7l.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Debian 12 "Bookworm" has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3 python3-dev python3-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
