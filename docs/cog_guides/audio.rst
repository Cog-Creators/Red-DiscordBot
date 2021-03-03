.. _audio:

=====
Audio
=====

This is the cog guide for the audio cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load audio

.. _audio-usage:

-----
Usage
-----

Play audio through voice channels.


.. _audio-commands:

--------
Commands
--------

.. _audio-command-audioset:

^^^^^^^^
audioset
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]audioset 

**Description**

Music configuration options.

.. _audio-command-audioset-autodeafen:

"""""""""""""""""""
audioset autodeafen
"""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset autodeafen 

**Description**

Toggle whether the bot will be auto deafened upon joining the voice channel.

.. _audio-command-audioset-autoplay:

"""""""""""""""""
audioset autoplay
"""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset autoplay 

**Description**

Change auto-play setting.

.. _audio-command-audioset-autoplay-playlist:

""""""""""""""""""""""""""
audioset autoplay playlist
""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset autoplay playlist <playlist_name_OR_id> [args]

**Description**

Set a playlist to auto-play songs from.

**Usage**:
​ ​ ​ ​ ``[p]audioset autoplay playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
    ​Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]audioset autoplay MyGuildPlaylist``
​ ​ ​ ​ ``[p]audioset autoplay MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]audioset autoplay PersonalPlaylist --scope User --author Draper``

.. _audio-command-audioset-autoplay-reset:

"""""""""""""""""""""""
audioset autoplay reset
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset autoplay reset 

**Description**

Resets auto-play to the default playlist.

.. _audio-command-audioset-autoplay-toggle:

""""""""""""""""""""""""
audioset autoplay toggle
""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset autoplay toggle 

**Description**

Toggle auto-play when there no songs in queue.

.. _audio-command-audioset-cache:

""""""""""""""
audioset cache
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset cache [level]

**Description**

Sets the caching level.

Level can be one of the following:

0: Disables all caching
1: Enables Spotify Cache
2: Enables YouTube Cache
3: Enables Lavalink Cache
5: Enables all Caches

If you wish to disable a specific cache use a negative number.

.. _audio-command-audioset-cacheage:

"""""""""""""""""
audioset cacheage
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset cacheage <age>

**Description**

Sets the cache max age.

This commands allows you to set the max number of days before an entry in the cache becomes
invalid.

.. _audio-command-audioset-countrycode:

""""""""""""""""""""
audioset countrycode
""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset countrycode <country>

**Description**

Set the country code for Spotify searches.

.. _audio-command-audioset-dailyqueue:

"""""""""""""""""""
audioset dailyqueue
"""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset dailyqueue 

**Description**

Toggle daily queues.

Daily queues creates a playlist for all tracks played today.

.. _audio-command-audioset-dc:

"""""""""""
audioset dc
"""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset dc 

**Description**

Toggle the bot auto-disconnecting when done playing.

This setting takes precedence over ``[p]audioset emptydisconnect``.

.. _audio-command-audioset-dj:

"""""""""""
audioset dj
"""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset dj 

**Description**

Toggle DJ mode.

DJ mode allows users with the DJ role to use audio commands.

.. _audio-command-audioset-emptydisconnect:

""""""""""""""""""""""""
audioset emptydisconnect
""""""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset emptydisconnect <seconds>

**Description**

Auto-disconnect from channel when bot is alone in it for x seconds, 0 to disable.

``[p]audioset dc`` takes precedence over this setting.

.. _audio-command-audioset-emptypause:

"""""""""""""""""""
audioset emptypause
"""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset emptypause <seconds>

**Description**

Auto-pause after x seconds when room is empty, 0 to disable.

.. _audio-command-audioset-globalapi:

""""""""""""""""""
audioset globalapi
""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset globalapi 

**Description**

Change globalapi settings.

.. _audio-command-audioset-globalapi-timeout:

""""""""""""""""""""""""""
audioset globalapi timeout
""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset globalapi timeout <timeout>

**Description**

Set GET request timeout.

Example: 0.1 = 100ms 1 = 1 second

.. _audio-command-audioset-globalapi-toggle:

"""""""""""""""""""""""""
audioset globalapi toggle
"""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset globalapi toggle 

**Description**

