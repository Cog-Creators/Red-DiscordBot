.. 3.4.x Changelogs

Redbot 3.4.5 (2020-12-24)
=========================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Injabie3`, :ghuser:`NeuroAssassin`

End-user changelog
------------------

Streams
*******

- Fixed Streams failing to load and work properly (:issue:`4687`, :issue:`4688`)

Redbot 3.4.4 (2020-12-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreus7`, :ghuser:`NeuroAssassin`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.4 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.2_1170>`__.

2. Ubuntu 16.04 is no longer supported as it will soon reach its end of life and it is no longer viable for us to maintain support for it.

    While you might still be able to run Red on it, we will no longer put any resources into supporting it. If you're using Ubuntu 16.04, we highly recommend that you upgrade to the latest LTS version of Ubuntu.


End-user changelog
------------------

Core Bot
********

- Red's logging will now shine in your terminal more than ever (:issue:`4577`)
- Improved consistency of command usage in the help messages within all commands in Core Red (:issue:`4589`)
- Added a friendly error when the duration provided to commands that use the ``commands.TimedeltaConverter`` converter is out of the maximum bounds allowed by Python interpreter (:issue:`4019`, :issue:`4628`, :issue:`4630`)
- Fixed an error when removing path from a different operating system than the bot is currently running on with ``[p]removepath`` (:issue:`2609`, :issue:`4662`, :issue:`4466`)

Audio
*****

- Fixed ``[p]llset java`` failing to set the Java executable path (:issue:`4621`, :issue:`4624`)
- Fixed Soundcloud playback (:issue:`4683`)
- Fixed YouTube age-restricted track playback (:issue:`4683`)
- Added more friendly messages for 429 errors to let users know they have been temporarily banned from accessing the service instead of a generic Lavalink error (:issue:`4683`)
- Environment information will now be appended to Lavalink tracebacks in the spring.log (:issue:`4683`)

Cleanup
*******

- ``[p]cleanup self`` will now delete the command message when the bot has permissions to do so (:issue:`4640`)

Dev
***

- Added new ``[p]bypasscooldown`` command that allows owners to bypass command cooldowns (:issue:`4440`)

Economy
*******

- ``[p]economyset slotmin`` and ``[p]economyset slotmax`` now warn when the new value will cause the slots command to not work (:issue:`4583`)

General
*******

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4678`)

Mod
***

- ``[p]ban`` command will no longer error out when the given reason is too long (:issue:`4187`, :issue:`4189`)

Streams
*******

- Scheduled YouTube streams now work properly with the cog (:issue:`3691`, :issue:`4615`)
- YouTube stream schedules are now announced before the stream (:issue:`4615`)

    - Alerts about YouTube stream schedules can be disabled with a new ``[p]streamset ignoreschedule`` command (:issue:`4615`)

- Improved error logging (:issue:`4680`)

Trivia Lists
************

- Added ``whosthatpokemon5`` trivia list containing Pokémon from the 5th generation (:issue:`4646`)
- Added ``geography`` trivia list (:issue:`4618`)


Developer changelog
-------------------

- `get_audit_reason()` can now be passed a ``shorten`` keyword argument which will automatically shorten the returned audit reason to fit the max length allowed by Discord audit logs (:issue:`4189`)
- ``bot.remove_command()`` now returns the command object of the removed command as does the equivalent method from `discord.ext.commands.Bot` class (:issue:`4636`)


Documentation changes
---------------------

- Added `cog guide for Downloader cog <streams>` (:issue:`4511`)
- Added `cog guide for Economy cog <streams>` (:issue:`4519`)
- Added `cog guide for Streams cog <streams>` (:issue:`4521`)
- Added `guide_cog_creators` document (:issue:`4637`)
- Removed install instructions for Ubuntu 16.04 (:issue:`4650`)


