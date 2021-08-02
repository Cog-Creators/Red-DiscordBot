.. config shite

.. role:: python(code)
    :language: python

=====
Audio
=====

This API acts as a wrapper for Red-LavaLink and allows developers to interact with the audio cog

.. note:: First attempt of creating an API for redbots audio module.
          This is not in any way production ready/stable yet. Use at your own risk

          Many features of the core audio cog have been moved to the API's code, thus the audio cog depends on it now
          This API however doesn't depend on the audio cog being loaded

***********
Basic Usage
***********

.. code-block:: python

    from redbot.core import commands, Audio

    class MyAudioCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.audio: Audio = None
            #This function starts the lavalink server and established a lavalink and database connection

        async def initialize(self):
            self.audio = Audio.initialize(self.bot, "MyAudioCog", 365911945565569036)

        @commands.command()
        async def connect(self, ctx, channel: discord.VoiceChannel):
            await self.audio.Player.connect(channel)
            await ctx.send(f"Successfully connected to {channel.mention"})

        @commands.command()
        async def play(self, ctx, query: str):
            await self.audio.Player.play(query, ctx.author)

            now_playing = await audio.current(ctx.guild)
            await ctx.send(f"Now playing: {now_playing.title}")

***************
Event Reference
***************

.. py:function:: on_lavalink_server_started(java_path)

    Dispatched when the lavalink server has been started

    :param str java_path: The java executable used to start the server

.. py:function:: on_lavalink_server_stopped()

    Dispatched when the lavalink server has been stopped

.. py:function:: on_lavalink_connection_established(host, password, ws_port)

    Dispatched when the lavalink connection has been established

    :param str host: The host of the lavalink server
    :param str password: The password of the lavalink server
    :param in ws_port: The server's websocket port

.. py:function:: on_red_audio_track_start(guild, track, requester)

    Dispatched when a track has started

    :param discord.Guild guild: The guild in which the track has been started
    :param lavalink.Track track: The track which have been started
    :param discord.Member requester: The requester of the track

.. py:function:: on_red_audio_track_enqueue(guild, track, requester)

    Dispatched when a track is enqueued

    :param discord.Guild guild: The guild in which the track has been enqueued
    :param lavalink.Track track: The tracks which have been enqueued
    :param discord.Member requester: The requester of the tracks

.. py:function:: on_red_audio_track_end(guild, track, requester, reason)

    Dispatched when a track has ended

    :param discord.Guild guild: The guild in which the track has ended
    :param lavalink.Track track: The track which has ended
    :param discord.Member requester: The requester of the track
    :param lavalink.TrackEndReason reason: The reason why the track has ended

.. py:function:: on_red_audio_queue_end(guild, track, requester)

    Dispatched when the queue has ended

    :param discord.Guild guild: The guild in which the queue has ended
    :param lavalink.Track track: The last played track
    :param discord.Member requester: The requester of the last track

.. py:function:: on_red_audio_track_skip(guild, track, requester)

    Dispatched when a track is skipped

    :param discord.Guild guild: The guild in which the track has been skipped
    :param lavalink.Track track: The current track
    :param discord.Member requester: The user who requested the skip

.. py:function:: on_red_audio_track_exception(guild, track, requester, exception)

    :param discord.Guild guild: The guild in which the exception occurred
    :param lavalink.Track track: The track which got stuck
    :param discord.Member requester: The user who requested the track
    :param str exception: The exception

.. py:function:: on_red_audio_track_stuck(guild, track, requester, threshold)

    :param discord.Guild guild: The guild in which the track has been stuck
    :param lavalink.Track track: The track which got stuck
    :param discord.Member requester: The user who requested the track
    :param int threshold: Threshold milliseconds that the track has been stuck for

.. py:function:: on_red_audio_audio_paused(guild, paused)

    Dispatched when the player is paused/resumed

    :param discord.Guild guild: The guild in which the player has been stopped/resumed
    :param bool paused: True if the player has been paused, False if resumed

.. py:function:: on_red_audio_audio_stop(guild)

    Dispatched when the player has been manually stopped

    :param discord.Guild guild: The guild in which the player disconnected

.. py:function:: on_red_audio_audio_disconnect(guild)

    Dispatched when the player disconnects from a voice channel

    :param discord.Guild guild: The guild in which the player disconnected

*************
API Reference
*************

.. py:currentmodule:: redbot.core.audio

Audio
^^^^^
.. note:: This class shouldn't be instantiated manually. Use :py:meth:`Audio.initialize` to do so.

.. autoclass:: Audio
    :members:

Player
^^^^^^
.. note:: This class wraps various lavalink.Player methods and meanwhile interacts with RED's
          inbuilt config and databases. It is instantiated for you on startup and thus shouldn't be instantiated
          manually. :py:meth:`Audio.player` returns that class instance for you.

.. autoclass:: redbot.core.audio.Player
    :members:

ServerManager
^^^^^^^^^^^^^

.. note:: This class handles the lavalink server subprocess. While the properties provided by this class may be useful,
          one shouldn't interact with any other function since starting of the server and dealing with the jar is
          handled by :py:meth:`Audio.initialize`. Shutting down is handled by :py:meth:`Audio.stop`

.. autoclass:: redbot.core.audio.ServerManager
    :members: