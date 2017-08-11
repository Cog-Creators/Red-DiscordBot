.. V3 Bank

.. role:: python(code)
    :language: python

====
Bank
====

Bank has now been separated from Economy for V3. New to bank is support for
having a global bank.

***********
Basic Usage
***********

.. code-block:: python

    from core import bank

    class MyCog:
        @commands.command()
        async def balance(self, ctx, user: discord.Member=None):
            if user is None:
                user = ctx.author
            bal = bank.get_balance(user)
            currency = bank.get_currency_name(ctx.guild)
            await ctx.send(
                "{}'s balance is {} {}".format(
                    user.display_name, bal, currency
                )
            )

*************
API Reference
*************

Bank
======

.. automodule:: core.bank

.. autoclass:: Account


.. autofunction:: get_balance


.. autocofunction:: set_balance


.. autocofunction:: withdraw_credits


.. autocofunction:: deposit_credits


.. autocofunction:: transfer_credits(from_, to, amount)


.. autofunction:: can_spend


.. autocofunction:: wipe_bank


.. autofunction:: get_guild_accounts


.. autofunction:: get_global_accounts


.. autofunction:: get_account


.. autofunction:: is_global


.. autocofunction:: set_global


.. autofunction:: get_bank_name


.. autocofunction:: set_bank_name


.. autofunction:: get_currency_name


.. autocofunction:: set_currency_name


.. autofunction:: get_default_balance


.. autocofunction:: set_default_balance
