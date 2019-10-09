.. Making cogs for V3

.. role:: python(code)
    :language: python

====================
Creating cogs for V3
====================

This guide serves as a tutorial on creating cogs for Red V3.
It will cover the basics of setting up a package for your
cog and the basics of setting up the file structure. We will
also point you towards some further resources that may assist
you in the process.

---------------
Getting started
---------------

To start off, be sure that you have installed Python 3.7.
Next, you need to decide if you want to develop against the Stable or Develop verison of Red.
Depending on what your goal is should help determine which version you need

.. attention:: 
    The Develop version may have changes on it that break compatibility with the Stable version and other cogs.
    If your goal is to support both versions, make sure you build compatibility layers or use separete branches to keep compatibility until the next Red release

Open a terminal or command prompt and type one of the following
    Stable Version: :code:`python3.7 -m pip install -U Red-DiscordBot`
    
    Develop Version: :code:`python3.7 -m pip install -U git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=Red-DiscordBot`

(Windows users may need to use :code:`py -3.7` or :code:`python` instead of :code:`python3.7`)

--------------------
Setting up a package
--------------------

To set up a package, we would just need to create a new folder.
This should be named whatever you want the cog to be named (for
the purposes of this example, we'll call this :code:`mycog`).
In this folder, create three files: :code:`__init__.py`,
:code:`mycog.py`, and :code:`info.json`. Open the folder in
a text editor or IDE (examples include `Sublime Text 3 <https://www.sublimetext.com/>`_,
`Visual Studio Code <https://code.visualstudio.com/>`_, `Atom <https://atom.io/>`_, and
`PyCharm <http://www.jetbrains.com/pycharm/>`_).

.. attention:: 
    While you can intentionally override Red's cogs/extensions, this may break things.
    We would prefer if people wanted custom behavior
    for any core cog/extension, an issue and/or PR is made
    Overriding Permissions specifically is dangerous.

    Subclassing to make changes to Red's cogs/extensions
    may not be a safe way to stay up to date either,
    as changes to cogs and their interactions with red
    are not guaranteed to not be breaking.

    Any cogs doing this are doing so at their own risk,
    and should also inform users of associated risks.

--------------
Creating a cog
--------------

With your package opened in a text editor or IDE, open :code:`mycog.py`.
In that file, place the following code:

.. code-block:: python

    from redbot.core import commands

    class Mycog(commands.Cog):
        """My custom cog"""

        @commands.command()
        async def mycom(self, ctx):
            """This does stuff!"""
            # Your code will go here
            await ctx.send("I can do stuff!")

Open :code:`__init__.py`. In that file, place the following:

.. code-block:: python

    from .mycog import Mycog

    def setup(bot):
        bot.add_cog(Mycog())

Make sure that both files are saved.

----------------
Testing your cog
----------------

To test your cog, you will need a running instance of V3.
Assuming you installed V3 as outlined above, run :code:`redbot-setup`
and provide the requested information. Once that's done, run Red
by doing :code:`redbot <instance name> --dev` to start Red.
Complete the inital setup by providing a valid token and setting a
prefix. Once the bot has started up, use the link provided in the
console to add it to a server (note that you must have the
:code:`Manage Server` (or :code:`Administrator`) permission to add bots
to a server). Once it's been added to a server, find the full path
to the directory where your cog package is located. In Discord, do
:code:`[p]addpath <path_to_folder_containing_package>`, then do
:code:`[p]load mycog`. Once the cog is loaded, do :code:`[p]mycom`
The bot should respond with :code:`I can do stuff!`. If it did, you
have successfully created a cog!

.. note:: **Package/Folder layout**
    You must make sure you structure your local path correctly or 
    you get an error about missing the setup function. As cogs are 
    considered packages, they are each contained within separate folders.
    The folder you need to add using :code:`[p]addpath` is the parent
    folder of these package folders. Below is an example

    .. code-block:: text
        - D:\
        -- red-env
        -- red-data
        -- red-cogs
        ---- mycog
        ------ __init__.py
        ------ mycog.py
        ---- coolcog
        ------ __init__.py
        ------ coolcog.py
    You would then use :code:`[p]addpath D:\red-cogs` to add the path
    and then you can use :code:`[p]load mycog` or :code:`[p]load coolcog`
    to load them

--------------------
Additional resources
--------------------

Be sure to check out the :doc:`/guide_migration` for some resources
on developing cogs for V3. This will also cover differences between V2 and V3 for
those who developed cogs for V2.
