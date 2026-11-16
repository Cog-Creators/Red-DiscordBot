.. _install-oracle-linux-8:
.. os-image-location::

    [oracle-linux-8]
    download_type = 'html'
    url = 'https://yum.oracle.com/oracle-linux-templates.html'
    url_xpath = ".//*[@id='ol8']//a[@class='kvm-image']/@href"
    checksum_xpath = ".//*[@id='ol8']//*[@class='kvm-sha256']/text()"
    expected_java_version = 21

    [oracle-linux-8-arm]
    download_type = 'html'
    arch = 'aarch64'
    url = 'https://yum.oracle.com/oracle-linux-templates.html'
    url_xpath = ".//*[@id='ol8_aarch64']//a[@class='kvm-image']/@href"
    checksum_xpath = ".//*[@id='ol8_aarch64']//*[@class='kvm-sha256']/text()"
    expected_java_version = 21

======================================
Installing Red on Oracle Linux 8.6-8.x
======================================

.. include:: _includes/install-guide-rhel8-derivatives.rst