Toggle the server settings.

Default is OFF

.. _audio-command-audioset-globaldailyqueue:

"""""""""""""""""""""""""
audioset globaldailyqueue
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset globaldailyqueue 

**Description**

Toggle global daily queues.

Global daily queues creates a playlist for all tracks played today.

.. _audio-command-audioset-jukebox:

""""""""""""""""
audioset jukebox
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset jukebox <price>

**Description**

Set a price for queueing tracks for non-mods, 0 to disable.

.. _audio-command-audioset-localpath:

""""""""""""""""""
audioset localpath
""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset localpath [local_path]

**Description**

Set the localtracks path if the Lavalink.jar is not run from the Audio data folder.

Leave the path blank to reset the path to the default, the Audio data directory.

.. _audio-command-audioset-logs:

"""""""""""""
audioset logs
"""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset logs 

**Description**

Sends the Lavalink server logs to your DMs.

.. _audio-command-audioset-lyrics:

"""""""""""""""
audioset lyrics
"""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset lyrics 

**Description**

Prioritise tracks with lyrics.

.. _audio-command-audioset-maxlength:

""""""""""""""""""
audioset maxlength
""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset maxlength <seconds>

**Description**

Max length of a track to queue in seconds, 0 to disable.

Accepts seconds or a value formatted like 00:00:00 (``hh:mm:ss``) or 00:00 (``mm:ss``). Invalid
input will turn the max length setting off.

.. _audio-command-audioset-mycountrycode:

""""""""""""""""""""""
audioset mycountrycode
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset mycountrycode <country>

**Description**

Set the country code for Spotify searches.

.. _audio-command-audioset-notify:

"""""""""""""""
audioset notify
"""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset notify 

**Description**

Toggle track announcement and other bot messages.

.. _audio-command-audioset-persistqueue:

"""""""""""""""""""""
audioset persistqueue
"""""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset persistqueue 

**Description**

Toggle persistent queues.

Persistent queues allows the current queue to be restored when the queue closes.

.. _audio-command-audioset-restart:

""""""""""""""""
audioset restart
""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset restart 

**Description**

Restarts the lavalink connection.

.. _audio-command-audioset-restrict:

"""""""""""""""""
audioset restrict
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset restrict 

**Description**

Toggle the domain restriction on Audio.

When toggled off, users will be able to play songs from non-commercial websites and links.
When toggled on, users are restricted to YouTube, SoundCloud, Mixer, Vimeo, Twitch, and
Bandcamp links.

.. _audio-command-audioset-restrictions:

"""""""""""""""""""""
audioset restrictions
"""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset restrictions 

**Description**

Manages the keyword whitelist and blacklist.

.. _audio-command-audioset-restrictions-blacklist:

"""""""""""""""""""""""""""""""
audioset restrictions blacklist
"""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist 

**Description**

Manages the keyword blacklist.

.. _audio-command-audioset-restrictions-blacklist-add:

"""""""""""""""""""""""""""""""""""
audioset restrictions blacklist add
"""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist add <keyword>

**Description**

Adds a keyword to the blacklist.

.. _audio-command-audioset-restrictions-blacklist-clear:

"""""""""""""""""""""""""""""""""""""
audioset restrictions blacklist clear
"""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist clear 

**Description**

Clear all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-blacklist-delete:

""""""""""""""""""""""""""""""""""""""
audioset restrictions blacklist delete
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist delete <keyword>

.. tip:: Aliases: ``audioset restrictions blacklist del``, ``audioset restrictions blacklist remove``

**Description**

Removes a keyword from the blacklist.

.. _audio-command-audioset-restrictions-blacklist-list:

""""""""""""""""""""""""""""""""""""
audioset restrictions blacklist list
""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist list 

**Description**

List all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-global:

""""""""""""""""""""""""""""
audioset restrictions global
""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset restrictions global 

**Description**

Manages the global keyword whitelist/blacklist.

.. _audio-command-audioset-restrictions-global-blacklist:

""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist 

**Description**

Manages the global keyword blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-add:

""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist add
""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist add <keyword>

**Description**

Adds a keyword to the blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-clear:

""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist clear
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist clear 

**Description**

