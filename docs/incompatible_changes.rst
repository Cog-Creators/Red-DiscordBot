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

TBD.


Behavior changes
----------------

``menu()`` now listens to both reaction add and remove
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
