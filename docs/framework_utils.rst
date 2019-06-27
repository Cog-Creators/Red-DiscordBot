.. red's core utils documentation

=========
Utilities
=========

General Utility
===============

.. automodule:: redbot.core.utils
    :members: deduplicate_iterables, bounded_gather, bounded_gather_iter

Chat Formatting
===============

.. automodule:: redbot.core.utils.chat_formatting
    :members:

Embed Helpers
=============

.. automodule:: redbot.core.utils.embed
    :members:

Reaction Menus
==============

.. automodule:: redbot.core.utils.menus

Examples
^^^^^^^^

Using Provided Menus
++++++++++++++++++++
This example shows sending a menu into the context channel, for the
command author to scroll through some pages of text and embeds, and
waiting for the menu to exit:

.. code-block:: python
    :emphasize-lines: 13

    import discord
    from redbot.core import commands
    from redbot.core.utils import menus

    @commands.command()
    async def sendpages(ctx):
        """Send some useless pages."""
        pages = [
            "This is page 1",
            discord.Embed(title="This is page 2"),
            ("This is page 3", discord.Embed(title="This is also page 3"))
        ]
        await menus.PagedMenu.send_and_wait(ctx, pages=pages)

This example shows sending a menu into a specific channel, for any user
to select an option from. This option is then passed onto a callback
along with the user who selected it. The menu stays running as a
background task and the callback is called multiple times.

.. code-block:: python
    :emphasize-lines: 6, 7, 8

    import discord
    from redbot.core.utils import menus

    async def send_reactrole_menu(channel, reactroles) -> menus.OptionsMenu:
        options = [(role.mention, role) for role in reactroles]
        return await menus.OptionsMenu.send_and_return(
            channel=channel, options=options, title="React to add or remove a role"
        )

    async def add_or_remove_reactrole(member: discord.Member, role: discord.Role):
        if role in member.roles:
            await member.remove_roles(role, reason="Removing reactrole")
        else:
            await member.add_roles(role, "Adding reactrole")

Extending Provided Menus
++++++++++++++++++++++++
This is an example of a paged menu which lazily fetches batches of pages
from some API and caches them, as the user scrolls through it:

.. code-block:: python

    from redbot.core.utils import menus
    from .api import fetch_preceding_pages, fetch_following_pages

    class LazilyPagedMenu(menus.PagedMenu):

        def __init__(self, **kwargs) -> None:
            # PagedMenu.__init__ requires the pages kwarg.
            # Since we're creating pages ourselves, we allow it to be empty.
            super().__init__(pages=kwargs.pop("pages", []), pagenum_in_footer=False, **kwargs)
            # This attribute is just an example of what might be passed to our API to fetch pages
            self._remote_page_idx = 0

        async def _before_send(self, **kwargs):
            # Fetch the initial pages
            if not self._pages:
                self._pages.extend(await fetch_following_pages(self._remote_page_idx))

        @menus.ReactionMenu.handler("⬅")
        async def prev_page(self, payload: discord.RawReactionActionEvent):
            self._remote_page_idx -= 1
            if self._cur_idx == 0:
                # Fetch the previous few pages and add them to the start of the page list
                self._pages[0:0] = new_pages = await fetch_preceding_pages(self._remote_page_idx)
                self._cur_idx += len(new_pages)
            # The base method decrements self._cur_idx and updates the message
            await super().prev_page(payload)

        @menus.ReactionMenu.handler("➡")
        async def next_page(self, payload: discord.RawReactionActionEvent):
            self._remote_page_idx += 1
            if self._cur_idx == len(self._pages) - 1:
                # Fetch the next few pages and add them to the end of the page list
                new_pages = await fetch_following_pages(self._remote_page_idx)
                self._pages.extend(new_pages)
            # The base method increments self._cur_idx and updates the message
            await super().next_page(payload)

ReactionMenu
^^^^^^^^^^^^

.. autoclass:: redbot.core.utils.menus.ReactionMenu
    :members:
    :member-order: bysource
    :exclude-members: INITIAL_EMOJIS, handler, add_handler

    .. autoattribute:: INITIAL_EMOJIS
        :annotation:

    .. automethod:: handler(*emojis, event = RAW_REACTION_ADD | RAW_REACTION_REMOVE)
        :decorator:

    .. automethod:: add_handler(handler, *emojis, event = RAW_REACTION_ADD | RAW_REACTION_REMOVE)

PagedMenu
^^^^^^^^^
.. autoclass:: PagedMenu
    :members:

OptionsMenu
^^^^^^^^^^^
.. autoclass:: OptionsMenu
    :members:

PagedOptionsMenu
^^^^^^^^^^^^^^^^
.. autoclass:: PagedOptionsMenu
    :members:

ReactionEvent
^^^^^^^^^^^^^

.. autoclass:: ReactionEvent

    .. autoattribute:: REACTION_ADD
        :annotation:

    .. autoattribute:: REACTION_REMOVE
        :annotation:

    .. autoattribute:: REACTION_CLEAR
        :annotation:

    .. autoattribute:: RAW_REACTION_ADD
        :annotation:

    .. autoattribute:: RAW_REACTION_REMOVE
        :annotation:

    .. autoattribute:: RAW_REACTION_CLEAR
        :annotation:

Event Predicates
================

.. automodule:: redbot.core.utils.predicates
    :members:

Mod Helpers
===========

.. automodule:: redbot.core.utils.mod
    :members:

Tunnel
======

.. automodule:: redbot.core.utils.tunnel
    :members: Tunnel

Common Filters
==============

.. automodule:: redbot.core.utils.common_filters
    :members:
