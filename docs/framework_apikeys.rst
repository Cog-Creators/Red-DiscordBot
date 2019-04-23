.. V3 Shared API Key Reference

===============
Shared API Keys
===============

Red has a central API key storage utilising the core bots config. This allows cog creators to add a single location to store API keys for their cogs which may be shared between other cogs.

There needs to be some consistency between cog creators when using shared API keys between cogs. To help make this easier service should be all **lowercase** and the key names should match the naming convetion of the API being accessed. 

Example:

Twitch has a client ID and client secret so a user should be asked to input

``[p]set api twitch client_id,1234ksdjf client_secret,1234aldlfkd``

and when accessed in the code it should be done by 

.. code-block:: python

    await self.bot.db.api_tokens.get_raw("twitch", default={"client_id": None, "client_secret: None"})

Each service has its own dict of key, value pairs for each required key type. If there's only one key required then a name for the key is still required for storing and accessing.

Example:

``[p]set api youtube api_key,1234ksdjf``

and when accessed in the code it should be done by 

.. code-block:: python

    await self.bot.db.api_tokens.get_raw("youtube", default={"api_key": None})


***********
Basic Usage
***********

.. code-block:: python

    class MyCog:
        @commands.command()
        async def youtube(self, ctx, user: str):
            apikey = await self.bot.db.api_tokens.get_raw("youtube", default={"api_key": None})
            if apikey["api_key"] is None:
                return await ctx.send("The YouTube API key has not been set.")
            # Use the API key to access content as you normally would
