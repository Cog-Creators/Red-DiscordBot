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

To start off, be sure that you have installed Python 3.6.2 or higher. Open a terminal or command prompt and type
:code:`pip install --process-dependency-links -U git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=redbot[test]`
(note that if you get an error with this, try again but put :code:`python -m` in front of the command
This will install the latest version of V3.

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

--------------
Creating a cog
--------------

With your package opened in a text editor or IDE, open :code:`mycog.py`.
In that file, place the following code:

.. code-block:: python

    from discord.ext import commands

    class Mycog:
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

--------------------
Additional resources
--------------------

Be sure to check out the :doc:`/guide_migration` for some resources
on developing cogs for V3. This will also cover differences between V2 and V3 for
those who developed cogs for V2.
