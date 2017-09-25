# Anime cog for Red-DiscordBot by Twentysix, an
#  open-source discord bot (github.com/Cog-Creators/Red-DiscordBot)
# Authored by Swann (github.com/swannobi)
# Last updated Sept 25, 2017

import discord
from discord.ext import commands
import aiohttp
import sys
import random
from __main__ import send_cmd_help
from .utils.async import Route
from .utils.sync import ResponseError

### Globals ###
API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJTSjQzMnY2Y1oiLCJ0b2tlbklkIjoiUzFQTlR3cDViIiwiaWF0IjoxNTA1NzUwMzE4fQ.YUbO3VqsULq6oql7WO0SE-raZ49sEjVVP1rnUsLt6C6OY8_Lo_1h2-EgMwpPnRv7M5om-6MLDrfSpleBijWAJBkxu79bRThJ4pg3EZLd0Vq8v10Z0PLFWIemAp46n-MJQ1fRl8TQJ0bsRvwHUJxJZoJfrNlzm7chg93Ws29umkmH3Cy0nOVDwRcga-4cA6sjCUMAXKqPVPC20FNZ0EwzQwcOHkxkRkW5-C7QmVmYnoaFowCnvSKWhOa6VXWzZlWqqfNF-EV8d4YR6zWRG7gJ1B5TmorGnk5tgEKSGBuGlBNS5OukRC2L1QauL98wNF3AOdEttxE156jJQ7aOvnwIhw"
# This list intentionally left blank.
TYPES=[]

class Anime:
    """Responsible for requesting the weeb.sh API to serve anime reaction images."""

    def __init__(self, bot):
        self.bot = bot
        # Weeb.sh
        self.api_url = "https://api.weeb.sh/"
        self.cdn_url = "https://cdn.weeb.sh/"
        self.base_uri = "images/"
        self.tags_uri = "images/tags"
        self.types_uri = "images/types"
        self.random_uri = "images/random"
        # Request headers
        # If you don't have an auth key, get one from Wolke!
        self.headers = {"Authorization":"Bearer "+API_KEY,"Content-Type":"application/json"}
        # Dynmically load valid types when cog is loaded
        self.types = self._get(self.api_url, self.types_uri, self.headers).sync_query()["types"]
        self.nsfw_types = self._get(self.api_url, self.types_uri+"?nsfw=true", self.headers).sync_query()["types"]
        # Workaround. self attributes are outside the scope 
        #  of the discord.ext.commands decorator.
        TYPES.extend(self.types)
        # Set the tags; TODO currently unused.
        self.tags = self._get(self.api_url, self.tags_uri, self.headers).sync_query()["tags"]
        self.nsfw_tags = self._get(self.api_url, self.tags_uri+"?nsfw=true", self.headers).sync_query()["tags"]
        # Get the current API information as of the time this cog was loaded.
        self.info = self._get(self.api_url, self.base_uri, self.headers).sync_query()

    # Inner method to create the request object. Invoke it with .sync_query()
    def _get(self, api, uri, http_headers):
        return Route(base_url=api,path=uri,headers=http_headers)

    # Responsible for invoking the request object and creating an Embed to post in the channel.
    # Uses embed.description instead of embed.title because apparently titles don't get 
    #  evaluated/cleaned up. In a title you get <@123123123123> instead of @Swann. ¯\_(-_-)_/¯
    async def anime(self, imgtype, nsfw="false", random=False, description=""):
        """Posts an anime reaction image"""
        # Will fail silently if the user tries to invoke an invalid image type.
        if imgtype not in self.types:
            return
        path = self.random_uri + "?type=" + imgtype + "&nsfw=" + nsfw
        try:
            result = self._get(self.api_url, path, self.headers).sync_query()
            data = discord.Embed()
            if description != "":
                data.description = description 
            if random:
                data.title = "Randomly chose: "+imgtype
            data.set_image(url=result["url"])
            data.set_footer(text="Powered by Wolfe's weeb.sh")
            await self.bot.say(embed=data)
        # Fails silently & dumps to console whenever the query returns a non-200-level http code.
        except ResponseError as err:
            print("Query failed :(")
            print(err)
        # Fails loudly if the bot lacks the proper permissions.
        except discord.HTTPException:
            await self.bot.say("[sad awoo~] I need the embed links permission :(")

    @commands.command(pass_context=True, aliases=TYPES)
    async def image(self, ctx, *, text : str=None):
        """Posts a random anime reaction image macro, typed according to the alias."""
        category = ctx.message.content.replace("~","").split(" ")[0]
        # Posts the command help message if this was invoked without a type.
        if category == "image":
            send_cmd_help(ctx)
            return
        # NSFW images are enabled in NSFW channels.
        # TODO once discord.py is updated, use Channel.is_nsfw().
        if ctx.message.channel.name == "nsfw":
            await self.anime( category, description=text, nsfw="true" )
        else:
            await self.anime( category, description=text )

    # Calls the core anime() function with a random type.
    @commands.command(pass_context=True)
    async def random(self, ctx, *, text : str=None):
        """Picks a random image from a random category (SFW).""" 
        await self.anime( random.choice(self.types), random=True, description=text )

    @commands.command(pass_context=False)
    async def info(self):
        """Posts the weeb.sh gateway info."""
        await self.bot.say(self.info)

def setup(bot):
    bot.add_cog(Anime(bot))

