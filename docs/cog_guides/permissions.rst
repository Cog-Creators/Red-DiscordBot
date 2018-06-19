.. |default-arg1| replace::
    ``<allow_or_deny>``: Defines if you want to allow or deny the
    the usage of something.

.. |default-arg2| replace::
    ``<cog_or_command>``: What you want to allow or deny. It can be
    a cog or a command. If it is a cog, notice the capitalization.

.. |default-arg3| replace::
    ``<who_or_what>``: The object you want to grant/revoke the permission
    to. It can be an user, a text/voice channel, a role or a guild. You can
    check the order of the checks :ref:`here <permissions-usage-working>`.

.. _permissions:

===========
Permissions
===========

This is the cog guide for the permissions cog. You will
find detailled docs about the usage and the commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load permissions

.. _permissions-usage:

-----
Usage
-----

The permissions cog will allow you to define extra custom
rules for who can use a command. If no applicable rules are
found, then command will behave as if the cog was not loaded.

.. _permissions-usage-working:

^^^^^^^^^^^^
How it works
^^^^^^^^^^^^

You will be able to create "rules" that will overwrites the
default command permissions. For example, the ban command will
work if you have the moderator role, but you can change it so it will
work with a custom role and only in a specific channel for example.

You can set rules for cog and commands, they will be global or
server-wide. The rules will be checked in the following order:

#. Owner level command rule (global)

#. Owner level cog rule (global)

#. Server level command rule (server-wide)

#. Server level cog rule (server-wide)

For each of those, rules have varying priorities listed below
(highest to lowest priority):

#. User whitelist

#. User blacklist

#. Voice channel whitelist

#. Voice channel blacklist

#. Text channel whitelist

#. Text channel blacklist

#. Role rules (see below)

#. Server whitelist

#. Server blacklist

#. Default settings

For the role whitelist and blacklist rules, roles will be checked
individually in order from highest to lowest role the user has. Each
role will be checked for whitelist, then blacklist. The first role
with a setting found will be the one used.

.. _permissions-usage-file:

^^^^^^^^^^^^^^^^^^^^^^^^^
Setting rules from a file
^^^^^^^^^^^^^^^^^^^^^^^^^

The permissions cog can set rules from a .yaml file: all entries are
based on ID. An example of the expected format is below:

.. code-block:: yaml

    cogs:
      Admin:
        allow:
          - 78631113035100160
        deny:
          - 96733288462286848
      Audio:
        allow:
          - 133049272517001216
        default: deny
    commands:
      cleanup bot:
        allow:
          - 78631113035100160
        default: deny
      ping:
        deny:
          - 96733288462286848
        default: allow

.. _ permissions-usage-example:

^^^^^^^^^^^^^^^^^^^^^^^
Example confirgurations
^^^^^^^^^^^^^^^^^^^^^^^

*   Locking Audio cog to approved servers as a bot Owner:

    .. code-block:: none

        [p]permissions setglobaldefault Audio deny
        [p]permissions addglobalrule allow Audio [server ID or name]

*   Locking Audio to specific voice channels as a server owner or admin:

    .. code-block:: none

        [p]permissions setguilddefault Audio deny
        [p]permissions addguildrule allow Cleanup [role ID]

*   Allowing extra roles to use cleanup

    .. code-block:: none

        [p]permissions addguildrule allow Cleanup [role ID]

*   Preventing cleanup from being used in channels where message history
    is important:

    .. code-block:: none

        [p]permissions addguildrule deny Cleanup [channel ID or mention]

.. _permissions-commands:

--------
Commands
--------

.. tip:: For providing an object (member/channel/role/server), you can
    use its ID for best results.

    Go in your user settings > Appearance and tick "Developer mode".
    You will be able to copy the ID of something when you right click.

.. _permissions-command-permissions:

^^^^^^^^^^^
permissions
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p][permissions|p]

**Description**

Main group command used for the cog. Every commands of the cog
is a subcommand of this one.

.. _permissions-command-addglobalrule:

"""""""""""""""""""""""""
permissions addglobalrule
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions addglobalrule <allow_or_deny> <cog_or_command> <who_or_what>

**Description**

Creates a rule that will overwrites the current permissions for the
command. You can allow or deny the usage of a command or a cog for
a special member, a voice channel, a text channel, a role or a guild.

The rule will be global and applied on every server and in DMs.

**Arguments**

*   |default-arg1|

*   |default-arg2|

*   |default-arg3|

**Examples**

*   This will deny the usage of the Audio cog in the "Red - Discord Bot"
    server.

    .. code-block:: none

        [p]p addglobalrule deny Audio "Red - Discord Bot"

*   This will allow the usage of the ban command for the user Twentysix. He
    will be able to use that command on every server.

    .. code-block:: none

        [p]p addglobalrule allow ban @Twentysix#5252

.. _permissions-command-addguildrule:

""""""""""""""""""""""""
permissions addguildrule
""""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions addguildrule <allow_or_deny> <cog_or_command> <who_or_what>

**Description**

Creates a rule that will overwrites the current permissions for the
command. You can allow or deny the usage of a command or a cog for
a special member, a voice channel, a text channel or a role.

The rule will be server-wide and only be applied on the guild's members.

**Arguments**

*   |default-arg1|

*   |default-arg2|

*   |default-arg3|

**Examples**

*   This will allow the usage of the Audio cog in the "Music channel"
    voice channel.

    .. code-block:: none

        [p]p addguildrule allow Audio "Music channel"

*   This will deny the usage of the slot command in the #general channel.

    .. code-block:: none

        [p]p addguildrule deny slot #general

.. _permissions-command-removeglobalrule:

""""""""""""""""""""""""""""
permissions removeglobalrule
""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions removeglobalrule <allow_or_deny> <cog_or_command> <who_or_what>

**Description**

Remove something from the rules. You need to provide the same
arguments that you used when creating the rule using :ref:`addglobalrule
<permissions-command-addglobalrule>`.

This is used for global rules. For server-wide rules, check
:ref:`removeguildrule <permissions-command-removeguildrule>`.

**Arguments**

*   |default-arg1|

*   |default-arg2|

*   |default-arg3|

**Example**

*   This will remove the rule created in the previous example for
    :ref:`addglobalrule <permissions-command-addglobalrule>`.

    .. code-block:: none

        [p]p removeglobalrule deny Audio "Red - Discord Bot"

.. _permissions-command-removeguildrule:

"""""""""""""""""""""""""""
permissions removeguildrule
"""""""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions removeguildrule <allow_or_deny> <cog_or_command> <who_or_what>

**Description**

Remove something from the rules. You need to provide the same
arguments that you used when creating the rule using :ref:`addguildrule
<permissions-command-addguildrule>`.

This is used for server-wide rules. For global rules, check
:ref:`removeguildrule <permissions-command-removeglobalrule>`.

**Arguments**

*   |default-arg1|

*   |default-arg2|

*   |default-arg3|

**Example**

*   This will remove the rule created in the previous example for
    :ref:`addglobalrule <permissions-command-addguildrule>`.

    .. code-block:: none

        [p]p removeguildrule allow Audio "Music channel"

.. _permissions-command-setdefaultglobalrule:

""""""""""""""""""""""""""""""""
permissions setdefaultglobalrule
""""""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions setdefaultglobalrule <cog_or_command> [allow_or_deny]

**Description**

Set a default rule over a cog or a command. If no specific is found for
a command or a cog, that rule is applied. That rule will be global and
applied on all servers. For server-wide and non-global rules, check the
:ref:`setdefaultglobalrule <permissions-command-setdefaultguildrule>`
command.

This can be combined with other rules to make cog or commands only available
in specific destinations.

If you want to remove a default rule, omit the ``[allow_or_deny]`` argument.

**Arguments**

*   |default-arg2|

*   |default-arg1| If not given, you will remove an already existing rule for
    the given cog/command.

**Example**

*   This will remove the permission of using the ``Mod`` cog everywhere, except
    in the "Laggron's Dumb Cogs" server. It's also using the
    :ref:`addglobalrule <permissions-command-addglobalrule>` command.

    .. code-block:: none

        [p]p setdefaultglobalrule Mod deny
        [p]p addglobalrule allow Mod "Laggron's Dumb Cogs"

.. _permissions-command-setdefaultguildrule:

"""""""""""""""""""""""""""""""
permissions setdefaultguildrule
"""""""""""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions setdefaultguildrule <cog_or_command> [allow_or_deny]

**Description**

Set a default rule over a cog or a command. If no specific is found for
a command or a cog, that rule is applied. That rule will be only
server-specific and not global. For global rules, check the
:ref:`setdefaultglobalrule <permissions-command-setdefaultguildrule>`
command.

This can be combined with other rules to make cog or commands only available
in specific destinations.

If you want to remove a default rule, omit the ``[allow_or_deny]`` argument.

**Arguments**

*   |default-arg2|

*   |default-arg1| If not given, you will remove an already existing rule for
    the given cog/command.

**Example**

*   This will deny the usage of the ``Economy`` cog commands everywhere except
    for the role "Money games". It's also using the
    :ref:`addglobalrule <permissions-command-addglobalrule>` command.

    .. code-block:: none

        [p]p setdefaultguildrule Economy deny
        [p]p addguildrule allow Economy "Money games"

.. _permissions-command-setglobalacl:

""""""""""""""""""""""""
permissions setglobalacl
""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions setglobalacl

**Description**

Gets a YAML file to set rules from. You must upload the file with the
command.

The rules will be global. For server-wide rules, please check
:ref:`setguildacl <permissions-command-setguildacl>`.

.. warning:: Using this command will **reset** current rules. If you
    want to add new rules, use the :ref:`updateglobalacl
    <permissions-command-updateglobalacl>` command instead.