Redbot 3.4.3 (2020-11-16)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`KianBral`, :ghuser:`maxbooiii`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.3 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1132>`__.

End-user changelog
------------------

Core Bot
********

- Added ``[p]set competing`` command that allows users to set the bot's competing status (:issue:`4607`, :issue:`4609`)

Audio
*****

- Volume changes on ARM systems running a 64 bit OS will now work again (:issue:`4608`)
- Fixed only 100 results being returned on a Youtube playlist (:issue:`4608`)
- Fixed YouTube VOD duration being set to unknown (:issue:`3885`, :issue:`4608`)
- Fixed some YouTube livestreams getting stuck (:issue:`4608`)
- Fixed internal Lavalink manager failing for Java with untypical version formats (:issue:`4608`)
- Improved AAC audio handling (:issue:`4608`)
- Added support for SoundCloud HLS streams (:issue:`4608`)

Economy
*******

- The ``[p]leaderboard`` command no longer fails in DMs when a global bank is used (:issue:`4569`)

Mod
***

- The ban reason is now properly set in the audit log and modlog when using the ``[p]massban`` command (:issue:`4575`)
- The ``[p]userinfo`` command now shows the new Competing activity (:issue:`4610`, :issue:`4611`)

Modlog
******

- The ``[p]case`` and ``[p]casesfor`` commands no longer fail when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)

Mutes
*****

- Fixed automatic remuting on member join for indefinite mutes (:issue:`4568`)

Trivia
******

- ``[p]triviaset custom upload`` now ensures that the filename is lowercase when uploading (:issue:`4594`)

Developer changelog
-------------------

- ``modlog.get_case()`` and methods using it no longer raise when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)

Documentation changes
---------------------

- Added `guide for Cog Manager UI <cogmanagerui>` (:issue:`4152`)
- Added `cog guide for CustomCommands cog <customcommands>` (:issue:`4490`)


Redbot 3.4.2 (2020-10-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.2 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1128>`__.

End-user changelog
------------------

- **Core Bot** - Added info about the metadata file to ``redbot --debuginfo`` (:issue:`4557`)
- **Audio** - Fixed the ``[p]local search`` command (:issue:`4553`)
- **Audio** - Fixed random "Something broke when playing the track." errors for YouTube tracks (:issue:`4559`)
- **Audio** - Commands in ``[p]llset`` group can now be used in DMs (:issue:`4562`)
- **Mod** - Fixed ``[p]massban`` not working for banning members that are in the server (:issue:`4556`, :issue:`4555`)
- **Streams** - Added error messages when exceeding the YouTube quota in the Streams cog (:issue:`4552`)
- **Streams** - Improved logging for unexpected errors in the Streams cog (:issue:`4552`)

Documentation changes
---------------------

- Added `cog guide for Cleanup cog <cleanup>` (:issue:`4488`)
- Removed multi-line commands from `install_linux_mac` to avoid confusing readers (:issue:`4550`)


