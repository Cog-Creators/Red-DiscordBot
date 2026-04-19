.. _backup-red:

============================
Backing Up and Restoring Red
============================

Red can be backed up and restored to any device as long as it is a supported operating system. See page: :ref:`end-user-guarantees`.

Backup steps are to be done in order and carefully to avoid any issues.

#. Take note of the installed cogs with ``[p]cogs``; and cog repositories with ``[p]load downloader``, then ``[p]repo list`` (``[p]`` is your bot's prefix).
#. Stop the bot, ideally with ``[p]shutdown``.
#. Activate your venv, and run ``redbot-setup backup <instancename>``, replacing ``<instancename>`` with the name of your instance.
#. Copy your backup file to the new machine/location.
#. Extract the file to a location of your choice (remember the full path and make sure that the user you are going to install/run Red under can access this path).
#. :ref:`Install Red <install-guides>` as normal on the new machine/location.
#. Run ``redbot-setup`` in your venv to create a new instance, using the path you remembered above as your data path.
#. Start your new instance.
#. Re-add the cog repositories using the same names as before.
#. Do ``[p]cog update``.
#. Re-add any cogs that were not re-installed (you may have to uninstall them first as Downloader may think they are still installed).

    .. note::

        The config (data) from cogs has been saved, but not the code itself.

    .. tip::

        You can fix permissions (if needed) on your directory using:

        .. code-block:: bash

            sudo chown -R <user>:<user> ~/.local

        Replace ``<user>`` with your actual username.