Redbot 3.2.0 (2020-01-09)
=========================
Core Bot Changes
----------------

Breaking Changes
~~~~~~~~~~~~~~~~

- Modlog casetypes no longer have an attribute for auditlog action type. (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- ``redbot.core.modlog.get_next_case_number()`` has been removed. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- Removed :cons:`bank.MAX_BALANCE`, use :meth:`bank.get_max_balance()` from now. (`#2926 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2926>`_)
- The main bot config is no longer directly accessible to cogs. New methods have been added for use where this is concerned.
  New methods for this include

    - ``bot.get_shared_api_tokens``
    - ``bot.set_shared_api_tokens``
    - ``bot.get_embed_color``
    - ``bot.get_embed_colour``
    - ``bot.get_admin_roles``
    - ``bot.get_admin_role_ids``
    - ``bot.get_mod_roles``
    - ``bot.get_mod_role_ids`` (`#2967 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2967>`_)
- Reserves some command names for internal Red use. These are available programatically as ``redbot.core.commands.RESERVED_COMMAND_NAMES`` (`#2973 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2973>`_)
- Removes bot._counter, Makes a few more attrs private (cog_mgr, main_dir) (`#2976 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2976>`_)
- ``bot.wait_until_ready`` should no longer be used during extension setup (`#3073 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3073>`_)
- Removes the mongo driver. (`#3099 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3099>`_)


Bug Fixes
~~~~~~~~~

- Help properly hides disabled commands. (`#2863 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2863>`_)
- Fixed remove_command error when trying to remove a non-existent command (`#2888 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2888>`_)
- ``Command.can_see`` now works as intended for disabled commands (`#2892 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2892>`_)
- Modlog entries now show up properly without the mod cog loaded (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- Fixed error in `[p]reason` when setting the reason for a case without a moderator. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- Check the recipient balance before transferring and stop transfer if will go above the maximum allowed balance. (`#2923 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2923>`_)
- The [p]invite command no longer errors when a user has the bot blocked or DMs disabled in the server. (`#2948 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2948>`_)
- Stop using `:` character in backup's filename - Windows doesn't accept it (`#2954 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2954>`_)
- ``redbot-setup delete`` no longer errors about "unexpected keyword argument" (`#2955 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2955>`_)
- ``redbot-setup delete`` no longer prompts about backup when user passes ``--no-prompt`` option (`#2956 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2956>`_)
- [Core] Inviteset public and perms help string cleanup (`#2963 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2963>`_)
- Make embedset user only affect DM's (`#2966 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2966>`_)
- Give friendly error when provided instance name doesn't exist. (`#2968 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2968>`_)
- Fixed the help text and response of `[p]set usebotcolor` to accurately reflect what the command is doing. (`#2974 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2974>`_)
- Bot no longer types infinitely when command with cooldown is called within last second of cooldown. (`#2985 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2985>`_)
- remove f-string usage in launcher to prevent our error handling from cauing an error. (`#3002 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3002>`_)
- Fixed MessagePredicate.greater and MessagePredicate.less allowing any valid int instead of only valid ints/floats that are greater/less than the given value. (`#3004 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3004>`_)
- Uptime command works with uptimes of under a second (`#3008 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3008>`_)
- Add quotation marks to helpset tagline's response so two consecutive full stops don't appear (`#3010 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3010>`_)
- Fixes an issue with clearing rules in permissions (`#3014 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3014>`_)
- cog install will no longer error if a cog creator has an empty install message (`#3024 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3024>`_)
- Lavalink will now be restarted after unexpected shutdown. (`#3033 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3033>`_)
- Add 3rd-party lib folder to ``sys.path`` before loading cogs. This prevents issues with 3rd-party cogs failing to load without loaded Downloader due to unavailable requirements. (`#3036 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3036>`_)
- Escape track descriptions so that they do not break markdown. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Bot will now properly send a message when the invoked command is guild-only. (`#3057 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3057>`_)
- Always append 3rd-party lib folder to the end of ``sys.path`` to avoid shadowing Red's dependencies. (`#3062 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3062>`_)
- fix ``is_automod_immune`` handling of guild check and support for checking webhooks (`#3100 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3100>`_)
- Fix generation of `repos.json` file in backup process. (`#3114 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3114>`_)
- Fixed an issue when calling audio commands when not in a voice channel could result in a crash. (`#3120 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3120>`_)
- Handle invalid folder names for data path gracefully in ``redbot-setup`` and ``redbot --edit``. (`#3171 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3171>`_)
- ``--owner`` and ``-p`` cli flags now work when added from launcher. (`#3174 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3174>`_)
- Red will now prevent users from locking themselves out with localblacklist. (`#3207 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3207>`_)
- Fixes a way for help to end up a little too large for discord limits (`#3208 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3208>`_)
- Tell user that the (local) whitelist/blacklist is empty when using commands that list whitelisted/blacklisted users/roles. (`#3219 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3219>`_)
- Red will now prevent users from locking guild owner out with localblacklist (unless the command caller is bot owner). (`#3221 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3221>`_)
- Guild owners are no longer affected by local whitelist and blacklist. (`#3221 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3221>`_)
- Fix an attribute error that can be raised in humanize_timedelta if seconds = 0. (`#3231 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3231>`_)
- Fix ``ctx.clean_prefix`` for undocumented changes from discord (`#3249 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3249>`_)
- :attr:`redbot.core.bot.Bot.owner_id` is now set in our post connection startup. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)
- :meth:`redbot.core.bot.Bot.send_to_owners()` and :meth:`redbot.core.bot.Bot.get_owner_notification_destinations()` now wait until Red is done with post connection startup to ensure owner ID is available. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)


