.. downloader framework reference

Downloader Framework
====================

Info.json
*********

The info.json file may exist inside every package folder in the repo,
it is optional however. This string describes the valid keys within
an info file (and maybe how the Downloader cog uses them).

KEYS (case sensitive):

- ``author`` (list of strings) - list of names of authors of the cog

- ``bot_version`` (list of integer) - Min version number of Red in the format ``(MAJOR, MINOR, PATCH)``

- ``description`` (string) - A long description of the cog that appears when a user executes ```!cog info``.

- ``hidden`` (bool) - Determines if a cog is available for install.

- ``install_msg`` (string) - The message that gets displayed when a cog is installed

- ``required_cogs`` (map of cogname to repo URL) - A map of required cogs that this cog depends on.
  Downloader will not deal with this functionality but it may be useful for other cogs.

- ``requirements`` (list of strings) - list of required libraries that are
  passed to pip on cog install. ``SHARED_LIBRARIES`` do NOT go in this
  list.

- ``short`` (string) - A short description of the cog that appears when
  a user executes `!cog list`

- ``tags`` (list of strings) - A list of strings that are related to the
  functionality of the cog. Used to aid in searching.

- ``type`` (string) - Optional, defaults to ``COG``. Must be either ``COG`` or
  ``SHARED_LIBRARY``. If ``SHARED_LIBRARY`` then ``hidden`` will be ``True``.

API Reference
*************

.. automodule:: cogs.downloader.json_mixins

.. autoclass RepoJSONMixin
    :members

.. automodule:: cogs.downloader.installable

Installable
^^^^^^^^^^^

.. autoclass:: Installable
    :members:

.. automodule:: cogs.downloader.repo_manager

Repo
^^^^

.. autoclass:: Repo
    :members:

Repo Manager
^^^^^^^^^^^^

.. autoclass:: RepoManager
    :members:

Exceptions
^^^^^^^^^^

.. automodule:: cogs.downloader.errors
    :members:

