.. red commands module documentation

================
Commands Package
================

This package acts almost identically to :doc:`discord.ext.commands <dpy:ext/commands/api>`; i.e.
all of the attributes from discord.py's are also in ours. 
Some of these attributes, however, have been slightly modified, while others have been added to
extend functionalities used throughout the bot, as outlined below.

.. autofunction:: redbot.core.commands.command

.. autofunction:: redbot.core.commands.group

.. autoclass:: redbot.core.commands.Command
    :members:
    :inherited-members: format_help_for_context

.. autoclass:: redbot.core.commands.Group
    :members:

.. autoclass:: redbot.core.commands.Context
    :members:

.. autoclass:: redbot.core.commands.GuildContext

.. autoclass:: redbot.core.commands.DMContext

.. automodule:: redbot.core.commands.requires
    :members: PrivilegeLevel, PermState, Requires

.. automodule:: redbot.core.commands.converter
    :members:
    :exclude-members: convert
    :no-undoc-members:
