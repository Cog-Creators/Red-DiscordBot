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

    from redbot.core import commands
    from redbot.core.i18n import Translator, cog_i18n
    
    _ = Translator("ExampleCog", __file__)

    @cog_i18n(_)
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

We recommend using redgettext - a modified version of pygettext for Red.
You can install redgettext by running :code:`pip install redgettext` in a command prompt.

To generate the :code:`messages.pot` file, you will now need to run
:code:`python -m redgettext -c [path_to_cog]`
This file will contain all strings to be translated, including
docstrings.
(For advanced usage check :code:`python -m redgettext -h`)

You can now use a tool like `poedit
<https://poedit.net/>`_ to translate the strings in your messages.pot file.

-------------
API Reference
-------------

.. automodule:: redbot.core.i18n
    :members:
    :special-members: __call__
