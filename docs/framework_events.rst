.. framework events list

=============
Custom Events
=============

RPC Server
^^^^^^^^^^

.. py:method:: Red.on_shutdown()

    Dispatched when the bot begins its shutdown procedures.

Economy
^^^^^^^

.. py:method:: red_economy_payday_claim(payload: redbot.core.bank.PaydayClaimInformation)

    Dispatched when a user claims their daily payday.

    :type payload: redbot.core.bank.PaydayClaimInformation
    :param payload.member: The member who is claiming their payday. (:class:`discord.Member`)
    :param payload.channel: The channel where the payday claim is made. (:class:`discord.TextChannel`, :class:`discord.Thread`, :class:`discord.ForumChannel`)
    :param payload.amount: The amount of currency claimed in the payday. (:class:`int`)
    :param payload.old_balance: The old balance of the user before the payday claim. (:class:`int`)
    :param payload.new_balance: The new balance of the user after the payday claim. (:class:`int`)
    :method payload.to_dict: Returns a serializable dictionary representation of the payload. (:class:`dict`)
    :method payload.to_json: Returns the payload as JSON. (:class:`str`)
