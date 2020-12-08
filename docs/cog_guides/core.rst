.. _core:

====
Core
====

This is the cog guide for the core cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load core

.. _core-usage:

-----
Usage
-----

Commands related to core functions.


.. _core-commands:

--------
Commands
--------

.. _core-command-allowlist:

^^^^^^^^^
allowlist
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]allowlist 

.. tip:: Alias: ``whitelist``

**Description**

Allowlist management commands.

.. _core-command-allowlist-add:

"""""""""""""
allowlist add
"""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist add <user>...

**Description**

Adds a user to the allowlist.

.. _core-command-allowlist-clear:

"""""""""""""""
allowlist clear
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist clear 

**Description**

Clears the allowlist.

.. _core-command-allowlist-list:

""""""""""""""
allowlist list
""""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist list 

**Description**

Lists users on the allowlist.

.. _core-command-allowlist-remove:

""""""""""""""""
allowlist remove
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist remove <user>...

**Description**

Removes user from the allowlist.

.. _core-command-autoimmune:

^^^^^^^^^^
autoimmune
^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]autoimmune 

**Description**

Server settings for immunity from automated actions.

.. _core-command-autoimmune-add:

""""""""""""""
autoimmune add
""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune add <user_or_role>

**Description**

Makes a user or role immune from automated moderation actions.

.. _core-command-autoimmune-isimmune:

"""""""""""""""""""
autoimmune isimmune
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune isimmune <user_or_role>

**Description**

Checks if a user or role would be considered immune from automated actions.

.. _core-command-autoimmune-list:

"""""""""""""""
autoimmune list
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune list 

**Description**

Gets the current members and roles configured for automatic
moderation action immunity.

.. _core-command-autoimmune-remove:

"""""""""""""""""
autoimmune remove
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune remove <user_or_role>

**Description**

Makes a user or role immune from automated moderation actions.

.. _core-command-blocklist:

^^^^^^^^^
blocklist
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]blocklist 

.. tip:: Aliases: ``blacklist``, ``denylist``

**Description**

Blocklist management commands.

.. _core-command-blocklist-add:

"""""""""""""
blocklist add
"""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist add <user>...

**Description**

Adds a user to the blocklist.

.. _core-command-blocklist-clear:

"""""""""""""""
blocklist clear
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist clear 

**Description**

Clears the blocklist.

.. _core-command-blocklist-list:

""""""""""""""
blocklist list
""""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist list 

**Description**

Lists users on the blocklist.

.. _core-command-blocklist-remove:

""""""""""""""""
blocklist remove
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist remove <user>...

**Description**

Removes user from the blocklist.

.. _core-command-command:

^^^^^^^
command
^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]command 

**Description**

Manage the bot's commands and cogs.

.. _core-command-command-defaultdisablecog:

"""""""""""""""""""""""""
command defaultdisablecog
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command defaultdisablecog <cogname>

**Description**

Set the default state for a cog as disabled.

.. _core-command-command-defaultenablecog:

""""""""""""""""""""""""
command defaultenablecog
""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command defaultenablecog <cogname>

**Description**

Set the default state for a cog as enabled.

.. _core-command-command-disable:

"""""""""""""""
command disable
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]command disable <command>

**Description**

Disable a command.

If you're the bot owner, this will disable commands
globally by default.

.. _core-command-command-disable-global:

""""""""""""""""""""""
command disable global
""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command disable global <command>

**Description**

Disable a command globally.

.. _core-command-command-disable-server:

""""""""""""""""""""""
command disable server
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command disable server <command>

.. tip:: Alias: ``command disable guild``

**Description**

Disable a command in this server only.

.. _core-command-command-disablecog:

""""""""""""""""""
command disablecog
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command disablecog <cogname>

**Description**

Disable a cog in this guild.

.. _core-command-command-disabledmsg:

"""""""""""""""""""
command disabledmsg
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command disabledmsg [message]

**Description**

Set the bot's response to disabled commands.

Leave blank to send nothing.

To include the command name in the message, include the
``{command}`` placeholder.

.. _core-command-command-enable:

""""""""""""""
command enable
""""""""""""""

**Syntax**

.. code-block:: none

    [p]command enable <command>

**Description**

Enable a command.

If you're a bot owner, this will try to enable a globally
disabled command by default.

.. _core-command-command-enable-global:

"""""""""""""""""""""
command enable global
"""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command enable global <command>

**Description**

Enable a command globally.

.. _core-command-command-enable-server:

"""""""""""""""""""""
command enable server
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command enable server <command>

.. tip:: Alias: ``command enable guild``

**Description**

Enable a command in this server.

.. _core-command-command-enablecog:

"""""""""""""""""
command enablecog
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command enablecog <cogname>

**Description**

Enable a cog in this guild.

.. _core-command-command-listdisabled:

""""""""""""""""""""
command listdisabled
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabled 

**Description**

List disabled commands.

If you're the bot owner, this will show global disabled commands by default.

.. _core-command-command-listdisabled-global:

"""""""""""""""""""""""""""
command listdisabled global
"""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabled global 

**Description**

List disabled commands globally.

.. _core-command-command-listdisabled-guild:

""""""""""""""""""""""""""
command listdisabled guild
""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabled guild 

**Description**

List disabled commands in this server.

.. _core-command-command-listdisabledcogs:

""""""""""""""""""""""""
command listdisabledcogs
""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabledcogs 

**Description**

List the cogs which are disabled in this guild.

.. _core-command-contact:

^^^^^^^
contact
^^^^^^^

**Syntax**

.. code-block:: none

    [p]contact <message>

**Description**

Sends a message to the owner.

.. _core-command-dm:

^^
dm
^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]dm <user_id> <message>

**Description**

Sends a DM to a user.

This command needs a user ID to work.
To get a user ID, go to Discord's settings and open the
'Appearance' tab. Enable 'Developer Mode', then right click
a user and click on 'Copy ID'.

.. _core-command-embedset:

^^^^^^^^
embedset
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]embedset 

**Description**

Commands for toggling embeds on or off.

This setting determines whether or not to use embeds as a response to a command (for commands that support it).
The default is to use embeds.

.. _core-command-embedset-channel:

""""""""""""""""
embedset channel
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]embedset channel [enabled]

**Description**

Toggle the channel's embed setting.

If enabled is None, the setting will be unset and
the guild default will be used instead.

If set, this is used instead of the guild default
to determine whether or not to use embeds. This is
used for all commands done in a channel except
for help commands.

Examples:
    - ``[p]embedset channel False`` - Disables embeds in this channel.
    - ``[p]embedset channel`` - Resets value to use guild default.

**Arguments:**

- ``[enabled]`` Whether to use embeds in this channel. Leave blank to reset to default.

.. _core-command-embedset-global:

"""""""""""""""
embedset global
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]embedset global 

**Description**

Toggle the global embed setting.

This is used as a fallback if the user or guild hasn't set a preference.
The default is to use embeds.

.. _core-command-embedset-server:

"""""""""""""""
embedset server
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]embedset server [enabled]

.. tip:: Alias: ``embedset guild``

**Description**

Toggle the guild's embed setting.

If enabled is None, the setting will be unset and
the global default will be used instead.

If set, this is used instead of the global default
to determine whether or not to use embeds. This is
used for all commands done in a guild channel except
for help commands.

Examples:
    - ``[p]embedset server False`` - Disables embeds on this server.
    - ``[p]embedset server`` - Resets value to use global default.

**Arguments:**

- ``[enabled]`` Whether to use embeds on this server. Leave blank to reset to default.

.. _core-command-embedset-showsettings:

"""""""""""""""""""""
embedset showsettings
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]embedset showsettings 

**Description**

Show the current embed settings.

.. _core-command-embedset-user:

"""""""""""""
embedset user
"""""""""""""

**Syntax**

.. code-block:: none

    [p]embedset user [enabled]

**Description**

Toggle the user's embed setting for DMs.

If enabled is None, the setting will be unset and
the global default will be used instead.

If set, this is used instead of the global default
to determine whether or not to use embeds. This is
used for all commands executed in a DM with the bot.

Examples:
    - ``[p]embedset user False`` - Disables embeds in your DMs.
    - ``[p]embedset user`` - Resets value to use global default.

**Arguments:**

- ``[enabled]`` Whether to use embeds in your DMs. Leave blank to reset to default.

.. _core-command-helpset:

^^^^^^^
helpset
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]helpset 

**Description**

Manage settings for the help command.

.. _core-command-helpset-deletedelay:

"""""""""""""""""""
helpset deletedelay
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset deletedelay <seconds>

**Description**

Set the delay after which help pages will be deleted.

The setting is disabled by default, and only applies to non-menu help,
sent in server text channels.
Setting the delay to 0 disables this feature.

The bot has to have MANAGE_MESSAGES permission for this to work.

.. _core-command-helpset-maxpages:

""""""""""""""""
helpset maxpages
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset maxpages <pages>

**Description**

Set the maximum number of help pages sent in a server channel.

This setting does not apply to menu help.

If a help message contains more pages than this value, the help message will
be sent to the command author via DM. This is to help reduce spam in server
text channels.

The default value is 2 pages.

.. _core-command-helpset-pagecharlimit:

"""""""""""""""""""""
helpset pagecharlimit
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset pagecharlimit <limit>

**Description**

Set the character limit for each page in the help message.

This setting only applies to embedded help.

The default value is 1000 characters. The minimum value is 500.
The maximum is based on the lower of what you provide and what discord allows.

Please note that setting a relatively small character limit may
mean some pages will exceed this limit.

.. _core-command-helpset-resetformatter:

""""""""""""""""""""""
helpset resetformatter
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset resetformatter 

**Description**

This resets Red's help formatter to the default formatter. 

.. _core-command-helpset-resetsettings:

"""""""""""""""""""""
helpset resetsettings
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset resetsettings 

**Description**

This resets Red's help settings to their defaults.

This may not have an impact when using custom formatters from 3rd party cogs

.. _core-command-helpset-showhidden:

""""""""""""""""""
helpset showhidden
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset showhidden [show_hidden]

**Description**

This allows the help command to show hidden commands.

This defaults to False.
Using this without a setting will toggle.

.. _core-command-helpset-showsettings:

""""""""""""""""""""
helpset showsettings
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset showsettings 

**Description**

Show the current help settings. 

.. _core-command-helpset-tagline:

"""""""""""""""
helpset tagline
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset tagline [tagline]

**Description**

Set the tagline to be used.

This setting only applies to embedded help. If no tagline is
specified, the default will be used instead.

.. _core-command-helpset-usemenus:

""""""""""""""""
helpset usemenus
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset usemenus [use_menus]

**Description**

Allows the help command to be sent as a paginated menu instead of separate
messages.

This defaults to False.
Using this without a setting will toggle.

.. _core-command-helpset-usetick:

"""""""""""""""
helpset usetick
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset usetick [use_tick]

**Description**

This allows the help command message to be ticked if help is sent in a DM.

Defaults to False.
Using this without a setting will toggle.

.. _core-command-helpset-verifychecks:

""""""""""""""""""""
helpset verifychecks
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset verifychecks [verify]

**Description**

Sets if commands which can't be run in the current context should be
filtered from help.

Defaults to True.
Using this without a setting will toggle.

.. _core-command-helpset-verifyexists:

""""""""""""""""""""
helpset verifyexists
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset verifyexists [verify]

**Description**

This allows the bot to respond indicating the existence of a specific
help topic even if the user can't use it.

.. Note:: This setting on it's own does not fully prevent command enumeration.


Defaults to False.
Using this without a setting will toggle.

.. _core-command-ignore:

^^^^^^
ignore
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]ignore 

**Description**

Add servers or channels to the ignore list.

.. _core-command-ignore-channel:

""""""""""""""
ignore channel
""""""""""""""

**Syntax**

.. code-block:: none

    [p]ignore channel [channel]

**Description**

Ignore commands in the channel or category.

Defaults to the current channel.

.. _core-command-ignore-list:

"""""""""""
ignore list
"""""""""""

**Syntax**

.. code-block:: none

    [p]ignore list 

**Description**

List the currently ignored servers and channels.

.. _core-command-ignore-server:

"""""""""""""
ignore server
"""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]ignore server 

.. tip:: Alias: ``ignore guild``

**Description**

Ignore commands in this server.

.. _core-command-info:

^^^^
info
^^^^

**Syntax**

.. code-block:: none

    [p]info 

**Description**

Shows info about Red.

See ``[p]custominfo`` to customize.

.. _core-command-invite:

^^^^^^
invite
^^^^^^

**Syntax**

.. code-block:: none

    [p]invite 

**Description**

Shows Red's invite url.

This will always send the invite to DMs to keep it private.

This command is locked to the owner unless ``[p]inviteset public`` is set to True.

.. _core-command-inviteset:

^^^^^^^^^
inviteset
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]inviteset 

**Description**

Commands to setup Red's invite settings.

.. _core-command-inviteset-perms:

"""""""""""""""
inviteset perms
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]inviteset perms <level>

