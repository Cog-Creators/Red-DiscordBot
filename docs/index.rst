.. Red - Discord Bot documentation master file, created by
    sphinx-quickstart on Thu Aug 10 23:18:25 2017.
    You can adapt this file completely to your liking, but it should at least
    contain the root `toctree` directive.

.. _main:

Welcome to Red - Discord Bot's documentation!
=============================================

.. image:: https://readthedocs.org/projects/red-discordbot/badge/?version=v3-develop
  :target: http://red-discordbot.readthedocs.io/en/v3-develop/?badge=v3-develop
  :alt: Documentation Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
  :target: https://github.com/ambv/black
  :alt: Code style: black

.. image:: https://d322cqt584bo4o.cloudfront.net/red-discordbot/localized.svg
  :target: https://crowdin.com/project/red-discordbot
  :alt: Crowdin

.. image:: https://img.shields.io/badge/Support-Red!-orange.svg
  :target: https://www.patreon.com/Red_Devs
  :alt: Patreon

.. toctree::
    :maxdepth: 1
    :caption: Installation Guides:

    install_windows
    install_mac
    install_ubuntu_xenial
    install_ubuntu_bionic
    install_debian
    install_centos
    install_arch
    install_raspbian
    cog_dataconverter
    autostart_systemd

.. toctree::
    :maxdepth: 2
    :caption: How to use

    getting_started

    cog_guides/admin
    cog_guides/alias
    cog_guides/audio
    cog_guides/bank
    cog_guides/economy
    cog_guides/downloader
    cog_guides/permissions

.. toctree::
    :maxdepth: 2
    :caption: Cog Reference:

    cog_downloader
    cog_permissions

.. toctree::
    :maxdepth: 2
    :caption: Red Development Framework Reference:

    guide_migration
    guide_cog_creation
    guide_data_conversion
    framework_bank
    framework_bot
    framework_cogmanager
    framework_config
    framework_datamanager
    framework_downloader
    framework_events
    framework_i18n
    framework_modlog
    framework_commands
    framework_rpc
    framework_utils

.. These files need to be included or Travis will fail

.. toctree::
    :maxdepth: 1
    :caption: Other

    host-list


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