Clear all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-delete:

"""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist delete
"""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist delete <keyword>

.. tip:: Aliases: ``audioset restrictions global blacklist del``, ``audioset restrictions global blacklist remove``

**Description**

Removes a keyword from the blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-list:

"""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist list
"""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist list 

**Description**

List all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-global-whitelist:

""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist 

**Description**

Manages the global keyword whitelist.

.. _audio-command-audioset-restrictions-global-whitelist-add:

""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist add
""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist add <keyword>

**Description**

Adds a keyword to the whitelist.

If anything is added to whitelist, it will blacklist everything else.

.. _audio-command-audioset-restrictions-global-whitelist-clear:

""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist clear
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist clear 

**Description**

Clear all keywords from the whitelist.

.. _audio-command-audioset-restrictions-global-whitelist-delete:

"""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist delete
"""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist delete <keyword>

.. tip:: Aliases: ``audioset restrictions global whitelist del``, ``audioset restrictions global whitelist remove``

**Description**

Removes a keyword from the whitelist.

.. _audio-command-audioset-restrictions-global-whitelist-list:

"""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist list
"""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist list 

**Description**

List all keywords added to the whitelist.

.. _audio-command-audioset-restrictions-whitelist:

"""""""""""""""""""""""""""""""
audioset restrictions whitelist
"""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist 

**Description**

Manages the keyword whitelist.

.. _audio-command-audioset-restrictions-whitelist-add:

"""""""""""""""""""""""""""""""""""
audioset restrictions whitelist add
"""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist add <keyword>

**Description**

Adds a keyword to the whitelist.

If anything is added to whitelist, it will blacklist everything else.

.. _audio-command-audioset-restrictions-whitelist-clear:

"""""""""""""""""""""""""""""""""""""
audioset restrictions whitelist clear
"""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist clear 

**Description**

Clear all keywords from the whitelist.

.. _audio-command-audioset-restrictions-whitelist-delete:

""""""""""""""""""""""""""""""""""""""
audioset restrictions whitelist delete
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist delete <keyword>

.. tip:: Aliases: ``audioset restrictions whitelist del``, ``audioset restrictions whitelist remove``

**Description**

Removes a keyword from the whitelist.

.. _audio-command-audioset-restrictions-whitelist-list:

""""""""""""""""""""""""""""""""""""
audioset restrictions whitelist list
""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist list 

**Description**

List all keywords added to the whitelist.

.. _audio-command-audioset-role:

"""""""""""""
audioset role
"""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset role <role_name>

**Description**

Set the role to use for DJ mode.

.. _audio-command-audioset-settings:

"""""""""""""""""
audioset settings
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset settings 

.. tip:: Alias: ``audioset info``

**Description**

Show the current settings.

.. _audio-command-audioset-spotifyapi:

"""""""""""""""""""
audioset spotifyapi
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset spotifyapi 

**Description**

Instructions to set the Spotify API tokens.

.. _audio-command-audioset-status:

"""""""""""""""
audioset status
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset status 

**Description**

Enable/disable tracks' titles as status.

.. _audio-command-audioset-thumbnail:

""""""""""""""""""
audioset thumbnail
""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset thumbnail 

**Description**

Toggle displaying a thumbnail on audio messages.

.. _audio-command-audioset-vote:

"""""""""""""
audioset vote
"""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset vote <percent>

**Description**

Percentage needed for non-mods to skip tracks, 0 to disable.

.. _audio-command-audioset-youtubeapi:

"""""""""""""""""""
audioset youtubeapi
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset youtubeapi 

**Description**

Instructions to set the YouTube API key.

.. _audio-command-audiostats:

^^^^^^^^^^
audiostats
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]audiostats 

**Description**

Audio stats.

.. _audio-command-autoplay:

^^^^^^^^
autoplay
^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]autoplay 

**Description**

Starts auto play.

.. _audio-command-bump:

^^^^
bump
^^^^

**Syntax**

.. code-block:: none

    [p]bump <index>

**Description**

Bump a track number to the top of the queue.

.. _audio-command-bumpplay:

^^^^^^^^
bumpplay
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]bumpplay [play_now=False] <query>

**Description**

