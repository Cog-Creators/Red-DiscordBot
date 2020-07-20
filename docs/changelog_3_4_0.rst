.. 3.4.x Changelogs

Redbot 3.4.0 (Unreleased)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`Vexed01`
|
| **Read before updating**:
| 1. There's been a change in behavior of ``[p]tempban``. Look at `Mod changelog <important-340-1>` for full details.

End-user changelog
------------------


.. _important-340-1:

Mod
***

- ``[p]tempban`` now respects default days setting (``[p]modset defaultdays``) (:issue:`3993`)
- ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)


Developer changelog
-------------------

- Added `bot.message_eligible_as_command() <RedBase.message_eligible_as_command()>` utility method which can be used to determine if a message may be responded to as a command (:issue:`4077`)
- `bot.ignored_channel_or_guild() <RedBase.ignored_channel_or_guild()>` now accepts `discord.Message` objects (:issue:`4077`)
- Red no longer fails to run subcommands of a command group allowed or denied by permission hook (:issue:`3956`)


Documentation changes
---------------------



Miscellaneous
-------------

