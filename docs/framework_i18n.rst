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
    from redbot.core.i18n import Translator, cog_i18n, set_contextual_locales_from_guild
    
    # The translator should be defined in the module scope, with __file__ as the second parameter
    _ = Translator("ExampleCog", __file__)

    # This decorator must be used for cog and command docstrings to be translated!
    @cog_i18n(_)
    class ExampleCog(commands.Cog):
        """Cog description"""
        def __init__(self, bot):
            self.bot = bot

        @commands.command()
        async def mycom(self, ctx):
            """Command description"""
            # Correct way to translate strings:
            await ctx.send(_("This is a test command run by {author}!").format(author=ctx.author.display_name))

            # !!! Do not do this - String interpolation should happen after translation
            await ctx.send(_("This is a test command run by {author}!".format(author=ctx.author.display_name)))

            # !!! Do not use f-strings - String interpolation should happen after translation
            await ctx.send(_(f"This is a test command run by {ctx.author.display_name}!"))
        
        @commands.Cog.listener()
        async def on_message(self, message):
            # In non-command locations, you must manually call this method for guild locale settings to apply
            await set_contextual_locales_from_guild(self.bot, message.guild)
            if message.author.bot:
                return
            await message.channel.send(_("This is a non command with translation support!"))

--------
Tutorial
--------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Preparing your cog for translations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first step to adding translations to your cog is to add Red's internationalization framework
to the strings in your cog. The first step is to instantiate an instance of
`redbot.core.i18n.Translator` just after the imports in each file. This object is traditionally 
stored in the variable ``_`` to reduce its character count and visual impact on the code. Next,
add the `redbot.core.i18n.cog_i18n` decorator to your cog class. This will allow docstrings of
the class and its commands to be translated. Every user-facing string that is not a docstring
should then be wrapped by the Translator object. If variables are included in a string,
``.format()`` must be used, and should be called after the translation function call. This is
because ``.format()`` within the translation function call and f-strings cause the interpolation
to happen **before** the translation is applied. The translation logic needs to match the template
string to translate it, and will be unable to successfully match after interpolation occurs.
Finally, any non-command portions of your code, including listeners, tasks, and views, should call
`redbot.core.i18n.set_contextual_locales_from_guild` prior to translating any strings, as only
commands are able to implicitly determine which guild's configured locale to use. See the example
above for the exact recommended syntax.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Generating a messages.pot file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A ``messages.pot`` file is a template for translating all of the strings in your cog. It should
be generated using ``redgettext`` - a modified version of ``pygettext`` for use with Red cogs.
You can install ``redgettext`` by running :code:`pip install redgettext` in your development
environment.

Once you have ``redgettext`` installed, you will now need to run

:code:`python -m redgettext -c [path_to_cog_folder]`

This will generate a ``messages.pot`` file in ``path_to_cog_folder/locales``. This file will
contain all strings to be translated, including docstrings.

(For advanced usage check :code:`python -m redgettext -h`)

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Creating language specific translations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can now use a tool like `poedit
<https://poedit.net/>`_ to translate the strings in your ``messages.pot`` file.

Alternatively, you can use any text editor to manually create translations. To do this, first
create a copy of the ``messages.pot`` file in the same folder, and name the copy
``LANGUAGE-CODE.po``, where ``LANGUAGE-CODE`` is a five character language code supported by
``[p]set locale``. Open the copy in your text editor of choice. This file contains the strings
in your cog prefixed by ``msgid`` and an empty string for you to apply translations prefixed by
``msgstr``. The original string should be translated to the target language by modifying the
associated ``msgstr``. Any variables within curly braces should **not** be translated to avoid
breaking the code when translations are applied. If keyword arguments were used in ``.format()``
calls, it may be safe to re-order variables if the grammer of the language requires doing so.

-------------
API Reference
-------------

.. automodule:: redbot.core.i18n
    :members:
    :special-members: __call__, __init__
