from discord.ext import commands
from random import choice, shuffle
import aiohttp
import functools
import asyncio

try:
    from imgurpython import ImgurClient
except:
    ImgurClient = False

CLIENT_ID = "1fd3ef04daf8cab"
CLIENT_SECRET = "f963e574e8e3c17993c933af4f0522e1dc01e230"
GIPHY_API_KEY = "dc6zaTOxFJmzC"


class Image:
    """Image related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.imgur = ImgurClient(CLIENT_ID, CLIENT_SECRET)

    @commands.group(name="imgur", no_pm=True, pass_context=True)
    async def _imgur(self, ctx):
        """Retrieves pictures from imgur"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_imgur.command(pass_context=True, name="random")
    async def imgur_random(self, ctx, *, term: str=None):
        """Retrieves a random image from Imgur

        Search terms can be specified"""
        if term is None:
            task = functools.partial(self.imgur.gallery_random, page=0)
        else:
            task = functools.partial(self.imgur.gallery_search, term,
                                     advanced=None, sort='time',
                                     window='all', page=0)
        task = self.bot.loop.run_in_executor(None, task)

        try:
            results = await asyncio.wait_for(task, timeout=10)
        except asyncio.TimeoutError:
            await self.bot.say("Error: request timed out")
        else:
            if results:
                item = choice(results)
                link = item.gifv if hasattr(item, "gifv") else item.link
                await self.bot.say(link)
            else:
                await self.bot.say("Your search terms gave no results.")

    @_imgur.command(pass_context=True, name="search")
    async def imgur_search(self, ctx, *, term: str):
        """Searches Imgur for the specified term and returns up to 3 results"""
        task = functools.partial(self.imgur.gallery_search, term,
                                 advanced=None, sort='time',
                                 window='all', page=0)
        task = self.bot.loop.run_in_executor(None, task)

        try:
            results = await asyncio.wait_for(task, timeout=10)
        except asyncio.TimeoutError:
            await self.bot.say("Error: request timed out")
        else:
            if results:
                shuffle(results)
                msg = "Search results...\n"
                for r in results[:3]:
                    msg += r.gifv if hasattr(r, "gifv") else r.link
                    msg += "\n"
                await self.bot.say(msg)
            else:
                await self.bot.say("Your search terms gave no results.")

    @_imgur.command(pass_context=True, name="subreddit")
    async def imgur_subreddit(self, ctx, subreddit: str, sort_type: str="top", window: str="day"):
        """Gets images from the specified subreddit section

        Sort types: new, top
        Time windows: day, week, month, year, all"""
        sort_type = sort_type.lower()

        if sort_type not in ("new", "top"):
            await self.bot.say("Only 'new' and 'top' are a valid sort type.")
            return
        elif window not in ("day", "week", "month", "year", "all"):
            await self.bot.send_cmd_help(ctx)
            return

        if sort_type == "new":
            sort = "time"
        elif sort_type == "top":
            sort = "top"

        links = []

        task = functools.partial(self.imgur.subreddit_gallery, subreddit,
                                 sort=sort, window=window, page=0)
        task = self.bot.loop.run_in_executor(None, task)
        try:
            items = await asyncio.wait_for(task, timeout=10)
        except asyncio.TimeoutError:
            await self.bot.say("Error: request timed out")
            return

        for item in items[:3]:
            link = item.gifv if hasattr(item, "gifv") else item.link
            links.append("{}\n{}".format(item.title, link))

        if links:
            await self.bot.say("\n".join(links))
        else:
            await self.bot.say("No results found.")

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

        async with aiohttp.get(url) as r:
            result = await r.json()
            if r.status == 200:
                if result["data"]:
                    await self.bot.say(result["data"][0]["url"])
                else:
                    await self.bot.say("No results found.")
            else:
                await self.bot.say("Error contacting the API")

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

        async with aiohttp.get(url) as r:
            result = await r.json()
            if r.status == 200:
                if result["data"]:
                    await self.bot.say(result["data"]["url"])
                else:
                    await self.bot.say("No results found.")
            else:
                await self.bot.say("Error contacting the API")


def setup(bot):
    if ImgurClient is False:
        raise RuntimeError("You need the imgurpython module to use this.\n"
                           "pip3 install imgurpython")

    bot.add_cog(Image(bot))