Force play a URL or search for a track.

.. _audio-command-disconnect:

^^^^^^^^^^
disconnect
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]disconnect 

**Description**

Disconnect from the voice channel.

.. _audio-command-eq:

^^
eq
^^

**Syntax**

.. code-block:: none

    [p]eq 

**Description**

Equalizer management.

Band positions are 1-15 and values have a range of -0.25 to 1.0.
Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
6.3k, 10k, and 16k Hz.
Setting a band value to -0.25 nullifies it while +0.25 is double.

.. _audio-command-eq-delete:

"""""""""
eq delete
"""""""""

**Syntax**

.. code-block:: none

    [p]eq delete <eq_preset>

.. tip:: Aliases: ``eq del``, ``eq remove``

**Description**

Delete a saved eq preset.

.. _audio-command-eq-list:

"""""""
eq list
"""""""

**Syntax**

.. code-block:: none

    [p]eq list 

**Description**

List saved eq presets.

.. _audio-command-eq-load:

"""""""
eq load
"""""""

**Syntax**

.. code-block:: none

    [p]eq load <eq_preset>

**Description**

Load a saved eq preset.

.. _audio-command-eq-reset:

""""""""
eq reset
""""""""

**Syntax**

.. code-block:: none

    [p]eq reset 

**Description**

Reset the eq to 0 across all bands.

.. _audio-command-eq-save:

"""""""
eq save
"""""""

**Syntax**

.. code-block:: none

    [p]eq save [eq_preset]

**Description**

Save the current eq settings to a preset.

.. _audio-command-eq-set:

""""""
eq set
""""""

**Syntax**

.. code-block:: none

    [p]eq set <band_name_or_position> <band_value>

**Description**

Set an eq band with a band number or name and value.

Band positions are 1-15 and values have a range of -0.25 to 1.0.
Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
6.3k, 10k, and 16k Hz.
Setting a band value to -0.25 nullifies it while +0.25 is double.

.. _audio-command-genre:

^^^^^
genre
^^^^^

**Syntax**

.. code-block:: none

    [p]genre 

**Description**

Pick a Spotify playlist from a list of categories to start playing.

.. _audio-command-llsetup:

^^^^^^^
llsetup
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]llsetup 

.. tip:: Alias: ``llset``

**Description**

Lavalink server configuration options.

.. _audio-command-llsetup-external:

""""""""""""""""
llsetup external
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]llsetup external 

**Description**

Toggle using external Lavalink servers.

.. _audio-command-llsetup-host:

""""""""""""
llsetup host
""""""""""""

**Syntax**

.. code-block:: none

    [p]llsetup host <host>

**Description**

Set the Lavalink server host.

.. _audio-command-llsetup-info:

""""""""""""
llsetup info
""""""""""""

**Syntax**

.. code-block:: none

    [p]llsetup info 

.. tip:: Alias: ``llsetup settings``

**Description**

Display Lavalink connection settings.

.. _audio-command-llsetup-java:

""""""""""""
llsetup java
""""""""""""

**Syntax**

.. code-block:: none

    [p]llsetup java [java_path]

**Description**

Change your Java executable path

Enter nothing to reset to default.

.. _audio-command-llsetup-password:

""""""""""""""""
llsetup password
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]llsetup password <password>

**Description**

Set the Lavalink server password.

.. _audio-command-llsetup-wsport:

""""""""""""""
llsetup wsport
""""""""""""""

**Syntax**

.. code-block:: none

    [p]llsetup wsport <ws_port>

**Description**

Set the Lavalink websocket server port.

.. _audio-command-local:

^^^^^
local
^^^^^

**Syntax**

.. code-block:: none

    [p]local 

**Description**

Local playback commands.

.. _audio-command-local-folder:

""""""""""""
local folder
""""""""""""

**Syntax**

.. code-block:: none

    [p]local folder [folder]

.. tip:: Alias: ``local start``

**Description**

Play all songs in a localtracks folder.

.. _audio-command-local-play:

""""""""""
local play
""""""""""

**Syntax**

.. code-block:: none

    [p]local play 

**Description**

Play a local track.

.. _audio-command-local-search:

""""""""""""
local search
""""""""""""

**Syntax**

