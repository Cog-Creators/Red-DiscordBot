.. v3.1.0 Changelog

####################
v3.1.0 Release Notes
####################

----------------------
Mongo Driver Migration
----------------------

Due to the required changes of the Mongo driver for Config, all existing Mongo users will need to
complete the below instructions to continue to use Mongo after updating to 3.1.
This includes **all** users, regardless of any prior migration attempt to a development version of
3.1.

 #. Upgrade to 3.1
 #. Convert all existing Mongo instances to JSON using the new converters
 #. Start each bot instance while using JSON and load any and all cogs you have in order to successfully preserve data.
 #. Turn each instance off and convert back to Mongo.
    **NOTE:** No data is wiped from your Mongo database when converting to JSON.
    You may want to use a *new* database name when converting back to Mongo in order to not have duplicate data.

-------------
Setup Utility
-------------

New commands were introduced to simplify the conversion/editing/removal process both on our end and the users end.
Please use ``redbot-setup --help`` to learn how to use the new features.

.. HINT::

    Converting to JSON: ``redbot-setup convert <instance_name> json``

    Converting to Mongo: ``redbot-setup convert <instance_name> mongo``

################
v3.1.0 Changelog
################

-----
Audio
-----

 * Add Spotify support (`#2328`_)
 * Play local folders via text command (`#2457`_)
 * Change pause to a toggle (`#2461`_)
 * Remove aliases (`#2462`_)
 * Add track length restriction (`#2465`_)
 * Seek command can now seek to position (`#2470`_)
 * Add option for dc at queue end (`#2472`_)
 * Emptydisconnect and status refactor (`#2473`_)
 * Queue clean and queue clear addition (`#2476`_)
 * Fix for audioset status (`#2481`_)
 * Playlist download addition (`#2482`_)
 * Add songs when search-queuing (`#2513`_)
 * Match v2 behavior for channel change (`#2521`_)
 * Bot will no longer complain about permissions when trying to connect to user-limited channel, if it has "Move Members" permission (`#2525`_)
 * Fix issue on audiostats command when more than 20 servers to display (`#2533`_)
 * Fix for prev command display (`#2556`_)
 * Fix for localtrack playing (`#2557`_)
 * Fix for playlist queue when not playing (`#2586`_)
 * Track search and append fixes (`#2591`_)
 * DJ role should ask for a role (`#2606`_)

----
Core
----

 * Warn on usage of ``yaml.load`` (`#2326`_)
 * New Event dispatch: ``on_message_without_command`` (`#2338`_)
 * Improve output format of cooldown messages (`#2412`_)
 * Delete cooldown messages when expired (`#2469`_)
 * Fix local blacklist/whitelist management (`#2531`_)
 * ``[p]set locale`` now only accepts actual locales (`#2553`_)
 * ``[p]listlocales`` now displays ``en-US`` (`#2553`_)
 * ``redbot --version`` will now give you current version of Red (`#2567`_)
 * Redesign help and related formatter (`#2628`_)
 * Default locale changed from ``en`` to ``en-US`` (`#2642`_)
 * New command ``[p]datapath`` that prints the bot's datapath (`#2652`_)

------
Config
------

 * Updated Mongo driver to support large guilds (`#2536`_)
 * Introduced ``init_custom`` method on Config objects (`#2545`_)
 * We now record custom group primary key lengths in the core config object (`#2550`_)
 * Migrated internal UUIDs to maintain cross platform consistency (`#2604`_)

-------------
DataConverter
-------------

 * It's dead jim (Removal) (`#2554`_)

----------
discord.py
----------

 * No longer vendoring discord.py (`#2587`_)
 * Upgraded discord.py dependency to version 1.0.1 (`#2587`_)

----------
Downloader
----------

 * ``[p]cog install`` will now tell user that cog has to be loaded (`#2523`_)
 * The message when libraries fail to install is now formatted (`#2576`_)
 * Fixed bug, that caused Downloader to include submodules on cog list (`#2590`_)
 * ``[p]cog uninstall`` allows to uninstall multiple cogs now (`#2592`_)
 * ``[p]cog uninstall`` will now remove cog from installed cogs even if it can't find the cog in install path anymore (`#2595`_)
 * ``[p]cog install`` will not allow to install cogs which aren't suitable for installed version of Red anymore (`#2605`_)
 * Cog Developers now have to use ``min_bot_version`` in form of version string instead of ``bot_version`` in info.json and they can also use ``max_bot_version`` to specify maximum version of Red, more in :doc:`framework_downloader`. (`#2605`_)

------
Filter
------

 * Filter performs significantly better on large servers. (`#2509`_)

--------
Launcher
--------

* Fixed extras in the launcher (`#2588`_)

---
Mod
---

 * Admins can now decide how many times message has to be repeated before ``deleterepeats`` removes it (`#2437`_)
 * Fix: make ``[p]ban [days]`` optional as per the doc (`#2602`_)
 * Added the command ``voicekick`` to kick members from a voice channel with optional mod case. (`#2639`_)

-----------
Permissions
-----------

 * Removed: ``p`` alias for ``permissions`` command (`#2467`_)

-------------
Setup Scripts
-------------

 * ``redbot-setup`` now uses the click CLI library (`#2579`_)
 * ``redbot-setup convert`` now used to convert between libraries (`#2579`_)
 * Backup support for Mongo is currently broken (`#2579`_)

-------
Streams
-------

 * Add support for custom stream alert messages per guild (`#2600`_)
 * Add ability to exclude rerun Twitch streams, and note rerun streams in embed status (`#2620`_)

-----
Tests
-----

 * Test for ``trivia`` cog uses explicitly utf-8 encoding for checking yaml files (`#2565`_)

------
Trivia
------

 * Fix of dead image link for Sao Tome and Principe in ``worldflags`` trivia (`#2540`_)

-----------------
Utility Functions
-----------------

 * New: ``chat_formatting.humaize_timedelta`` (`#2412`_)
 * ``Tunnel`` - Spelling correction of method name - changed ``files_from_attatch`` to ``files_from_attach`` (old name is left for backwards compatibility) (`#2496`_)
 * ``Tunnel`` - fixed behavior of ``react_close()``, now when tunnel closes message will be sent to other end (`#2507`_)
 * ``chat_formatting.humanize_list`` - Improved error handling of empty lists (`#2597`_)

.. _#2326: https://github.com/Cog-Creators/Red-DiscordBot/pull/2326
.. _#2328: https://github.com/Cog-Creators/Red-DiscordBot/pull/2328
.. _#2338: https://github.com/Cog-Creators/Red-DiscordBot/pull/2338
.. _#2412: https://github.com/Cog-Creators/Red-DiscordBot/pull/2412
.. _#2437: https://github.com/Cog-Creators/Red-DiscordBot/pull/2437
.. _#2457: https://github.com/Cog-Creators/Red-DiscordBot/pull/2457
.. _#2461: https://github.com/Cog-Creators/Red-DiscordBot/pull/2461
.. _#2462: https://github.com/Cog-Creators/Red-DiscordBot/pull/2462
.. _#2465: https://github.com/Cog-Creators/Red-DiscordBot/pull/2465
.. _#2467: https://github.com/Cog-Creators/Red-DiscordBot/pull/2467
.. _#2469: https://github.com/Cog-Creators/Red-DiscordBot/pull/2469
.. _#2470: https://github.com/Cog-Creators/Red-DiscordBot/pull/2470
.. _#2472: https://github.com/Cog-Creators/Red-DiscordBot/pull/2472
.. _#2473: https://github.com/Cog-Creators/Red-DiscordBot/pull/2473
.. _#2476: https://github.com/Cog-Creators/Red-DiscordBot/pull/2476
.. _#2481: https://github.com/Cog-Creators/Red-DiscordBot/pull/2481
.. _#2482: https://github.com/Cog-Creators/Red-DiscordBot/pull/2482
.. _#2496: https://github.com/Cog-Creators/Red-DiscordBot/pull/2496
.. _#2507: https://github.com/Cog-Creators/Red-DiscordBot/pull/2507
.. _#2509: https://github.com/Cog-Creators/Red-DiscordBot/pull/2509
.. _#2513: https://github.com/Cog-Creators/Red-DiscordBot/pull/2513
.. _#2521: https://github.com/Cog-Creators/Red-DiscordBot/pull/2521
.. _#2523: https://github.com/Cog-Creators/Red-DiscordBot/pull/2523
.. _#2525: https://github.com/Cog-Creators/Red-DiscordBot/pull/2525
.. _#2531: https://github.com/Cog-Creators/Red-DiscordBot/pull/2531
.. _#2533: https://github.com/Cog-Creators/Red-DiscordBot/pull/2533
.. _#2536: https://github.com/Cog-Creators/Red-DiscordBot/pull/2536
.. _#2540: https://github.com/Cog-Creators/Red-DiscordBot/pull/2540
.. _#2545: https://github.com/Cog-Creators/Red-DiscordBot/pull/2545
.. _#2550: https://github.com/Cog-Creators/Red-DiscordBot/pull/2550
.. _#2553: https://github.com/Cog-Creators/Red-DiscordBot/pull/2553
.. _#2554: https://github.com/Cog-Creators/Red-DiscordBot/pull/2554
.. _#2556: https://github.com/Cog-Creators/Red-DiscordBot/pull/2556
.. _#2557: https://github.com/Cog-Creators/Red-DiscordBot/pull/2557
.. _#2565: https://github.com/Cog-Creators/Red-DiscordBot/pull/2565
.. _#2567: https://github.com/Cog-Creators/Red-DiscordBot/pull/2567
.. _#2576: https://github.com/Cog-Creators/Red-DiscordBot/pull/2576
.. _#2579: https://github.com/Cog-Creators/Red-DiscordBot/pull/2579
.. _#2586: https://github.com/Cog-Creators/Red-DiscordBot/pull/2586
.. _#2587: https://github.com/Cog-Creators/Red-DiscordBot/pull/2587
.. _#2588: https://github.com/Cog-Creators/Red-DiscordBot/pull/2588
.. _#2590: https://github.com/Cog-Creators/Red-DiscordBot/pull/2590
.. _#2591: https://github.com/Cog-Creators/Red-DiscordBot/pull/2591
.. _#2592: https://github.com/Cog-Creators/Red-DiscordBot/pull/2592
.. _#2595: https://github.com/Cog-Creators/Red-DiscordBot/pull/2595
.. _#2597: https://github.com/Cog-Creators/Red-DiscordBot/pull/2597
.. _#2600: https://github.com/Cog-Creators/Red-DiscordBot/pull/2600
.. _#2602: https://github.com/Cog-Creators/Red-DiscordBot/pull/2602
.. _#2604: https://github.com/Cog-Creators/Red-DiscordBot/pull/2604
.. _#2605: https://github.com/Cog-Creators/Red-DiscordBot/pull/2605
.. _#2606: https://github.com/Cog-Creators/Red-DiscordBot/pull/2606
.. _#2620: https://github.com/Cog-Creators/Red-DiscordBot/pull/2620
.. _#2628: https://github.com/Cog-Creators/Red-DiscordBot/pull/2628
.. _#2639: https://github.com/Cog-Creators/Red-DiscordBot/pull/2639
.. _#2642: https://github.com/Cog-Creators/Red-DiscordBot/pull/2642
.. _#2652: https://github.com/Cog-Creators/Red-DiscordBot/pull/2652
