.. 3.2.x Changelogs

Redbot 3.2.3 (2020-01-17)
=========================

Core Bot Changes
----------------

- Further improvements have been made to bot startup and shutdown.
- Prefixes are now cached for performance.
- Added the means for cog creators to use a global preinvoke hook.
- The bot now ensures it has at least the bare neccessary permissions before running commands.
- Deleting instances works as intended again.
- Sinbad stopped fighting it and embraced the entrypoint madness.

Core Commands
-------------

- The servers command now also shows the ids.

Admin Cog
---------

- The selfrole command now has reasonable expectations about hierarchy.

Help Formatter
--------------

- ``[botname]`` is now replaced with the bot's display name in help text.
- New features added for cog creators to further customize help behavior.
  
  - Check out our command reference for details on new ``format_help_for_context`` method.
- Embed settings are now consistent.

Downloader
----------

- Improved a few user facing messages.
- Added pagination of output on cog update.
- Added logging of failures.

Docs
----

There's more detail to the below changes, so go read the docs.
For some reason, documenting documentation changes is hard.

- Added instructions about git version.
- Clarified instructions for installation and update.
- Added more details to the API key reference.
- Fixed some typos and versioning mistakes.


Audio
-----

Draper did things.

- No seriously, Draper did things.
- Wait you wanted details? Ok, I guess we can share those.
- Audio properly disconnects with autodisconnect, even if notify is being used.
- Symbolic links now work as intended for local tracks.
- Bump play now shows the correct time till next track.
- Multiple user facing messages have been made more correct.

Redbot 3.2.2 (2020-01-10)
=========================

Hotfixes
--------

- Fix Help Pagination issue

Docs
----

- Correct venv docs


Redbot 3.2.1 (2020-01-10)
=========================

Hotfixes
--------

- Fix Mongo conversion from being incorrectly blocked
- Fix announcer not creating a message for success feedback
- Log an error with creating case types rather than crash


Redbot 3.2.0 (2020-01-09)
=========================
Core Bot Changes
----------------

Breaking Changes
~~~~~~~~~~~~~~~~