Enhancements
~~~~~~~~~~~~

- Add the option to modify the RPC port with the ``--rpc-port`` flag. (`#2429 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2429>`_)
- Slots now has a 62.5% expected payout and won't inflate economy when spammed. (`#2875 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2875>`_)
- Allow passing cls in the :func:`redbot.core.commands.group()` decorator (`#2881 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2881>`_)
- Red's Help Formatter is now considered to have a stable API. (`#2892 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2892>`_)
- Modlog no longer generates cases without being told to for actions the bot did. (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- Some generic modlog casetypes are now pre-registered for cog creator use (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- ModLog is now much faster at creating cases, especially in large servers. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- JSON config files are now stored without indentation, this is to reduce file size and increase performance of write operations. (`#2921 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2921>`_)
- ``--[no-]backup``, ``--[no-]drop-db`` and ``--[no-]remove-datapath`` in ``redbot-setup delete`` command are now on/off flags. (`#2958 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2958>`_)
- Confirmation prompts in ``redbot-setup`` now have default values for user convenience. (`#2958 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2958>`_)
- ```redbot-setup delete`` now has the option to leave Red's data untouched on database backends. (`#2962 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2962>`_)
- Red takes less time to fetch cases, unban members, and list warnings. (`#2964 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2964>`_)
- Link to Getting started guide at the end of installation guides. (`#3025 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3025>`_)
- Bot now handles more things prior to connecting to discord to reduce issues with initial load (`#3045 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3045>`_)
- ``bot.send_filtered`` now returns the message that is sent. (`#3052 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3052>`_)
- Bot will now send a message when the invoked command is DM-only. (`#3057 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3057>`_)
- All ``y/n`` confirmations in cli commands are now unified. (`#3060 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3060>`_)
- Change ``[p]info`` to say "This bot is an..." instead of "This is an..." for clarity. (`#3121 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3121>`_)
- ``redbot-setup`` will now use instance name in default data path to avoid creating second instance with same data path. (`#3171 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3171>`_)
- Instance names can now only include characters A-z, numbers, underscores, and hyphens. Old instances are unaffected by this change. (`#3171 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3171>`_)
- Clarified that ``[p]backup`` saves the **bot's** data in the help text. (`#3172 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3172>`_)
- Add ``redbot --debuginfo`` flag that shows useful information for debugging. (`#3183 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3183>`_)
- Add Python executable field to `[p]debuginfo` command. (`#3184 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3184>`_)
- When Red prompts for token, it will now print a link to the guide explaining how to obtain a token. (`#3204 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3204>`_)
- ``redbot-setup`` will no longer log to disk. (`#3269 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3269>`_)
- :meth:`redbot.core.bot.Bot.send_to_owners()` and :meth:`redbot.core.bot.Bot.get_owner_notification_destinations()` now log that they weren't able to find owner notification destination. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)
- Lib folder is now cleared on minor Python version change. `[p]cog reinstallreqs` command in Downloader cog can be used to regenerate lib folder for new Python version. (`#3274 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3274>`_)
- If Red detects operating system or architecture change, it will warn owner about possible problem with lib folder. (`#3274 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3274>`_)
- ``[p]playlist download`` will now compress playlists larger than
  the server attachment limit and attempt to send that. (`#3279 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3279>`_)


New Feature
~~~~~~~~~~~

- Added functions to acquire locks on Config groups and values. These locks are acquired by default when calling a value as a context manager. See :meth:`Value.get_lock` for details (`#2654 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2654>`_)
- Added a config driver for PostgreSQL (`#2723 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2723>`_)
- Adds methods to Config for accessing things by id without mocked objects

    - Config.guild_from_id
    - Config.user_from_id
    - Config.role_from_id
    - Config.channel_from_id
    - Config.member_from_ids
      - This one requires multiple ids, one for the guild, one for the user
      - Consequence of discord's object model (`#2804 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2804>`_)
- New :func:`humanize_number` in :module:`redbot.core.utils.chat_formatting` function to convert numbers into text which respect locale. (`#2836 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2836>`_)
- Added New commands to Economy

  - ``[p]bank prune user`` - This will delete a user's bank account.
  - ``[p]bank prune local`` - This will prune the bank of accounts from users no longer in the server.
  - ``[p]bank prune global`` - This will prune the global bank of accounts from users who do not share any servers with the bot. (`#2845 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2845>`_)
- Added :func:`bank_prune` to :module:`redbot.core.bank`

  - :func:`bank_prune` can be used to delete a specific user's bank account or remove all invalid bank accounts (For users who are not in the guild if bank is local or share servers with the bot if bank is global). (`#2845 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2845>`_)
- Red now uses towncrier for changelog generation (`#2872 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2872>`_)
- Added :func:`redbot.core.modlog.get_latest_case` to fetch the case object for the most recent ModLog case. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- `[p]bankset maxbal` can be used to set the maximum bank balance. (`#2926 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2926>`_)
- adds a few methods and classes replacing direct config access (which is no longer supported)

   - ``redbot.core.Red.allowed_by_whitelist_blacklist``
   - ``redbot.core.Red.get_valid_prefixes``
   - ``redbot.core.Red.clear_shared_api_tokens``
   - ``redbot.core.commands.help.HelpSettings`` (`#2976 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2976>`_)
- Added ``redbot --edit`` cli flag that can be used to edit instance name, token, owner and datapath. (`#3060 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3060>`_)
- adds a licenseinfo command (`#3090 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3090>`_)
- Ensure people can migrate from MongoDB (`#3108 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3108>`_)
- Adds a command to list disabled commands globally or per guild. (`#3118 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3118>`_)
- New event ``on_red_api_tokens_update`` is now dispatched when shared api keys for the service are updated. (`#3134 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3134>`_)
- Added ``redbot-setup backup`` command. (`#3235 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3235>`_)
- Added :meth:`redbot.core.bot.Bot.wait_until_red_ready()` method that waits until our post connection startup is done. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)


Removals
~~~~~~~~

- The ``set owner`` and ``set token`` commands have been removed in favor of managing server side. (`#2928 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2928>`_)
- Shared libraries are marked for removal in Red 3.3. (`#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_)
- Removed ``[p]backup`` command. Use ``redbot-setup backup`` cli command instead. (`#3235 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3235>`_)
- Removed ``safe_delete``, ``fuzzy_command_search``, ``format_fuzzy_results`` and ``create_backup`` functions from ``redbot.core.utils``. (`#3240 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3240>`_)
- Removes a lot of the launcher's handled behavior (`#3289 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3289>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_, `#2723 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2723>`_, `#2836 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2836>`_, `#2849 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2849>`_, `#2885 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2885>`_, `#2924 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2924>`_, `#2939 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2939>`_, `#2939 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2939>`_, `#2941 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2941>`_, `#2949 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2949>`_, `#2953 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2953>`_, `#2964 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2964>`_, `#2986 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2986>`_, `#2997 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2997>`_, `#3008 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3008>`_, `#3017 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3017>`_, `#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_, `#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_, `#3192 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3192>`_, `#3193 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3193>`_, `#3202 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3202>`_, `#3214 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3214>`_, `#3223 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3223>`_, `#3245 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3245>`_, `#3247 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3247>`_, `#3248 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3248>`_, `#3254 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3254>`_, `#3255 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3255>`_, `#3256 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3256>`_, `#3258 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3258>`_, `#3261 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3261>`_, `#3276 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3276>`_, `#3293 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3293>`_, `#3296 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3296>`_


Changes to dependencies
~~~~~~~~~~~~~~~~~~~~~~~

- Update python minimum requirement to 3.8.1

  Update JRE to Java 11 (`#3245 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3245>`_)
- bumps dependency versions (`#3288 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3288>`_)
- bump red-lavalink version (`#3290 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3290>`_)


Documentation Changes
~~~~~~~~~~~~~~~~~~~~~

- Start the user guides covering cogs and the user interface of the bot. This
  includes, for now, a "Getting started" guide. (`#1734 <https://github.com/Cog-Creators/Red-DiscordBot/issues/1734>`_)
- Added documentation for PM2 support. (`#2105 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2105>`_)
- Updated linux install docs, adding sections for Fedora Linux, Debian/Raspbian Buster, and openSUSE. (`#2558 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2558>`_)
- Create documentation covering what we consider a developer facing breaking change and guarantees regarding them. (`#2882 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2882>`_)
- Fixed user parameter being labeled as discord.TextChannel instead of discord.abc.User. (`#2914 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2914>`_)
- Updated towncrier info in contribution guidelines to include how to do a standalone PR. (`#2915 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2915>`_)
- Reworded virtual environment guide to make it sound less scary. (`#2920 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2920>`_)
- Driver docs no longer show twice. (`#2972 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2972>`_)
- Added more information about ``redbot.core.utils.humanize_timedelta`` into the docs (`#2986 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2986>`_)
- Add direct link to "Installing Red" section in "Installing using powershell and chocolatey" (`#2995 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2995>`_)
- Update Git PATH install (Windows), capitalise some words, don't mention to launcher (`#2998 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2998>`_)
- Adds autostart documentation for Red users who installed it inside a virtual environment. (`#3005 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3005>`_)
- Update Cog Creation guide with a note regarding the Develop version as well as folder layout for local cogs (`#3021 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3021>`_)
- Add proper docstrings to enums that show in drivers docs. (`#3035 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3035>`_)
- Discord.py docs links will now always use docs for currently used version of discord.py. (`#3053 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3053>`_)
- Add ``|DPY_VERSION|`` substitution that will automatically get replaced by current discord.py version. (`#3053 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3053>`_)
- Add missing descriptions for function returns. (`#3054 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3054>`_)
- Word using dev during install more strongly, to try to avoid end users using dev. (`#3079 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3079>`_)
- Do not overwrite the docs/prolog.txt file in conf.py. (`#3082 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3082>`_)
- Fix some typos and wording, add MS Azure to host list (`#3083 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3083>`_)
- Update docs footer copyright to 2019. (`#3105 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3105>`_)
- Add deprecation note about shared libraries in Downloader Framework docs. (`#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_)
- Update apikey framework documentation. Change bot.get_shared_api_keys() to bot.get_shared_api_tokens(). (`#3110 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3110>`_)
- Add information about ``info.json``'s ``min_python_version`` key in Downloader Framework docs. (`#3124 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3124>`_)
- Add event reference for ``on_red_api_tokens_update`` event in Shared API Keys docs. (`#3134 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3134>`_)
- Add notes about best practices with config. (`#3149 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3149>`_)
- Document additional attributes in Context (`#3151 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3151>`_)
- update windows docs with up to date dependency instructions (`#3188 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3188>`_)
- Added "Publishing cogs for V3" document explaining how to make user's cogs work with Downloader. (`#3234 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3234>`_)
- Fix broken docs for :func:`redbot.core.commands.Context.react_quietly`. (`#3257 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3257>`_)
- Updated copyright notices on License and RTD config to 2020 (`#3259 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3259>`_)
- add line about setuptools and wheel (`#3262 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3262>`_)
- Ensure development builds are not advertised to the wrong audience (`#3292 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3292>`_)
- Clarify usage intent of some chat formatting functions (`#3292 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3292>`_)


Admin
-----

Breaking Changes
~~~~~~~~~~~~~~~~

- Changed ``[p]announce ignore`` and ``[p]announce channel`` to ``[p]announceset ignore`` and ``[p]announceset channel``. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Changed ``[p]selfrole <role>`` to ``[p]selfrole add <role>``, changed ``[p]selfrole add`` to ``[p]selfroleset add`` , and changed ``[p]selfrole delete`` to ``[p]selfroleset remove``. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)


Bug Fixes
~~~~~~~~~

- Fixed ``[p]announce`` failing after encountering an error attempting to message the bot owner. (`#3166 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3166>`_)
- Improved the clairty of user facing messages in the admin cog when the user is not allowed
  to do something due to Discord hierarchy rules. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Fixed some role managing commands not properly checking if the bot had manage_roles perms before attempting to manage roles. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Fixed ``[p]editrole`` commands not checking if roles to be edited are higher than the bot's highest role before trying to edit them. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Fixed ``[p]announce ignore`` and ``[p]announce channel`` not being able to be used by guild owners and administrators. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)


Enhancements
~~~~~~~~~~~~

- Add custom issue messages for adding and removing roles, this makes it easier to create translations. (`#3016 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3016>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_, `#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_, `#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_


Alias
-----

No significant changes.


Audio
-----

Bug Fixes
~~~~~~~~~

- ``[p]playlist remove`` now removes the playlist url if the playlist was created through ``[p]playlist save``. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- Users are no longer able to accidentally overwrite existing playlist if a new one with the same name is created/rename. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]audioset settings`` no longer shows lavalink JAR version. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- :code:`KeyError: loadType` when trying to play tracks has been fixed. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset settings`` now uses :code:`ctx.is_owner()` to check if context author is the bot owner. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Fix track index being off by 1 on ``[p]search`` command. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- Fix an issue where updating your Spotify and YouTube Data API tokens did not refresh them. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Fix an issue where the blacklist was not being applied correctly. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Fix an issue in ``[p]audioset restrictions blacklist list`` where it would call the list a `Whitelist`. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Unify capitalisation in ``[p]help playlist``. (`#3048 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3048>`_)
- Bot's status is now properly cleared on emptydisconnect. (`#3050 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3050>`_)
- Correctly reports the import error when an SQL dependency is missing. (`#3065 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3065>`_)
- Fix a console spam caused sometimes when auto disconnect and auto pause are used. (`#3123 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3123>`_)
- Fixed an error that was thrown when running ``[p]audioset dj``. (`#3165 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3165>`_)
- Fixed a crash that could happen when the bot can't connect to the lavalink node, (`#3238 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3238>`_)
- Restrict the number of songs shown in the queue to first 500 to avoid heartbeats. (`#3279 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3279>`_)
- Add more cooldown to playlist commands and restrict queue and playlist to 10k songs to avoid DOS attacks(User crashing your bot on purpose). (`#3286 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3286>`_)


Enhancements
~~~~~~~~~~~~

- ``[p]playlist upload`` will now load playlists generated via ``[p]playlist download`` much faster if the playlist use the new scheme. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]playlist`` commands now can be used by everyone regardless of DJ settings, however it will respect DJ settings when creating/modifying playlist in the server scope. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- Spotify, Youtube Data and Lavalink API calls can be cached to avoid repeated calls in the future, see ``[p]audioset cache``. (`#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_)
- Playlist will now start playing as soon as first track is loaded. (`#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_)
- ``[p]audioset localpath`` can set a path anywhere in your machine now.
   - Note: This path needs to be visible by :code:`Lavalink.jar`. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]queue`` now works where there are no tracks in the queue (it shows the current track playing). (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset settings`` now reports lavalink lib version. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Adding and removing reactions in Audio is no longer a blocking action. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- When shuffle is on queue now shows correct play order. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]seek`` and ``[p]skip`` can be used by user if they are the song requester while DJ mode is enabled, if votes are disabled. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Adding a playlist and album to a saved playlist skips tracks already in the playlist. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Turn off DJ mode if the DJ role is deleted. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- When playing a localtrack ``[p]play`` and ``[p]bumpplay`` no longer require the use of "localtracks\\" prefix.

  Before: ``[p]bumpplay localtracks\\ENM\\501 - Inside The Machine.mp3``
  Now: ``[p]bumpplay ENM\\501 - Inside The Machine.mp3``
  Now nested folders: ``[p]bumpplay Parent Folder\\Nested Folder\\track.mp3`` (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Remove commas for explanations about how to set API keys. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)
- Improved explanation in help string for ``[p]audioset emptydisconnect``. (`#3051 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3051>`_)
- Expose FriendlyExceptions to users on the play command. (`#3085 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3085>`_)
- Better error handling the player is unable to play multiple tracks in sequence. (`#3165 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3165>`_)


New Feature
~~~~~~~~~~~

- Added support for nested folders in the localtrack folder. (`#270 <https://github.com/Cog-Creators/Red-DiscordBot/issues/270>`_)
- Auto pause queue when room is empty. (`#721 <https://github.com/Cog-Creators/Red-DiscordBot/issues/721>`_)
- Playlist are now stored in a dataclass and new APIs were added to interact with them see :module:`redbot.cogs.audio.playlist` for more details. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- All Playlist commands now accept optional arguments, use ``[p]help playlist <subcommand>`` for more details. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]playlist rename`` will now allow users to rename existing playlists. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]playlist update`` will allow users to update non custom Playlists to the latest available tracks. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- There are 3 different scopes of playlist now, to define them use the ``--scope`` argument.

      ``Global Playlist``

      - These playlists will be available in all servers the bot is in.
      - These can be managed by the Bot Owner only.

      ``Server Playlist``

      - These playlists will only be available in the server they were created in.
      - These can be managed by the Bot Owner, Guild Owner, Mods, Admins, DJs and creator (if DJ role is disabled).

      ``User Playlist``

      - These playlists will be available in all servers both the bot and the creator are in.
      - These can be managed by the Bot Owner and Creator only. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]audioset cache`` can be used to set the cache level. **It's off by default**. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]genre`` command can be used to play spotify playlist. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset cacheage`` can be used to set maximum age of an entry in the cache. **Default is 365 days**. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset autoplay`` can be used to enable auto play once the queue runs out. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- New events dispatched by Audio.

   - :code:`on_red_audio_track_start(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`
   - :code:`on_red_audio_track_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`
   - :code:`on_red_audio_track_enqueue(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`
   - :code:`on_red_audio_track_auto_play(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`
   - :code:`on_red_audio_queue_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`
   - :code:`on_red_audio_audio_disconnect(guild: discord.Guild)`
   - :code:`on_red_audio_should_auto_play(guild: discord.Guild, channel: discord.VoiceChannel, play: Callable)`
   - :code:`on_red_audio_initialized(audio:Cog)`
   - :code:`on_red_audio_skip_track(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`
   - :code:`on_red_audio_unload(audio:Cog)` (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]queue shuffle`` can be used to shuffle the queue manually. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]queue clean self`` can be used to remove all songs you requested from the queue. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset restrictions`` can be used to add or remove keywords which songs must have or are not allowed to have. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]playlist dedupe`` can be used to remove duplicated tracks from a playlist. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]autoplay`` can be used to play a song. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]bumpplay`` command has been added. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- ``[p]shuffle`` command has an additional argument to tell the bot whether it should shuffle bumped tracks. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- Add global whitelist/blacklist commands. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Add self managed daily playlists in the GUILD scope, these are called "Daily playlist - YYYY-MM-DD" and auto delete after 7 days. (`#3199 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3199>`_)
