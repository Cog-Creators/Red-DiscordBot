.. _install-arch:
.. os-image-location::

    [arch-linux]
    download_type = 'html'
    url = 'https://fastly.mirror.pkgbuild.com/images/latest/'
    url_xpath = '''
    concat(
        "../v",
        substring-before(
            substring-after(
                .//*[
                    starts-with(@href, "Arch-Linux-x86_64-cloudimg-")
                    and ends-with(@href, ".qcow2")
                ]/@href,
                "Arch-Linux-x86_64-cloudimg-"
            ),
            ".qcow2"
        ),
        "/",
        .//*[
            starts-with(@href, "Arch-Linux-x86_64-cloudimg-")
            and ends-with(@href, ".qcow2")
        ]/@href
    )
    '''
    checksum_file_url_xpath = '''
    concat(
        "../v",
        substring-before(
            substring-after(
                .//*[
                    starts-with(@href, "Arch-Linux-x86_64-cloudimg-")
                    and ends-with(@href, ".qcow2.SHA256")
                ]/@href,
                "Arch-Linux-x86_64-cloudimg-"
            ),
            ".qcow2.SHA256"
        ),
        "/",
        .//*[
            starts-with(@href, "Arch-Linux-x86_64-cloudimg-")
            and ends-with(@href, ".qcow2.SHA256")
        ]/@href
    )
    '''

============================
Installing Red on Arch Linux
============================

.. include:: _includes/supported-arch-x64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Install the pre-requirements with pacman:

.. prompt:: bash

    sudo pacman -Syu git jre25-openjdk-headless base-devel nano

On Arch Linux, Python 3.11 can be installed from the Arch User Repository (AUR) from the ``python311`` package.

The manual build process is the Arch-supported install method for AUR packages. You can install ``python311`` package with the following commands:

.. prompt:: bash

    git clone https://aur.archlinux.org/python311.git /var/tmp/python311
    cd /var/tmp/python311
    makepkg -sicL
    cd -
    rm -rf /var/tmp/python311

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