.. code-block:: none

    [p]local search <search_words>

**Description**

Search for songs across all localtracks folders.

.. _audio-command-now:

^^^
now
^^^

**Syntax**

.. code-block:: none

    [p]now 

**Description**

Now playing.

.. _audio-command-pause:

^^^^^
pause
^^^^^

**Syntax**

.. code-block:: none

    [p]pause 

**Description**

Pause or resume a playing track.

.. _audio-command-percent:

^^^^^^^
percent
^^^^^^^

**Syntax**

.. code-block:: none

    [p]percent 

**Description**

Queue percentage.

.. _audio-command-play:

^^^^
play
^^^^

**Syntax**

.. code-block:: none

    [p]play <query>

**Description**

Play a URL or search for a track.

.. _audio-command-playlist:

^^^^^^^^
playlist
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]playlist 

**Description**

Playlist configuration options.

Scope info:
​ ​ ​ ​ **Global**:
​ ​ ​ ​ ​ ​ ​ ​ Visible to all users of this bot.
​ ​ ​ ​ ​ ​ ​ ​ Only editable by bot owner.
​ ​ ​ ​ **Guild**:
​ ​ ​ ​ ​ ​ ​ ​ Visible to all users in this guild.
​ ​ ​ ​ ​ ​ ​ ​ Editable by bot owner, guild owner, guild admins, guild mods, DJ role and playlist creator.
​ ​ ​ ​ **User**:
​ ​ ​ ​ ​ ​ ​ ​ Visible to all bot users, if --author is passed.
​ ​ ​ ​ ​ ​ ​ ​ Editable by bot owner and creator.

.. _audio-command-playlist-append:

"""""""""""""""
playlist append
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist append <playlist_name_OR_id> <track_name_OR_url> [args]

**Description**

Add a track URL, playlist link, or quick search to a playlist.

The track(s) will be appended to the end of the playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist append playlist_name_OR_id track_name_OR_url [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist append MyGuildPlaylist Hello by Adele``
​ ​ ​ ​ ``[p]playlist append MyGlobalPlaylist Hello by Adele --scope Global``
​ ​ ​ ​ ``[p]playlist append MyGlobalPlaylist Hello by Adele --scope Global --Author Draper#6666``

.. _audio-command-playlist-copy:

"""""""""""""
playlist copy
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist copy <id_or_name> [args]

**Description**

Copy a playlist from one scope to another.

**Usage**:
​ ​ ​ ​ ``[p]playlist copy playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --from-scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --from-author [user]
​ ​ ​ ​ ​ ​ ​ ​ --from-guild [guild] **Only the bot owner can use this**

​ ​ ​ ​ ​ ​ ​ ​ --to-scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --to-author [user]
​ ​ ​ ​ ​ ​ ​ ​ --to-guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist copy MyGuildPlaylist --from-scope Guild --to-scope Global``
​ ​ ​ ​ ``[p]playlist copy MyGlobalPlaylist --from-scope Global --to-author Draper#6666 --to-scope User``
​ ​ ​ ​ ``[p]playlist copy MyPersonalPlaylist --from-scope user --to-author Draper#6666 --to-scope Guild --to-guild Red - Discord Bot``

.. _audio-command-playlist-create:

"""""""""""""""
playlist create
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist create <name> [args]

**Description**