**Description**

Make the bot create its own role with permissions on join.

The bot will create its own role with the desired permissions        when it joins a new server. This is a special role that can't be        deleted or removed from the bot.

For that, you need to provide a valid permissions level.
You can generate one here: https://discordapi.com/permissions.html

Please note that you might need two factor authentication for        some permissions.

Example:
    - ``[p]inviteset perms 134217728`` - Adds a "Manage Nicknames" permission requirement to the invite.

**Arguments:**

- ``<level>`` The permission level to require for the bot in the generated invite.

.. _core-command-inviteset-public:

""""""""""""""""
inviteset public
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]inviteset public [confirm=False]

**Description**

Toggles if ``[p]invite`` should be accessible for the average user.

Bot must me made into a ``Public bot`` in the developer dashboard for public invites to work.

Example:
    - ``[p]inviteset public yes`` - Toggles the public invite setting.

**Arguments:**

- ``[confirm]`` Required to set to public. Not required to toggle back to private.

.. _core-command-leave:

^^^^^
leave
^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]leave 

**Description**

Leaves the current server.

.. Note:: This command is interactive.


.. _core-command-licenseinfo:

^^^^^^^^^^^
licenseinfo
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]licenseinfo 

.. tip:: Alias: ``licenceinfo``

**Description**

Get info about Red's licenses.

.. _core-command-load:

^^^^
load
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]load [cogs...]

**Description**

Loads cog packages from the local paths and installed cogs.

See packages available to load with ``[p]cogs``.

Additional cogs can be added using Downloader, or from local paths using ``[p]addpath``.

Examples:
    - ``[p]load general`` - Loads the ``general`` cog.
    - ``[p]load admin mod mutes`` - Loads multiple cogs.

**Arguments:**

- ``[cogs...]`` The cog packages to load.

.. _core-command-localallowlist:

^^^^^^^^^^^^^^
localallowlist
^^^^^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]localallowlist 

.. tip:: Alias: ``localwhitelist``

**Description**

Server specific allowlist management commands.

.. _core-command-localallowlist-add:

""""""""""""""""""
localallowlist add
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist add <user_or_role>...

**Description**

Adds a user or role to the server allowlist.

.. _core-command-localallowlist-clear:

""""""""""""""""""""
localallowlist clear
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist clear 

**Description**

Clears the allowlist.

.. _core-command-localallowlist-list:

"""""""""""""""""""
localallowlist list
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist list 

**Description**

Lists users and roles on the  server allowlist.

.. _core-command-localallowlist-remove:

"""""""""""""""""""""
localallowlist remove
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist remove <user_or_role>...

**Description**

Removes user or role from the allowlist.

.. _core-command-localblocklist:

^^^^^^^^^^^^^^
localblocklist
^^^^^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]localblocklist 

.. tip:: Alias: ``localblacklist``

**Description**

Server specific blocklist management commands.

.. _core-command-localblocklist-add:

""""""""""""""""""
localblocklist add
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist add <user_or_role>...

**Description**

Adds a user or role to the blocklist.

.. _core-command-localblocklist-clear:

""""""""""""""""""""
localblocklist clear
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist clear 

**Description**

Clears the server blocklist.

.. _core-command-localblocklist-list:

"""""""""""""""""""
localblocklist list
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist list 

**Description**

Lists users and roles on the blocklist.

.. _core-command-localblocklist-remove:

"""""""""""""""""""""
localblocklist remove
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist remove <user_or_role>...

**Description**

Removes user or role from blocklist.

.. _core-command-mydata:

^^^^^^
mydata
^^^^^^

**Syntax**

.. code-block:: none

    [p]mydata 

**Description**

Commands which interact with the data Red has about you.

More information can be found in the :doc:`End User Data Documentation.<../red_core_data_statement>`

.. _core-command-mydata-3rdparty:

"""""""""""""""
mydata 3rdparty
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata 3rdparty 

**Description**

View the End User Data statements of each 3rd-party module.

This will send an attachment with the End User Data statements of all loaded 3rd party cog.

.. _core-command-mydata-forgetme:

"""""""""""""""
mydata forgetme
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata forgetme 

**Description**

Have Red forget what it knows about you.

This may not remove all data about you, data needed for operation,
such as command cooldowns will be kept until no longer necessary.

Further interactions with Red may cause it to learn about you again.

.. _core-command-mydata-getmydata:

""""""""""""""""
mydata getmydata
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata getmydata 

**Description**

[Coming Soon] Get what data Red has about you.

.. _core-command-mydata-ownermanagement:

""""""""""""""""""""""
mydata ownermanagement
""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement 

**Description**

Commands for more complete data handling.

.. _core-command-mydata-ownermanagement-allowuserdeletions:

"""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement allowuserdeletions
"""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement allowuserdeletions 

**Description**

Set the bot to allow users to request a data deletion.

This is on by default.
Opposite of ``[p]mydata ownermanagement disallowuserdeletions``

.. _core-command-mydata-ownermanagement-deleteforuser:

""""""""""""""""""""""""""""""""""""
mydata ownermanagement deleteforuser
""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement deleteforuser <user_id>

**Description**

Delete data Red has about a user for a user.

This will cause the bot to get rid of or disassociate a lot of non-operational data from the specified user.
Users have access to different command for this unless they can't interact with the bot at all.
This is a mostly safe operation, but you should not use it unless processing a request from this user as it may impact their usage of the bot.

**Arguments:**

- ``<user_id>`` The id of the user whose data would be deleted.

.. _core-command-mydata-ownermanagement-deleteuserasowner:

""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement deleteuserasowner
""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement deleteuserasowner <user_id>

**Description**

Delete data Red has about a user.

This will cause the bot to get rid of or disassociate a lot of data about the specified user.
This may include more than just end user data, including anti abuse records.

**Arguments:**

- ``<user_id>`` The id of the user whose data would be deleted.

.. _core-command-mydata-ownermanagement-disallowuserdeletions:

""""""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement disallowuserdeletions
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement disallowuserdeletions 

**Description**

Set the bot to not allow users to request a data deletion.

Opposite of ``[p]mydata ownermanagement allowuserdeletions``

.. _core-command-mydata-ownermanagement-processdiscordrequest:

""""""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement processdiscordrequest
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement processdiscordrequest <user_id>

**Description**

Handle a deletion request from Discord.

This will cause the bot to get rid of or disassociate all data from the specified user ID.
You should not use this unless Discord has specifically requested this with regard to a deleted user.
This will remove the user from various anti-abuse measures.
If you are processing a manual request from a user, you may want ``[p]mydata ownermanagement deleteforuser`` instead.

**Arguments:**

- ``<user_id>`` The id of the user whose data would be deleted.

.. _core-command-mydata-ownermanagement-setuserdeletionlevel:

"""""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement setuserdeletionlevel
"""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement setuserdeletionlevel <level>

**Description**

Sets how user deletions are treated.

Example:
    - ``[p]mydata ownermanagement setuserdeletionlevel 1``

**Arguments:**

- ``<level>`` The strictness level for user deletion. See Level guide below.

Level:
    - ``0``: What users can delete is left entirely up to each cog.
    - ``1``: Cogs should delete anything the cog doesn't need about the user.

.. _core-command-mydata-whatdata:

"""""""""""""""
mydata whatdata
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata whatdata 

**Description**

Find out what type of data Red stores and why.

.. _core-command-reload:

^^^^^^
reload
^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]reload [cogs...]

**Description**

Reloads cog packages.

This will unload and then load the specified cogs.

Cogs that were not loaded will be loaded.

Examples:
    - ``[p]reload general`` - Unloads then loads the ``general`` cog.
    - ``[p]reload admin mod mutes`` - Unloads then loads multiple cogs.

**Arguments:**

- ``[cogs...]`` The cog packages to unload.

.. _core-command-restart:

^^^^^^^
restart
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]restart [silently=False]

**Description**

Attempts to restart Red.

Makes Red quit with exit code 26.
The restart is not guaranteed: it must be dealt with by the process manager in use.

.. _core-command-servers:

^^^^^^^
servers
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]servers 

**Description**

Lists and allows Red to leave servers.

.. Note:: This command is interactive.


.. _core-command-set:

^^^
set
^^^

**Syntax**

.. code-block:: none

    [p]set 

**Description**

Commands for changing Red's settings.

