.. red's core utils documentation

=================
Utility Functions
=================

General Utility
===============

.. automodule:: redbot.core.utils
    :members: deduplicate_iterables, bounded_gather, bounded_gather_iter

.. autoclass:: AsyncIter
    :members:
    :special-members: __await__
    :exclude-members: enumerate, filter

    .. automethod:: enumerate
        :async-for:

    .. automethod:: filter
        :async-for:


Chat Formatting
===============

.. automodule:: redbot.core.utils.chat_formatting
    :members:

Embed Helpers
=============

.. automodule:: redbot.core.utils.embed
    :members:
    :exclude-members: randomize_color

Reaction Menus
==============

.. automodule:: redbot.core.utils.menus
    :members:

Event Predicates
================

MessagePredicate
****************

.. autoclass:: redbot.core.utils.predicates.MessagePredicate
    :members:

ReactionPredicate
*****************

.. autoclass:: redbot.core.utils.predicates.ReactionPredicate
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
