.. 3.4.x Changelogs

Redbot 3.4.0 (2020-08-18)
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
- Cog package names (i.e. name of the folder the cog is in and the name used when loading the cog) now have to be `valid Python identifiers <https://docs.python.org/3/reference/lexical_analysis.html#identifiers>`_ (:issue:`3605`, :issue:`3679`)
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
    - Cog disabling is automatically applied for commands and only needs to be done manually for things like event listeners; see `guidelines-for-cog-creators` for more information

- Added data request API (:issue:`4045`,  :issue:`4169`)

    - New special methods added to `commands.Cog`: `red_get_data_for_user()` (documented provisionally), `red_delete_data_for_user()`
    - New special module level variable added: ``__red_end_user_data_statement__``
    - These methods and variables should be added by all cogs according to their documentation; see `guidelines-for-cog-creators` for more information
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