- Modlog casetypes no longer have an attribute for auditlog action type. (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- Removed ``redbot.core.modlog.get_next_case_number()``. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- Removed ``bank.MAX_BALANCE``, use ``bank.get_max_balance()`` from now on. (`#2926 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2926>`_)
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
- Reserved some command names for internal Red use. These are available programatically as ``redbot.core.commands.RESERVED_COMMAND_NAMES``. (`#2973 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2973>`_)
- Removed ``bot._counter``, Made a few more attrs private (``cog_mgr``, ``main_dir``). (`#2976 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2976>`_)
- Extension's ``setup()`` function should no longer assume that we are, or even will be connected to Discord.
  This also means that cog creators should no longer use ``bot.wait_until_ready()`` inside it. (`#3073 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3073>`_)
- Removed the mongo driver. (`#3099 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3099>`_)


Bug Fixes
~~~~~~~~~

- Help now properly hides disabled commands. (`#2863 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2863>`_)
- Fixed ``bot.remove_command`` throwing an error when trying to remove a non-existent command. (`#2888 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2888>`_)
- ``Command.can_see`` now works as intended for disabled commands. (`#2892 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2892>`_)
- Modlog entries now show up properly without the mod cog loaded. (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- Fixed an error in ``[p]reason`` when setting the reason for a case without a moderator. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- Bank functions now check the recipient balance before transferring and stop the transfer if the recipient's balance will go above the maximum allowed balance. (`#2923 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2923>`_)
- Removed potential for additional bad API calls per ban/unban. (`#2945 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2945>`_)
- The ``[p]invite`` command no longer errors when a user has the bot blocked or DMs disabled in the server. (`#2948 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2948>`_)
- Stopped using the ``:`` character in backup's filename - Windows doesn't accept it. (`#2954 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2954>`_)
- ``redbot-setup delete`` no longer errors with "unexpected keyword argument". (`#2955 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2955>`_)
- ``redbot-setup delete`` no longer prompts about backup when the user passes the option ``--no-prompt``. (`#2956 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2956>`_)
- Cleaned up the ``[p]inviteset public`` and ``[p]inviteset perms`` help strings.  (`#2963 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2963>`_)
- ```[p]embedset user`` now only affects DM's. (`#2966 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2966>`_)
- Fixed an unfriendly error when the provided instance name doesn't exist. (`#2968 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2968>`_)
- Fixed the help text and response of ``[p]set usebotcolor`` to accurately reflect what the command is doing. (`#2974 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2974>`_)
- Red no longer types infinitely when a command with a cooldown is called within the last second of a cooldown. (`#2985 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2985>`_)
- Removed f-string usage in the launcher to prevent our error handling from causing an error. (`#3002 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3002>`_)
- Fixed ``MessagePredicate.greater`` and ``MessagePredicate.less`` allowing any valid int instead of only valid ints/floats that are greater/less than the given value. (`#3004 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3004>`_)
- Fixed an error in ``[p]uptime`` when the uptime is under a second. (`#3009 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3009>`_)
- Added quotation marks to the response of ``[p]helpset tagline`` so that two consecutive full stops do not appear. (`#3010 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3010>`_)
- Fixed an issue with clearing rules in permissions. (`#3014 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3014>`_)
- Lavalink will now be restarted after an unexpected shutdown. (`#3033 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3033>`_)
- Added a 3rd-party lib folder to ``sys.path`` before loading cogs. This prevents issues with 3rd-party cogs failing to load when Downloader is not loaded to install requirements. (`#3036 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3036>`_)
- Escaped track descriptions so that they do not break markdown. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Red will now properly send a message when the invoked command is guild-only. (`#3057 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3057>`_)
- Arguments ``--co-owner`` and ``--load-cogs`` now properly require at least one argument to be passed. (`#3060 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3060>`_)
- Now always appends the 3rd-party lib folder to the end of ``sys.path`` to avoid shadowing Red's dependencies. (`#3062 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3062>`_)
- Fixed ``is_automod_immune``'s handling of the guild check and added support for checking webhooks. (`#3100 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3100>`_)
- Fixed the generation of the ``repos.json`` file in the backup process. (`#3114 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3114>`_)
- Fixed an issue where calling audio commands when not in a voice channel could result in a crash. (`#3120 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3120>`_)
- Added handling for invalid folder names in the data path gracefully in ``redbot-setup`` and ``redbot --edit``. (`#3171 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3171>`_)
- ``--owner`` and ``-p`` cli flags now work when added from launcher. (`#3174 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3174>`_)
- Red will now prevent users from locking themselves out with localblacklist. (`#3207 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3207>`_)
- Fixed help ending up a little too large for discord embed limits. (`#3208 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3208>`_)
- Fixed formatting issues in commands that list whitelisted/blacklisted users/roles when the list is empty. (`#3219 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3219>`_)
- Red will now prevent users from locking the guild owner out with localblacklist (unless the command caller is bot owner). (`#3221 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3221>`_)
- Guild owners are no longer affected by the local whitelist and blacklist. (`#3221 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3221>`_)
- Fixed an attribute error that can be raised in ``humanize_timedelta`` if ``seconds = 0``. (`#3231 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3231>`_)
- Fixed ``ctx.clean_prefix`` issues resulting from undocumented changes from discord. (`#3249 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3249>`_)
- ``redbot.core.bot.Bot.owner_id`` is now set in the post connection startup. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)
- ``redbot.core.bot.Bot.send_to_owners()`` and ``redbot.core.bot.Bot.get_owner_notification_destinations()`` now wait until Red is done with post connection startup to ensure owner ID is available. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)


Enhancements
~~~~~~~~~~~~

- Added the option to modify the RPC port with the ``--rpc-port`` flag. (`#2429 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2429>`_)
- Slots now has a 62.5% expected payout and will not inflate economy when spammed. (`#2875 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2875>`_)
- Allowed passing ``cls`` in the ``redbot.core.commands.group()`` decorator. (`#2881 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2881>`_)
- Red's Help Formatter is now considered to have a stable API. (`#2892 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2892>`_)
- Modlog no longer generates cases without being told to for actions the bot did. (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- Some generic modlog casetypes are now pre-registered for cog creator use. (`#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_)
- ModLog is now much faster at creating cases, especially in large servers. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- JSON config files are now stored without indentation, this is to reduce the file size and increase the performance of write operations. (`#2921 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2921>`_)
- ``--[no-]backup``, ``--[no-]drop-db`` and ``--[no-]remove-datapath`` in the ``redbot-setup delete`` command are now on/off flags. (`#2958 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2958>`_)
- The confirmation prompts in ``redbot-setup`` now have default values for user convenience. (`#2958 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2958>`_)
- ``redbot-setup delete`` now has the option to leave Red's data untouched on database backends. (`#2962 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2962>`_)
- Red now takes less time to fetch cases, unban members, and list warnings. (`#2964 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2964>`_)
- Red now handles more things prior to connecting to discord to reduce issues during the initial load. (`#3045 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3045>`_)
- ``bot.send_filtered`` now returns the message that is sent. (`#3052 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3052>`_)
- Red will now send a message when the invoked command is DM-only. (`#3057 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3057>`_)
- All ``y/n`` confirmations in cli commands are now unified. (`#3060 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3060>`_)
- Changed ``[p]info`` to say "This bot is an..." instead of "This is an..." for clarity. (`#3121 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3121>`_)
- ``redbot-setup`` will now use the instance name in default data paths to avoid creating a second instance with the same data path. (`#3171 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3171>`_)
- Instance names can now only include characters A-z, numbers, underscores, and hyphens. Old instances are unaffected by this change. (`#3171 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3171>`_)
- Clarified that ``[p]backup`` saves the **bot's** data in the help text. (`#3172 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3172>`_)
- Added ``redbot --debuginfo`` flag which shows useful information for debugging. (`#3183 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3183>`_)
- Added the Python executable field to ``[p]debuginfo``. (`#3184 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3184>`_)
- When Red prompts for a token, it will now print a link to the guide explaining how to obtain a token. (`#3204 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3204>`_)
- ``redbot-setup`` will no longer log to disk. (`#3269 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3269>`_)
- ``redbot.core.bot.Bot.send_to_owners()`` and ``redbot.core.bot.Bot.get_owner_notification_destinations()`` now log when they are not able to find the owner notification destination. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)
- The lib folder is now cleared on minor Python version changes. ``[p]cog reinstallreqs`` in Downloader can be used to regenerate the lib folder for a new Python version. (`#3274 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3274>`_)
- If Red detects operating system or architecture change, it will now warn the owner about possible problems with the lib folder. (`#3274 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3274>`_)
- ``[p]playlist download`` will now compress playlists larger than the server attachment limit and attempt to send that. (`#3279 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3279>`_)


New Features
~~~~~~~~~~~~

- Added functions to acquire locks on Config groups and values. These locks are acquired by default when calling a value as a context manager. See ``Value.get_lock`` for details. (`#2654 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2654>`_)
- Added a config driver for PostgreSQL. (`#2723 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2723>`_)
- Added methods to Config for accessing things by id without mocked objects

    - ``Config.guild_from_id``
    - ``Config.user_from_id``
    - ``Config.role_from_id``
    - ``Config.channel_from_id``
    - ``Config.member_from_ids``
      - This one requires multiple ids, one for the guild, one for the user
      - Consequence of discord's object model (`#2804 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2804>`_)
- New method ``humanize_number`` in ``redbot.core.utils.chat_formatting`` to convert numbers into text that respects the current locale. (`#2836 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2836>`_)
- Added new commands to Economy

  - ``[p]bank prune user`` - This will delete a user's bank account.
  - ``[p]bank prune local`` - This will prune the bank of accounts for users who are no longer in the server.
  - ``[p]bank prune global`` - This will prune the global bank of accounts for users who do not share any servers with the bot. (`#2845 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2845>`_)
- Red now uses towncrier for changelog generation. (`#2872 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2872>`_)
- Added ``redbot.core.modlog.get_latest_case`` to fetch the case object for the most recent ModLog case. (`#2908 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2908>`_)
- Added ``[p]bankset maxbal`` to set the maximum bank balance. (`#2926 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2926>`_)
- Added a few methods and classes replacing direct config access (which is no longer supported)

   - ``redbot.core.Red.allowed_by_whitelist_blacklist``
   - ``redbot.core.Red.get_valid_prefixes``
   - ``redbot.core.Red.clear_shared_api_tokens``
   - ``redbot.core.commands.help.HelpSettings`` (`#2976 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2976>`_)
- Added the cli flag ``redbot --edit`` which is used to edit the instance name, token, owner, and datapath. (`#3060 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3060>`_)
- Added ``[p]licenseinfo``. (`#3090 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3090>`_)
- Ensured that people can migrate from MongoDB. (`#3108 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3108>`_)
- Added a command to list disabled commands globally or per guild. (`#3118 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3118>`_)
- New event ``on_red_api_tokens_update`` is now dispatched when shared api keys for a service are updated. (`#3134 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3134>`_)
- Added ``redbot-setup backup``. (`#3235 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3235>`_)
- Added the method ``redbot.core.bot.Bot.wait_until_red_ready()`` that waits until Red's post connection startup is done. (`#3273 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3273>`_)


Removals
~~~~~~~~

- ``[p]set owner`` and ``[p]set token`` have been removed in favor of managing server side. (`#2928 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2928>`_)
- Shared libraries are marked for removal in Red 3.4. (`#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_)
- Removed ``[p]backup``. Use the cli command ``redbot-setup backup`` instead. (`#3235 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3235>`_)
- Removed the functions ``safe_delete``, ``fuzzy_command_search``, ``format_fuzzy_results`` and ``create_backup`` from ``redbot.core.utils``. (`#3240 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3240>`_)
- Removed a lot of the launcher's handled behavior. (`#3289 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3289>`_)


Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

- `#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_, `#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_, `#2723 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2723>`_, `#2836 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2836>`_, `#2849 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2849>`_, `#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_, `#2885 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2885>`_, `#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_, `#2897 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2897>`_, `#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_, `#2924 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2924>`_, `#2939 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2939>`_, `#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_, `#2941 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2941>`_, `#2949 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2949>`_, `#2953 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2953>`_, `#2964 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2964>`_, `#2986 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2986>`_, `#2993 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2993>`_, `#2997 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2997>`_, `#3008 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3008>`_, `#3017 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3017>`_, `#3048 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3048>`_, `#3059 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3059>`_, `#3080 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3080>`_, `#3089 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3089>`_, `#3104 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3104>`_, `#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_, `#3129 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3129>`_, `#3152 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3152>`_, `#3160 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3160>`_, `#3168 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3168>`_, `#3173 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3173>`_, `#3176 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3176>`_, `#3186 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3186>`_, `#3192 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3192>`_, `#3193 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3193>`_, `#3195 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3195>`_, `#3202 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3202>`_, `#3214 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3214>`_, `#3223 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3223>`_, `#3229 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3229>`_, `#3245 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3245>`_, `#3247 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3247>`_, `#3248 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3248>`_, `#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_, `#3254 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3254>`_, `#3255 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3255>`_, `#3256 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3256>`_, `#3258 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3258>`_, `#3261 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3261>`_, `#3275 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3275>`_, `#3276 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3276>`_, `#3293 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3293>`_, `#3278 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3278>`_, `#3285 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3285>`_, `#3296 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3296>`_,


Dependency changes
~~~~~~~~~~~~~~~~~~~~~~~

- Added ``pytest-mock`` requirement to ``tests`` extra. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- Updated the python minimum requirement to 3.8.1, updated JRE to Java 11. (`#3245 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3245>`_)
- Bumped dependency versions. (`#3288 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3288>`_)
- Bumped red-lavalink version. (`#3290 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3290>`_)


Documentation Changes
~~~~~~~~~~~~~~~~~~~~~

- Started the user guides covering cogs and the user interface of the bot. This includes, for now, a "Getting started" guide. (`#1734 <https://github.com/Cog-Creators/Red-DiscordBot/issues/1734>`_)
- Added documentation for PM2 support. (`#2105 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2105>`_)
- Updated linux install docs, adding sections for Fedora Linux, Debian/Raspbian Buster, and openSUSE. (`#2558 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2558>`_)
- Created documentation covering what we consider a developer facing breaking change and the guarantees regarding them. (`#2882 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2882>`_)
- Fixed the user parameter being labeled as ``discord.TextChannel`` instead of ``discord.abc.User`` in ``redbot.core.utils.predicates``. (`#2914 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2914>`_)
- Updated towncrier info in the contribution guidelines to explain how to create a changelog for a standalone PR. (`#2915 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2915>`_)
- Reworded the virtual environment guide to make it sound less scary. (`#2920 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2920>`_)
- Driver docs no longer show twice. (`#2972 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2972>`_)
- Added more information about ``redbot.core.utils.humanize_timedelta`` into the docs. (`#2986 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2986>`_)
- Added a direct link to the "Installing Red" section in "Installing using powershell and chocolatey". (`#2995 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2995>`_)
- Updated Git PATH install (Windows), capitalized some words, stopped mentioning the launcher. (`#2998 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2998>`_)
- Added autostart documentation for Red users who installed Red inside of a virtual environment. (`#3005 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3005>`_)
- Updated the Cog Creation guide with a note regarding the Develop version as well as the folder layout for local cogs. (`#3021 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3021>`_)
- Added links to the getting started guide at the end of installation guides. (`#3025 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3025>`_)
- Added proper docstrings to enums that show in drivers docs. (`#3035 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3035>`_)
- Discord.py doc links will now always use the docs for the currently used version of discord.py. (`#3053 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3053>`_)
- Added ``|DPY_VERSION|`` substitution that will automatically get replaced by the current discord.py version. (`#3053 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3053>`_)
- Added missing descriptions for function returns. (`#3054 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3054>`_)
- Stopped overwriting the ``docs/prolog.txt`` file in ``conf.py``. (`#3082 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3082>`_)
- Fixed some typos and wording, added MS Azure to the host list. (`#3083 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3083>`_)
- Updated the docs footer copyright to 2019. (`#3105 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3105>`_)
- Added a deprecation note about shared libraries in the Downloader Framework docs. (`#3106 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3106>`_)
- Updated the apikey framework documentation. Changed ``bot.get_shared_api_keys()`` to ``bot.get_shared_api_tokens()``. (`#3110 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3110>`_)
- Added information about ``info.json``'s ``min_python_version`` key in Downloader Framework docs. (`#3124 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3124>`_)
- Added an event reference for the ``on_red_api_tokens_update`` event in the Shared API Keys docs. (`#3134 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3134>`_)
- Added notes explaining the best practices with config. (`#3149 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3149>`_)
- Documented additional attributes in Context. (`#3151 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3151>`_)
- Updated Windows docs with up to date dependency instructions. (`#3188 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3188>`_)
- Added a "Publishing cogs for V3" document explaining how to make user's cogs work with Downloader. (`#3234 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3234>`_)
- Fixed broken docs for ``redbot.core.commands.Context.react_quietly``. (`#3257 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3257>`_)
- Updated copyright notices on License and RTD config to 2020. (`#3259 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3259>`_)
- Added a line about setuptools and wheel. (`#3262 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3262>`_)
- Ensured development builds are not advertised to the wrong audience. (`#3292 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3292>`_)
- Clarified the usage intent of some of the chat formatting functions. (`#3292 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3292>`_)


Admin
-----

Breaking Changes
~~~~~~~~~~~~~~~~

- Changed ``[p]announce ignore`` and ``[p]announce channel`` to ``[p]announceset ignore`` and ``[p]announceset channel``. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Changed ``[p]selfrole <role>`` to ``[p]selfrole add <role>``, changed ``[p]selfrole add`` to ``[p]selfroleset add`` , and changed ``[p]selfrole delete`` to ``[p]selfroleset remove``. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)


Bug Fixes
~~~~~~~~~

- Fixed ``[p]announce`` failing after encountering an error attempting to message the bot owner. (`#3166 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3166>`_)
- Improved the clarity of user facing messages when the user is not allowed to do something due to Discord hierarchy rules. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Fixed some role managing commands not properly checking if Red had ``manage_roles`` perms before attempting to manage roles. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Fixed ``[p]editrole`` commands not checking if roles to be edited are higher than Red's highest role before trying to edit them. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)
- Fixed ``[p]announce ignore`` and ``[p]announce channel`` not being able to be used by guild owners and administrators. (`#3250 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3250>`_)


Enhancements
~~~~~~~~~~~~

- Added custom issue messages for adding and removing roles, this makes it easier to create translations. (`#3016 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3016>`_)


Audio
-----

Bug Fixes
~~~~~~~~~

- ``[p]playlist remove`` now removes the playlist url if the playlist was created through ``[p]playlist save``. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- Users are no longer able to accidentally overwrite existing playlist if a new one with the same name is created/renamed. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]audioset settings`` no longer shows lavalink JAR version. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Fixed a ``KeyError: loadType`` when trying to play tracks. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset settings`` now uses ``ctx.is_owner()`` to check if the context author is the bot owner. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Fixed track indexs being off by 1 in ``[p]search``. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- Fixed an issue where updating your Spotify and YouTube Data API tokens did not refresh them. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Fixed an issue where the blacklist was not being applied correctly. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Fixed an issue in ``[p]audioset restrictions blacklist list`` where it would call the list a ``Whitelist``. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Red's status is now properly cleared on emptydisconnect. (`#3050 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3050>`_)
- Fixed a console spam caused sometimes when auto disconnect and auto pause are used. (`#3123 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3123>`_)
- Fixed an error that was thrown when running ``[p]audioset dj``. (`#3165 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3165>`_)
- Fixed a crash that could happen when the bot can't connect to the lavalink node. (`#3238 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3238>`_)
- Restricted the number of songs shown in the queue to first 500 to avoid heartbeats. (`#3279 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3279>`_)
- Added more cooldowns to playlist commands and restricted the queue and playlists to 10k songs to avoid bot errors. (`#3286 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3286>`_)


Enhancements
~~~~~~~~~~~~

- ``[p]playlist upload`` will now load playlists generated via ``[p]playlist download`` much faster if the playlist uses the new scheme. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]playlist`` commands now can be used by everyone regardless of DJ settings, however it will respect DJ settings when creating/modifying playlists in the server scope. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- Spotify, Youtube Data, and Lavalink API calls can be cached to avoid repeated calls in the future, see ``[p]audioset cache``. (`#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_)
- Playlists will now start playing as soon as first track is loaded. (`#2890 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2890>`_)
- ``[p]audioset localpath`` can set a path anywhere in your machine now. Note: This path needs to be visible by ``Lavalink.jar``. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]queue`` now works when there are no tracks in the queue, showing the track currently playing. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset settings`` now reports Red Lavalink version. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Adding and removing reactions in Audio is no longer a blocking action. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- When shuffle is on, queue now shows the correct play order. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]seek`` and ``[p]skip`` can be used by user if they are the song requester while DJ mode is enabled and votes are disabled. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Adding a playlist and an album to a saved playlist skips tracks already in the playlist. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- DJ mode is now turned off if the DJ role is deleted. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- When playing a localtrack, ``[p]play`` and ``[p]bumpplay`` no longer require the use of the prefix "localtracks\\".

  Before: ``[p]bumpplay localtracks\\ENM\\501 - Inside The Machine.mp3``
  Now: ``[p]bumpplay ENM\\501 - Inside The Machine.mp3``
  Now nested folders: ``[p]bumpplay Parent Folder\\Nested Folder\\track.mp3`` (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- Removed commas in explanations about how to set API keys. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)
