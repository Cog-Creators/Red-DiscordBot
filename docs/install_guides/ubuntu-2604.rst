.. _install-ubuntu-2604:
.. os-image-location::

    [ubuntu-2604]
    download_type = 'html'
    url = 'https://cloud-images.ubuntu.com/resolute/current/'
    url_xpath = '''
    concat(
        "../",
        substring-before(substring-after(/html/head/title, "daily ["), "]"),
        "/resolute-server-cloudimg-amd64.img"
    )
    '''
    checksum_file_url_xpath = '''
    concat(
        "../",
        substring-before(substring-after(/html/head/title, "daily ["), "]"),
        "/SHA256SUMS"
    )
    '''

    [ubuntu-2604-amd64v3]
    download_type = 'html'
    url = 'https://cloud-images.ubuntu.com/resolute/current/'
    url_xpath = '''
    concat(
        "../",
        substring-before(substring-after(/html/head/title, "daily ["), "]"),
        "/resolute-server-cloudimg-amd64v3.img"
    )
    '''
    checksum_file_url_xpath = '''
    concat(
        "../",
        substring-before(substring-after(/html/head/title, "daily ["), "]"),
        "/SHA256SUMS"
    )
    '''

    [ubuntu-2604-arm]
    download_type = 'html'
    arch = 'aarch64'
    url = 'https://cloud-images.ubuntu.com/resolute/current/'
    url_xpath = '''
    concat(
        "../",
        substring-before(substring-after(/html/head/title, "daily ["), "]"),
        "/resolute-server-cloudimg-arm64.img"
    )
    '''
    checksum_file_url_xpath = '''
    concat(
        "../",
        substring-before(substring-after(/html/head/title, "daily ["), "]"),
        "/SHA256SUMS"
    )
    '''

    [ubuntu-2604-arm-raspi]
    download_type = 'html'
    arch = 'aarch64'
    machine_type = 'raspi3b'
    image_format = 'raw+xz'
    url = 'https://cdimage.ubuntu.com/ubuntu-server/resolute/daily-preinstalled/current/'
    url_xpath = '''
    concat(
        /html/head/link[@rel="canonical"]/@href, "/resolute-preinstalled-server-arm64+raspi.img.xz"
    )
    '''
    checksum_file_url_xpath = '"SHA256SUMS"'

==================================
Installing Red on Ubuntu 26.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend adding the ``deadsnakes`` ppa to install Python 3.11:

.. prompt:: bash

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. prompt:: bash

    sudo apt -y install python3.11 python3.11-dev python3.11-venv git openjdk-25-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