The YAML files works with IDs. Check :ref:`this <permissions-commands>` for
more informations about IDs.

Here is how to create one:

#.  Use any text editor (not Word, more something like TextEdit or Notepad++)
    and create a file with the ``.yaml`` extension. For example, let's create
    ``global permissions.yaml``.

#.  In that YAML file, the rules are divided into two categories:
    ``cogs`` and ``commands``. You will write the name of the categories
    in the file.

    .. code-block:: yaml

        cogs:
          # this is where you will set cog rules

        commands:
          # this is where you will set command rules

    .. note:: Lines that starts with a ``#`` are comments and ignored.

#.  Now you will be able to write rules for something. For example, if we want
    to deny the usage of the Audio cog everywhere except in the text channel
    #music-commands and in the voice channel "Bot music", this is what you will
    do with commands:

    .. code-block:: none

        [p]p setdefaultguildrule Audio deny
        [p]p addguildrule allow Audio #music-commands
        [p]p addguildrule allow Audio "Bot music"

    This is how you should format the rules if using the YAML files:

    .. code-block:: yaml

        cogs:
          Audio:
            default: deny
            allow:
              - 363010780385378306
              - 363031463349714945

**Example**

This is an example of a YAML which set the following rules:

- Admin allowed in x and denied in y
- Audio allowed in x and denied by default
- cleanup bot command allowed in x and denied by default
- ping command denied in x and allowed by default

.. code-block:: yaml

    cogs:
      Admin:
        allow:
          - 78631113035100160
        deny:
          - 96733288462286848
      Audio:
        allow:
          - 133049272517001216
        default: deny
    commands:
      cleanup bot:
        allow:
          - 78631113035100160
        default: deny
      ping:
        deny:
          - 96733288462286848
        default: allow

.. _permissions-command-setguildacl:

"""""""""""""""""""""""
permissions setguildacl
"""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions setguildacl

**Description**

Gets a YAML file to set rules from. You must upload the file with the
command.

The rules will be server-wide. For global rules, please check
:ref:`setglobaldacl <permissions-command-setglobalacl>`.

.. warning:: Using this command will **reset** current rukes. If you
    want to add new rules, use the :ref:`updateguildacl
    <permissions-command-updateguildacl>` command instead.

For more informations about YAML files, check
:ref:`this <permissions-command-setglobalacl>`.

.. _permissions-command-updateglobalacl:

"""""""""""""""""""""""""""
permissions updateglobalacl
"""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions updateglobalacl

**Description**

Add new rules with a YAML file. You must upload the file with the
command.

The rules will be global. For server-wide rules, please check
:ref:`updateguildacl <permissions-command-updateguildacl>`.

This command is the same as
:ref:`setglobalacl <permissions-command-setglobalacl>`, except it doesn't
overwrites the current rules, but extend them with what you gave.

.. _permissions-command-updateguildacl:

""""""""""""""""""""""""""
permissions updateguildacl
""""""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions updateguildacl

**Description**

Add new rules with a YAML file. You must upload the file with the
command.

The rules will be server-wide. For global rules, please check
:ref:`updateglobalacl <permissions-command-updateglobalacl>`.

This command is the same as
:ref:`setguildacl <permissions-command-setguildacl>`, except it doesn't
overwrites the current rules, but extend them with what you gave.

.. _permissions-command-getglobalacl:

""""""""""""""""""""""""
permissions getglobalacl
""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions getglobalacl

**Description**

Build and upload a YAML file from the current global rules.

.. tip:: You can edit this file, then send it back using the
    :ref:`setglobalacl <permissions-command-setglobalacl>` command.

.. _permissions-command-getguildacl:

"""""""""""""""""""""""
permissions getguildacl
"""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions getguildacl

**Description**

Build and upload a YAML file from the current server rules.

.. tip:: You can edit this file, then send it back using the
    :ref:`setguildacl <permissions-command-setguildacl>` command.

.. _permissions-command-clearglobalsettings:

"""""""""""""""""""""""""""""""
permissions clearglobalsettings
"""""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions clearglobalsettings

**Description**

Reset all global rules.

.. warning:: This cannot be undone.

.. _permissions-command-clearguildsettings:

""""""""""""""""""""""""""""""
permissions clearguildsettings
""""""""""""""""""""""""""""""

.. note:: |guildowner-lock| It will also work if you have the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]permissions clearguildsettings

**Description**

Reset all server rules.

.. warning:: This cannot be undone.

.. _permissions-command-canrun:

""""""""""""""""""
permissions canrun
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]permissions canrun <user> <command>

**Description**

Check if someone can run a command in the current location
(refers to text channel, voice channel, roles and server).

**Arguments**

*   ``<user>``: The user to test.

*   ``<command>``: The command to check.

.. _permissions-command-explain:

"""""""""""""""""""
permissions explain
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]permissions explain

**Description**

Print a short description of how the cog works.