- Expanded local track support to all file formats (m3u, m4a, mp4, etc). (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- Cooldowns are now reset upon failure of commands that have a cooldown timer. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- Improved the explanation in the help string for ``[p]audioset emptydisconnect``. (`#3051 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3051>`_)
- Added a typing indicator to playlist dedupe. (`#3058 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3058>`_)
- Exposed clearer errors to users in the play commands. (`#3085 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3085>`_)
- Better error handling when the player is unable to play multiple tracks in the sequence. (`#3165 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3165>`_)


New Features
~~~~~~~~~~~~

- Added support for nested folders in the localtrack folder. (`#270 <https://github.com/Cog-Creators/Red-DiscordBot/issues/270>`_)
- Now auto pauses the queue when the voice channel is empty. (`#721 <https://github.com/Cog-Creators/Red-DiscordBot/issues/721>`_)
- All Playlist commands now accept optional arguments, use ``[p]help playlist <subcommand>`` for more details. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]playlist rename`` will now allow users to rename existing playlists. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]playlist update`` will now allow users to update non-custom Playlists to the latest available tracks. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- There are now 3 different scopes of playlist. To define them, use the ``--scope`` argument.

      ``Global Playlist``

      - These playlists will be available in all servers the bot is in.
      - These can be managed by the Bot Owner only.

      ``Server Playlist``

      - These playlists will only be available in the server they were created in.
      - These can be managed by the Bot Owner, Guild Owner, Mods, Admins, DJs, and the Creator (if the DJ role is disabled).

      ``User Playlist``

      - These playlists will be available in all servers both the bot and the creator are in.
      - These can be managed by the Bot Owner and Creator only. (`#2861 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2861>`_)
- ``[p]audioset cache`` can be used to set the cache level. **It's off by default**. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]genre`` can be used to play spotify playlists. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset cacheage`` can be used to set the maximum age of an entry in the cache. **Default is 365 days**. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset autoplay`` can be used to enable auto play once the queue runs out. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- New events dispatched by Audio.

   - ``on_red_audio_track_start(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_enqueue(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_auto_play(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_queue_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_audio_disconnect(guild: discord.Guild)``
   - ``on_red_audio_skip_track(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`` (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]queue shuffle`` can be used to shuffle the queue manually. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]queue clean self`` can be used to remove all songs you requested from the queue. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]audioset restrictions`` can be used to add or remove keywords which songs must have or are not allowed to have. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]playlist dedupe`` can be used to remove duplicated tracks from a playlist. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]autoplay`` can be used to play a random song. (`#2904 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2904>`_)
- ``[p]bumpplay`` can be used to add a song to the front of the queue. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- ``[p]shuffle`` has an additional argument to tell the bot whether it should shuffle bumped tracks. (`#2940 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2940>`_)
- Added global whitelist/blacklist commands. (`#3047 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3047>`_)
- Added self-managed daily playlists in the GUILD scope, these are called "Daily playlist - YYYY-MM-DD" and auto delete after 7 days. (`#3199 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3199>`_)


