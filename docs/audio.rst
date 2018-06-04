.. _audio:

=====
Audio
=====

This is the cog guide for the audio cog. You will
find detailled docs about the usage and the commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load audio

.. _audio-usage:

-----
Usage
-----

The new audio system has nothing to do with the V2 one.
It's harder, better, faster, stronger. It adds unique
features and it uses Lavalink, a powerful streaming
tool used by Rythm, FredBoat, Dyno and more...

Currently, you can stream using these services:

* YouTube

* SoundCloud

* Bandcamp

* Vimeo

* Twitch streams

* Local files

* HTTP URLs

Here's a quick introduction on how it works.

.. _audio-usage-music:

^^^^^
Music
^^^^^

.. note:: If you use one of the music commands, the bot will
    automatically join your voice channel. You can make it disconnect
    using the :ref:`disconnect <audio-command-disconnect>` command.

You can start listening music with two commands:
:ref:`play <audio-command-play>` and :ref:`search <audio-command-search>`.

The first one will search for the song (YouTube by default) and
play the first result. You can also give a link.

.. tip:: Examples:

    .. code-block:: none

        [p]play harder better faster stronger

    .. code-block:: none

        [p]play https://www.youtube.com/watch?v=GDpmVUEjagg

The second command, :ref:`search <audio-command-search>`, will search
(still on YouTube by default) with the given keywords, then it will
output an interactive message with the search results. You'll just
have to click on the number to start the song.

.. tip:: Example:

    .. code-block:: none

        [p]search harder better faster stronger

    Output:

    .. image:: .ressources/audio-search.png

.. _audio-usage-queue-control:

^^^^^^^^^^^^^
Queue control
^^^^^^^^^^^^^

The queue control in Red is very powerful and easy to use. You can use
the :ref:`queue <audio-command-queue>` command to see the current queue.
It will show all of the songs in the queue with an interactive message.
Once you type the command, something like this should be shown:

.. image:: .ressources/audio-queue.png

You can click on the reactions to scroll through the pages.

You can skip a song and jump to the next one in the queue using the
:ref:`skip <audio-command-skip>` command. The :ref:`prev <audio-command-prev>`
command goes one song backward.

If you just added a song to the queue but you want to listen it now,
you can use the :ref:`bump <audio-command-bump>` command that will
move the desired song to the top of the queue.

However, if you want to remove a song from the queue, you can use the
:ref:`remove <audio-command-remove>` command.

Last thing: if you need to shuffle your playlist, you can use the
:ref:`shuffle <audio-command-shuffle>` command that will make Red select
next songs randomly.

.. tip:: You can make Red show the current song with the
    :ref:`now <audio-command-now>` command. You will also be able to
    skip, prev, play/pause and stop using the reactions.

.. _audio-usage-music-control:

^^^^^^^^^^^^^^
Stream control
^^^^^^^^^^^^^^

You can control the music stream how you want. Red allows you to do multiple
actions on the stream.

If you need to pause the stream, use the
:ref:`pause/resume <audio-command-pause>` command.

You can go forward and backward in the current track using the
:ref:`seek <audio-command-seek>` command.

.. tip:: Examples:

    To seek ahead on a track by 60 seconds:

    .. code-block:: none

        [p]seek 60

    To seek behind on a track by 30 seconds:

    .. code-block:: none

        [p]seek -30
