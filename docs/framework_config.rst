.. config shite

.. role:: python(code)
    :language: python

======
Config
======

Config was introduced in V3 as a way to make data storage easier and safer for all developers regardless of skill level.
It will take some getting used to as the syntax is entirely different from what Red has used before, but we believe
Config will be extremely beneficial to both cog developers and end users in the long run.

***********
Basic Usage
***********

.. code-block:: python

    from core import Config

    class MyCog:
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890)

            self.config.register_global(
                foo=True
            )

        @commands.command()
        async def return_some_data(self, ctx):
            await ctx.send(config.foo())

*************
API Reference
*************

.. important::

    Before we begin with the nitty gritty API Reference, you should know that there are tons of working code examples
    inside the bot itself! Simply take a peek inside of the :code:`tests/core/test_config.py` file for examples of using
    Config in all kinds of ways.

.. automodule:: core.config

.. autoclass:: Config
    :members:

.. autoclass:: Group
    :members:
    :special-members:

.. autoclass:: MemberGroup
    :members:

.. autoclass:: Value
    :members:
    :special-members: __call__


****************
Driver Reference
****************

.. automodule:: core.drivers

.. autoclass:: red_base.BaseDriver
    :members:
