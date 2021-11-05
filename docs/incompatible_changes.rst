.. Backward incompatible changes list

=============================
Backward incompatible changes
=============================

This page lists all functionalities that are currently deprecated, features that have been removed in past minor releases, and any other backward incompatible changes that are planned or have been removed in past minor releases. The objective is to give users a clear rationale why a certain change has been made, and what alternatives (if any) should be used instead.

Lists below are sorted by (planned) date of the change (latest first).

.. contents::
    :depth: 3
    :local:

For Users
*********

Deprecated functionality
------------------------

redbot-launcher
~~~~~~~~~~~~~~~

.. deprecated:: 3.2.0

The vast majority of functionality provided by ``redbot-launcher`` can already be
achieved through other means.

In Red 3.2.0, ``redbot-launcher`` has been stripped most of its functionality
as it can already be done through other (better supported) means:

- Updating Red (a proper way to update Red is now documented in `update_red`)
- Creating instances (as documented in install guides, it should be done through ``redbot-setup``)
- Removing instances (available under ``redbot-setup delete``)
- Removing all instances (no direct alternative, can be done through ``redbot-setup delete``)
- Debug information (available under ``redbot --debuginfo`` and ``[p]debuginfo`` bot command)

Currently, ``redbot-launcher`` only provides auto-restart functionality.
We plan to fully remove ``redbot-launcher`` once our documentation has information on
how to set up auto-restart on all of the supported operating systems.

Documentation for `autostart_systemd` and `autostart_mac` is already available,
documentation for Windows is still in works.

Behavior changes
----------------

Red requires to have at least one owner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 3.5.0

There was never a reason to allow users to run the bot without having an owner set
and it had been a point of confusion for new users that are trying to set up Red
using a team application which, by default, doesn't have any owners set.

If your instance does not have any owner set, Red will print an error message on startup
and exit before connecting to Discord. This error message contains all
the needed information on how to set a bot owner and the security implications of it.

If, for some reason, you intentionally are running Red without any owner set,
you may still be able to do that by setting an invalid user ID as owner
but THIS IS NOT SUPPORTED.


For Developers
**************

Deprecated functionality
------------------------

Downloader's shared libraries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. deprecated:: 3.2.0

Shared libraries have been deprecated in favor of pip-installable libraries.
Shared libraries do not provide any functionality that can't already be achieved
with pip requirements *and* as such don't provide much value in return for
the added complexity.

Known issues, especially those related to hot-reload, were not handled automatically
for shared libraries, same as they are not handled for the libraries installed
through pip.

Removed functionality
---------------------

``guild_id`` parameter to ``Red.allowed_by_whitelist_blacklist()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. deprecated-removed:: 3.4.8 30

``guild_id`` parameter to `Red.allowed_by_whitelist_blacklist()` has been removed as
it is not possible to properly handle the local allowlist/blocklist logic with just
the guild ID. Part of the local allowlist/blocklist handling is to check
whether the provided user is a guild owner.

Use the ``guild`` parameter instead.

Example:

.. code:: python

    if await bot.allowed_by_whitelist(who_id=user_id, guild_id=guild.id, role_ids=role_ids):
        ...

Becomes:

.. code:: python

    if await bot.allowed_by_whitelist(who_id=user_id, guild=guild, role_ids=role_ids):
        ...

``redbot.core.commands.converter.GuildConverter``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. deprecated-removed:: 3.4.8 60

Use `discord.Guild`/`redbot.core.commands.GuildConverter` instead.

Example:

.. code:: python

    from redbot.core import commands
    from redbot.core.commands.converter import GuildConverter

    class MyCog(commands.Cog):
        @commands.command()
        async def command(self, ctx, server: GuildConverter):
            await ctx.send(f"You chose {server.name}!")

Becomes:

.. code:: python

    import discord
    from redbot.core import commands

    class MyCog(commands.Cog):
        @commands.command()
        async def command(self, ctx, server: discord.Guild):
            await ctx.send(f"You chose {server.name}!")


Behavior changes
----------------

``redbot.core.bot.RedBase`` has been merged into ``redbot.core.bot.Red``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 3.5.0

Historically, ``RedBase`` existed to allow using Red for self/user bots back when
it was not against Discord's Terms of Service. Since this is no longer a concern,
everything from ``RedBase`` have been moved directly to `Red` and ``RedBase`` class
has been removed.

If you were using ``RedBase`` for runtime type checking or type annotations,
you should now use `Red` instead. Since both of these classes resided in the same
module, it should be a matter of simple find&replace.

``Context.maybe_send_embed()`` requires content with length of 1-2000 characters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 3.5.0

`Context.maybe_send_embed()` now requires the message's length to be
between 1 and 2000 characters.

Since the length limits for regular message content and embed's description are
different, it is easy to miss an issue with inappropriate handling of length limits
during development. This change should aid with early detection of such issue by
consistently rejecting message with length that can't be used with
both embed and non-embed message.

This change only affects code that is already not guaranteed to work.
You should make sure that your code properly handles message length limits.

``menu()`` listens to both reaction add and remove
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 3.5.0

Listening only to reaction add results in bad user experience.
If the bot had Manage Messages permission, it removed the user's reaction
so that they don't have to click twice but this comes with a noticable delay.
This issue is even more noticable under load, when the bot ended up hitting
Discord-imposed rate limits.

If your calls to `menu()` are using the default controls (``redbot.core.utils.menus.DEFAULT_CONTROLS``),
you don't have to do anything.

Otherwise, you should ensure that your custom functions used for the menu controls
do not depend on this behavior in some way. In particular, you should make sure that
your functions do not automatically remove author's reaction.

Here's an example code that needs to be updated:

.. code:: python

    import contextlib

    import discord
    from redbot.core.utils.menus import close_menu, menu

    CUSTOM_CONTROLS = {
        "\N{CROSS MARK}": close_menu,
        "\N{WAVING HAND SIGN}": custom_control,
    }


    async def custom_control(ctx, pages, controls, message, page, timeout, emoji):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            with contextlib.suppress(discord.NotFound):
                await message.remove_reaction(emoji, ctx.author)

        await ctx.send("Hello world!")
        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


    async def show_menu(ctx):
        await menu(ctx, ["Click :wave: to say hi!"], CUSTOM_CONTROLS)

To make this code work on Red 3.5 and higher, you need to update ``custom_control()`` function:

.. code:: python

    async def custom_control(ctx, pages, controls, message, page, timeout, emoji):
        await ctx.send("Hello world!")
        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)
