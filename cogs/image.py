from discord.ext import commands
from random import randint
import aiohttp
import random
try:
    from imgurpython import ImgurClient
except:
    ImgurClient = False

CLIENT_ID = "1fd3ef04daf8cab"
CLIENT_SECRET = "f963e574e8e3c17993c933af4f0522e1dc01e230"


class Image:
    """Image related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.imgurclient = ImgurClient(CLIENT_ID, CLIENT_SECRET)

    @commands.group(no_pm=True, pass_context=True)
    async def imgur(self, ctx):
        """Retrieves a picture from imgur

        imgur search [keyword] - Retrieves first hit of search query.
        imgur [subreddit section] [top or new] - Retrieves top 3 hottest or
                        latest pictures of today for given a subreddit
                        section, e.g. 'funny'."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @imgur.command(pass_context=True, name="random")
    async def imgur_random(self, ctx):
        """Retrieves a random image from Imgur"""
        rand = randint(0, 59)  # 60 results per generated page
        items = self.imgurclient.gallery_random(page=0)
        await self.bot.say(items[rand].link)

    @imgur.command(pass_context=True, name="search")
    async def imgur_search(self, ctx, *, term: str):
        """Searches Imgur for the specified term"""
        items =\
            self.imgurclient.gallery_search(term, advanced=None, sort='time',
                                            window='all', page=0)
        if len(items) < 1:
            await self.bot.say("Your search terms gave no results.")
        else:
            await self.bot.say(items[0].link)

    @imgur.command(pass_context=True, name="subreddit")
    async def imgur_subreddit(self, ctx, subreddit: str, sort_type: str):
        """Gets images from the specified subreddit section"""
        if sort_type.lower() == "top" or sort_type.lower() == "new":
            if sort_type.lower() == "new":
                imgSort = "time"
            elif sort_type.lower() == "top":
                imgSort = "top"
            # Find the time window with the most images (at least 3)
            windowList = ['day', 'week', 'month', 'year', 'all']
            for x in windowList:
                items =\
                    self.imgurclient.subreddit_gallery(subreddit, sort=imgSort,
                                                       window=x, page=0)
                if (len(items) < 3):
                    continue
                else:
                    for i in range(0, 3):
                        itemTitle = items[i].title
                        if items[i].animated:
                            itemLink = items[i].gifv
                        else:
                            itemLink = items[i].link
                        await self.bot.say("{}\n{}\n".format(itemTitle,
                                                             itemLink))
                    break
            else:
                await self.bot.say("\"{}\" either does not exist or does not" +
                                   " have enough content!".format(subreddit))
        else:
            await self.bot.say("Only top or new is a valid subcommand.")
            return

    @commands.command(no_pm=True)
    async def gif(self, *text):
        """Retrieves first search result from giphy

        gif [keyword]"""
        if len(text) > 0:
            if len(text[0]) > 1 and len(text[0]) < 20:
                try:
                    msg = "+".join(text)
                    search = "http://api.giphy.com/v1/gifs/search?q=" + msg +\
                             "&api_key=dc6zaTOxFJmzC"
                    async with aiohttp.get(search) as r:
                        result = await r.json()
                    if result["data"] != []:
                        url = result["data"][0]["url"]
                        await self.bot.say(url)
                    else:
                        await\
                            self.bot.say("Your search terms gave no results.")
                except:
                    await self.bot.say("Error.")
            else:
                await self.bot.say("Invalid search.")
        else:
            await self.bot.say("gif [text]")

    @commands.command(no_pm=True, pass_context=True)
    async def gifr(self, *text):
        """Retrieves a random gif from a giphy search

        gifr [keyword]"""
        random.seed()
        if len(text) > 0:
            if len(text[0]) > 1 and len(text[0]) < 20:
                try:
                    msg = "+".join(text)
                    search = "http://api.giphy.com/v1/gifs/random" +\
                             "?&api_key=dc6zaTOxFJmzC&tag=" + msg
                    async with aiohttp.get(search) as r:
                        result = await r.json()
                        if result["data"] != []:
                            url = result["data"]["url"]
                            await self.bot.say(url)
                        else:
                            await\
                                self.bot.say("Your search terms " +
                                             "gave no results.")
                except:
                    await self.bot.say("Error.")
            else:
                await self.bot.say("Invalid search.")
        else:
            await self.bot.say("gifr [text]")


def setup(bot):
    if ImgurClient:
        bot.add_cog(Image(bot))
    else:
        raise RuntimeError("You need the imgurpython module to use this!\n"
                           "pip3 install imgurpython")
