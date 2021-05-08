.. _downloader:

==========
Downloader
==========

This is the cog guide for the downloader cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load downloader

.. _downloader-usage:

-----
Usage
-----

Install community cogs made by Cog Creators.

Community cogs, also called third party cogs, are not included
in the default Red install.

Community cogs come in repositories. Repos are a group of cogs
you can install. You always need to add the creator's repository
using the ``[p]repo`` command before you can install one or more
cogs from the creator.


.. _downloader-commands:

--------
Commands
--------

.. _downloader-command-cog:

^^^
cog
^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]cog 

**Description**

Base command for cog installation management commands.

.. _downloader-command-cog-checkforupdates:

"""""""""""""""""""
cog checkforupdates
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]cog checkforupdates 

**Description**

Check for available cog updates (including pinned cogs).

This command doesn't update cogs, it only checks for updates.
Use ``[p]cog update`` to update cogs.

.. _downloader-command-cog-info:

""""""""
cog info
""""""""

**Syntax**

.. code-block:: none

    [p]cog info <repo> <cog>

**Description**

List information about a single cog.

Example:
    - ``[p]cog info 26-Cogs defender``

**Arguments**

- ``<repo>`` The repo to get cog info from.
- ``<cog>`` The cog to get info on.

.. _downloader-command-cog-install:

"""""""""""
cog install
"""""""""""

**Syntax**

.. code-block:: none

    [p]cog install <repo> <cogs...>

**Description**

Install a cog from the given repo.

Examples:
    - ``[p]cog install 26-Cogs defender``
    - ``[p]cog install Laggrons-Dumb-Cogs say roleinvite``

**Arguments**

- ``<repo>`` The name of the repo to install cogs from.
- ``<cogs...>`` The cog or cogs to install.

.. _downloader-command-cog-installversion:

""""""""""""""""""
cog installversion
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]cog installversion <repo> <revision> <cogs...>

**Description**

Install a cog from the specified revision of given repo.

Revisions are "commit ids" that point to the point in the code when a specific change was made.
The latest revision can be found in the URL bar for any GitHub repo by `pressing "y" on that repo <https://docs.github.com/en/free-pro-team@latest/github/managing-files-in-a-repository/getting-permanent-links-to-files#press-y-to-permalink-to-a-file-in-a-specific-commit>`_.

Older revisions can be found in the URL bar by `viewing the commit history of any repo <https://cdn.discordapp.com/attachments/133251234164375552/775760247787749406/unknown.png>`_

Example:
    - ``[p]cog installversion Broken-Repo e798cc268e199612b1316a3d1f193da0770c7016 cog_name``

**Arguments**

- ``<repo>`` The name of the repo to install cogs from.
- ``<revision>`` The revision to install from.
- ``<cogs...>`` The cog or cogs to install.

.. _downloader-command-cog-list:

""""""""
cog list
""""""""

**Syntax**

.. code-block:: none

    [p]cog list <repo>

**Description**

List all available cogs from a single repo.

Example:
    - ``[p]cog list 26-Cogs``

**Arguments**

- ``<repo>`` The repo to list cogs from.

.. _downloader-command-cog-listpinned:

""""""""""""""
cog listpinned
""""""""""""""

**Syntax**

.. code-block:: none

    [p]cog listpinned 

**Description**

List currently pinned cogs.

.. _downloader-command-cog-pin:

"""""""
cog pin
"""""""

**Syntax**

.. code-block:: none

    [p]cog pin <cogs...>

**Description**

Pin cogs - this will lock cogs on their current version.

Examples:
    - ``[p]cog pin defender``
    - ``[p]cog pin outdated_cog1 outdated_cog2``

**Arguments**

- ``<cogs...>`` The cog or cogs to pin. Must already be installed.

.. _downloader-command-cog-uninstall:

"""""""""""""
cog uninstall
"""""""""""""

**Syntax**

.. code-block:: none

    [p]cog uninstall <cogs...>

**Description**

Uninstall cogs.

You may only uninstall cogs which were previously installed
by Downloader.

Examples:
    - ``[p]cog uninstall defender``
    - ``[p]cog uninstall say roleinvite``

**Arguments**

- ``<cogs...>`` The cog or cogs to uninstall.

.. _downloader-command-cog-unpin:

"""""""""
cog unpin
"""""""""

**Syntax**

.. code-block:: none

    [p]cog unpin <cogs...>

**Description**

Unpin cogs - this will remove the update lock from those cogs.

Examples:
    - ``[p]cog unpin defender``
    - ``[p]cog unpin updated_cog1 updated_cog2``

**Arguments**

- ``<cogs...>`` The cog or cogs to unpin. Must already be installed and pinned.

