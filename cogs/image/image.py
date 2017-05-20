from discord.ext import commands
from random import shuffle
import aiohttp
from core.utils.helpers import JsonDB
from core import checks

CLIENT_ID = "1fd3ef04daf8cab"
CLIENT_SECRET = "f963e574e8e3c17993c933af4f0522e1dc01e230"
GIPHY_API_KEY = "dc6zaTOxFJmzC"


class Image:
    """Image related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = JsonDB("data/settings.json")
        self.session = aiohttp.ClientSession()
        self.imgur_base_url = "https://api.imgur.com/3/"

    @commands.group(name="imgur")
    @commands.guild_only()
    async def _imgur(self, ctx):
        """Retrieves pictures from imgur"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_imgur.command(name="search")
    async def imgur_search(self, ctx, *, term: str):
        """Searches Imgur for the specified term and returns up to 3 results"""
        url = self.imgur_base_url + "time/all/0"
        params = {"q": term}
        headers = {"Authorization": "Client-ID {}".format(self.settings.get("imgur_client_id"))}
        async with self.session.get(url, headers=headers, data=params) as search_get:
            data = await search_get.json()

        if data["success"]:
            results = data["data"]
            if not results:
                await ctx.send("Your search returned no results")
                return
            shuffle(results)
            msg = "Search results...\n"
            for r in results[:3]:
                msg += r["gifv"] if "gifv" in r else r["link"]
                msg += "\n"
            await ctx.send(msg)
        else:
            await ctx.send("Something went wrong. Error code is {}".format(data["status"]))

    @_imgur.command(name="subreddit")
    async def imgur_subreddit(self, ctx, subreddit: str, sort_type: str="top", window: str="day"):
        """Gets images from the specified subreddit section

        Sort types: new, top
        Time windows: day, week, month, year, all"""
        sort_type = sort_type.lower()
        window = window.lower()

        if sort_type not in ("new", "top"):
            await ctx.send("Only 'new' and 'top' are a valid sort type.")
            return
        elif window not in ("day", "week", "month", "year", "all"):
            await self.bot.send_cmd_help(ctx)
            return

        if sort_type == "new":
            sort = "time"
        elif sort_type == "top":
            sort = "top"

        links = []
        headers = {"Authorization": "Client-ID {}".format(self.settings.get("imgur_client_id"))}
        url = self.imgur_base_url + "r/{}/{}/{}/0".format(subreddit, sort, window)

        async with self.session.get(url, headers=headers) as sub_get:
            data = await sub_get.json()

        if data["success"]:
            items = data["data"]
            if items:
                for item in items[:3]:
                    link = item["gifv"] if "gifv" in item else item["link"]
                    links.append("{}\n{}".format(item["title"], link))

                if links:
                    await ctx.send("\n".join(links))
            else:
                await ctx.send("No results found.")
        else:
            await ctx.send("Something went wrong. Error code is {}".format(data["status"]))

    @checks.is_owner()
    @commands.command()
    async def imgurclientid(self, ctx, imgur_client_id: str):
        """Sets the imgur client id"""
        await self.settings.set("imgur_client_id", imgur_client_id)
        await ctx.send("Set the imgur client id!")

    @commands.command(pass_context=True, no_pm=True)
    async def gif(self, ctx, *keywords):
        """Retrieves first search result from giphy"""
        if keywords:
            keywords = "+".join(keywords)
        else:
            await self.bot.send_cmd_help(ctx)
            return

        url = ("http://api.giphy.com/v1/gifs/search?&api_key={}&q={}"
               "".format(GIPHY_API_KEY, keywords))

        async with self.session.get(url) as r:
            result = await r.json()
            if r.status == 200:
                if result["data"]:
                    await ctx.send(result["data"][0]["url"])
                else:
                    await ctx.send("No results found.")
            else:
                await ctx.send("Error contacting the API")

    @commands.command(pass_context=True, no_pm=True)
    async def gifr(self, ctx, *keywords):
        """Retrieves a random gif from a giphy search"""
        if keywords:
            keywords = "+".join(keywords)
        else:
            await self.bot.send_cmd_help(ctx)
            return

        url = ("http://api.giphy.com/v1/gifs/random?&api_key={}&tag={}"
               "".format(GIPHY_API_KEY, keywords))

        async with self.session.get(url) as r:
            result = await r.json()
            if r.status == 200:
                if result["data"]:
                    await ctx.send(result["data"]["url"])
                else:
                    await ctx.send("No results found.")
            else:
                await ctx.send("Error contacting the API")

    async def set_keys(self):
        if not self.settings.get("giphy_key"):
            await self.settings.set("giphy_key", GIPHY_API_KEY)
        if not self.settings.get("imgur_client_id"):
            await self.settings.set("imgur_client_id", CLIENT_ID)

