.. _install-rocky-linux-9:
.. os-image-location::

    [rocky-linux-9]
    download_type = 'checksum-file'
    # one of the mirrors for https://download.rockylinux.org/pub/rocky/9/images/x86_64/CHECKSUM
    url = 'https://ftp.nluug.nl/pub/os/Linux/distr/rocky/9/images/x86_64/CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Rocky-9-GenericCloud\.latest\.x86_64\.qcow2'

    [rocky-linux-9-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    # one of the mirrors for https://download.rockylinux.org/pub/rocky/9/images/aarch64/CHECKSUM
    url = 'https://ftp.nluug.nl/pub/os/Linux/distr/rocky/9/images/aarch64/CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'Rocky-9-GenericCloud\.latest\.aarch64\.qcow2'

===============================
Installing Red on Rocky Linux 9
===============================

.. include:: _includes/install-guide-rhel9-derivatives.rst
