============================
Backing Up and Restoring Red
============================

Red can be backed up and restored to any device as long as it is supported operating system. See page: `version_guarantees`.

Backup steps must be done correctly to ensure that it can be restored without any issues occurring.

#. Take note of the installed cogs and cog repositories with ``[p]cogs``, then ``[p]load downloader``, then ``[p]repo list`` (``[p]`` is considered as your bot's prefix).
#. Stop the bot, ideally with ``[p]shutdown``.
#. Activate your venv, and run ``redbot-setup backup <instancename>`` replacing ``<instancename>`` with the name of your instance.
#. Copy your backup file to the new machine/location.
#. Extract the file to a location of your choice (remember the full path and make sure that the user you are going to install/run Red under can access this path).
#. Install Red as normal on the new machine/location
#. Run ``redbot-setup`` in your venv to create a new instance, except use the path you remembered above as your data path.
#. Start your new instance.
#. Re-add the Repos using the same names as before
#. Do ``[p]cog update``
#. Re-add any cogs that were not re-installed (you may have to uninstall them first as Downloader may think they are still installed)

    .. note::

        The config (data) from cogs has been saved, but not the code itself.