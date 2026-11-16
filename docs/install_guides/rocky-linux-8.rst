.. _install-rocky-linux-8:
.. os-image-location::

    [rocky-linux-8]
    download_type = 'checksum-file'
    # one of the mirrors for https://download.rockylinux.org/pub/rocky/8/images/x86_64/CHECKSUM
    url = 'https://ftp.nluug.nl/pub/os/Linux/distr/rocky/8/images/x86_64/CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Rocky-8-GenericCloud\.latest\.x86_64\.qcow2'
    expected_java_version = 21

    [rocky-linux-8-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    # one of the mirrors for https://download.rockylinux.org/pub/rocky/8/images/aarch64/CHECKSUM
    url = 'https://ftp.nluug.nl/pub/os/Linux/distr/rocky/8/images/aarch64/CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Rocky-8-GenericCloud\.latest\.aarch64\.qcow2'
    expected_java_version = 21

=====================================
Installing Red on Rocky Linux 8.6-8.x
=====================================

.. include:: _includes/install-guide-rhel8-derivatives.rst