.. _core-command-set-addadminrole:

""""""""""""""""
set addadminrole
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set addadminrole <role>

**Description**

Adds an admin role for this guild.

Admins have all the same access and Mods, plus additional admin level commands like:
 - ``[p]set serverprefix``
 - ``[p]addrole``
 - ``[p]ban``
 - ``[p]ignore guild``

 And more.

 Examples:
    - ``[p]set addadminrole @Admins``
    - ``[p]set addadminrole Super Admins``

**Arguments:**

- ``<role>`` The role to add as an admin.

.. _core-command-set-addmodrole:

""""""""""""""
set addmodrole
""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set addmodrole <role>

**Description**

Adds a moderator role for this guild.

This grants access to moderator level commands like:
 - ``[p]mute``
 - ``[p]cleanup``
 - ``[p]customcommand create``

 And more.

 Examples:
    - ``[p]set addmodrole @Mods``
    - ``[p]set addmodrole Loyal Helpers``

**Arguments:**

- ``<role>`` The role to add as a moderator.

.. _core-command-set-api:

"""""""
set api
"""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set api <service> <tokens>

**Description**

Set, list or remove various external API tokens.

This setting will be asked for by some 3rd party cogs and some core cogs.

To add the keys provide the service name and the tokens as a comma separated
list of key,values as described by the cog requesting this command.

.. Note:: API tokens are sensitive and should only be used in a private channel

or in DM with the bot.

.. _core-command-set-api-list:

""""""""""""
set api list
""""""""""""

**Syntax**

.. code-block:: none

    [p]set api list 

**Description**

Show all external API services along with their keys that have been set.

Secrets are not shown.

.. _core-command-set-api-remove:

""""""""""""""
set api remove
""""""""""""""

**Syntax**

.. code-block:: none

    [p]set api remove [services...]

**Description**

Remove the given services with all their keys and tokens.

.. _core-command-set-avatar:

""""""""""
set avatar
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set avatar [url]

**Description**

Sets Red's avatar

Supports either an attachment or an image URL.

Examples:
    - ``[p]set avatar`` - With an image attachment, this will set the avatar.
    - ``[p]set avatar`` - Without an attachment, this will show the command help.
    - ``[p]set avatar https://links.flaree.xyz/k95`` - Sets the avatar to the provided url.

**Arguments:**

- ``[url]`` An image url to be used as an avatar. Leave blank when uploading an attachment.

.. _core-command-set-avatar-remove:

"""""""""""""""""
set avatar remove
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set avatar remove 

.. tip:: Alias: ``set avatar clear``

**Description**

Removes Red's avatar.

.. _core-command-set-colour:

""""""""""
set colour
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set colour [colour]

.. tip:: Alias: ``set color``

**Description**

Sets a default colour to be used for the bot's embeds.

Acceptable values for the colour parameter can be found at:

https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.ColourConverter

Examples:
    - ``[p]set colour dark red``
    - ``[p]set colour blurple``
    - ``[p]set colour 0x5DADE2``
    - ``[p]set color 0x#FDFEFE``
    - ``[p]set color #7F8C8D``

**Arguments:**

- ``[colour]`` The colour to use for embeds. Leave blank to set to the default value (red).

.. _core-command-set-competing:

"""""""""""""
set competing
"""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set competing [competing]

**Description**

Sets Red's competing status.

.. _core-command-set-custominfo:

""""""""""""""
set custominfo
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set custominfo [text]

**Description**

Customizes a section of ``[p]info``.

The maximum amount of allowed characters is 1024.
Supports markdown, links and "mentions".
Link example:
```My link <https://example.com>`_``

.. _core-command-set-deletedelay:

"""""""""""""""
set deletedelay
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set deletedelay [time]

**Description**

Set the delay until the bot removes the command message.

Must be between -1 and 60.

Set to -1 to disable this feature.

This is applied only the current server and not globally.

Examples:
    - ``[p]set deletedelay`` - Shows the current delete delay setting.
    - ``[p]set deletedelay 60`` - Sets the delete delay to the max of 60 seconds.
    - ``[p]set deletedelay -1`` - Disables deleting command messages.

**Arguments:**

- ``[time]`` The seconds to wait before deleting the command message. Use -1 to disable.

.. _core-command-set-description:

"""""""""""""""
set description
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set description [description]

**Description**

Sets the bot's description.
Use without a description to reset.
This is shown in a few locations, including the help menu.

The maximum description length is 250 characters to ensure it displays properly.

The default is "Red V3".

Examples:
    - ``[p]set description`` - Resets the description to the default setting.
    - ``[p]set description MyBot: A Red V3 Bot``

**Arguments:**

- ``[time]`` The seconds to wait before deleting the command message. Use -1 to disable.

.. _core-command-set-fuzzy:

"""""""""
set fuzzy
"""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set fuzzy 

**Description**

Toggle whether to enable fuzzy command search in DMs.

This allows the bot to identify potential misspelled commands and offer corrections.

Default is for fuzzy command search to be disabled.

.. _core-command-set-globallocale:

""""""""""""""""
set globallocale
""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set globallocale <language_code>

**Description**

Changes the bot's default locale.
This will be used when a server has not set a locale, or in DMs.

``<language_code>`` can be any language code with country code included,
e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.

Go to Red's Crowdin page to see locales that are available with translations:
https://translate.discord.red

To reset to English, use "en-US".

.. _core-command-set-globalregionalformat:

""""""""""""""""""""""""
set globalregionalformat
""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set globalregionalformat [language_code]

.. tip:: Alias: ``set globalregion``

**Description**

Changes bot's regional format. This is used for formatting date, time and numbers.

``<language_code>`` can be any language code with country code included,
e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.

Leave ``<language_code>`` empty to base regional formatting on bot's locale.

.. _core-command-set-listening:

"""""""""""""
set listening
"""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set listening [listening]

**Description**

Sets Red's listening status.

.. _core-command-set-locale:

""""""""""
set locale
""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set locale <language_code>

**Description**

Changes the bot's locale in this server.

``<language_code>`` can be any language code with country code included,
e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.

Go to Red's Crowdin page to see locales that are available with translations:
https://translate.discord.red

Use "default" to return to the bot's default set language.
To reset to English, use "en-US".

.. _core-command-set-nickname:

""""""""""""
set nickname
""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]set nickname [nickname]

**Description**

Sets Red's nickname.

.. _core-command-set-ownernotifications:

""""""""""""""""""""""
set ownernotifications
""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set ownernotifications 

**Description**

Commands for configuring owner notifications.

.. _core-command-set-ownernotifications-adddestination:

"""""""""""""""""""""""""""""""""""""
set ownernotifications adddestination
"""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications adddestination <channel>

**Description**

Adds a destination text channel to receive owner notifications.

.. _core-command-set-ownernotifications-listdestinations:

"""""""""""""""""""""""""""""""""""""""
set ownernotifications listdestinations
"""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications listdestinations 

**Description**

Lists the configured extra destinations for owner notifications.

.. _core-command-set-ownernotifications-optin:

""""""""""""""""""""""""""""
set ownernotifications optin
""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications optin 

**Description**

Opt-in on receiving owner notifications.

This is the default state.

.. _core-command-set-ownernotifications-optout:

"""""""""""""""""""""""""""""
set ownernotifications optout
"""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications optout 

**Description**

Opt-out of receiving owner notifications.

.. _core-command-set-ownernotifications-removedestination:

""""""""""""""""""""""""""""""""""""""""
set ownernotifications removedestination
""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications removedestination <channel>

.. tip:: Aliases: ``set ownernotifications remdestination``, ``set ownernotifications deletedestination``, ``set ownernotifications deldestination``

**Description**

Removes a destination text channel from receiving owner notifications.

.. _core-command-set-playing:

"""""""""""
set playing
"""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set playing [game]

.. tip:: Alias: ``set game``

**Description**

Sets Red's playing status.

.. _core-command-set-prefix:

""""""""""
set prefix
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set prefix [prefixes...]

.. tip:: Alias: ``set prefixes``

**Description**

Sets Red's global prefix(es).

.. _core-command-set-regionalformat:

""""""""""""""""""
set regionalformat
""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set regionalformat [language_code]

.. tip:: Alias: ``set region``

**Description**

Changes bot's regional format in this server. This is used for formatting date, time and numbers.

``<language_code>`` can be any language code with country code included,
e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.

Leave ``<language_code>`` empty to base regional formatting on bot's locale in this server.

.. _core-command-set-removeadminrole:

"""""""""""""""""""
set removeadminrole
"""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set removeadminrole <role>

.. tip:: Aliases: ``set remadmindrole``, ``set deladminrole``, ``set deleteadminrole``

**Description**

Removes an admin role for this guild.

Examples:
    - ``[p]set removeadminrole @Admins``
    - ``[p]set removeadminrole Super Admins``

**Arguments:**

- ``<role>`` The role to remove from being an admin.

.. _core-command-set-removemodrole:

"""""""""""""""""
set removemodrole
"""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set removemodrole <role>

.. tip:: Aliases: ``set remmodrole``, ``set delmodrole``, ``set deletemodrole``

**Description**

Removes a mod role for this guild.

Examples:
    - ``[p]set removemodrole @Mods``
    - ``[p]set removemodrole Loyal Helpers``

**Arguments:**

- ``<role>`` The role to remove from being a moderator.

.. _core-command-set-serverfuzzy:

"""""""""""""""
set serverfuzzy
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set serverfuzzy 

**Description**

Toggle whether to enable fuzzy command search for the server.

This allows the bot to identify potential misspelled commands and offer corrections.

.. Note:: This can be processor intensive and may be unsuitable for larger servers.


Default is for fuzzy command search to be disabled.

.. _core-command-set-serverprefix:

""""""""""""""""
set serverprefix
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]set serverprefix [prefixes...]

.. tip:: Alias: ``set serverprefixes``

**Description**

Sets Red's server prefix(es).

.. _core-command-set-showsettings:

""""""""""""""""
set showsettings
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set showsettings 

**Description**

Show the current settings for Red.

.. _core-command-set-status:

""""""""""
set status
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status <status>

**Description**

Sets Red's status.

Available statuses:
    online
    idle
    dnd
    invisible

.. _core-command-set-streaming:

"""""""""""""
set streaming
"""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set streaming [streamer] [stream_title]

.. tip:: Alias: ``set stream``

**Description**

Sets Red's streaming status.

Leaving both streamer and stream_title empty will clear it.

.. _core-command-set-usebotcolour:

""""""""""""""""
set usebotcolour
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set usebotcolour 

.. tip:: Alias: ``set usebotcolor``

**Description**

Toggle whether to use the bot owner-configured colour for embeds.

Default is to use the bot's configured colour.
Otherwise, the colour used will be the colour of the bot's top role.

.. _core-command-set-username:

""""""""""""
set username
""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set username <username>

.. tip:: Alias: ``set name``

**Description**

Sets Red's username.

.. _core-command-set-watching:

""""""""""""
set watching
""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set watching [watching]

**Description**

Sets Red's watching status.

.. _core-command-shutdown:

^^^^^^^^
shutdown
^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]shutdown [silently=False]

**Description**

Shuts down the bot.

Allows Red to shut down gracefully.

This is the recommended method for shutting down the bot.

.. _core-command-traceback:

^^^^^^^^^
traceback
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]traceback [public=False]

**Description**

Sends to the owner the last command exception that has occurred.

If public (yes is specified), it will be sent to the chat instead.

.. Warning:: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.


Examples:
    - ``[p]traceback`` - Sends the traceback to your DMs.
    - ``[p]traceback True`` - Sends the last traceback in the current context.

**Arguments:**

- ``[public]`` Whether to send traceback to the current context. Leave blank to send to DMs.

.. _core-command-unignore:

^^^^^^^^
unignore
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unignore 

**Description**

Remove servers or channels from the ignore list.

.. _core-command-unignore-channel:

""""""""""""""""
unignore channel
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]unignore channel [channel]

**Description**

Remove a channel or category from the ignore list.

Defaults to the current channel.

.. _core-command-unignore-server:

"""""""""""""""
unignore server
"""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unignore server 

.. tip:: Alias: ``unignore guild``

**Description**

Remove this server from the ignore list.

.. _core-command-unload:

^^^^^^
unload
^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]unload [cogs...]

**Description**

Unloads previously loaded cog packages.

See packages available to unload with ``[p]cogs``.

Examples:
    - ``[p]unload general`` - Unloads the ``general`` cog.
    - ``[p]unload admin mod mutes`` - Unloads multiple cogs.

**Arguments:**

- ``[cogs...]`` The cog packages to unload.

.. _core-command-uptime:

^^^^^^
uptime
^^^^^^

**Syntax**

.. code-block:: none

    [p]uptime 

**Description**

Shows Red's uptime.
