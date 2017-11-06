.. i18n framework reference

.. role:: python(code)
    :language: python

==============================
Internationalization Framework
==============================

-----------
Basic Usage
-----------

.. code-block:: python

    from discord.ext import commands
    from redbot.core.i18n import CogI18n
    
    _ = CogI18n("ExampleCog", __file__)

    class ExampleCog:
        """description"""

        @commands.command()
        async def mycom(self, ctx):
            """command description"""
            await ctx.send(_("This is a test command"))

--------
Tutorial
--------

After making your cog, generate a :code:`messages.pot` file

The process of generating this will depend on the operating system
you are using

In a command prompt in your cog's package (where yourcog.py is),
create a directory called "locales".
Then do one of the following:

Windows: :code:`python <your python install path>\Tools\i18n\pygettext.py -n -p locales`

Mac: ?

Linux: :code:`pygettext3 -n -p locales`

This will generate a messages.pot file with strings to be translated

-------------
API Reference
-------------

.. automodule:: redbot.core.i18n