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

********
Tutorial
********

This tutorial will walk you through how to use Config.

First, you need to import Config:

.. code-block:: python

    from core import Config

Then, in the class's :code:`__init__` function, you need to get a config instance:

.. code-block:: python

    class MyCog:
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890)

The :code:`identifier` in :code:`get_conf` is used to keep your cog's data separate
from that of another cog, and thus should be unique to your cog. For example: if we
have two cogs named :code:`MyCog` and their identifier is different, each will have
its own data without overwriting the other's data. Note that it is also possible
to force registration of a data key before allowing you to get and set data for
that key by adding :code:`force_registration=True` after identifier (that defaults
to :code:`False` though)

After we've gotten that, we need to register default values:

.. code-block:: python

    class MyCog:
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890)
            default_global = {
                "foobar": True,
                "foo": {
                    "bar": True,
                    "baz": False
                }
            }
            default_guild = {
                "blah": [],
                "baz": 1234567890
            }
            self.config.register_global(**default_global)
            self.config.register_guild(**default_guild)

As seen in the example above, we can set up our defaults in dicts and then use those in
the appropriate :code:`register` function. As seen above, there's :code:`register_global`
and :code:`register_guild`, but there's also :code:`register_member`, :code:`register_role`,
:code:`register_user`, and :code`register_channel`. Note that :code:`member` stores based on
guild id AND the user's id.

Once we have our defaults registered and we have the object, we can now use those values
in various ways:

.. code-block:: python

    @commands.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def setbaz(self, ctx, new_value):
        await self.config.guild(ctx.guild).baz.set(new_value)
        await ctx.send("Value of baz has been changed!")

    @commands.command()
    @checks.is_owner()
    async def setfoobar(self, ctx, new_value):
        await self.config.foobar.set(new_value)

    @commands.command()
    async def checkbaz(self, ctx):
        baz_val = self.config.guild(ctx.guild).baz()
        await ctx.send("The value of baz is {}".format("True" if baz_val else "False"))

Notice a few things in the above examples:
1. Global doesn't have anything in between :code:`self.config` and the variable
2. The setters need to be awaited (because they're coroutines)
3. If you're getting the value, the syntax is
:code:`self.config.<insert thing here, or nothing if global>.variable_name()`
If setting, it's :code:`self.config.<insert thing here, or nothing if global>.variable_name.set(new_value)`

Please note that in addition to nothing for global, and guild for guild (which takes an object of type
:code:`discord.Guild`), there are:
member: takes :code:`discord.Member`
user: takes :code:`discord.User`
role: takes :code:`discord.Role`
channel: takes :code:`discord.TextChannel`

If you need to wipe data from the config, you want to look at :code:`clear` or :code:`clear_all`
Which one you should use depends on what you want to do. If you're looking to clear data for a
single guild/member/channel/role/user, you want to use :code:`clear` as that will clear the
data only for the specified thing (though, if used on global, it will reset all of the data
for keys registered with :code:`register_global`). If using :code:`clear_all`, it will reset
all data for all guilds/members/channels/roles/users (or if used on a global, it will reset
everything for all kinds)

*************
API Reference
*************

.. important::

    Before we begin with the nitty gritty API Reference, you should know that there are tons of working code examples
    inside the bot itself! Simply take a peek inside of the :code:`tests/core/test_config.py` file for examples of using
    Config in all kinds of ways.

.. automodule:: core.config

Config
^^^^^^

.. autoclass:: Config
    :members:

Group
^^^^^

.. autoclass:: Group
    :members:
    :special-members:

MemberGroup
^^^^^^^^^^^

.. autoclass:: MemberGroup
    :members:

Value
^^^^^

.. autoclass:: Value
    :members:
    :special-members: __call__


****************
Driver Reference
****************

.. automodule:: core.drivers

.. autoclass:: red_base.BaseDriver
    :members:
