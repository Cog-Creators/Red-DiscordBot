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
using the `[p]repo` command before you can install one or more
cogs from the creator.


.. _downloader-commands:

--------
Commands
--------

.. _downloader-command-pipinstall:

^^^^^^^^^^
pipinstall
^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]pipinstall [deps...]

**Description**

Install a group of dependencies using pip.

.. _downloader-command-repo:

^^^^
repo
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]repo 

**Description**

Repo management commands.

.. _downloader-command-repo-update:

^^^^^^
update
^^^^^^

**Syntax**

.. code-block:: none

    [p]repo update [repos...]

**Description**

Update all repos, or ones of your choosing.

.. _downloader-command-repo-list:

^^^^
list
^^^^

**Syntax**

.. code-block:: none

    [p]repo list 

**Description**

List all installed repos.

.. _downloader-command-repo-info:

^^^^
info
^^^^

**Syntax**

.. code-block:: none

    [p]repo info <repo_name>

**Description**

Show information about a repo.

.. _downloader-command-repo-delete:

^^^^^^
delete
^^^^^^

**Syntax**

.. code-block:: none

    [p]repo delete <repo_name>

**Description**

Remove a repo and its files.

.. _downloader-command-repo-add:

^^^
add
^^^

**Syntax**

.. code-block:: none

    [p]repo add <name> <repo_url> [branch]

**Description**

Add a new repo.

Repo names can only contain characters A-z, numbers, underscores, and hyphens.
The branch will be the default branch if not specified.

.. _downloader-command-cog:

^^^
cog
^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]cog 

**Description**

Cog installation management commands.

.. _downloader-command-cog-checkforupdates:

^^^^^^^^^^^^^^^
checkforupdates
^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog checkforupdates 

**Description**

Check for available cog updates (including pinned cogs).

This command doesn't update cogs, it only checks for updates.
Use `[p]cog update` to update cogs.

.. _downloader-command-cog-listpinned:

^^^^^^^^^^
listpinned
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog listpinned 

**Description**

List currently pinned cogs.

.. _downloader-command-cog-installversion:

^^^^^^^^^^^^^^
installversion
^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog installversion <repo_name> <revision> <cogs>

**Description**

Install a cog from the specified revision of given repo.

.. _downloader-command-cog-pin:

^^^
pin
^^^

**Syntax**

.. code-block:: none

    [p]cog pin <cogs>

**Description**

Pin cogs - this will lock cogs on their current version.

.. _downloader-command-cog-list:

^^^^
list
^^^^

**Syntax**

.. code-block:: none

    [p]cog list <repo_name>

**Description**

List all available cogs from a single repo.

.. _downloader-command-cog-updateallfromrepos:

^^^^^^^^^^^^^^^^^^
updateallfromrepos
^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog updateallfromrepos <repos>

**Description**

Update all cogs from repos of your choosing.

.. _downloader-command-cog-info:

^^^^
info
^^^^

**Syntax**

.. code-block:: none

    [p]cog info <repo_name> <cog_name>

**Description**

List information about a single cog.

.. _downloader-command-cog-reinstallreqs:

^^^^^^^^^^^^^
reinstallreqs
^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog reinstallreqs 

**Description**

This command will reinstall cog requirements and shared libraries for all installed cogs.

Red might ask user to use this when it clears contents of lib folder
because of change in minor version of Python.

.. _downloader-command-cog-unpin:

^^^^^
unpin
^^^^^

**Syntax**

.. code-block:: none

    [p]cog unpin <cogs>

**Description**

Unpin cogs - this will remove update lock from cogs.

.. _downloader-command-cog-updatetoversion:

^^^^^^^^^^^^^^^
updatetoversion
^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog updatetoversion <repo_name> <revision> [cogs]

**Description**

Update all cogs, or ones of your choosing to chosen revision of one repo.

Note that update doesn't mean downgrade and therefore revision
has to be newer than the one that cog currently has. If you want to
downgrade the cog, uninstall and install it again.

.. _downloader-command-cog-install:

^^^^^^^
install
^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog install <repo_name> <cogs>

**Description**

Install a cog from the given repo.

.. _downloader-command-cog-update:

^^^^^^
update
^^^^^^

**Syntax**

.. code-block:: none

    [p]cog update [cogs...]

**Description**

Update all cogs, or ones of your choosing.

.. _downloader-command-cog-uninstall:

^^^^^^^^^
uninstall
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]cog uninstall <cogs>

**Description**

Uninstall cogs.

You may only uninstall cogs which were previously installed
by Downloader.

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
