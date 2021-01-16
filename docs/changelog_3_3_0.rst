.. 3.3.x Changelogs

Redbot 3.3.12 (2020-08-18)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`douglas-cpp`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MeatyChunks`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

End-user changelog
------------------

Core Bot
********

- Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)

Mod
***

- ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)

Streams
*******

- Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

Trivia Lists
************

- Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)


Miscellaneous
-------------

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)


Redbot 3.3.11 (2020-08-10)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`Flame`, :ghuser:`jack1142`, :ghuser:`MeatyChunks`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

End-user changelog
------------------

Audio
*****

- Audio should now work again on all voice regions (:issue:`4162`, :issue:`4168`)
- Removed an edge case where an unfriendly error message was sent in Audio cog (:issue:`3879`)

Cleanup
*******

- Fixed a bug causing ``[p]cleanup`` commands to clear all messages within last 2 weeks when ``0`` is passed as the amount of messages to delete (:issue:`4114`, :issue:`4115`)

CustomCommands
**************

- ``[p]cc show`` now sends an error message when command with the provided name couldn't be found (:issue:`4108`)

Downloader
**********

- ``[p]findcog`` no longer fails for 3rd-party cogs without any author (:issue:`4032`, :issue:`4042`)
- Update commands no longer crash when a different repo is added under a repo name that was once used (:issue:`4086`)

Permissions
***********

- ``[p]permissions removeserverrule`` and ``[p]permissions removeglobalrule`` no longer error when trying to remove a rule that doesn't exist (:issue:`4028`, :issue:`4036`)

Warnings
********

- ``[p]warn`` now sends an error message (instead of no feedback) when an unregistered reason is used by someone who doesn't have Administrator permission (:issue:`3839`, :issue:`3840`)


Redbot 3.3.10 (2020-07-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`

End-user changelog
------------------

Audio
*****

- Added information about internally managed jar to ``[p]audioset info`` (:issue:`3915`)
- Updated to Lavaplayer 1.3.50
- Twitch playback and YouTube searching should be functioning again.

Core Bot
********

- Fixed delayed help when ``[p]set deletedelay`` is enabled (:issue:`3884`, :issue:`3883`)
- Bumped the Discord.py requirement from 1.3.3 to 1.3.4 (:issue:`4053`)
- Added settings view commands for nearly all cogs. (:issue:`4041`)
- Added more strings to be fully translatable by i18n. (:issue:`4044`)

Downloader
**********

- Added ``[p]cog listpinned`` subcommand to see currently pinned cogs (:issue:`3974`)
- Fixed unnecessary typing when running downloader commands (:issue:`3964`, :issue:`3948`)
- Added embed version of ``[p]findcog`` (:issue:`3965`, :issue:`3944`)
- Fixed ``[p]findcog`` not differentiating between core cogs and local cogs(:issue:`3969`, :issue:`3966`)

Filter
******

- Added ``[p]filter list`` to show filtered words, and removed DMs when no subcommand was passed (:issue:`3973`)

Image
*****

- Updated instructions for obtaining and setting the GIPHY API key (:issue:`3994`)

Mod
***

- Added option to delete messages within the passed amount of days with ``[p]tempban`` (:issue:`3958`)
- Added the ability to permanently ban a temporary banned user with ``[p]hackban`` (:issue:`4025`)
- Fixed the passed reason not being used when using ``[p]tempban`` (:issue:`3958`)
- Fixed invite being sent with ``[p]tempban`` even when no invite was set (:issue:`3991`)
- Prevented an issue whereby the author may lock him self out of using the bot via whitelists (:issue:`3903`)
- Reduced the number of API calls made to the storage APIs (:issue:`3910`)

Permissions
***********

- Uploaded YAML files now accept integer commands without quotes (:issue:`3987`, :issue:`3185`)
- Uploaded YAML files now accept command rules with empty dictionaries (:issue:`3987`, :issue:`3961`)

Streams
*******

- Fixed streams cog sending multiple owner notifications about twitch secret not set (:issue:`3901`, :issue:`3587`)
- Fixed old bearer tokens not being invalidated when the API key is updated (:issue:`3990`, :issue:`3917`)

