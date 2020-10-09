.. _mod:

===
Mod
===

This is the cog guide for the mod cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load mod

.. _mod-usage:

-----
Usage
-----

Moderation tools.


.. _mod-commands:

--------
Commands
--------

.. _mod-command-slowmode:

^^^^^^^^
slowmode
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]slowmode [interval=0:00:00]

**Description**

Changes channel's slowmode setting.

Interval can be anything from 0 seconds to 6 hours.
Use without parameters to disable.

.. _mod-command-rename:

^^^^^^
rename
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]rename <user> [nickname]

**Description**

Change a user's nickname.

Leaving the nickname empty will remove it.

.. _mod-command-userinfo:

^^^^^^^^
userinfo
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]userinfo [user]

**Description**

Show information about a user.

This includes fields for status, discord join date, server
join date, voice state and previous names/nicknames.

If the user has no roles, previous names or previous nicknames,
these fields will be omitted.

.. _mod-command-names:

^^^^^
names
^^^^^

**Syntax**

.. code-block:: none

    [p]names <user>

**Description**

Show previous names and nicknames of a user.

.. _mod-command-voiceunban:

^^^^^^^^^^
voiceunban
^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]voiceunban <user> [reason]

**Description**

Unban a user from speaking and listening in the server's voice channels.

.. _mod-command-voiceban:

^^^^^^^^
voiceban
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]voiceban <user> [reason]

**Description**

Ban a user from speaking and listening in the server's voice channels.

.. _mod-command-mute:

^^^^
mute
^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mute 

**Description**

Mute users.

.. _mod-command-mute-voice:

^^^^^
voice
^^^^^

**Syntax**

.. code-block:: none

    [p]mute voice <user> [reason]

**Description**

Mute a user in their current voice channel.

.. _mod-command-mute-channel:

^^^^^^^
channel
^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mute channel <user> [reason]

**Description**

Mute a user in the current text channel.

.. _mod-command-mute-server:

^^^^^^
server
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mute server <user> [reason]

**Description**

Mutes user in the server.

.. _mod-command-unmute:

^^^^^^
unmute
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmute 

**Description**

Unmute users.

.. _mod-command-unmute-channel:

^^^^^^^
channel
^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmute channel <user> [reason]

**Description**

Unmute a user in this channel.

.. _mod-command-unmute-server:

^^^^^^
server
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmute server <user> [reason]

**Description**

Unmute a user in this server.

.. _mod-command-unmute-voice:

^^^^^
voice
^^^^^

**Syntax**

.. code-block:: none

    [p]unmute voice <user> [reason]

**Description**

Unmute a user in their current voice channel.

.. _mod-command-kick:

^^^^
kick
^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]kick <user> [reason]

**Description**

Kick a user.

If a reason is specified, it will be the reason that shows up
in the audit log.

.. _mod-command-ban:

^^^
ban
^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]ban <user> [days] [reason]

**Description**

Ban a user from this server and optionally delete days of messages.

If days is not a number, it's treated as the first word of the reason.

Minimum 0 days, maximum 7. If not specified, defaultdays setting will be used instead.

.. _mod-command-hackban:

^^^^^^^
hackban
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]hackban [user_ids]... [days] [reason]

**Description**

Preemptively bans user(s) from the server.

User IDs need to be provided in order to ban
using this command.

.. _mod-command-tempban:

^^^^^^^
tempban
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]tempban <user> [duration=1 day, 0:00:00] [days] [reason]

**Description**

Temporarily ban a user from this server.

.. _mod-command-softban:

^^^^^^^
softban
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]softban <user> [reason]

**Description**

Kick a user and delete 1 day's worth of their messages.

.. _mod-command-voicekick:

^^^^^^^^^
voicekick
^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]voicekick <member> [reason]

**Description**

Kick a member from a voice channel.

.. _mod-command-unban:

^^^^^
unban
^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unban <user_id> [reason]

**Description**

Unban a user from this server.

Requires specifying the target user's ID. To find this, you may either:
 1. Copy it from the mod log case (if one was created), or
 2. enable developer mode, go to Bans in this server's settings, right-
click the user and select 'Copy ID'.

.. _mod-command-modset:

^^^^^^
modset
^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]modset 

**Description**

Manage server administration settings.

.. _mod-command-modset-defaultdays:

^^^^^^^^^^^
defaultdays
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]modset defaultdays [days=0]

**Description**

Set the default number of days worth of messages to be deleted when a user is banned.

The number of days must be between 0 and 7.

.. _mod-command-modset-deleterepeats:

^^^^^^^^^^^^^
deleterepeats
^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]modset deleterepeats [repeats]

**Description**

Enable auto-deletion of repeated messages.

Must be between 2 and 20.

Set to -1 to disable this feature.

.. _mod-command-modset-mentionspam:

^^^^^^^^^^^
mentionspam
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]modset mentionspam 

**Description**

Manage the automoderation settings for mentionspam.

.. _mod-command-modset-mentionspam-strict:

^^^^^^
strict
^^^^^^

**Syntax**

.. code-block:: none

    [p]modset mentionspam strict [enabled]

**Description**

Setting to account for duplicate mentions.

If enabled all mentions will count including duplicated mentions.
If disabled only unique mentions will count.

Use this command without any parameter to see current setting.

.. _mod-command-modset-mentionspam-warn:

^^^^
warn
^^^^

**Syntax**

.. code-block:: none

    [p]modset mentionspam warn <max_mentions>

**Description**

Sets the autowarn conditions for mention spam.

Users will be warned if they send any messages which contain more than
`<max_mentions>` mentions.

`<max_mentions>` Must be 0 or greater. Set to 0 to disable this feature.

.. _mod-command-modset-mentionspam-kick:

^^^^
kick
^^^^

**Syntax**

.. code-block:: none

    [p]modset mentionspam kick <max_mentions>

**Description**

Sets the autokick conditions for mention spam.

Users will be kicked if they send any messages which contain more than
`<max_mentions>` mentions.

`<max_mentions>` Must be 0 or greater. Set to 0 to disable this feature.

.. _mod-command-modset-mentionspam-ban:

^^^
ban
^^^

**Syntax**

.. code-block:: none

    [p]modset mentionspam ban <max_mentions>

**Description**

Set the autoban conditions for mention spam.

Users will be banned if they send any message which contains more than
`<max_mentions>` mentions.

`<max_mentions>` Must be 0 or greater. Set to 0 to disable this feature.

.. _mod-command-modset-showsettings:

^^^^^^^^^^^^
showsettings
^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]modset showsettings 

**Description**

Show the current server administration settings.

.. _mod-command-modset-reinvite:

^^^^^^^^
reinvite
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]modset reinvite 

**Description**

Toggle whether an invite will be sent to a user when unbanned.

If this is True, the bot will attempt to create and send a single-use invite
to the newly-unbanned user.

.. _mod-command-modset-hierarchy:

^^^^^^^^^
hierarchy
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]modset hierarchy 

**Description**

Toggle role hierarchy check for mods and admins.

**WARNING**: Disabling this setting will allow mods to take
actions on users above them in the role hierarchy!

This is enabled by default.

.. _mod-command-modset-dm:

^^
dm
^^

**Syntax**

.. code-block:: none

    [p]modset dm [enabled]

**Description**

Toggle whether a message should be sent to a user when they are kicked/banned.

If this option is enabled, the bot will attempt to DM the user with the guild name
and reason as to why they were kicked/banned.

.. _mod-command-moveignoredchannels:

^^^^^^^^^^^^^^^^^^^
moveignoredchannels
^^^^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]moveignoredchannels 

**Description**

Move ignored channels and servers to core

.. _mod-command-movedeletedelay:

^^^^^^^^^^^^^^^
movedeletedelay
^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]movedeletedelay 

**Description**

Move deletedelay settings to core