.. _downloader-command-cog-update:

""""""""""
cog update
""""""""""

**Syntax**

.. code-block:: none

    [p]cog update [cogs...]

**Description**

Update all cogs, or ones of your choosing.

Examples:
    - ``[p]cog update``
    - ``[p]cog update defender``

**Arguments**

- ``[cogs...]`` The cog or cogs to update. If omitted, all cogs are updated.

.. _downloader-command-cog-updateallfromrepos:

""""""""""""""""""""""
cog updateallfromrepos
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]cog updateallfromrepos <repos...>

**Description**

Update all cogs from repos of your choosing.

Examples:
    - ``[p]cog updateallfromrepos 26-Cogs``
    - ``[p]cog updateallfromrepos Laggrons-Dumb-Cogs 26-Cogs``

**Arguments**

- ``<repos...>`` The repo or repos to update all cogs from.

.. _downloader-command-cog-updatetoversion:

"""""""""""""""""""
cog updatetoversion
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]cog updatetoversion <repo> <revision> [cogs...]

**Description**

Update all cogs, or ones of your choosing to chosen revision of one repo.

Note that update doesn't mean downgrade and therefore ``revision``
has to be newer than the version that cog currently has installed. If you want to
downgrade the cog, uninstall and install it again.

See ``[p]cog installversion`` for an explanation of ``revision``.

Example:
    - ``[p]cog updatetoversion Broken-Repo e798cc268e199612b1316a3d1f193da0770c7016 cog_name``

**Arguments**

- ``<repo>`` The repo or repos to update all cogs from.
- ``<revision>`` The revision to update to.
- ``[cogs...]`` The cog or cogs to update.

.. _downloader-command-findcog:

^^^^^^^
findcog
^^^^^^^

**Syntax**

.. code-block:: none

    [p]findcog <command_name>

**Description**

Find which cog a command comes from.

This will only work with loaded cogs.

Example:
    - ``[p]findcog ping``

**Arguments**

- ``<command_name>`` The command to search for.

.. _downloader-command-pipinstall:

^^^^^^^^^^
pipinstall
^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]pipinstall <deps...>

**Description**

Install a group of dependencies using pip.

Examples:
    - ``[p]pipinstall bs4``
    - ``[p]pipinstall py-cpuinfo psutil``

Improper usage of this command can break your bot, be careful.

**Arguments**

- ``<deps...>`` The package or packages you wish to install.

.. _downloader-command-repo:

^^^^
repo
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]repo 

**Description**

Base command for repository management.

.. _downloader-command-repo-add:

""""""""
repo add
""""""""

**Syntax**

.. code-block:: none

    [p]repo add <name> <repo_url> [branch]

**Description**

Add a new repo.

Examples:
    - ``[p]repo add 26-Cogs https://github.com/Twentysix26/x26-Cogs``
    - ``[p]repo add Laggrons-Dumb-Cogs https://github.com/retke/Laggrons-Dumb-Cogs v3``

Repo names can only contain characters A-z, numbers, underscores, and hyphens.
The branch will be the default branch if not specified.

**Arguments**

- ``<name>`` The name given to the repo.
- ``<repo_url>`` URL to the cog branch. Usually GitHub or GitLab.
- ``[branch]`` Optional branch to install cogs from.

.. _downloader-command-repo-delete:

"""""""""""
repo delete
"""""""""""

**Syntax**

.. code-block:: none

    [p]repo delete <repo>

.. tip:: Aliases: ``repo remove``, ``repo del``

**Description**

Remove a repo and its files.

Example:
    - ``[p]repo delete 26-Cogs``

**Arguments**

- ``<repo>`` The name of an already added repo

.. _downloader-command-repo-info:

"""""""""
repo info
"""""""""

**Syntax**

.. code-block:: none

    [p]repo info <repo>

**Description**

Show information about a repo.

Example:
    - ``[p]repo info 26-Cogs``

**Arguments**

- ``<repo>`` The name of the repo to show info about.

.. _downloader-command-repo-list:

"""""""""
repo list
"""""""""

**Syntax**

.. code-block:: none

    [p]repo list 

**Description**

List all installed repos.

.. _downloader-command-repo-update:

"""""""""""
repo update
"""""""""""

**Syntax**

.. code-block:: none

    [p]repo update [repos...]

**Description**

Update all repos, or ones of your choosing.

This will *not* update the cogs installed from those repos.

Examples:
    - ``[p]repo update``
    - ``[p]repo update 26-Cogs``
    - ``[p]repo update 26-Cogs Laggrons-Dumb-Cogs``

**Arguments**

- ``[repos...]`` The name or names of repos to update. If omitted, all repos are updated.