Trivia Lists
************

- Fixed URLs in ``whosthatpokemon`` (:issue:`3975`, :issue:`3023`)
- Fixed trivia files ``leagueults`` and ``sports`` (:issue:`4026`)
- Updated ``greekmyth`` to include more answer variations (:issue:`3970`)
- Added new ``lotr`` trivia list (:issue:`3980`)
- Added new ``r6seige`` trivia list (:issue:`4026`)


Developer changelog
-------------------

- Added the utility functions ``map``, ``find``, and ``next`` to ``AsyncIter`` (:issue:`3921`, :issue:`3887`)
- Updated deprecation times for ``APIToken``, and loops being passed to various functions to the first minor release (represented by ``X`` in ``3.X.0``) after 2020-08-05 (:issue:`3608`)
- Updated deprecation warnings for shared libs to reflect that they have been moved for an undefined time (:issue:`3608`)
- Added new ``discord.com`` domain to ``INVITE_URL_RE`` common filter (:issue:`4012`)
- Fixed incorrect role mention regex in ``MessagePredicate`` (:issue:`4030`)
- Vendor the ``discord.ext.menus`` module (:issue:`4039`)


Miscellaneous
-------------

- Improved error responses for when Modlog and Autoban on mention spam were already disabled (:issue:`3951`, :issue:`3949`)
- Clarified that ``[p]embedset user`` only affects commands executed in DMs (:issue:`3972`, :issue:`3953`)
- Added link to Getting Started guide if the bot was not in any guilds (:issue:`3906`)
- Fixed exceptions being ignored or not sent to log files in special cases (:issue:`3895`)
- Added the option of using dots in the instance name when creating your instances (:issue:`3920`)
- Added a confirmation when using hyphens in instance names to discourage the use of them (:issue:`3920`)
- Fixed migration owner notifications being sent even when migration was not necessary (:issue:`3911`. :issue:`3909`)
- Fixed commands being translated where they should not be (:issue:`3938`, :issue:`3919`)
- Fixed grammar errors and added full stopts in ``core_commands.py`` (:issue:`4023`)


Redbot 3.3.9 (2020-06-12)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`Predeactor`, :ghuser:`Vexed01`
|
| **Read before updating**:
| 1. Bot owners can no longer restrict access to some commands in Permissions cog using global permissions rules. Look at `Permissions changelog <important-339-2>` for full details.
| 2. There's been a change in behavior of warning messages. Look at `Warnings changelog <important-339-1>` for full details.


End-user changelog
------------------

Security
********

**NOTE**: If you can't update immediately, we recommend disabling the affected command until you can.

- **Mod** - ``[p]tempban`` now properly respects Discord's hierarchy rules (:issue:`3957`)

Core Bot
********

- ``[p]info`` command can now be used when bot doesn't have Embed Links permission (:issue:`3907`, :issue:`3102`)
- Fixed ungraceful error that happened in ``[p]set custominfo`` when provided text was too long (:issue:`3923`)
- Red's start up message now shows storage type (:issue:`3935`)

Audio
*****

- Audio now properly ignores streams when max length is enabled (:issue:`3878`, :issue:`3877`)
- Commands that should work in DMs no longer error (:issue:`3880`)

Filter
******

- Fixed behavior of detecting quotes in commands for adding/removing filtered words (:issue:`3925`)

.. _important-339-2:

Permissions
***********

- **Both global and server rules** can no longer prevent guild owners from accessing commands for changing server rules. Bot owners can still use ``[p]command disable`` if they wish to completely disable any command in Permissions cog (:issue:`3955`, :issue:`3107`)

  Full list of affected commands:

  - ``[p]permissions acl getserver``
  - ``[p]permissions acl setserver``
  - ``[p]permissions acl updateserver``
  - ``[p]permissions addserverrule``
  - ``[p]permissions removeserverrule``
  - ``[p]permissions setdefaultserverrule``
  - ``[p]permissions clearserverrules``
  - ``[p]permissions canrun``
  - ``[p]permissions explain``

.. _important-339-1:

Warnings
********

- Warnings sent to users don't show the moderator who warned the user by default now. Newly added ``[p]warningset showmoderators`` command can be used to switch this behaviour (:issue:`3781`)
- Warn channel functionality has been fixed (:issue:`3781`)


Developer changelog
-------------------

Core Bot
********

- Added `bot.set_prefixes() <RedBase.set_prefixes()>` method that allows developers to set global/server prefixes (:issue:`3890`)


Documentation changes
---------------------

- Added Oracle Cloud to free hosting section in :ref:`host-list` (:issue:`3916`)

Miscellaneous
-------------

- Added missing help message for Downloader, Reports and Streams cogs (:issue:`3892`)
- **Core Bot** - cooldown in ``[p]contact`` no longer applies when it's used without any arguments (:issue:`3942`)
- **Core Bot** - improved instructions on obtaining user ID in help of ``[p]dm`` command (:issue:`3946`)
- **Alias** - ``[p]alias global`` group, ``[p]alias help``, and ``[p]alias show`` commands can now be used in DMs (:issue:`3941`, :issue:`3940`)
- **Audio** - Typo fix (:issue:`3889`, :issue:`3900`)
- **Audio** - Fixed ``[p]audioset autoplay`` being available in DMs (:issue:`3899`)
- **Bank** - ``[p]bankset`` now displays bank's scope (:issue:`3954`)
- **Mod** - Preemptive fix for d.py 1.4 (:issue:`3891`)


Redbot 3.3.8 (2020-05-29)
==================================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Bakersbakebread`, :ghuser:`DariusStClair`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`qaisjp`, :ghuser:`Tobotimus`

End-user changelog
------------------

Core Bot
********

- Important fixes to how PostgreSQL data backend saves data in bulks (:issue:`3829`)
- Fixed ``[p]localwhitelist`` and ``[p]localblacklist`` commands (:issue:`3857`)
- Red now includes information on how to update when sending information about being out of date (:issue:`3744`)
- Using backslashes in bot's username/nickname no longer causes issues (:issue:`3826`, :issue:`3825`)

Admin
*****

- Fixed server lock (:issue:`3815`, :issue:`3814`)

Alias
*****

- Added pagination to ``[p]alias list`` and ``[p]alias global list`` to avoid errors for users with a lot of aliases (:issue:`3844`, :issue:`3834`)
- ``[p]alias help`` should now work more reliably (:issue:`3864`)

Audio
*****

- Twitch playback is functional once again (:issue:`3873`)
- Recent errors with YouTube playback should be resolved (:issue:`3873`)
- Added new option (settable with ``[p]audioset lyrics``) that makes Audio cog prefer (prioritize) tracks with lyrics (:issue:`3519`)
- Added global daily (historical) queues (:issue:`3518`)
- Added ``[p]audioset countrycode`` that allows to set the country code for spotify searches (:issue:`3528`)
- Fixed ``[p]local search`` (:issue:`3528`, :issue:`3501`)
- Local folders with special characters should work properly now (:issue:`3528`, :issue:`3467`)
- Audio no longer fails to take the last spot in the voice channel with user limit (:issue:`3528`)
- ``[p]local play`` no longer enqueues tracks from nested folders (:issue:`3528`)
- Fixed ``[p]playlist dedupe`` not removing tracks (:issue:`3518`)
- ``[p]disconnect`` now allows to disconnect if both DJ mode and voteskip aren't enabled (:issue:`3502`, :issue:`3485`)
- Many UX improvements and fixes, including, among other things:

  - Creating playlists without explicitly passing ``-scope`` no longer causes errors (:issue:`3500`)
  - ``[p]playlist list`` now shows all accessible playlists if ``--scope`` flag isn't used (:issue:`3518`)
  - ``[p]remove`` now also accepts a track URL in addition to queue index (:issue:`3201`)
  - ``[p]playlist upload`` now accepts a playlist file uploaded in the message with a command (:issue:`3251`)
  - Commands now send friendly error messages for common errors like lost Lavalink connection or bot not connected to voice channel (:issue:`3503`, :issue:`3528`, :issue:`3353`, :issue:`3712`)

CustomCommands
**************

- ``[p]customcom create`` no longer allows spaces in custom command names (:issue:`3816`)

Mod
***

- ``[p]userinfo`` now shows default avatar when no avatar is set (:issue:`3819`)

Modlog
******

- Fixed (again) ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3805`, :issue:`3784`, :issue:`3778`)