Redbot 3.4.1 (2020-10-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`absj30`, :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`chloecormier`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Generaleoley`, :ghuser:`hisztendahl`, :ghuser:`jack1142`, :ghuser:`KaiGucci`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`NeuroAssassin`, :ghuser:`nfitzen`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`PythonTryHard`, :ghuser:`SharkyTheKing`, :ghuser:`Stonedestroyer`, :ghuser:`thisisjvgrace`, :ghuser:`TrustyJAID`, :ghuser:`TurnrDev`, :ghuser:`Vexed01`, :ghuser:`Vuks69`, :ghuser:`xBlynd`, :ghuser:`zephyrkul`

Read before updating
--------------------

1. This release fixes a security issue in Mod cog. See `Security changelog below <important-341-2>` for more information.
2. This Red update bumps discord.py to version 1.5.1, which explicitly requests Discord intents. Red requires all Privileged Intents to be enabled. More information can be found at :ref:`enabling-privileged-intents`.
3. Mutes functionality has been moved from the Mod cog to a new separate cog (Mutes) featuring timed and role-based mutes. If you were using it (or want to start now), you can load the new cog with ``[p]load mutes``. You can see the full `Mutes changelog below <important-341-1>`.
4. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

   We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.1/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.
   Please ensure that the WS port in Audio's settings (``[p]llset wsport``) is set to the port from the ``application.yml``.

End-user changelog
------------------

.. _important-341-2:

Security
********

**NOTE:** If you can't update immediately, we recommend globally disabling the affected command until you can.

- **Mod** - Fixed unauthorized privilege escalation exploit in ``[p]massban`` (also called ``[p]hackban``) command. Full security advisory `can be found on our GitHub <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-mp9m-g7qj-6vqr>`__.

Core Bot
********

- Fixed an incorrect error being reported on ``[p]set name`` when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- Fixed ``[p]set nickname`` erroring when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- Fixed an ungraceful error being raised when running ``[p]traceback`` with closed DMs (:issue:`4329`)
- Fixed errors that could arise from invalid URLs in ``[p]set avatar`` (:issue:`4437`)
- Fixed an error being raised with ``[p]set nickname`` when no nickname was provided (:issue:`4451`)
- Fixed and clarified errors being raised with ``[p]set username`` (:issue:`4463`)
- Fixed an ungraceful error being raised when the output of ``[p]unload`` is larger than 2k characters (:issue:`4469`)
- Fixed an ungraceful error being raised when running ``[p]choose`` with empty options (:issue:`4499`)
- Fixed an ungraceful error being raised when a bot left a guild while a menu was open (:issue:`3902`)
- Fixed info missing on the non-embed version of ``[p]debuginfo`` (:issue:`4524`)
- Added ``[p]set api list`` to list all currently set API services, without tokens (:issue:`4370`)
- Added ``[p]set api remove`` to remove API services, including tokens (:issue:`4370`)
- Added ``[p]helpset usetick``, toggling command message being ticked when help is sent to DM (:issue:`4467`, :issue:`4075`)
- Added a default color field to ``[p]set showsettings`` (:issue:`4498`, :issue:`4497`)
- Added the datapath and metadata file to ``[p]debuginfo`` (:issue:`4524`)
- Added a list of disabled intents to ``[p]debuginfo`` (:issue:`4423`)
- Bumped discord.py dependency to version 1.5.1 (:issue:`4423`)
- Locales and regional formats can now be set in individual guilds using ``[p]set locale`` and ``[p]set regionalformat`` (:issue:`3896`, :issue:`1970`)

    - Global locale and regional format setters have been renamed to ``[p]set globallocale`` and ``[p]set globalregionalformat``

Audio
*****

- Scattered grammar and typo fixes (:issue:`4446`)
- Fixed Bandcamp playback (:issue:`4504`)
- Fixed YouTube playlist playback (:issue:`4504`)
- Fixed YouTube searching issues (:issue:`4504`)
- Fixed YouTube age restricted track playback (:issue:`4504`)
- Fixed the Audio cog not being translated when setting locale (:issue:`4492`, :issue:`4495`)
- Fixed tracks getting stuck at 0:00 after long player sessions (:issue:`4529`)
- Removed lavalink logs from being added to backup (:issue:`4453`, :issue:`4452`)
- Removed stream durations from being in queue duration (:issue:`4513`)
- Added the Global Audio API, to cut down on Youtube 429 errors and allow Spotify playback past user's quota. (:issue:`4446`)
- Added persistent queues, allowing for queues to be restored on a bot restart or cog reload (:issue:`4446`)
- Added ``[p]audioset restart``, allowing for Lavalink connection to be restarted (:issue:`4446`)
- Added ``[p]audioset autodeafen``, allowing for bot to auto-deafen itself when entering voice channel (:issue:`4446`)
- Added ``[p]audioset mycountrycode``, allowing Spotify search locale per user (:issue:`4446`)
- Added ``[p]llsetup java``, allowing for a custom Java executable path (:issue:`4446`)
- Added ``[p]llset info`` to show Lavalink settings (:issue:`4527`)
- Added ``[p]audioset logs`` to download Lavalink logs if the Lavalink server is set to internal (:issue:`4527`)

Cleanup
*******

- Allowed ``[p]cleanup self`` to work in DMs for all users (:issue:`4481`)

Custom Commands
***************

- Fixed an ungraceful error being thrown on ``[p]cc edit`` (:issue:`4325`)

Dev
***

- Added ``[p]repl pause`` to pause/resume the REPL session in the current channel (:issue:`4366`)

Economy
*******

- Added an embed option for ``[p]leaderboard`` (:issue:`4184`, :issue:`4104`)

General
*******

- Fixed issues with text not being properly URL encoded (:issue:`4024`)
- Fixed an ungraceful error occurring when a title is longer than 256 characters in ``[p]urban`` (:issue:`4474`)
- Changed "boosters" to "boosts" in ``[p]serverinfo`` to clarify what the number represents (:issue:`4507`)

Mod
***

- Added ``[p]modset mentionspam strict`` allowing for duplicated mentions to count towards the mention spam cap (:issue:`4359`)
- Added an option to ban users not in the guild to ``[p]ban`` (:issue:`4422`, :issue:`4419`)
- Added a default tempban duration for ``[p]tempban`` (:issue:`4473`, :issue:`3992`)
- Fixed nicknames not being properly stored and logged (:issue:`4131`)
- Fixed plural typos in ``[p]userinfo`` (:issue:`4397`, :issue:`4379`)
- Renamed ``[p]hackban`` to ``[p]massban``, keeping ``[p]hackban`` as an alias, allowing for multiple users to be banned at once (:issue:`4422`, :issue:`4419`)
- Moved mutes to a separate, individual cog (:issue:`3634`)

.. _important-341-1:

Mutes
*****

- Added ``[p]muteset forcerole`` to make mutes role based, instead of permission based (:issue:`3634`)
- Added an optional time argument to all mutes, to specify when the user should be unmuted (:issue:`3634`)
- Changed ``[p]mute`` to only handle serverwide muting, ``[p]mute voice`` and ``[p]mute channel`` have been moved to separate commands called ``[p]mutechannel`` and ``[p]mutevoice`` (:issue:`3634`)
- Mute commands can now take multiple user arguments, to mute multiple users at a time (:issue:`3634`)

Modlog
******

- Fixed an error being raised when running ``[p]casesfor`` and ``[p]case`` (:issue:`4415`)
- Long reasons in Modlog are now properly shortened in message content (:issue:`4541`)

Trivia Lists
************

- Fixed incorrect order of Machamp and Machoke questions (:issue:`4424`)
- Added new MLB trivia list (:issue:`4455`)
- Added new Who's That Pokémon - Gen. IV trivia list (:issue:`4434`)
- Added new Hockey trivia list (:issue:`4384`)

Warnings
********

- Fixed users being able to warn users above them in hierarchy (:issue:`4100`)
- Added bool arguments to toggle commands to improve consistency (:issue:`4409`)

Developer changelog
-------------------

| **Important:**
| 1. Red now allows users to set locale per guild, which requires 3rd-party cogs to set contextual locale manually in code ran outside of command's context. See the `Core Bot changelog below <important-dev-341-1>` for more information.

.. _important-dev-341-1:

Core Bot
********

- Added API for setting contextual locales (:issue:`3896`, :issue:`1970`)

    - New function added: `redbot.core.i18n.set_contextual_locales_from_guild()`
    - Contextual locale is automatically set for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information

- Added `bot.remove_shared_api_services() <RedBase.remove_shared_api_services()>` to remove all keys and tokens associated with an API service (:issue:`4370`)
- Added an option to return all tokens for an API service if ``service_name`` is not specified in `bot.get_shared_api_tokens() <RedBase.get_shared_api_tokens()>` (:issue:`4370`)
- Added `bot.get_or_fetch_user() <RedBase.get_or_fetch_user()>` and `bot.get_or_fetch_member() <RedBase.get_or_fetch_member()>` methods (:issue:`4403`, :issue:`4402`)
- Moved ``redbot.core.checks.bot_in_a_guild()`` to `redbot.core.commands.bot_in_a_guild()` (old name has been left as an alias) (:issue:`4515`, :issue:`4510`)

Bank
****

- Bank API methods now consistently throw TypeError if a non-integer amount is supplied (:issue:`4376`)

Mod
***

- Deprecated ``redbot.core.utils.mod.is_allowed_by_hierarchy`` (:issue:`4435`)

Modlog
******

- Added an option to accept a ``discord.Object`` in case creation (:issue:`4326`)
- Added ``last_known_username`` parameter to `modlog.create_case()` function (:issue:`4326`)
- Fixed an error being raised with a deleted channel in `Case.message_content()` (:issue:`4415`)

Utility
*******

- Added `redbot.core.utils.get_end_user_data_statement()` and `redbot.core.utils.get_end_user_data_statement_or_raise()` to attempt to fetch a cog's End User Data Statement (:issue:`4404`)
- Added `redbot.core.utils.chat_formatting.quote()` to quote text in a message (:issue:`4425`)

Documentation changes
---------------------

Config
******

- Added custom group documentation and tutorial (:issue:`4416`, :issue:`2896`)

Modlog
******

- Clarified that naive ``datetime`` objects will be treated as local times for parameters ``created_at`` and ``until`` in `modlog.create_case()` (:issue:`4389`)

Other
*****

- Added guide to creating a Bot Application in Discord Developer Portal, with enabling intents (:issue:`4502`)

Miscellaneous
-------------

- Added JSON schema files for ``info.json`` files (:issue:`4375`)
- Added ``[all]`` and ``[dev]`` bundled install extras (:issue:`4443`)
- Replaced the link to the approved repository list on CogBoard and references to ``cogs.red`` with a link to new Red Index (:issue:`4439`)
- Improved documentation about arguments in command syntax (:issue:`4058`)
- Replaced a few instances of Red with the bot name in command docstrings (:issue:`4470`)
- Fixed grammar in places scattered throughout bot (:issue:`4500`)
- Properly define supported Python versions to be lower than 3.9 (:issue:`4538`)


Redbot 3.4.0 (2020-08-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`DevilXD`, :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kablekompany`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`SharkyTheKing`, :ghuser:`thisisjvgrace`, :ghuser:`Tinonb`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`
|
| **Read before updating**:
| 1. Red 3.4 comes with support for data deletion requests. Bot owners should read `red_core_data_statement` to ensure they know what information about their users is stored by the bot.
| 2. Debian Stretch, Fedora 30 and lower, and OpenSUSE Leap 15.0 and lower are no longer supported as they have already reached end of life.
| 3. There's been a change in behavior of ``[p]tempban``. Look at `Mod changelog <important-340-1>` for full details.
| 4. There's been a change in behavior of announcements in Admin cog. Look at `Admin changelog <important-340-2>` for full details.
| 5. Red 3.4 comes with breaking changes for cog developers. Look at `Developer changelog <important-340-3>` for full details.

End-user changelog
------------------

Core Bot
********

- Added per-guild cog disabling (:issue:`4043`, :issue:`3945`)

    - Bot owners can set the default state for a cog using ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands
    - Guild owners can enable/disable cogs for their guild using ``[p]command disablecog`` and ``[p]command enablecog`` commands
    - Cogs disabled in the guild can be listed with ``[p]command listdisabledcogs``

- Added support for data deletion requests; see `red_core_data_statement` for more information (:issue:`4045`)
- Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)
- ``[p]licenseinfo`` now has a 3 minute cooldown to prevent a single user from spamming channel by using it (:issue:`4110`)
- Added ``[p]helpset showsettings`` command (:issue:`4013`, :issue:`4022`)
- Updated Red's emoji usage to ensure consistent rendering accross different devices (:issue:`4106`, :issue:`4105`, :issue:`4127`)
- Whitelist and blacklist are now called allowlist and blocklist. Old names have been left as aliases (:issue:`4138`)

.. _important-340-2:

Admin
*****

- ``[p]announce`` will now only send announcements to guilds that have explicitly configured text channel to send announcements to using ``[p]announceset channel`` command (:issue:`4088`, :issue:`4089`)

Downloader
**********

- ``[p]cog info`` command now shows end user data statement made by the cog creator (:issue:`4169`)
- ``[p]cog update`` command will now notify the user if cog's end user data statement has changed since last update (:issue:`4169`)

.. _important-340-1:

Mod
***

- ``[p]tempban`` now respects default days setting (``[p]modset defaultdays``) (:issue:`3993`)
- Users can now set mention spam triggers which will warn or kick the user. See ``[p]modset mentionspam`` for more information (:issue:`3786`, :issue:`4038`)
- ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)

ModLog
******

- Added timestamp to text version of ``[p]casesfor`` and ``[p]case`` commands (:issue:`4118`, :issue:`4137`)

Streams
*******

- Stream alerts will no longer make roles temporarily mentionable if bot has "Mention @everyone, @here, and All Roles" permission in the channel (:issue:`4182`)
- Mixer service has been closed and for that reason we've removed support for it from the cog (:issue:`4072`)
- Hitbox commands have been renamed to smashcast (:issue:`4161`)
- Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

Trivia Lists
************

- Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)

.. _important-340-3:

Developer changelog
-------------------

| **Important:**
| 1. Red now offers cog disabling API, which should be respected by 3rd-party cogs in guild-related actions happening outside of command's context. See the `Core Bot changelog below <important-dev-340-1>` for more information.
| 2. Red now provides data request API, which should be supported by all 3rd-party cogs. See the changelog entries in the `Core Bot changelog below <important-dev-340-1>` for more information.

Breaking changes
****************

- By default, none of the ``.send()`` methods mention roles or ``@everyone/@here`` (:issue:`3845`)

    - see `discord.AllowedMentions` and ``allowed_mentions`` kwarg of ``.send()`` methods, if your cog requires to mention roles or ``@everyone/@here``

- `Context.maybe_send_embed()` now supresses all mentions, including user mentions (:issue:`4192`)
- The default value of the ``filter`` keyword argument has been changed to ``None`` (:issue:`3845`)
- Cog package names (i.e. name of the folder the cog is in and the name used when loading the cog) now have to be `valid Python identifiers <https://docs.python.org/3/reference/lexical_analysis.html#identifiers>`__ (:issue:`3605`, :issue:`3679`)
- Method/attribute names starting with ``red_`` or being in the form of ``__red_*__`` are now reserved. See `version_guarantees` for more information (:issue:`4085`)
- `humanize_list()` no longer raises `IndexError` for empty sequences (:issue:`2982`)
- Removed things past deprecation time: (:issue:`4163`)

    - ``redbot.core.commands.APIToken``
    - ``loop`` kwarg from `bounded_gather_iter()`, `bounded_gather()`, and `start_adding_reactions()`

.. _important-dev-340-1:

Core Bot
********

- Added cog disabling API (:issue:`4043`, :issue:`3945`)

    - New methods added: `bot.cog_disabled_in_guild() <RedBase.cog_disabled_in_guild()>`, `bot.cog_disabled_in_guild_raw() <RedBase.cog_disabled_in_guild_raw()>`
    - Cog disabling is automatically applied for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information

- Added data request API (:issue:`4045`,  :issue:`4169`)

    - New special methods added to `commands.Cog`: `red_get_data_for_user()` (documented provisionally), `red_delete_data_for_user()`
    - New special module level variable added: ``__red_end_user_data_statement__``
    - These methods and variables should be added by all cogs according to their documentation; see `recommendations-for-cog-creators` for more information
    - New ``info.json`` key added: ``end_user_data_statement``; see `Info.json format documentation <info-json-format>` for more information

- Added `bot.message_eligible_as_command() <RedBase.message_eligible_as_command()>` utility method which can be used to determine if a message may be responded to as a command (:issue:`4077`)
- Added a provisional API for replacing the help formatter. See `documentation <framework-commands-help>` for more details (:issue:`4011`)
- `bot.ignored_channel_or_guild() <RedBase.ignored_channel_or_guild()>` now accepts `discord.Message` objects (:issue:`4077`)
- `commands.NoParseOptional <NoParseOptional>` is no longer provisional and is now fully supported part of API (:issue:`4142`)
- Red no longer fails to run subcommands of a command group allowed or denied by permission hook (:issue:`3956`)
- Autohelp in group commands is now sent *after* invoking the group, which allows before invoke hooks to prevent autohelp from getting triggered (:issue:`4129`)
- RPC functionality no longer makes Red hang for a minute on shutdown (:issue:`4134`, :issue:`4143`)

Vendored packages
*****************

- Updated ``discord.ext.menus`` vendor (:issue:`4167`)

Utility Functions
*****************

- `humanize_list()` now accepts ``locale`` and ``style`` keyword arguments. See its documentation for more information (:issue:`2982`)
- `humanize_list()` is now properly localized (:issue:`2906`, :issue:`2982`)
- `humanize_list()` now accepts empty sequences (:issue:`2982`)


Documentation changes
---------------------

- Removed install instructions for Debian Stretch (:issue:`4099`)
- Added admin user guide (:issue:`3081`)
- Added alias user guide (:issue:`3084`)
- Added bank user guide (:issue:`4149`)


Miscellaneous
-------------

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)
- ``[p]set nickname``, ``[p]set serverprefix``, ``[p]streamalert``, and ``[p]streamset`` commands now can be run by users with permissions related to the actions they're making (:issue:`4109`)
- `bordered()` now uses ``+`` for corners if keyword argument ``ascii_border`` is set to `True` (:issue:`4097`)
- Fixed timestamp storage in few places in Red (:issue:`4017`)