CustomCom
---------

Enhancements
~~~~~~~~~~~~

- The group command ``[p]cc create`` can now be used to create simple CCs without specifying "simple". (`#1767 <https://github.com/Cog-Creators/Red-DiscordBot/issues/1767>`_)
- Added a query option for CC typehints for URL-based CCs. (`#3228 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3228>`_)
- Now uses the ``humanize_list`` utility for iterable parameter results, e.g. ``{#:Role.members}``. (`#3277 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3277>`_)


Downloader
----------

Bug Fixes
~~~~~~~~~

- Made the regex for repo names use raw strings to stop causing a ``DeprecationWarning`` for invalid escape sequences. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- Downloader will no longer attempt to install cogs that are already installed. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- Repo names can now only contain the characters listed in the help text (A-Z, 0-9, underscores, and hyphens). (`#2827 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2827>`_)
- ``[p]findcog`` no longer attempts to find a cog for commands without a cog. (`#2902 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2902>`_)
- Downloader will no longer attempt to install a cog with same name as another cog that is already installed. (`#2927 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2927>`_)
- Added error handling for when a remote repository or branch is deleted, now notifies the which repository failed and continues to update the others. (`#2936 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2936>`_)
- ``[p]cog install`` will no longer error if a cog has an empty install message. (`#3024 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3024>`_)
- Made ``redbot.cogs.downloader.repo_manager.Repo.clean_url`` work with relative urls. This property is ``str`` type now. (`#3141 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3141>`_)
- Fixed an error on repo add from empty string values for the ``install_msg`` info.json field. (`#3153 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3153>`_)
- Disabled all git auth prompts when adding/updating a repo with Downloader. (`#3159 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3159>`_)
- ``[p]findcog`` now properly works for cogs with less typical folder structure. (`#3177 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3177>`_)
- ``[p]cog uninstall`` now fully unloads cog - the bot will not try to load it on next startup. (`#3179 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3179>`_)


Enhancements
~~~~~~~~~~~~

- Downloader will now check if the Python and bot versions match requirements in ``info.json`` during update. (`#1866 <https://github.com/Cog-Creators/Red-DiscordBot/issues/1866>`_)
- ``[p]cog install`` now accepts multiple cog names. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- When passing cogs to ``[p]cog update``, it will now only update those cogs, not all cogs from the repo those cogs are from. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added error messages for failures when installing/reinstalling requirements and copying cogs and shared libraries. (`#2571 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2571>`_)
- ``[p]findcog`` now uses sanitized urls (without HTTP Basic Auth fragments). (`#3129 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3129>`_)
- ``[p]repo info`` will now show the repo's url, branch, and authors. (`#3225 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3225>`_)
- ``[p]cog info`` will now show cog authors. (`#3225 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3225>`_)
- ``[p]findcog`` will now show the repo's branch. (`#3225 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3225>`_)


New Features
~~~~~~~~~~~~

- Added ``[p]repo update [repos]`` which updates repos without updating the cogs from them. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog installversion <repo_name> <revision> <cogs>`` which installs cogs from a specified revision (commit, tag) of the given repo. When using this command, the cog will automatically be pinned. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog pin <cogs>`` and ``[p]cog unpin <cogs>`` for pinning cogs. Cogs that are pinned will not be updated when using update commands. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog checkforupdates`` that lists which cogs can be updated (including pinned cog) without updating them. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog updateallfromrepos <repos>`` that updates all cogs from the given repos. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog updatetoversion <repo_name> <revision> [cogs]`` that updates all cogs or ones of user's choosing to chosen revision of the given repo. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Added ``[p]cog reinstallreqs`` that reinstalls cog requirements and shared libraries for all installed cogs. (`#3167 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3167>`_)


Documentation Changes
~~~~~~~~~~~~~~~~~~~~~

- Added ``redbot.cogs.downloader.installable.InstalledModule`` to Downloader's framework docs. (`#2527 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2527>`_)
- Removed API References for Downloader. (`#3234 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3234>`_)


Image
-----

Enhancements
~~~~~~~~~~~~

- Updated the giphycreds command to match the formatting of the other API commands. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)
- Removed commas from explanations about how to set API keys. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)


