==============================
Changelog - Alternative look 3
==============================

Redbot 3.4.13 (2021-09-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Arman0334`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`fredster33`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`qenu`, :ghuser:`TheDataLeek`, :ghuser:`Twentysix26`, :ghuser:`TwinDragon`, :ghuser:`Vexed01`

Read before updating
--------------------

#. If you're hosting a public/big bot (>75 servers) or strive to scale your bot at that level, you should read :doc:`our stance on (privileged) intents and public bots <intents>`.
#. Fedora 32 is no longer supported as it has already reached end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.13 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1238>`__.


End-user changelog
------------------

New Functionality
*****************

- **Alias** - Added commands for editing existing aliases (:issue:`5108`)
- **Audio** - Added a per-guild max volume setting (:issue:`5165`)

    This can be changed with the ``[p]audioset maxvolume`` command

- **Cleanup** - All ``[p]cleanup`` commands will now send a notification with the number of deleted messages. The notification is deleted automatically after 5 seconds (:issue:`5218`)

    This can be disabled with the ``[p]cleanupset notify`` command

- **Filter** - Added ``[p]filter clear`` and ``[p]filter channel clear`` commands for clearing the server's/channel's filter list (:issue:`4841`, :issue:`4981`)

Core Bot
++++++++

- Added a new ``[p]diagnoseissues`` command to allow the bot owners to diagnose issues with various command checks with ease (:issue:`4717`, :issue:`5243`)

    Since some of us are pretty excited about this feature, here's a very small teaser showing a part of what it can do:

    .. figure:: https://user-images.githubusercontent.com/6032823/132610057-d6c65d67-c244-4f0b-9458-adfbe0c68cab.png

- Added a setting for ``[p]help``'s reaction timeout (:issue:`5205`)

    This can be changed with ``[p]helpset reacttimeout`` command

- Red 3.4.13 is the first release to (finally) support Python 3.9! (:issue:`4655`, :issue:`5121`)

Enhancements
************

- **Admin** - The ``[p]selfroleset add`` and ``[p]selfroleset remove`` commands can now be used to add multiple selfroles at once (:issue:`5237`, :issue:`5238`)
- **Audio** - ``[p]summon`` will now indicate that it has succeeded or failed to summon the bot (:issue:`5186`)
- **Cleanup** - The ``[p]cleanup user`` command can now be used to clean messages of a user that is no longer in the server (:issue:`5169`)
- **Downloader** - The dot character (``.``) can now be used in repo names. No more issues with adding repositories using the commands provided by the Cog Index! (:issue:`5214`)
- **Mod** - The DM message from the ``[p]tempban`` command will now include the ban reason if ``[p]modset dm`` setting is enabled (:issue:`4836`, :issue:`4837`)
- **Streams** - Made small optimizations in regards to stream alerts (:issue:`4968`)
- **Trivia** - Added schema validation of the custom trivia files (:issue:`4571`, :issue:`4659`)

Core Bot
++++++++

- Revamped the ``[p]debuginfo`` to make it more useful for... You guessed it, debugging! (:issue:`4997`, :issue:`5156`)

    More specifically, added information about CPU and RAM, bot's instance name and owners

- The formatting of Red's console logs has been updated to make it more copy-paste friendly (:issue:`4868`, :issue:`5181`)
- Added the new native Discord timestamps in Modlog cases, ``[p]userinfo``, ``[p]serverinfo``, and ``[p]tempban`` (:issue:`5155`, :issue:`5241`)
- Upgraded all Red's dependencies (:issue:`5121`)
- The console error about missing Privileged Intents stands out more now (:issue:`5184`)
- The ``[p]invite`` command will now add a tick reaction after it DMs an invite link to the user (:issue:`5184`)

Removals
********

- **Core Bot** - Fedora 32 is no longer supported as it has already reached end of life (:issue:`5121`)

Fixes
*****

- **Core Bot** - Fixed a bunch of errors related to the missing permissions and channels/messages no longer existing (:issue:`5109`, :issue:`5163`, :issue:`5172`, :issue:`5191`)
- **Downloader** - Added a few missing line breaks (:issue:`5185`, :issue:`5187`)
- **Streams** - Fixed an issue with some YouTube streamers getting removed from stream alerts after a while (:issue:`5195`, :issue:`5223`)
- **Warnings** - 0 point warnings are, once again, allowed. (:issue:`5177`, :issue:`5178`)

Audio
+++++

- Fixed an issue with short clips being cutoff when auto-disconnect on queue end is enabled (:issue:`5158`, :issue:`5188`)
- Fixed fetching of age-restricted tracks (:issue:`5233`)
- Fixed searching of YT Music (:issue:`5233`)
- Fixed playback from SoundCloud (:issue:`5233`)

Mod
+++

- Fixed an error with handling of temporary ban expirations while the guild is unavailable due to Discord outage (:issue:`5173`)
- The ``[p]rename`` command will no longer permit changing nicknames of members that are not lower in the role hierarchy than the command caller (:issue:`5187`, :issue:`5211`)


Developer changelog
-------------------

New Functionality
*****************

- Added `RelativedeltaConverter` and `parse_relativedelta` to the ``redbot.core.commands`` package (:issue:`5000`)

    This converter and function return `dateutil.relativedelta.relativedelta` object that represents a relative delta.
    In addition to regular timedelta arguments, it also accepts months and years!

- Added more APIs for allowlists and blocklists (:issue:`5206`)

    Here's the list of the methods that were added to the ``bot`` object:

        - `Red.add_to_blacklist()`
        - `Red.remove_from_blacklist()`
        - `Red.get_blacklist()`
        - `Red.clear_blacklist()`
        - `Red.add_to_whitelist()`
        - `Red.remove_from_whitelist()`
        - `Red.get_whitelist()`
        - `Red.clear_whitelist()`

- Added `CommandConverter` and `CogConverter` to the ``redbot.core.commands`` package (:issue:`5037`)


Documentation changes
---------------------

New Documentation
*****************

- Added a document about (privileged) intents and our stance regarding "public bots" (:issue:`5216`, :issue:`5221`)
- Added install instructions for Debian 11 Bullseye (:issue:`5213`, :issue:`5217`)
- Added Oracle Cloud's Always Free offering to the :ref:`host-list` (:issue:`5225`)

Enhancements
************

- Updated the commands in the install guide for Mac OS to work properly on Apple Silicon devices (:issue:`5234`)

Fixes
*****

- Fixed the examples of commands that are only available to people with the mod role (:issue:`5180`)
- Fixed few other small issues with the documentation :) (:issue:`5048`, :issue:`5092`, :issue:`5149`, :issue:`5207`, :issue:`5209`, :issue:`5215`, :issue:`5219`, :issue:`5220`)