Create an empty playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist create playlist_name [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist create MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist create MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist create MyPersonalPlaylist --scope User``

.. _audio-command-playlist-dedupe:

"""""""""""""""
playlist dedupe
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist dedupe <playlist_name_OR_id> [args]

**Description**

Remove duplicate tracks from a saved playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist dedupe playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist dedupe MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist dedupe MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist dedupe MyPersonalPlaylist --scope User``

.. _audio-command-playlist-delete:

"""""""""""""""
playlist delete
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist delete <playlist_name_OR_id> [args]

.. tip:: Alias: ``playlist del``

**Description**

Delete a saved playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist delete playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist delete MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist delete MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist delete MyPersonalPlaylist --scope User``

.. _audio-command-playlist-download:

"""""""""""""""""
playlist download
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]playlist download <playlist_name_OR_id> [v2=False] [args]

**Description**

Download a copy of a playlist.

These files can be used with the ``[p]playlist upload`` command.
Red v2-compatible playlists can be generated by passing True
for the v2 variable.

**Usage**:
​ ​ ​ ​ ``[p]playlist download playlist_name_OR_id [v2=True_OR_False] [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist download MyGuildPlaylist True``
​ ​ ​ ​ ``[p]playlist download MyGlobalPlaylist False --scope Global``
​ ​ ​ ​ ``[p]playlist download MyPersonalPlaylist --scope User``

.. _audio-command-playlist-info:

"""""""""""""
playlist info
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist info <playlist_name_OR_id> [args]

**Description**

Retrieve information from a saved playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist info playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist info MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist info MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist info MyPersonalPlaylist --scope User``

.. _audio-command-playlist-list:

"""""""""""""
playlist list
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist list [args]

**Description**

List saved playlists.

**Usage**:
​ ​ ​ ​ ``[p]playlist list [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist list``
​ ​ ​ ​ ``[p]playlist list --scope Global``
​ ​ ​ ​ ``[p]playlist list --scope User``

.. _audio-command-playlist-queue:

""""""""""""""
playlist queue
""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist queue <name> [args]

**Description**

Save the queue to a playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist queue playlist_name [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist queue MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist queue MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist queue MyPersonalPlaylist --scope User``

.. _audio-command-playlist-remove:

"""""""""""""""
playlist remove
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist remove <playlist_name_OR_id> <url> [args]

**Description**

Remove a track from a playlist by url.

 **Usage**:
​ ​ ​ ​ ``[p]playlist remove playlist_name_OR_id url [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist remove MyGuildPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU``
​ ​ ​ ​ ``[p]playlist remove MyGlobalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU --scope Global``
​ ​ ​ ​ ``[p]playlist remove MyPersonalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU --scope User``

.. _audio-command-playlist-rename:

"""""""""""""""
playlist rename
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist rename <playlist_name_OR_id> <new_name> [args]

**Description**

Rename an existing playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist rename playlist_name_OR_id new_name [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist rename MyGuildPlaylist RenamedGuildPlaylist``
​ ​ ​ ​ ``[p]playlist rename MyGlobalPlaylist RenamedGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist rename MyPersonalPlaylist RenamedPersonalPlaylist --scope User``

.. _audio-command-playlist-save:

"""""""""""""
playlist save
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist save <name> <url> [args]

**Description**

Save a playlist from a url.

**Usage**:
​ ​ ​ ​ ``[p]playlist save name url [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist save MyGuildPlaylist https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM``
​ ​ ​ ​ ``[p]playlist save MyGlobalPlaylist https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM --scope Global``
​ ​ ​ ​ ``[p]playlist save MyPersonalPlaylist https://open.spotify.com/playlist/1RyeIbyFeIJVnNzlGr5KkR --scope User``

.. _audio-command-playlist-start:

""""""""""""""
playlist start
""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist start <playlist_name_OR_id> [args]

.. tip:: Alias: ``playlist play``

**Description**

Load a playlist into the queue.

**Usage**:
​ ​ ​ ​`` [p]playlist start playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist start MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist start MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist start MyPersonalPlaylist --scope User``

.. _audio-command-playlist-update:

"""""""""""""""
playlist update
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist update <playlist_name_OR_id> [args]

**Description**

Updates all tracks in a playlist.

**Usage**:
​ ​ ​ ​ ``[p]playlist update playlist_name_OR_id [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist update MyGuildPlaylist``
​ ​ ​ ​ ``[p]playlist update MyGlobalPlaylist --scope Global``
​ ​ ​ ​ ``[p]playlist update MyPersonalPlaylist --scope User``

.. _audio-command-playlist-upload:

"""""""""""""""
playlist upload
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]playlist upload [args]

**Description**

Uploads a playlist file as a playlist for the bot.

V2 and old V3 playlist will be slow.
V3 Playlist made with ``[p]playlist download`` will load a lot faster.

**Usage**:
​ ​ ​ ​ ``[p]playlist upload [args]``

**Args**:
​ ​ ​ ​ The following are all optional:
​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
​ ​ ​ ​ ​ ​ ​ ​ --author [user]
​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

**Scope** is one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User

**Author** can be one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123

**Guild** can be one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name

Example use:
​ ​ ​ ​ ``[p]playlist upload``
​ ​ ​ ​ ``[p]playlist upload --scope Global``
​ ​ ​ ​ ``[p]playlist upload --scope User``

.. _audio-command-prev:

^^^^
prev
^^^^

**Syntax**

.. code-block:: none

    [p]prev 

**Description**

Skip to the start of the previously played track.

.. _audio-command-queue:

^^^^^
queue
^^^^^

**Syntax**

.. code-block:: none

    [p]queue [page=1]

**Description**

List the songs in the queue.

.. _audio-command-queue-clean:

"""""""""""
queue clean
"""""""""""

**Syntax**

.. code-block:: none

    [p]queue clean 

**Description**

Removes songs from the queue if the requester is not in the voice channel.

.. _audio-command-queue-cleanself:

"""""""""""""""
queue cleanself
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]queue cleanself 

**Description**

Removes all tracks you requested from the queue.

.. _audio-command-queue-clear:

"""""""""""
queue clear
"""""""""""

**Syntax**

.. code-block:: none

    [p]queue clear 

**Description**

Clears the queue.

.. _audio-command-queue-search:

""""""""""""
queue search
""""""""""""

**Syntax**

.. code-block:: none

    [p]queue search <search_words>

**Description**

Search the queue.

.. _audio-command-queue-shuffle:

"""""""""""""
queue shuffle
"""""""""""""

**Syntax**

.. code-block:: none

    [p]queue shuffle 

**Description**

Shuffles the queue.

.. _audio-command-remove:

^^^^^^
remove
^^^^^^

**Syntax**

.. code-block:: none

    [p]remove <index_or_url>

**Description**

Remove a specific track number from the queue.

.. _audio-command-repeat:

^^^^^^
repeat
^^^^^^

**Syntax**

.. code-block:: none

    [p]repeat 

**Description**

Toggle repeat.

.. _audio-command-search:

^^^^^^
search
^^^^^^

**Syntax**

.. code-block:: none

    [p]search <query>

**Description**

Pick a track with a search.

Use ``[p]search list <search term>`` to queue all tracks found on YouTube. Use ``[p]search sc
<search term>`` to search on SoundCloud instead of YouTube.

.. _audio-command-seek:

^^^^
seek
^^^^

**Syntax**

.. code-block:: none

    [p]seek <seconds>

**Description**

Seek ahead or behind on a track by seconds or a to a specific time.

Accepts seconds or a value formatted like 00:00:00 (``hh:mm:ss``) or 00:00 (``mm:ss``).

.. _audio-command-shuffle:

^^^^^^^
shuffle
^^^^^^^

**Syntax**

.. code-block:: none

    [p]shuffle 

**Description**

Toggle shuffle.

.. _audio-command-shuffle-bumped:

""""""""""""""
shuffle bumped
""""""""""""""

**Syntax**

.. code-block:: none

    [p]shuffle bumped 

**Description**

Toggle bumped track shuffle.

Set this to disabled if you wish to avoid bumped songs being shuffled. This takes priority
over ``[p]shuffle``.

.. _audio-command-sing:

^^^^
sing
^^^^

**Syntax**

.. code-block:: none

    [p]sing 

**Description**

Make Red sing one of her songs.

.. _audio-command-skip:

^^^^
skip
^^^^

**Syntax**

.. code-block:: none

    [p]skip [skip_to_track]

**Description**

Skip to the next track, or to a given track number.

.. _audio-command-stop:

^^^^
stop
^^^^

**Syntax**

.. code-block:: none

    [p]stop 

**Description**

Stop playback and clear the queue.

.. _audio-command-summon:

^^^^^^
summon
^^^^^^

**Syntax**

.. code-block:: none

    [p]summon 

**Description**

Summon the bot to a voice channel.

.. _audio-command-volume:

^^^^^^
volume
^^^^^^

**Syntax**

.. code-block:: none

    [p]volume [vol]

**Description**

Set the volume, 1% - 150%.
