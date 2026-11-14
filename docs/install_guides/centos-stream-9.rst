.. _install-centos-stream-9:
.. os-image-location::

    [centos-stream-9]
    download_type = 'checksum-file'
    boot_mode = 'bios'
    url = 'https://cloud.centos.org/centos/9-stream/x86_64/images/CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'CentOS-Stream-GenericCloud-9-(?P<sort_key_0_int_desc>\d+)\.(?P<sort_key_1_int_desc>\d+)\.x86_64\.qcow2'

    [centos-stream-9-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://cloud.centos.org/centos/9-stream/aarch64/images/CHECKSUM'
    checksum_style = 'bsd'
    filename_pattern = 'CentOS-Stream-GenericCloud-9-(?P<sort_key_0_int_desc>\d+)\.(?P<sort_key_1_int_desc>\d+)\.aarch64\.qcow2'

=================================
Installing Red on CentOS Stream 9
=================================

.. include:: _includes/install-guide-rhel9-derivatives.rst
