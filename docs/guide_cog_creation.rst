.. Making cogs for V3

.. role:: python(code)
    :language: python

========================
Creating cogs for Red V3
========================

This guide serves as a tutorial on creating cogs for Red V3.
It will cover the basics of setting up a package for your
cog and the basics of setting up the file structure. We will
also point you towards some further resources that may assist
you in the process.

---------------
Getting started
---------------

To start off, be sure that you have installed Python 3.8.
Next, you need to decide if you want to develop against the Stable or Develop version of Red.
Depending on what your goal is should help determine which version you need.

.. attention::
    The Develop version may have changes on it which break compatibility with the Stable version and other cogs.
    If your goal is to support both versions, make sure you build compatibility layers or use separate branches to keep compatibility until the next Red release

Open a terminal or command prompt and type one of the following
    Stable Version: :code:`python3.8 -m pip install -U Red-DiscordBot`

.. note::

  To install the development version, replace ``Red-DiscordBot`` in the above commands with the
  link below. **The development version of the bot contains experimental changes. It is not
  intended for normal users.** We will not support anyone using the development version in any
  support channels. Using the development version may break third party cogs and not all core
  commands may work. Downgrading to stable after installing the development version may cause
  data loss, crashes or worse. Please keep this in mind when using the development version
  while working on cog creation.

  .. code-block:: none

      git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=Red-DiscordBot


(Windows users may need to use :code:`py -3.8` or :code:`python` instead of :code:`python3.8`)

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
Complete the initial setup by providing a valid token and setting a
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

    .. code-block:: none

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
    
    You can also take a look at `our cookiecutter <https://github.com/Cog-Creators/cog-cookiecutter>`_, for help creating the right structure.

-------------------
Publishing your cog
-------------------

Go to :doc:`/guide_publish_cogs`

--------------------
Additional resources
--------------------

Be sure to check out the :doc:`/guide_migration` for some resources
on developing cogs for V3. This will also cover differences between V2 and V3 for
those who developed cogs for V2.


.. _guidelines-for-cog-creators:

---------------------------
Guidelines for Cog Creators
---------------------------

The following are a list of guidelines Cog Creators should strive to follow.
Not all of these are strict requirements (some are) but are all generally advisable.

1. Cogs should follow a few naming conventions for consistency.

  - Cog classes should be TitleCased, using alphabetic characters only.
  - Commands should be lower case, using alphanumeric characters only.
  - Cog modules should be lower case, using alphabetic characters only.

2. Cogs and commands should have docstrings suitable for use in help output.

  - This one is slightly flexible if using other methods of setting help.

3. Don't prevent normal operation of the bot without the user opting into this.

  - This includes as a side effect by blocking the event loop.

4. If your cog uses logging:

  - The namespace for logging should be: ``red.your_repo_name.cog_name``.
  - Print statements are not a substitute for proper logging.

5. If you use asyncio.create_task, your tasks need to:

  - Be cancelled on cog unload.
  - Handle errors.

6. Event listeners should exit early if it is an event you don't need.
   This makes your events less expensive in terms of CPU time. Examples below:

  - Checking that you are in a guild before interacting with config for an antispam command.
  - Checking that you aren't reacting to a bot message (``not message.author.bot``) early on.

7. Use .gitignore (or something else) to keep unwanted files out of your cog repo.
8. Put a license on your cog repo.

  - By default, in most jurisdictions, without a license that at least offers the code for use,
    users cannot legally use your code.

9. Use botwide features when they apply. Some examples of this:

  - ``ctx.embed_color``
  - ``bot.is_automod_immune``

10. Use checks to limit command use when the bot needs special permissions.
11. Check against user input before doing things. Common things to check:

  - Resulting output is safe.
  - Values provided make sense. (eg. no negative numbers for payday)
  - Don't unsafely use user input for things like database input.

12. Don't abuse bot internals.

  - If you need access to something, ask us or open an issue.
  - If you're sure the current usage is safe, document why,
    but we'd prefer you work with us on ensuring you have access to what you need.

13. Update your cogs for breakage.

  - We announce this in advance.
  - If you need help, ask.

14. Check events against `bot.cog_disabled_in_guild() <RedBase.cog_disabled_in_guild()>`

  - Not all events need to be checked, only those that interact with a guild.
  - Some discretion may apply, for example,
    a cog which logs command invocation errors could choose to ignore this
    but a cog which takes actions based on messages should not.

15. Respect settings when treating non command messages as commands.

16. Handle user data responsibly

  - Don't do unexpected things with user data.
  - Don't expose user data to additional audiences without permission.
  - Don't collect data your cogs don't need.
  - Don't store data in unexpected locations.
    Utilize the cog data path, Config, or if you need something more
    prompt the owner to provide it.

17. Utilize the data deletion and statement APIs

  - See `redbot.core.commands.Cog.red_delete_data_for_user`
  - Make a statement about what data your cogs use with the module level
    variable ``__red_end_user_data_statement__``.
    This should be a string containing a user friendly explanation of what data
    your cog stores and why.
