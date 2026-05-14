.. V3 Migration Guide

.. role:: python(code)
    :language: python

==========================
Migrating cogs from Red V2
==========================

First, be sure to read :dpy_docs:`discord.py's migration guide <migrating_to_v1.html>`
as that covers all of the changes to discord.py that will affect the migration process

----------------
Red as a package
----------------

V3 makes Red a package that is installed with :code:`pip`. Please
keep this in mind when writing cogs as this affects how imports 
should be done (for example, to import :code:`pagify` in V2, one
would do :code:`from .utils.chat_formatting import pagify`; in
V3, this becomes :code:`from redbot.core.utils.chat_formatting import pagify`)

----------------
Cogs as packages
----------------

V3 makes cogs into packages. See :doc:`/guide_cog_creation`
for more on how to create packages for V3.

------
Config
------

Config is V3's replacement for :code:`dataIO`. Instead of fiddling with
creating config directories and config files as was done in V2, V3's
Config handles that whilst allowing for easy storage of settings on a
per-server/member/user/role/channel or global basis. Be sure to check
out :doc:`/framework_config` for the API docs for Config as well as a
tutorial on using Config.

*************
V2 Data Usage
*************

There has been much conversation on how to bring V2 data into V3 and, officially, we recommend that cog developers
make use of the public interface in Config (using the categories as described in these docs) rather than simply
copying and pasting your V2 data into V3. Using Config as recommended will result in a much better experience for
you in the long run and will simplify cog creation and maintenance.

However.

We realize that many of our cog creators have expressed disinterest in writing converters for V2 to V3 style data.
As a result we have opened up config to take standard V2 data and allow cog developers to manipulate it in V3 in
much the same way they would in V2. The following examples will demonstrate how to accomplish this.

.. warning::

    By following this method to use V2 data in V3 you may be at risk of data corruption if your cog is used on a bot
    with multiple shards. USE AT YOUR OWN RISK.

.. code-block:: python

    from redbot.core import Config, commands


    class ExampleCog(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, 1234567890)
            self.config.init_custom("V2", 1)
            self.data = {}

        async def load_data(self):
            self.data = await self.config.custom("V2", "V2").all()

        async def save_data(self):
            await self.config.custom("V2", "V2").set(self.data)


    async def setup(bot):
        cog = ExampleCog()
        await cog.load_data()
        await bot.add_cog(cog)

----
Bank
----

Bank in V3 has been split out from Economy. V3 introduces the ability
to have a global bank as well as the ability to change the bank name
and the name of the currency. Be sure to checkout :doc:`/framework_bank`
for more on Bank

-------
Mod Log
-------

V3 introduces Mod Log as an API, thus allowing for cogs to add custom case
types that will appear in a server's mod log channel. Be sure to checkout
:doc:`/framework_modlog` for more on Mod Log` 
