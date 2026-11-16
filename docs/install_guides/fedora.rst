.. _install-fedora:
.. os-image-location::

    [fedora-43]
    download_type = 'checksum-file'
    url = 'https://download.fedoraproject.org/pub/fedora/linux/releases/43/Cloud/x86_64/images/Fedora-Cloud-43-1.6-x86_64-CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Fedora-Cloud-Base-Generic-.*\.qcow2'

    [fedora-43-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://download.fedoraproject.org/pub/fedora/linux/releases/43/Cloud/aarch64/images/Fedora-Cloud-43-1.6-aarch64-CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Fedora-Cloud-Base-Generic-.*\.qcow2'

    [fedora-44]
    download_type = 'checksum-file'
    url = 'https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-44-1.7-x86_64-CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Fedora-Cloud-Base-Generic-.*\.qcow2'

    [fedora-44-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/aarch64/images/Fedora-Cloud-44-1.7-aarch64-CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Fedora-Cloud-Base-Generic-.*\.qcow2'

==============================
Installing Red on Fedora Linux
==============================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Fedora Linux 43 and above has all required packages available in official repositories. Install
them with dnf:

.. prompt:: bash

    sudo dnf -y install python3.11 python3.11-devel git adoptium-temurin-java-repository @development-tools nano
    sudo dnf config-manager setopt adoptium-temurin-java-repository.enabled=1
    sudo dnf -y install temurin-25-jre

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
