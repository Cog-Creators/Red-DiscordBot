from random import shuffle

import aiohttp

from redbot.core.i18n import Translator
from redbot.core import checks, Config, commands

_ = Translator(__file__)

GIPHY_API_KEY = "dc6zaTOxFJmzC"


class Image(commands.Cog, translator=_):
    """Image related commands."""

    default_global = {"imgur_client_id": None}

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=2652104208, force_registration=True)
        self.settings.register_global(**self.default_global)
        self.session = aiohttp.ClientSession()
        self.imgur_base_url = "https://api.imgur.com/3/"

    def __unload(self):
        self.session.detach()

    @commands.group(name="imgur")
    async def _imgur(self, ctx):
        """Retrieve pictures from Imgur.

        Make sure to set the Client ID using `[p]imgurcreds`.
        """
        pass

    @_imgur.command(name="search")
    async def imgur_search(self, ctx, *, term: str):
        """Search Imgur for the specified term.

        Returns up to 3 results.
        """
        url = self.imgur_base_url + "gallery/search/time/all/0"
        params = {"q": term}
        imgur_client_id = await self.settings.imgur_client_id()
        if not imgur_client_id:
            await ctx.send(
                _(
                    "A Client ID has not been set! Please set one with `{prefix}imgurcreds`."
                ).format(prefix=ctx.prefix)
            )
            return
        headers = {"Authorization": "Client-ID {}".format(imgur_client_id)}
        async with self.session.get(url, headers=headers, params=params) as search_get:
            data = await search_get.json()

        if data["success"]:
            results = data["data"]
            if not results:
                await ctx.send(_("Your search returned no results."))
                return
            shuffle(results)
            msg = _("Search results...\n")
            for r in results[:3]:
                msg += r["gifv"] if "gifv" in r else r["link"]
                msg += "\n"
            await ctx.send(msg)
        else:
            await ctx.send(
                _("Something went wrong. Error code is {code}.").format(code=data["status"])
            )

    @_imgur.command(name="subreddit")
    async def imgur_subreddit(
        self, ctx, subreddit: str, sort_type: str = "top", window: str = "day"
    ):
        """Get images from a subreddit.

        You can customize the search with the following options:
        - `<sort_type>`: new, top
        - `<window>`: day, week, month, year, all
        """
        sort_type = sort_type.lower()
        window = window.lower()

        if sort_type == "new":
            sort = "time"
        elif sort_type == "top":
            sort = "top"
        else:
            await ctx.send(_("Only 'new' and 'top' are a valid sort type."))
            return

        if window not in ("day", "week", "month", "year", "all"):
            await ctx.send_help()
            return

        imgur_client_id = await self.settings.imgur_client_id()
        if not imgur_client_id:
            await ctx.send(
                _(
                    "A Client ID has not been set! Please set one with `{prefix}imgurcreds`."
                ).format(prefix=ctx.prefix)
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
            await ctx.send(
                _("Something went wrong. Error code is {code}.").format(code=data["status"])
            )

    @checks.is_owner()
    @commands.command()
    async def imgurcreds(self, ctx, imgur_client_id: str):
        """Set the Imgur Client ID.

        To get an Imgur Client ID:
        1. Login to an Imgur account.
        2. Visit [this](https://api.imgur.com/oauth2/addclient) page
        3. Enter a name for your application
        4. Select *Anonymous usage without user authorization* for the auth type
        5. Set the authorization callback URL to `https://localhost`
        6. Leave the app website blank
        7. Enter a valid email address and a description
        8. Check the captcha box and click next
        9. Your Client ID will be on the next page.
        """
        await self.settings.imgur_client_id.set(imgur_client_id)
        await ctx.send(_("The Imgur Client ID has been set!"))

    @commands.guild_only()
    @commands.command()
    async def gif(self, ctx, *keywords):
        """Retrieve the first search result from Giphy."""
        if keywords:
            keywords = "+".join(keywords)
        else:
            await ctx.send_help()
            return

        url = "http://api.giphy.com/v1/gifs/search?&api_key={}&q={}".format(
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
                await ctx.send(_("Error contacting the Giphy API."))

    @commands.guild_only()
    @commands.command()
    async def gifr(self, ctx, *keywords):
        """Retrieve a random GIF from a Giphy search."""
        if keywords:
            keywords = "+".join(keywords)
        else:
            await ctx.send_help()
            return

        url = "http://api.giphy.com/v1/gifs/random?&api_key={}&tag={}".format(
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
                await ctx.send(_("Error contacting the API."))