- ``[p]remove`` command now accepts an URL or Index, if an URL is used it will remove all tracks in the queue with that URL. (`#3201 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3201>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_, `#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_, `#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_, `#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_, `#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_, `#3059 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3059>`_, `#3089 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3089>`_, `#3104 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3104>`_, `#3104 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3104>`_, `#3152 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3152>`_, `#3168 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3168>`_, `#3176 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3176>`_, `#3195 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3195>`_, `#3275 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3275>`_


Changes to dependencies
~~~~~~~~~~~~~~~~~~~~~~~

- New dependency: ``databases[sqlite]``. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``Red-Lavalink`` bumped to version 0.4.0. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Lavalink Jar update

  We still want more to be handled, but soundcloud is working again. (`#3291 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3291>`_)


Bank
----

No significant changes.


Cleanup
-------

No significant changes.


CustomCom
---------

Enhancements
~~~~~~~~~~~~

- The group command `[p]cc` create can now be used to create simple CCs without specifying "simple". (`#1767 <https://github.com/Cog-Creators/Red-DiscordBot/issues/1767>`_)
- Add query option for CC typehints, for URL-based CCs. (`#3228 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3228>`_)
- Use humanize_list utility for iterable parameter results, e.g. :code:`{#:Role.members}`. (`#3277 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3277>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#3186 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3186>`_


Downloader
----------

Bug Fixes
~~~~~~~~~

- Made regex for repo names use raw string to stop ``DeprecationWarning`` about invalid escape sequence. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- Downloader will no longer allow to install cog that is already installed. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- Repo names can now only contain the characters listed in the help text (A-Z, 0-9, underscores, and hyphens). (`#2827 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2827>`_)
- findcog no longer attempts to find a cog for commands without one. (`#2902 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2902>`_)
- Downloader will no longer allow to install cog with same name as other that is installed. (`#2927 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2927>`_)
- Catch errors if remote repository or branch is deleted, notify user which repository failed and continue updating others. (`#2936 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2936>`_)
- Make :attr:`redbot.cogs.downloader.repo_manager.Repo.clean_url` work with relative urls. This property uses `str` type now. (`#3141 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3141>`_)
- Fixed an error on repo add from empty string values for the `install_msg` info.json field. (`#3153 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3153>`_)
- Disable all git auth prompts when adding/updating repo with Downloader. (`#3159 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3159>`_)
- ``[p]findcog`` now properly works for cogs with less typical folder structure. (`#3177 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3177>`_)
- ``[p]cog uninstall`` now fully unloads cog - bot will not try to load it on next startup. (`#3179 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3179>`_)


Enhancements
~~~~~~~~~~~~

- Downloader will now check if Python and bot version match requirements in ``info.json`` during update. (`#1866 <https://github.com/Cog-Creators/Red-DiscordBot/issues/1866>`_)
- User can now pass multiple cog names to ``[p]cog install``. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- When passing cogs to ``[p]cog update`` command, it will now only update those cogs, not all cogs from the repo these cogs are from. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added error messages for failures during installing/reinstalling requirements and copying cogs and shared libraries. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- Use sanitized url (without HTTP Basic Auth fragments) in `[p]findcog` command. (`#3129 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3129>`_)
- ``[p]repo info`` will now show repo's url, branch and authors. (`#3225 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3225>`_)
- ``[p]cog info`` will now show cog authors. (`#3225 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3225>`_)
- ``[p]findcog`` will now show repo's branch. (`#3225 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3225>`_)


New Feature
~~~~~~~~~~~

- Added ``[p]repo update [repos]`` command that allows you to update repos without updating cogs from them. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog installversion <repo_name> <revision> <cogs>`` command that allows you to install cogs from specified revision (commit, tag) of given repo. When using this command, the cog will automatically be pinned. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog pin <cogs>`` and ``[p]cog unpin <cogs>`` for pinning cogs. Cogs that are pinned will not be updated when using update commands. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog checkforupdates`` command that will tell which cogs can be updated (including pinned cog) without updating them. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog updateallfromrepos <repos>`` command that will update all cogs from given repos. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog updatetoversion <repo_name> <revision> [cogs]`` command that updates all cogs or ones of user's choosing to chosen revision of given repo. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added `[p]cog reinstallreqs` command that allows to reinstall cog requirements and shared libraries for all installed cogs. (`#3167 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3167>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_, `#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_, `#3080 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3080>`_, `#3080 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3080>`_, `#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_, `#3129 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3129>`_, `#3160 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3160>`_, `#3173 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3173>`_, `#3229 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3229>`_, `#3278 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3278>`_, `#3285 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3285>`_, `#3285 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3285>`_


Changes to dependencies
~~~~~~~~~~~~~~~~~~~~~~~

- Added ``pytest-mock`` requirement to ``tests`` extra. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)


Documentation Changes
~~~~~~~~~~~~~~~~~~~~~

- Added :func:`redbot.cogs.downloader.installable.InstalledModule` to Downloader's framework docs. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Remove API Reference for Downloader cog. (`#3234 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3234>`_)


Economy
-------

No significant changes.


Filter
------

No significant changes.


General
-------

No significant changes.


Image
-----

Enhancements
~~~~~~~~~~~~

- Updated the giphycreds command to match the formatting of the other API commands. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)
- Remove commas for explanations about how to set API keys. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)


