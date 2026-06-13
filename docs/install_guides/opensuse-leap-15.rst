.. _install-opensuse-leap-15:
.. os-image-location::

    [opensuse-leap-156]
    download_type = 'checksum-file'
    url = 'https://download.opensuse.org/distribution/leap/15.6/appliances/openSUSE-Leap-15.6-Minimal-VM.x86_64-Cloud.qcow2.sha256'
    filename_pattern = '.*\.qcow2'
    expected_java_version = 21

    [opensuse-leap-156-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://download.opensuse.org/distribution/leap/15.6/appliances/openSUSE-Leap-15.6-Minimal-VM.aarch64-Cloud.qcow2.sha256'
    filename_pattern = '.*\.qcow2'
    expected_java_version = 21

=====================================
Installing Red on openSUSE Leap 15.6+
=====================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

openSUSE Leap 15.6+ has all required dependencies available in official repositories. Install them
with zypper:

.. prompt:: bash

    sudo zypper -n install python311 python311-devel git-core java-21-openjdk-headless nano
    sudo zypper -n install -t pattern devel_basis

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
