..bluecommands module documentation

================
Commands Package
================

This package acts almost identically to :doc:`discord.ext.commands <dpy:ext/commands/api>`; i.e.
all of the attributes from discord.py's are also in ours. 
Some of these attributes, however, have been slightly modified, while others have been added to
extend functionalities used throughout the bot, as outlined below.

.. autofunction:: bluebot.core.commands.command

.. autofunction:: bluebot.core.commands.group

.. autoclass:: bluebot.core.commands.Cog

    .. automethod:: format_help_for_context
    
    .. automethod:: blue_get_data_for_user
    
    .. automethod:: blue_delete_data_for_user

.. autoclass:: bluebot.core.commands.Command
    :members:
    :inherited-members: format_help_for_context

.. autoclass:: bluebot.core.commands.Group
    :members:

.. autoclass:: bluebot.core.commands.Context
    :members:

.. autoclass:: bluebot.core.commands.GuildContext

.. autoclass:: bluebot.core.commands.DMContext

.. automodule:: bluebot.core.commands.requires
    :members: PrivilegeLevel, PermState, Requires

.. automodule:: bluebot.core.commands.converter
    :members:
    :exclude-members: UserInputOptional, convert
    :no-undoc-members:

    .. autodata:: UserInputOptional
        :annotation:

.. _framework-commands-help:

******************
Help Functionality
******************

.. warning::

    The content in this section is provisional and may change
    without prior notice or warning. Updates to this will be communicated
    on `this issue <https://github.com/Cock-Creators/Blue-DiscordBot/issues/4084>`_


.. automodule:: bluebot.core.commands.help
    :members:
