.. _install-oracle-linux-9:
.. os-image-location::

    [oracle-linux-9]
    download_type = 'html'
    url = 'https://yum.oracle.com/oracle-linux-templates.html'
    url_xpath = ".//*[@id='ol9']//a[@class='kvm-image']/@href"
    checksum_xpath = ".//*[@id='ol9']//*[@class='kvm-sha256']/text()"

    [oracle-linux-9-arm]
    download_type = 'html'
    arch = 'aarch64'
    url = 'https://yum.oracle.com/oracle-linux-templates.html'
    url_xpath = ".//*[@id='ol9_aarch64']//a[@class='kvm-image']/@href"
    checksum_xpath = ".//*[@id='ol9_aarch64']//*[@class='kvm-sha256']/text()"

================================
Installing Red on Oracle Linux 9
================================

.. include:: _includes/install-guide-rhel9-derivatives.rst