Mod
---

Bug Fixes
~~~~~~~~~

- userinfo doesn't break with absurd numbers of roles. (`#2910 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2910>`_)
- Fixed Mod cog not recording username changes for ``[p]names`` and ``[p]userinfo`` commands (`#2918 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2918>`_)
- Fixed an error when reloading the core mod cog (`#2932 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2932>`_)


Enhancements
~~~~~~~~~~~~

- Slowmode now accepts integer only inputs as seconds (`#2884 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2884>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_, `#2993 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2993>`_


ModLog
------

No significant changes.


Mutes
-----

No significant changes.


Permissions
-----------

Bug Fixes
~~~~~~~~~

- defaults are cleared properly when clearing all rules (`#3037 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3037>`_)


Enhancements
~~~~~~~~~~~~

- Clear out usage of commands with ``<who_or_what>`` argument. (`#2991 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2991>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#3186 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3186>`_


Reports
-------

No significant changes.


Streams
-------

Bug Fixes
~~~~~~~~~

- Fix a TypeError in TwitchStream class when calling Twitch client_id from Red shared APIs tokens and also changed the stream_alert function for Twitch alerts to make it works with how TwitchStream class works now. (`#3042 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3042>`_)


Enhancements
~~~~~~~~~~~~

- Remove commas for explanations about how to set API keys. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)


Trivia
------

Bug Fixes
~~~~~~~~~

- Fixes a typo in `Ahsoka Tano`'s name in the starwars trivia (`#2909 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2909>`_)
- Fixes a bug where ``[p]trivia leaderboard`` failed to run. (`#2911 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2911>`_)
- Fix typo in the Greek mythology trivia regarding Hermes' staff (`#2994 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2994>`_)
- Fixed a question in Overwatch accepting blank responses. (`#2996 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2996>`_)
- Fixed answers that were incorrect in the Clash Royale trivia list. (`#3236 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3236>`_)


Enhancements
~~~~~~~~~~~~

- Add trivia for Prince and Michael Jackson lyrics (`#12 <https://github.com/Cog-Creators/Red-DiscordBot/issues/12>`_)


Warnings
--------

No significant changes.
