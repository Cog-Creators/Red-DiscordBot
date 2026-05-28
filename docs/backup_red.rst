.. _backup-red:

============================
Backing Up and Restoring Red
============================

Red can be backed up and restored to any system as long as it is a supported per our `end-user-guarantees`.
The system it's restored to can be different from the system that was backed up.

.. note::

    Some 3rd-party cogs may not support all systems that Core Red supports and such cogs may therefore not work,
    if restored to an unsupported system. This does not affect cogs that do not impose additional restrictions.

.. contents::
    :local:
    :depth: 2

Creating backups
****************

Windows
-------

To make a backup, perform the following steps:

#. Stop the bot, ideally with ``[p]shutdown``.
#. Activate your venv.

    .. prompt:: batch

        "%userprofile%\redenv\Scripts\activate.bat"
#. Backup your Red instance with the following command:

    .. prompt:: batch
        :prompts: (redenv) C:\\>

        redbot-setup backup <your instance name>

    .. attention::

        Replace ``<your instance name>`` with the name of the instance you want to backup.
#. The command will create a backup file for you and show you the path to it.

.. tip::
    
    If you want to backup your instance to a custom folder,
    you can run the ``redbot-setup backup`` command as shown below,
    replacing ``C:\path\to\backup\folder`` with the path to the folder that
    you want to backup your instance to:

    .. prompt:: batch
        :prompts: (redenv) C:\\>

        redbot-setup backup <your instance name> C:\path\to\backup\folder

Linux & Mac
-----------

To make a backup, perform the following steps:

#. Stop the bot, ideally with ``[p]shutdown``.
#. Activate your venv.

    .. prompt:: bash

        source ~/redenv/bin/activate
#. Backup your Red instance with the following command:

    .. prompt:: bash
        :prompts: (redenv) $

        redbot-setup backup <your instance name>

    .. attention::

        Replace ``<your instance name>`` with the name of the instance you want to backup.
#. The command will create a backup file for you and show you the path to it.

.. tip::
    
    If you want to backup your instance to a custom folder,
    you can run the ``redbot-setup backup`` command as shown below,
    replacing ``/path/to/backup/folder`` with the path to the folder that
    you want to backup your instance to:

    .. prompt:: bash
        :prompts: (redenv) $

        redbot-setup backup <your instance name> /path/to/backup/folder

Restoring backups
*****************

Windows
-------

To restore a backup, perform the following steps:

#. `Install Red <windows-install-guide>` on the new machine/location, skipping the ``redbot-setup`` step.
#. Activate your venv.

    .. prompt:: batch

        "%userprofile%\redenv\Scripts\activate.bat"
#. Restore your Red instance with the following command:

    .. prompt:: batch
        :prompts: (redenv) C:\\>

        redbot-setup restore C:\path\to\backup\file.tar.gz

    .. attention::

        Replace ``C:\path\to\backup\file.tar.gz`` with the path to the backup file
        that you want to restore from.

#. The command will guide you through the restore process.

Linux & Mac
-----------

To restore a backup, perform the following steps:

#. `Install Red <install-guides>` on the new machine/location, skipping the ``redbot-setup`` step.
#. Activate your venv.

    .. prompt:: bash

        source ~/redenv/bin/activate
#. Restore your Red instance with the following command:

    .. prompt:: bash
        :prompts: (redenv) $

        redbot-setup restore /path/to/backup/file.tar.gz

    .. attention::

        Replace ``/path/to/backup/file.tar.gz`` with the path to the backup file
        that you want to restore from.

#. The command will guide you through the restore process.
