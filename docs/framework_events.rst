.. framework events list

=============
Custom Events
=============

RPC Server
^^^^^^^^^^

.. py:method:: Red.on_shutdown()

    Dispatched when the bot begins it's shutdown procedures.

Economy
^^^^^^^

.. py:method:: red_economy_payday_claim(member: discord.Member, channel: discord.TextChannel | discord.Thread | discord.ForumChannel, amount: int)

    Dispatched when a user claims their daily payday.

    :param member: The member who claimed their payday.
    :param channel: The channel the payday was claimed in.
    :param amount: The amount of credits claimed.