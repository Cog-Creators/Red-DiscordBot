.. _mutes:

=====
Mutes
=====

This is the cog guide for the mutes cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load mutes

.. _mutes-usage:

-----
Usage
-----

Mute users temporarily or indefinitely.


.. _mutes-commands:

--------
Commands
--------

.. _mutes-command-activemutes:

^^^^^^^^^^^
activemutes
^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]activemutes 

**Description**

Displays active mutes on this server.

.. _mutes-command-mute:

^^^^
mute
^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mute <users...> [time_and_reason]

**Description**

Mute users.

``<users...>`` is a space separated list of usernames, ID's, or mentions.
``[time_and_reason]`` is the time to mute for and reason. Time is
any valid time length such as ``30 minutes`` or ``2 days``. If nothing
is provided the mute will use the set default time or indefinite if not set.

Examples:
``[p]mute @member1 @member2 spam 5 hours``
``[p]mute @member1 3 days``

.. _mutes-command-mutechannel:

^^^^^^^^^^^
mutechannel
^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mutechannel <users...> [time_and_reason]

.. tip:: Alias: ``channelmute``

**Description**

Mute a user in the current text channel.

``<users...>`` is a space separated list of usernames, ID's, or mentions.
``[time_and_reason]`` is the time to mute for and reason. Time is
any valid time length such as ``30 minutes`` or ``2 days``. If nothing
is provided the mute will use the set default time or indefinite if not set.

Examples:
``[p]mutechannel @member1 @member2 spam 5 hours``
``[p]mutechannel @member1 3 days``

.. _mutes-command-muteset:

^^^^^^^
muteset
^^^^^^^

**Syntax**

.. code-block:: none

    [p]muteset 

**Description**

Mute settings.

.. _mutes-command-muteset-defaulttime:

"""""""""""""""""""
muteset defaulttime
"""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset defaulttime [time]

.. tip:: Alias: ``muteset time``

**Description**

Set the default mute time for the mute command.

If no time interval is provided this will be cleared.

.. _mutes-command-muteset-forcerole:

"""""""""""""""""
muteset forcerole
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]muteset forcerole <force_role_mutes>

**Description**

Whether or not to force role only mutes on the bot

.. _mutes-command-muteset-makerole:

""""""""""""""""
muteset makerole
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]muteset makerole <name>

**Description**

Create a Muted role.

This will create a role and apply overwrites to all available channels
to more easily setup muting a user.

If you already have a muted role created on the server use
``[p]muteset role ROLE_NAME_HERE``

.. _mutes-command-muteset-notification:

""""""""""""""""""""
muteset notification
""""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]muteset notification [channel]

**Description**

Set the notification channel for automatic unmute issues.

If no channel is provided this will be cleared and notifications
about issues when unmuting users will not be sent anywhere.

.. _mutes-command-muteset-role:

""""""""""""
muteset role
""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]muteset role [role]

**Description**

Sets the role to be applied when muting a user.

If no role is setup the bot will attempt to mute a user by setting
channel overwrites in all channels to prevent the user from sending messages.

.. Note:: If no role is setup a user may be able to leave the server

and rejoin no longer being muted.

.. _mutes-command-muteset-senddm:

""""""""""""""
muteset senddm
""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset senddm <true_or_false>

**Description**

Set whether mute notifications should be sent to users in DMs.

.. _mutes-command-muteset-settings:

""""""""""""""""
muteset settings
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset settings 

.. tip:: Alias: ``muteset showsettings``

**Description**

Shows the current mute settings for this guild.

.. _mutes-command-muteset-showmoderator:

"""""""""""""""""""""
muteset showmoderator
"""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset showmoderator <true_or_false>

**Description**

Decide whether the name of the moderator muting a user should be included in the DM to that user.

.. _mutes-command-unmute:

^^^^^^
unmute
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmute <users...> [reason]

**Description**

Unmute users.

``<users...>`` is a space separated list of usernames, ID's, or mentions.
``[reason]`` is the reason for the unmute.

.. _mutes-command-unmutechannel:

^^^^^^^^^^^^^
unmutechannel
^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmutechannel <users...> [reason]

.. tip:: Alias: ``channelunmute``

**Description**

Unmute a user in this channel.

``<users...>`` is a space separated list of usernames, ID's, or mentions.
``[reason]`` is the reason for the unmute.

.. _mutes-command-voicemute:

^^^^^^^^^
voicemute
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]voicemute <users...> [reason]

**Description**

Mute a user in their current voice channel.

``<users...>`` is a space separated list of usernames, ID's, or mentions.
``[time_and_reason]`` is the time to mute for and reason. Time is
any valid time length such as ``30 minutes`` or ``2 days``. If nothing
is provided the mute will use the set default time or indefinite if not set.

Examples:
``[p]voicemute @member1 @member2 spam 5 hours``
``[p]voicemute @member1 3 days``

.. _mutes-command-voiceunmute:

^^^^^^^^^^^
voiceunmute
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]voiceunmute <users...> [reason]

**Description**

Unmute a user in their current voice channel.

``<users...>`` is a space separated list of usernames, ID's, or mentions.
``[reason]`` is the reason for the unmute.