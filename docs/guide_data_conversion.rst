.. Converting Data from a V2 cog

.. role:: python(code)
    :language: python

============================
Importing Data From a V2 Cog
============================

This guide serves as a tutorial on using the DataConverter class
to import settings from a V2 cog. 

------------------
Things you'll need
------------------

1. The path where each file holding related settings in v2 is
2. A conversion function to take the data and transform it to conform to Config

-----------------------
Getting your file paths
-----------------------

You should probably not try to find the files manually.
Asking the user for the base install path and using a relative path to where the
data should be, then testing that the file exists there is safer. This is especially
True if your cog has multiple settings files

Example

.. code-block:: python

    from discord.ext import commands
    from pathlib import Path

    @commands.command(name="filefinder")
    async def file_finding_command(self, ctx, filepath):
        """
        this finds a file based on a user provided input and a known relative path
        """

        base_path = Path(filepath)
        fp = base_path / 'data' / 'mycog' / 'settings.json'
        if not fp.is_file():
            pass
            # fail, prompting user
        else:
            pass
            # do something with the file

---------------
Converting data
---------------

Once you've gotten your v2 settings file, you'll want to be able to import it
There are a couple options available depending on how you would like to convert
the data.

The first one takes a data path, and a conversion function and does the rest for you.
This is great for simple data that just needs to quickly be imported without much
modification.


Here's an example of that in use:

.. code-block:: python

    from pathlib import Path
    from discord.ext import commands

    from redbot.core.utils.data_converter import DataConverter as dc
    from redbot.core.config import Config

    ...
            
    
        async def import_v2(self, file_path: Path):
            """
            to be called from a command limited to owner

            This should be a coroutine as the convert function will
            need to be awaited
            """

            # First we give the converter out cog's Config instance.
            converter = dc(self.config)
            
            # next we design a way to get all of the data into Config's internal
            # format. This should be a generator, but you can also return a single
            # list with identical results outside of memory usage
            def conversion_spec(v2data):
                for guild_id in v2.data.keys():
                    yield {('GUILD', guild_id): {('blacklisted',): True}}
                    # This is yielding a dictionary that is designed for config's set_raw. 
                    # The keys should be a tuple of Config scopes + the needed Identifiers. The
                    # values should be another dictionary whose keys are tuples representing
                    # config settings, the value should be the value to set for that.

            # Then we pass the file and the conversion function
            await converter.convert(file_path, conversion_spec)
            # From here, our data should be imported


You can also choose to convert all of your data and pass it as a single dict
This can be useful if you want finer control over the dataconversion or want to
preserve any data from v3 that may share the same entry and set it aside to prompt
a user

.. code-block:: python

    from pathlib import Path
    from discord.ext import commands

    from redbot.core.utils.data_converter import DataConverter as dc
    from redbot.core.config import Config

    ...

    await dc(config_instance).dict_import(some_processed_dict)


The format of the items of the dict is the same as in the above example


-----------------------------------
Config Scopes and their Identifiers
-----------------------------------

This section is provided as a quick reference for the identifiers for default
scopes available in Config. This does not cover usage of custom scopes, though the
data converter is compatible with those as well.

Global::
    :code:`('GLOBAL',)`
Guild::
    :code:`('GUILD', guild_id)`
Channel::
    :code:`('CHANNEL', channel_id)`
User::
    :code:`('USER', user_id)`
Member::
    :code:`('MEMBER', guild_id, user_id)`
Role::
    :code:`('ROLE', role_id)`


-----------------------------
More information and Examples
-----------------------------

For a more in depth look at how all of these commands function
You may want to take a look at how core data is being imported

:code:`redbot/cogs/dataconverter/core_specs.py`