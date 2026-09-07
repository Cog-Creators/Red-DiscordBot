.. V3 Shared API Key Reference

===============
Shared API Keys
===============

Red has a central API key storage utilising the core bots config. This allows cog creators to add a single location to store API keys for their cogs which may be shared between other cogs.

There needs to be some consistency between cog creators when using shared API keys between cogs. To help make this easier service should be all **lowercase** and the key names should match the naming convention of the API being accessed.

Example:

Twitch has a client ID and client secret so a user should be asked to input

``[p]set api twitch client_id,1234ksdjf client_secret,1234aldlfkd``

and when accessed in the code it should be done by 

.. code-block:: python

    await self.bot.get_shared_api_tokens("twitch")

Each service has its own dict of key, value pairs for each required key type. If there's only one key required then a name for the key is still required for storing and accessing.

Example:

``[p]set api youtube api_key,1234ksdjf``

and when accessed in the code it should be done by 

.. code-block:: python

    await self.bot.get_shared_api_tokens("youtube")


***********
Basic Usage
***********

.. code-block:: python

    class MyCog(commands.Cog):
        @commands.command()
        async def youtube(self, ctx, user: str):
            youtube_keys = await self.bot.get_shared_api_tokens("youtube")
            if youtube_keys.get("api_key") is None:
                return await ctx.send("The YouTube API key has not been set.")
            # Use the API key to access content as you normally would


**********************
Prompting for API Keys
**********************

The primary way to set keys is ``[p]set api``. Run on its own, with no service or tokens, it opens a secure modal for the owner to fill in, so a cog does not need to add its own command for this.

`SetApiView` is most useful as a fallback when a required key is missing. When a command needs a key that has not been set, a reply with the error message that includes this view will include a button that allows the owner to instantly open the secure modal. The parameters ``default_service`` and ``default_keys`` can be configured to pre-fill the modal with the service and key names the cog expects.

.. code-block:: python

    from redbot.core.utils.views import SetApiView

    class MyCog(commands.Cog):
        @commands.command()
        async def weather(self, ctx: commands.Context, *, city: str):
            tokens = await self.bot.get_shared_api_tokens("weather")
            if tokens.get("api_key") is None:
                view = SetApiView(default_service="weather", default_keys={"api_key": ""})
                await ctx.send(
                    "The weather API key has not been set. "
                    "Use the button below to set it (bot owner only).",
                    view=view,
                )
                return
            # use tokens["api_key"] as normal

``default_service`` pre-fills and locks the service name. ``default_keys`` is a mapping of the key names the service expects (values may be empty) and pre-populates the modal. The owner enters one ``key value`` pair per line, keeping the key label; for the example above the field is pre-filled with ``api_key YOUR_API_KEY``, and replacing the line with just the value is rejected. On submit the tokens are saved with `Red.set_shared_api_tokens`.

To embed the prompt in a custom `discord.ui.View`, use `SetApiModal` directly and send it with ``interaction.response.send_modal(...)``. `SetApiView` and `SetApiModal` are both owner-only.


***************
Event Reference
***************

.. function:: on_red_api_tokens_update(service_name, api_tokens)

    Dispatched when service's api keys are updated.

    :param service_name: Name of the service.
    :type service_name: :class:`str`
    :param api_tokens: New Mapping of token names to tokens. This contains api tokens that weren't changed too.
    :type api_tokens: Mapping[:class:`str`, :class:`str`]


*********************
Additional References
*********************

.. py:currentmodule:: redbot.core.bot

.. automethod:: Red.get_shared_api_tokens
    :noindex:

.. automethod:: Red.set_shared_api_tokens
    :noindex:

.. automethod:: Red.remove_shared_api_tokens
    :noindex:

.. automethod:: Red.remove_shared_api_services
    :noindex:
