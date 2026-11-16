.. _install-alma-linux-8:
.. os-image-location::

    [alma-linux-8]
    download_type = 'checksum-file'
    url = 'https://repo.almalinux.org/almalinux/8/cloud/x86_64/images/CHECKSUM'
    filename_pattern = 'AlmaLinux-8-GenericCloud-8\.(?P<sort_key_0_int_desc>\d+)-(?P<sort_key_1_int_desc>\d+)\.x86_64\.qcow2'
    expected_java_version = 21

    [alma-linux-8-arm]
    download_type = 'checksum-file'
    arch = 'aarch64'
    url = 'https://repo.almalinux.org/almalinux/8/cloud/aarch64/images/CHECKSUM'
    filename_pattern = 'AlmaLinux-8-GenericCloud-8\.(?P<sort_key_0_int_desc>\d+)-(?P<sort_key_1_int_desc>\d+)\.aarch64\.qcow2'
    expected_java_version = 21

====================================
Installing Red on Alma Linux 8.6-8.x
====================================

.. include:: _includes/install-guide-rhel8-derivatives.rst