Mod
---

Bug Fixes
~~~~~~~~~

- ``[p]userinfo`` no longer breaks when a user has an absurd numbers of roles. (`#2910 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2910>`_)
- Fixed Mod cog not recording username changes for ``[p]names`` and ``[p]userinfo`` commands. (`#2918 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2918>`_)
- Fixed ``[p]modset deletedelay`` deleting non-command messages. (`#2924 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2924>`_)
- Fixed an error when reloading Mod. (`#2932 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2932>`_)


Enhancements
~~~~~~~~~~~~

- Slowmode now accepts integer-only inputs as seconds. (`#2884 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2884>`_)


Permissions
-----------

Bug Fixes
~~~~~~~~~

- Defaults are now cleared properly when clearing all rules. (`#3037 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3037>`_)


Enhancements
~~~~~~~~~~~~

- Better explained the usage of commands with the ``<who_or_what>`` argument. (`#2991 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2991>`_)


Streams
-------

Bug Fixes
~~~~~~~~~

- Fixed a ``TypeError`` in the ``TwitchStream`` class when calling Twitch client_id from Red shared APIs tokens. (`#3042 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3042>`_)
- Changed the ``stream_alert`` function for Twitch alerts to make it work with how the ``TwitchStream`` class works now. (`#3042 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3042>`_)


Enhancements
~~~~~~~~~~~~

- Removed commas from explanations about how to set API keys. (`#2905 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2905>`_)


Trivia
------

Bug Fixes
~~~~~~~~~

- Fixed a typo in Ahsoka Tano's name in the Starwars trivia list. (`#2909 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2909>`_)
- Fixed a bug where ``[p]trivia leaderboard`` failed to run. (`#2911 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2911>`_)
- Fixed a typo in the Greek mythology trivia list regarding Hermes' staff. (`#2994 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2994>`_)
- Fixed a question in the Overwatch trivia list that accepted blank responses. (`#2996 <https://github.com/Cog-Creators/Red-DiscordBot/issues/2996>`_)
- Fixed questions and answers that were incorrect in the Clash Royale trivia list. (`#3236 <https://github.com/Cog-Creators/Red-DiscordBot/issues/3236>`_)


Enhancements
~~~~~~~~~~~~

- Added trivia lists for Prince and Michael Jackson lyrics. (`#12 <https://github.com/Cog-Creators/Red-DiscordBot/issues/12>`_)
