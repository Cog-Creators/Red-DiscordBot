.. 3.4.x Changelogs

Redbot 3.4.0 (Unreleased)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`
|
| **Read before updating**:
| 1. Debian Stretch, Fedora 30 and lower, and OpenSUSE Leap 15.0 and lower are no longer supported as they have already reached end of life.
| 2. There's been a change in behavior of ``[p]tempban``. Look at `Mod changelog <important-340-1>` for full details.
| 3. There's been a change in behavior of announcements in Admin cog. Look at `Admin changelog <important-340-2>` for full details.

End-user changelog
------------------

Core Bot
********

- Added per-guild cog disabling (:issue:`4043`, :issue:`3945`)

    - Bot owners can set the default state for a cog using ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands
    - Guild owners can enable/disable cogs for their guild using ``[p]command disablecog`` and ``[p]command enablecog`` commands
    - Cogs disabled in the guild can be listed with ``[p]command listdisabledcogs``

- Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)

.. _important-340-2:

Admin
*****

- ``[p]announce`` will now only send announcements to guilds that have explicitly configured text channel to send announcements to using ``[p]announceset channel`` command (:issue:`4088`, :issue:`4089`)

.. _important-340-1:

Mod
***

- ``[p]tempban`` now respects default days setting (``[p]modset defaultdays``) (:issue:`3993`)
- ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)

Streams
*******

- Mixer service has been closed and for that reason we've removed support for it from the cog (:issue:`4072`)


Developer changelog
-------------------

| **Important:**
| Red now offers cog disabling API, which should be respected by 3rd-party cogs in guild-related actions happening outside of command's context. See the changelog entry below.

- Added cog disabling API (:issue:`4043`, :issue:`3945`)

    - New methods added: `bot.cog_disabled_in_guild() <RedBase.cog_disabled_in_guild()>`, `bot.cog_disabled_in_guild_raw() <RedBase.cog_disabled_in_guild_raw()>`
    - Cog disabling is automatically applied for commands and only needs to be done manually for things like event listeners; see `guidelines-for-cog-creators` for more information

- Added `bot.message_eligible_as_command() <RedBase.message_eligible_as_command()>` utility method which can be used to determine if a message may be responded to as a command (:issue:`4077`)
- `bot.ignored_channel_or_guild() <RedBase.ignored_channel_or_guild()>` now accepts `discord.Message` objects (:issue:`4077`)
- Red no longer fails to run subcommands of a command group allowed or denied by permission hook (:issue:`3956`)


Documentation changes
---------------------

- Removed install instructions for Debian Stretch (:issue:`4099`)


Miscellaneous
-------------

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- `bordered()` now uses ``+`` for corners if keyword argument ``ascii_border`` is set to `True` (:issue:`4097`)
