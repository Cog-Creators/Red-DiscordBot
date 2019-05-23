.. _windows-install-guide:

=========================
Installing Red on Windows
=========================

---------------
Needed Software
---------------

The following software dependencies can all be installed quickly and easily through powershell,
using a trusted package manager for windows called `Chocolatey <https://chocolatey.org>`_

We also provide instructions for manually installing all of the dependencies.

******************************************
Installing using powershell and chocolatey
******************************************

To install via powershell, search "powershell" in the windows start menu,
right-click on it and then click "Run as administrator"

Then run each of the following commands:

.. code-block:: none

    Set-ExecutionPolicy Bypass -Scope Process -Force
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    choco install git --params "/GitOnlyOnPath /WindowsTerminal" -y
    choco install jre8 python -y; exit


********************************
Manually installing dependencies
********************************

* `Python <https://www.python.org/downloads/>`_ - Red needs Python 3.7.0 or greater

.. note:: Please make sure that the box to add Python to PATH is CHECKED, otherwise
          you may run into issues when trying to run Red

* `Git <https://git-scm.com/download/win>`_

.. attention:: Please choose the option to "Run Git from the Windows Command Prompt" in Git's setup

* `Java <https://java.com/en/download/manual.jsp>`_ - needed for Audio

.. attention:: Please choose the "Windows Online" installer

.. _installing-red-windows:

--------------
Installing Red
--------------

1. Open a command prompt (open Start, search for "command prompt", then click it)
2. Create and activate a virtual environment (strongly recommended), see the section `using-venv`
3. Run **one** of the following commands, depending on what extras you want installed

  .. note::

      If you're not inside an activated virtual environment, include the ``--user`` flag with all
      ``pip`` commands.

  * No MongoDB support:

    .. code-block:: none

        python -m pip install -U Red-DiscordBot

  * With MongoDB support:

    .. code-block:: none

        python -m pip install -U Red-DiscordBot[mongo]

  .. note::

      To install the development version, replace ``Red-DiscordBot`` in the above commands with the
      following link:

      .. code-block:: none

          git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=Red-DiscordBot

--------------------------
Setting Up and Running Red
--------------------------

After installation, set up your instance with the following command:

.. code-block:: none

    redbot-setup

This will set the location where data will be stored, as well as your
storage backend and the name of the instance (which will be used for
running the bot).

Once done setting up the instance, run the following command to run Red:

.. code-block:: none

    redbot <your instance name>

It will walk through the initial setup, asking for your token and a prefix.
You can find out how to obtain a token with
`this guide <https://discordpy.readthedocs.io/en/v1.0.1/discord.html#creating-a-bot-account>`_,
section "Creating a Bot Account".

You may also run Red via the launcher, which allows you to restart the bot
from discord, and enable auto-restart. You may also update the bot from the
launcher menu. Use the following command to run the launcher:

.. code-block:: none

    redbot-launcher