Permissions
***********

- Commands for settings ACL using yaml files now properly works on PostgreSQL data backend (:issue:`3829`, :issue:`3796`)

Warnings
********

- Warnings cog no longer allows to warn bot users (:issue:`3855`, :issue:`3854`)


Developer changelog
-------------------

| **Important:**
| If you're using RPC, please see the full annoucement about current state of RPC in main Red server
  `by clicking here <https://discord.com/channels/133049272517001216/411381123101491200/714560168465137694>`_.


Core Bot
********

- Red now inherits from `discord.ext.commands.AutoShardedBot` for better compatibility with code expecting d.py bot (:issue:`3822`)
- Libraries using ``pkg_resources`` (like ``humanize`` or ``google-api-python-client``) that were installed through Downloader should now work properly (:issue:`3843`)
- All bot owner IDs can now be found under ``bot.owner_ids`` attribute (:issue:`3793`)

  -  Note: If you want to use this on bot startup (e.g. in cog's initialisation), you need to await ``bot.wait_until_red_ready()`` first


Documentation changes
---------------------

- Added information about provisional status of RPC (:issue:`3862`)
- Revised install instructions (:issue:`3847`)
- Improved navigation in `document about updating Red <update_red>` (:issue:`3856`, :issue:`3849`)


Miscellaneous
-------------

- Few clarifications and typo fixes in few command help docstrings (:issue:`3817`, :issue:`3823`, :issue:`3837`, :issue:`3851`, :issue:`3861`)
- **Downloader** - Downloader no longer removes the repo when it fails to load it (:issue:`3867`)


Redbot 3.3.7 (2020-04-28)
=========================

This is a hotfix release fixing issue with generating messages for new cases in Modlog.


Redbot 3.3.6 (2020-04-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`yamikaitou`

End-user changelog
------------------

Core Bot
********

- Converting from and to Postgres driver with ``redbot-setup convert`` have been fixed (:issue:`3714`, :issue:`3115`)
- Fixed big delays in commands that happened when the bot was owner-less (or if it only used co-owners feature) and command caller wasn't the owner (:issue:`3782`)
- Various optimizations

  - Reduced calls to data backend when loading bot's commands (:issue:`3764`)
  - Reduced calls to data backend when showing help for cogs/commands (:issue:`3766`)
  - Improved performance for bots with big amount of guilds (:issue:`3767`)
  - Mod cog no longer fetches guild's bans every 60 seconds when handling unbanning for tempbans (:issue:`3783`)
  - Reduced the bot load for messages starting with a prefix when fuzzy search is disabled (:issue:`3718`)
  - Aliases in Alias cog are now cached for better performance (:issue:`3788`)

Core Commands
*************

- ``[p]set avatar`` now supports setting avatar using attachment (:issue:`3747`)
- Added ``[p]set avatar remove`` subcommand for removing bot's avatar (:issue:`3757`)
- Fixed list of ignored channels that is shown in ``[p]ignore``/``[p]unignore`` (:issue:`3746`)

Audio
*****

- Age-restricted tracks, live streams, and mix playlists from YouTube should work in Audio again (:issue:`3791`)
- Soundcloud's sets and playlists with more than 50 tracks should work in Audio again (:issue:`3791`)

CustomCommands
**************

- Added ``[p]cc raw`` command that gives you the raw response of a custom command for ease of copy pasting (:issue:`3795`)

Modlog
******

- Fixed ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3784`, :issue:`3778`)

Streams
*******

- Fixed incorrect stream URLs for Twitch channels that have localised display name (:issue:`3773`, :issue:`3772`)

Trivia
******

- Fixed the error in ``[p]trivia stop`` that happened when there was no ongoing trivia session in the channel (:issue:`3774`)

Trivia Lists
************

- Updated ``leagueoflegends`` list with new changes to League of Legends (`b8ac70e <https://github.com/Cog-Creators/Red-DiscordBot/commit/b8ac70e59aa1328f246784f14f992d6ffe00d778>`_)


Developer changelog
-------------------

Utility Functions
*****************

- Added `redbot.core.utils.AsyncIter` utility class which allows you to wrap regular iterable into async iterator yielding items and sleeping for ``delay`` seconds every ``steps`` items (:issue:`3767`, :issue:`3776`)
- `bold()`, `italics()`, `strikethrough()`, and `underline()` now accept ``escape_formatting`` argument that can be used to disable escaping of markdown formatting in passed text (:issue:`3742`)


Documentation changes
---------------------

- Added `document about updating Red <update_red>` (:issue:`3790`)
- ``pyenv`` instructions will now update ``pyenv`` if it's already installed (:issue:`3740`)
- Updated Python version in ``pyenv`` instructions (:issue:`3740`)
- Updated install docs to include Ubuntu 20.04 (:issue:`3792`)


Miscellaneous
-------------

- **Config** - JSON driver will now properly have only one lock per cog name (:issue:`3780`)
- **Core Commands** - ``[p]debuginfo`` now shows used storage type (:issue:`3794`)
- **Trivia** - Corrected spelling of Compact Disc in ``games`` list (:issue:`3759`, :issue:`3758`)


Redbot 3.3.5 (2020-04-09)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`

End-user changelog
------------------

Core Bot
********

- "Outdated" field no longer shows in ``[p]info`` when Red is up-to-date (:issue:`3730`)

Alias
*****

- Fixed regression in ``[p]alias add`` that caused it to reject commands containing arguments (:issue:`3734`)


Redbot 3.3.4 (2020-04-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`kennnyshiwa`

End-user changelog
------------------

Core Bot
********

- Fixed checks related to bank's global state that were used in commands in Bank, Economy and Trivia cogs (:issue:`3707`)

Alias
*****

- ``[p]alias add`` now sends an error when command user tries to alias doesn't exist (:issue:`3710`, :issue:`3545`)

Developer changelog
-------------------

Core Bot
********

- Bump dependencies, including update to discord.py 1.3.3 (:issue:`3723`)

Utility Functions
*****************

- `redbot.core.utils.common_filters.filter_invites` now filters ``discord.io/discord.li`` invites links (:issue:`3717`)
- Fixed false-positives in `redbot.core.utils.common_filters.filter_invites` (:issue:`3717`)

Documentation changes
---------------------

- Versions of pre-requirements are now included in Windows install guide (:issue:`3708`)


Redbot 3.3.3 (2020-03-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`AnonGuy`, :ghuser:`Dav-Git`, :ghuser:`FancyJesse`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Core Bot
********

- Delete delay for command messages has been moved from Mod cog to Core (:issue:`3638`, :issue:`3636`)
- Fixed various bugs with blacklist and whitelist (:issue:`3643`, :issue:`3642`)
- Added ``[p]set regionalformat`` command that allows users to set regional formatting that is different from bot's locale (:issue:`3677`, :issue:`3588`)
- ``[p]set locale`` allows any valid locale now, not just locales for which Red has translations (:issue:`3676`, :issue:`3596`)
- Permissions for commands in Bank, Economy and Trivia cogs can now be overridden by Permissions cog (:issue:`3672`, :issue:`3233`)
- Outages of ``pypi.org`` no longer prevent the bot from starting (:issue:`3663`)
- Fixed formatting of help strings in fuzzy search results (:issue:`3673`, :issue:`3507`)
- Fixed few deprecation warnings related to menus and uvloop (:issue:`3644`, :issue:`3700`)

Core Commands
*************

- ``[p]set game`` no longer errors when trying to clear the status (:issue:`3630`, :issue:`3628`)
- All owner notifcations in Core now use proper prefixes in messages (:issue:`3632`)
- Added ``[p]set playing`` and ``[p]set streaming`` aliases for respectively ``[p]set game`` and ``[p]set stream`` (:issue:`3646`, :issue:`3590`)

ModLog
******

- Modlog's cases now keep last known username to prevent losing that information from case's message on edit (:issue:`3674`, :issue:`3443`)

CustomCom
*********

- Added ``[p]cc search`` command that allows users to search through created custom commands (:issue:`2573`)

Cleanup
*******

- Added ``[p]cleanup spam`` command that deletes duplicate messages from the last X messages and keeps only one copy (:issue:`3688`)
- Removed regex support in ``[p]cleanup self`` (:issue:`3704`)

Downloader
**********

- ``[p]cog checkforupdates`` now includes information about cogs that can't be installed due to Red/Python version requirements (:issue:`3678`, :issue:`3448`)

General
*******

- Added more detailed mode to ``[p]serverinfo`` command that can be accessed with ``[p]serverinfo 1`` (:issue:`2382`, :issue:`3659`)

Image
*****

- Users can now specify how many images should be returned in ``[p]imgur search`` and ``[p]imgur subreddit`` using ``[count]`` argument (:issue:`3667`, :issue:`3044`)
- ``[p]imgur search`` and ``[p]imgur subreddit`` now return one image by default (:issue:`3667`, :issue:`3044`)

Mod
***

- ``[p]userinfo`` now shows user's activities (:issue:`3669`)
- ``[p]userinfo`` now shows status icon near the username (:issue:`3669`)
- Muting no longer fails if user leaves while applying overwrite (:issue:`3627`)
- Fixed error that happened when Mod cog was loaded for the first time during bot startup (:issue:`3632`, :issue:`3626`)

Permissions
***********

- Commands for setting default rules now error when user tries to deny access to command designated as being always available (:issue:`3504`, :issue:`3465`)

Streams
*******

- Fixed an error that happened when no game was set on Twitch stream (:issue:`3631`)
- Preview picture for YouTube stream alerts is now bigger (:issue:`3689`, :issue:`3685`)
- YouTube channels with a livestream that doesn't have any current viewer are now properly showing as streaming (:issue:`3690`)
- Failures in Twitch API authentication are now logged (:issue:`3657`)

Trivia
******

- Added ``[p]triviaset custom upload/delete/list`` commands for managing custom trivia lists from Discord (:issue:`3420`, :issue:`3307`)
- Trivia sessions no longer error on payout when winner's balance would exceed max balance (:issue:`3666`, :issue:`3584`)

Warnings
********

- Sending warnings to warned user can now be disabled with ``[p]warnset toggledm`` command (:issue:`2929`, :issue:`2800`)
- Added ``[p]warnset warnchannel`` command that allows to set a channel where warnings should be sent to instead of the channel command was called in (:issue:`2929`, :issue:`2800`)
- Added ``[p]warnset togglechannel`` command that allows to disable sending warn message in guild channel (:issue:`2929`, :issue:`2800`)
- ``[p]warn`` now tells the moderator when bot wasn't able to send the warning to the user (:issue:`3653`, :issue:`3633`)


Developer changelog
-------------------

Core Bot
********

- Deprecation warnings issued by Red now use correct stack level so that the cog developers can find the cause of them (:issue:`3644`)

Dev Cog
*******

- Add ``__name__`` to environment's globals (:issue:`3649`, :issue:`3648`)


Documentation changes
---------------------

- Fixed install instructions for Mac in `install_linux_mac` (:issue:`3675`, :issue:`3436`)
- Windows install instructions now use ``choco upgrade`` commands instead of ``choco install`` to ensure up-to-date packages (:issue:`3684`)


Miscellaneous
-------------

- **Core Bot** - Command errors (i.e. command on cooldown, dm-only and guild-only commands, etc) can now be translated (:issue:`3665`, :issue:`2988`)
- **Core Bot** - ``redbot-setup`` now prints link to Getting started guide at the end of the setup (:issue:`3027`)
- **Core Bot** - Whitelist and blacklist commands now properly require passing at least one user (or role in case of local whitelist/blacklist) (:issue:`3652`, :issue:`3645`)
- **Downloader** - Fix misleading error appearing when repo name is already taken in ``[p]repo add`` (:issue:`3695`)
- **Downloader** - Improved error messages for unexpected errors in ``[p]repo add`` (:issue:`3656`)
- **Downloader** - Prevent encoding errors from crashing ``[p]cog update`` (:issue:`3639`, :issue:`3637`)
- **Trivia** - Non-finite numbers can no longer be passed to ``[p]triviaset timelimit``, ``[p]triviaset stopafter`` and ``[p]triviaset payout`` (:issue:`3668`, :issue:`3583`)
- **Utility Functions** - `redbot.core.utils.menus.menu()` now checks permissions *before* trying to clear reactions (:issue:`3589`, :issue:`3145`)


Redbot 3.3.2 (2020-02-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`chasehult`, :ghuser:`Dav-Git`, :ghuser:`DiscordLiz`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Hedlund01`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`trundleroo`, :ghuser:`TrustyJAID`, :ghuser:`zephyrkul`

End-user changelog
------------------

Core Bot
********

- Ignored guilds/channels and whitelist/blacklist are now cached for performance (:issue:`3472`)
- Ignored guilds/channels have been moved from Mod cog to Core (:issue:`3472`)
- ``[p]ignore channel`` command can now also ignore channel categories (:issue:`3472`)

Core Commands
*************

- Core cogs will now send bot mention prefix properly in places where discord doesn't render mentions (:issue:`3579`, :issue:`3591`, :issue:`3499`)
- Fix a bug with ``[p]blacklist add`` that made it impossible to blacklist users that bot doesn't share a server with (:issue:`3472`, :issue:`3220`)
- Improve user experience of ``[p]set game/listening/watching/`` commands (:issue:`3562`)
- Add ``[p]licenceinfo`` alias for ``[p]licenseinfo`` command to conform with non-American English (:issue:`3460`)

Admin
*****

- ``[p]announce`` will now only send error message if an actual errors occurs (:issue:`3514`, :issue:`3513`)

Alias
*****

- ``[p]alias help`` will now properly work in non-English locales (:issue:`3546`)

Audio
*****

- Users should be able to play age-restricted tracks from YouTube again (:issue:`3620`)

Economy
*******

- Next payday time will now be adjusted for users when payday time is changed (:issue:`3496`, :issue:`3438`)

Downloader
**********

- Downloader will no longer fail because of invalid ``info.json`` files (:issue:`3533`, :issue:`3456`)
- Add better logging of errors when Downloader fails to add a repo (:issue:`3558`)

Image
*****

- Fix load error for users that updated Red from version lower than 3.1 to version 3.2 or newer (:issue:`3617`)

Mod
***

- ``[p]hackban`` and ``[p]unban`` commands support user mentions now (:issue:`3524`)
- Ignored guilds/channels have been moved from Mod cog to Core (:issue:`3472`)

Streams
*******

- Fix stream alerts for Twitch (:issue:`3487`)
- Significantly reduce the quota usage for YouTube stream alerts (:issue:`3237`)
- Add ``[p]streamset timer`` command which can be used to control how often the cog checks for live streams (:issue:`3237`)

Trivia
******

- Add better handling for errors in trivia session (:issue:`3606`)

Trivia Lists
************

- Remove empty answers in trivia lists (:issue:`3581`)

Warnings
********

- Users can now pass a reason to ``[p]unwarn`` command (:issue:`3490`, :issue:`3093`)


Developer changelog
-------------------

Core Bot
********

- Updated all our dependencies - we're using discord.py 1.3.2 now (:issue:`3609`)
- Add traceback logging to task exception handling (:issue:`3517`)
- Developers can now create a command from an async function wrapped in `functools.partial` (:issue:`3542`)
- Bot will now show deprecation warnings in logs (:issue:`3527`, :issue:`3615`)
- Subcommands of command group with ``invoke_without_command=True`` will again inherit this group's checks (:issue:`3614`)

Config
******

- Fix Config's singletons (:issue:`3137`, :issue:`3136`)

Utility Functions
*****************

- Add clearer error when page is of a wrong type in `redbot.core.utils.menus.menu()` (:issue:`3571`)

Dev Cog
*******

- Allow for top-level `await`, `async for` and `async with` in ``[p]debug`` and ``[p]repl`` commands (:issue:`3508`)

Downloader
**********

- Downloader will now replace ``[p]`` with clean prefix same as it does in help command (:issue:`3592`)
- Add schema validation to ``info.json`` file processing - it should now be easier to notice any issues with those files (:issue:`3533`, :issue:`3442`)


Documentation changes
---------------------

- Add guidelines for Cog Creators in `guide_cog_creation` document (:issue:`3568`)
- Restructure virtual environment instructions to improve user experience (:issue:`3495`, :issue:`3411`, :issue:`3412`)
- Getting started guide now explain use of quotes for arguments with spaces (:issue:`3555`, :issue:`3111`)
- ``latest`` version of docs now displays a warning about possible differences from current stable release (:issue:`3570`)
- Make systemd guide clearer on obtaining username and python path (:issue:`3537`, :issue:`3462`)
- Indicate instructions for different venv types in systemd guide better (:issue:`3538`)
- Service file in `autostart_systemd` now also waits for network connection to be ready (:issue:`3549`)
- Hide alias of ``randomize_colour`` in docs (:issue:`3491`)
- Add separate headers for each event predicate class for better navigation (:issue:`3595`, :issue:`3164`)
- Improve wording of explanation for ``required_cogs`` key in `guide_publish_cogs` (:issue:`3520`)


Miscellaneous
-------------

- Use more reliant way of checking if command is bot owner only in ``[p]warnaction`` (Warnings cog) (:issue:`3516`, :issue:`3515`)
- Update PyPI domain in ``[p]info`` and update checker (:issue:`3607`)
- Stop using deprecated code in core (:issue:`3610`)


Redbot 3.3.1 (2020-02-05)
=========================


Core Bot
--------

- Add a cli flag for setting a max size of message cache
- Allow to edit prefix from command line using ``redbot --edit``.
- Some functions have been changed to no longer use deprecated asyncio functions

Core Commands
-------------

- The short help text for dm has been made more useful
- dm no longer allows owners to have the bot attempt to DM itself

Utils
-----

- Passing the event loop explicitly in utils is deprecated (Removal in 3.4)

Mod Cog
-------

- Hackban now works properly without being provided a number of days

Documentation Changes
---------------------

- Add ``-e`` flag to ``journalctl`` command in systemd guide so that it takes the user to the end of logs automatically.
- Added section to install docs for CentOS 8
- Improve usage of apt update in docs

Redbot 3.3.0 (2020-01-26)
=========================

Core Bot
--------

- The bot's description is now configurable.
- We now use discord.py 1.3.1, this comes with added teams support.
- The commands module has been slightly restructured to provide more useful data to developers.
- Help is now self consistent in the extra formatting used.

Core Commands
-------------

- Slowmode should no longer error on nonsensical time quantities.
- Embed use can be configured per channel as well.

Documentation
-------------

- We've made some small fixes to inaccurate instructions about installing with pyenv.
- Notes about deprecating in 3.3 have been altered to 3.4 to match the intended timeframe.

Admin
-----

- Gives feedback when adding or removing a role doesn't make sense.

Audio
-----

- Playlist finding is more intuitive.
- disconnect and repeat commands no longer interfere with eachother.

CustomCom
---------

- No longer errors when exiting an interactive menu.

Cleanup
-------

- A rare edge case involving messages which are deleted during cleanup and are the only message was fixed.

Downloader
----------

- Some user facing messages were improved.
- Downloader's initialization can no longer time out at startup.

General
-------

- Roll command will no longer attempt to roll obscenely large amounts.

Mod
---

- You can set a default amount of days to clean up when banning.
- Ban and hackban now use that default.
- Users can now optionally be DMed their ban reason.

Permissions
-----------

- Now has stronger enforcement of prioritizing botwide settings.
