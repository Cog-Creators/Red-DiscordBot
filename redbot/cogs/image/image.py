from random import shuffle

import aiohttp

from redbot.core.i18n import Translator, cog_i18n
from redbot.core import checks, Config, commands

_ = Translator("Image", __file__)

GIPHY_API_KEY = "dc6zaTOxFJmzC"


@cog_i18n(_)
class Image:
    """Image related commands."""

    default_global = {"imgur_client_id": None}

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=2652104208, force_registration=True)
        self.settings.register_global(**self.default_global)
        self.session = aiohttp.ClientSession()
        self.imgur_base_url = "https://api.imgur.com/3/"

    def __unload(self):
        self.session.close()

    @commands.group(name="imgur")
    async def _imgur(self, ctx):
        """Retrieves pictures from imgur

        Make sure to set the client ID using
        [p]imgurcreds"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_imgur.command(name="search")
    async def imgur_search(self, ctx, *, term: str):
        """Searches Imgur for the specified term and returns up to 3 results"""
        url = self.imgur_base_url + "gallery/search/time/all/0"
        params = {"q": term}
        imgur_client_id = await self.settings.imgur_client_id()
        if not imgur_client_id:
            await ctx.send(
                _("A client ID has not been set! Please set one with {}").format(
                    "`{}imgurcreds`".format(ctx.prefix)
                )
            )
            return
        headers = {"Authorization": "Client-ID {}".format(imgur_client_id)}
        async with self.session.get(url, headers=headers, params=params) as search_get:
            data = await search_get.json()

        if data["success"]:
            results = data["data"]
            if not results:
                await ctx.send(_("Your search returned no results"))
                return
            shuffle(results)
            msg = _("Search results...\n")
            for r in results[:3]:
                msg += r["gifv"] if "gifv" in r else r["link"]
                msg += "\n"
            await ctx.send(msg)
        else:
            await ctx.send(_("Something went wrong. Error code is {}").format(data["status"]))

    @_imgur.command(name="subreddit")
    async def imgur_subreddit(
        self, ctx, subreddit: str, sort_type: str = "top", window: str = "day"
    ):
        """Gets images from the specified subreddit section

        Sort types: new, top
        Time windows: day, week, month, year, all"""
        sort_type = sort_type.lower()
        window = window.lower()

        if sort_type not in ("new", "top"):
            await ctx.send(_("Only 'new' and 'top' are a valid sort type."))
            return
        elif window not in ("day", "week", "month", "year", "all"):
            await ctx.send_help()
            return

        if sort_type == "new":
            sort = "time"
        elif sort_type == "top":
            sort = "top"

        imgur_client_id = await self.settings.imgur_client_id()
        if not imgur_client_id:
            await ctx.send(
                _("A client ID has not been set! Please set one with {}").format(
                    "`{}imgurcreds`".format(ctx.prefix)
                )
            )
            return

        links = []
        headers = {"Authorization": "Client-ID {}".format(imgur_client_id)}
        url = self.imgur_base_url + "gallery/r/{}/{}/{}/0".format(subreddit, sort, window)

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
                await ctx.send(_("No results found."))
        else:
            await ctx.send(_("Something went wrong. Error code is {}").format(data["status"]))

    @checks.is_owner()
    @commands.command()
    async def imgurcreds(self, ctx, imgur_client_id: str):
        """Sets the imgur client id
        You will need an account on Imgur to get this

        You can get these by visiting https://api.imgur.com/oauth2/addclient
        and filling out the form. Enter a name for the application, select
        'Anonymous usage without user authorization' for the auth type,
        set the authorization callback url to 'https://localhost'
        leave the app website blank, enter a valid email address, and
        enter a description. Check the box for the captcha, then click Next.
        Your client ID will be on the page that loads"""
        await self.settings.imgur_client_id.set(imgur_client_id)
        await ctx.send(_("Set the imgur client id!"))

    @commands.command(pass_context=True, no_pm=True)
    async def gif(self, ctx, *keywords):
        """Retrieves first search result from giphy"""
        if keywords:
            keywords = "+".join(keywords)
        else:
            await ctx.send_help()
            return

        url = "http://api.giphy.com/v1/gifs/search?&api_key={}&q={}" "".format(
            GIPHY_API_KEY, keywords
        )

        async with self.session.get(url) as r:
            result = await r.json()
            if r.status == 200:
                if result["data"]:
                    await ctx.send(result["data"][0]["url"])
                else:
                    await ctx.send(_("No results found."))
            else:
                await ctx.send(_("Error contacting the API"))

    @commands.command(pass_context=True, no_pm=True)
    async def gifr(self, ctx, *keywords):
        """Retrieves a random gif from a giphy search"""
        if keywords:
            keywords = "+".join(keywords)
        else:
            await ctx.send_help()
            return

        url = "http://api.giphy.com/v1/gifs/random?&api_key={}&tag={}" "".format(
            GIPHY_API_KEY, keywords
        )

        async with self.session.get(url) as r:
            result = await r.json()
            if r.status == 200:
                if result["data"]:
                    await ctx.send(result["data"]["url"])
                else:
                    await ctx.send(_("No results found."))
            else:
                await ctx.send(_("Error contacting the API"))
