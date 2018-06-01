.. don't forget to set permissions hyperlink
  + commands links + guide links

.. _getting-started:

===============
Getting started
===============

If you recently installed Red, you should read this.
This is a quick start guide for a general usage.

.. note::

    If you haven't installed Red, please do it by following
    the :ref:`installation guides <main>`.

Assuming you correctly installed Red, you should have a
window like this:

.. image:: .ressources/red-console.png

.. _gettings-started-invite:

-------------------------
Invite Red to your server
-------------------------

When started, the console will show you ``Invite URL`` (here at
the bottom of the screenshot).
Paste the link into your browser and select the server you want
to invite the bot in, like any other bot.

.. note:: You need the ``Manage server`` permission to add bots.

Complete the captcha, it should tell you ``Authorized!`` and you
should see your bot in the members list.

.. attention::
    If Discord shows ``Bot requires code grant``, please untick this
    option in your token settings

    .. image:: .ressources/code-grant.png

.. _getting-started-interact:

-----------------
Interact with Red
-----------------

As a chatbot, you interact with Red via the Discord text channels
(not from the command prompt). For that, you will use the prefix you
set before. For example, if your prefix is ``!``, you will execute your
command like this: ``!ping``.

.. note:: Since the prefix can be anything, it'll be referenced as ``[p]``
    in documentations.

.. _getting-started-commands:

~~~~~~~~~~~~
The commands
~~~~~~~~~~~~

The command you're going to use the most is help. That command will
show you **all of the available commands** of the bot with a small description.

.. code-block:: none

    [p]help

.. tip:: The message is generated dynamically and users will only see the
    commands they can use. You can edit this using the permissions cog.

You can also pick a command to get its detailled description and the
parameters.

.. code-block:: none

    [p]help command

The parameters are shown as enclosed in ``< >`` if they're needed, or
``[ ]`` if optional.
As an example, the ban command will show this in the help message:
``Syntax: !ban <user> [days] [reason]``

This means that it is necessary to provide ``user``. However, the
``days`` value (number of messages to delete) is optional, like
the ``reason`` value, used for the modlog.

You can use help to show the **categories** too (named cogs).
Just do so (notice the capitalization):

.. code-block:: none

    [p]help YourCategory

Help also shows **command groups**. They are group of commands.
To get the description of a subcommand, type this:

.. code-block:: none

    [p]help commandgroup subcommand

When using them, you also need to specify the command group.
As an example, ``cleanup`` has 6 subcommands. If you want
to use one, do it like this: ``[p]cleanup messages 10``

.. _getting-started-cogs:

----
Cogs
----

Red is built with cogs, fancy term for plugins. They are
modules that enhance the Red functionnalities. They contain
commands to use.

Red comes with 19 cogs containing the basic features, such
as moderation, utility, music, streams...

You can see your loaded and unloaded cogs with the ``[p]cogs``
command. By default, all cogs will be unloaded.

You can load or unload a cog by using the load or unload command

.. code-block:: none

    [p]load cogname
    [p]unload cogname

.. tip:: You can load and unload multiple cogs at once:

    .. code-block:: none

        [p]load cog1 cog2 ...

You can enable and disable everything you want, which means you can
customize Red how you want!

.. _getting-started-community-cogs:

~~~~~~~~~~~~~~
Community cogs
~~~~~~~~~~~~~~

There's an entire `community <https://discord.gg/red>`_ that contributes
to Red. Those contibutors make additional cogs for you to use. You can
download them using the downloader cog.

You can start using the downloader cog by loading it: ``[p]load downloader``

You can find cogs by searching on `cogs.red <https://dev.v3.cogs.red>`_. Find whatever you want,
there are hundreds of cogs available!

.. note:: ``cogs.red``, the website that list all of the cogs is not
    ready for v3 yet. For now, you can refer to `this issue
    <https://github.com/Cog-Creators/Red-DiscordBot/issues/1398>`_.

.. 26-cogs not available, let's use my repo :3

Cogs comes with repositories. A repository is a container of cogs
that you can install. Let's suppose you want to install the ``say``
cog from the repository ``Laggrons-Dumb-Cogs``. You'll first need
to install the repository.

.. code-block:: none

    [p]repo add Laggrons-Dumb-Cogs https://github.com/retke/Laggrons-Dumb-Cogs v3

.. note:: You may need to specify a branch. If so, add its name after the link.
    Here the branch we want is ``v3``.

Then you can add the cog

.. code-block:: none

    [p]cog install Laggrons-Dumb-Cogs say

Now the cog is installed, but not loaded. You can load it using the ``[p]load``
command we talked about before.

For more informations about the downloader, check its :ref:`guide <>`.

.. _getting-started-permissions:

-----------
Permissions
-----------

Red works with different levels of permissions. Every cog defines
the level of permission needed for a command.

* **Bot owner**

  The bot owner can access all commands on every guild. He can also use
  exclusive commands that can interact with the global settings
  or system files. If it *you* by default. If not set, use ``[p]set owner``

* **Server owner**

  The server owner can access all commands on his guild, except the global
  ones or those who can interact with system files (available for the
  bot owner).

* **Administrator**

  The administrator is defined by its roles. You can set an admin role
  with ``[p]set adminrole``. For example, in the mod cog, an admin can
  use the ``[p]modset`` command which defines the cog settings.

* **Moderator**

  A moderator is a step above the average users. You can set a moderator
  role with ``[p]set modrole``. For example, in the mod cog (again), a mod
  will be able to mute, kick and ban; but he won't be able to modify the
  cog settings with the ``[p]modset`` command.

.. tip::
    If you don't like the default permission settings for some commands or
    if want to restrict a cog or a command to a channel/member, you can use
    the :ref:`permissions <>` cog.

.. _getting-started-hosting:

-------
Hosting
-------

If you are hosting Red on your personnal computer, you will soon notice that
if you close the window or if you shut down you computer. He needs an
environement to work and respond.

You can try to host Red somewhere he will always be online, like on a virtual
private server (VPS) or on a personnal server (e.g. Raspberry Pi).

If you want to do it, follow these steps.

.. warning::
    Before trying to host Red on a Linux environement, you need to know the
    basics of the Unix commands, such as navigate the system files or use
    a terminal text editor.

    You should follow `this guide
    <https://www.digitalocean.com/community/tutorials/an-introduction-to-linux-basics>`_
    from DigitalOcean which will introduct you to the Linux basics.

1. **Find a host**

  You need to find a server to host Red. You can rent a VPS (it can be free)
  on an online service. Please check :ref:`this list <host-list>` for
  quality VPS providers.

  You can also buy a Raspberry Pi (~$20), which is a micro-computer that will
  be able to host Red. The model 3 or above is recommanded.

2. **Install Linux**

  Most of the VPS providers has tools for installing Linux automatically. If
  you're a beginner, we recommand **Ubuntu 16** which is easy to understand.

  For Raspberry Pi users, just install `Raspbian
  <https://www.raspberrypi.org/downloads/raspbian/>`_ on a micro-SD card.

3. **Install and set up Red**

  Just follow one of the Linux installation guide. We provide guides for the
  most used distributions. Check the :ref:`home page <main>` and search for
  your distribution.

4. **Set up an auto-restart**

  Once you got Red running on your server, it will still shut down if you close
  the Red window. You can set up an auto-restarting system that will create a
  side task and handle fatal errors, so you can just leave your server running
  and enjoy Red!

  For that, just follow :ref:`this guide <systemd-service-guide>`.
