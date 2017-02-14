from discord.ext import commands
from random import choice
import aiohttp
import re
import urllib


class AdvancedGoogle:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="advgoogle", pass_context=True, no_pm=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def _advgoogle(self, ctx, text):
        """Its google, you search with it.
        Example: google A magical pug

        Special search options are available; Image, Images, Maps
        Example: google image You know, for kids! > Returns first image
        Another example: google maps New York
        Another example: google images cats > Returns a random image
        based on the query
        LEGACY EDITION! SEE HERE!
        https://twentysix26.github.io/Red-Docs/red_cog_approved_repos/#refactored-cogs

        Originally made by Kowlin https://github.com/Kowlin/refactored-cogs
        edited by Aioxas"""
        search_type = ctx.message.content[len(ctx.prefix+ctx.command.name)+1:].lower().split(" ")
        option = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
        }
        regex = [
            re.compile(",\"ou\":\"([^`]*?)\""),
            re.compile("<h3 class=\"r\"><a href=\"\/url\?url=([^`]*?)&amp;"),
            re.compile("<h3 class=\"r\"><a href=\"([^`]*?)\""),
            re.compile("\/url?url=")
            ]
        search_valid = str(ctx.message.content
                           [len(ctx.prefix+ctx.command.name)+1:].lower())
        # Start of Image
        if search_type[0] == "image" or search_type[0] == "images":
            if search_valid == "image" or search_valid == "images":
                await self.bot.say("Please actually search something")
            else:
                if search_type[0] == "image":
                    url, error = await self.images(ctx, regex, option)
                elif search_type[0] == "images":
                    url, error = await self.images(ctx, regex, option, images=True)
                if url and not error:
                    await self.bot.say(url)
                elif error:
                    await self.bot.say("Your search yielded no results.")
            # End of Image
        # Start of Maps
        elif search_type[0] == "maps":
            if search_valid == "maps":
                await self.bot.say("Please actually search something")
            else:
                uri = "https://www.google.com/maps/search/"
                quary = str(ctx.message.content
                            [len(ctx.prefix+ctx.command.name)+6:].lower())
                encode = urllib.parse.quote_plus(quary, encoding='utf-8',
                                                 errors='replace')
                uir = uri+encode
                await self.bot.say(uir)
            # End of Maps
        # Start of generic search
        else:
            uri = "https://www.google.com/search?hl=en&q="
            quary = str(ctx.message.content
                        [len(ctx.prefix+ctx.command.name)+1:])
            encode = urllib.parse.quote_plus(quary, encoding='utf-8',
                                             errors='replace')
            uir = uri+encode
            async with aiohttp.get(uir, headers=option) as resp:
                test = str(await resp.content.read())
                query_find = regex[1].findall(test)
                if not query_find:
                    query_find = regex[2].findall(test)
                    try:
                        query_find = self.parsed(query_find, regex)
                        await self.bot.say("{}".format("\n".join(query_find)))
                    except IndexError:
                        await self.bot.say("Your search yielded no results.")
                elif regex[3].search(query_find[0]):
                        query_find = self.parsed(query_find, regex)
                        await self.bot.say("{}".format("\n".join(query_find)))
                else:
                    query_find = self.parsed(query_find, regex, found=False)
                    await self.bot.say("{}".format("\n".join(query_find)))

            # End of generic search

    async def images(self, ctx, regex, option, images: bool=False):
        uri = "https://www.google.com/search?hl=en&tbm=isch&tbs=isz:m&q="
        num = 7
        if images:
            num = 8
        quary = str(ctx.message.content
                    [len(ctx.prefix+ctx.command.name)+num:].lower())
        print(quary)
        encode = urllib.parse.quote_plus(quary, encoding='utf-8',
                                         errors='replace')
        uir = uri+encode
        url = None
        async with aiohttp.get(uir, headers=option) as resp:
            test = await resp.content.read()
            unicoded = test.decode("unicode_escape")
            query_find = regex[0].findall(unicoded)
            try:
                if images:
                    url = choice(query_find)
                elif not images:
                    url = query_find[0]
                error = False
            except IndexError:
                error = True
        return url, error

    def parsed(self, find, regex, found: bool=True):
        find = find[:5]
        if found:
            for r in find:
                if regex[3].search(r):
                    m = regex[3].search(r)
                    r = r[:m.start()]
                    + r[m.end():]
                    r = self.unescape(r)
                else:
                    r = self.unescape(r)
        elif not found:
            for r in find:
                r = self.unescape(r)
        for i in range(len(find)):
            if i == 0:
                find[i] = find[i] + "\n\n**You might also want to check these out:**"
            else:
                find[i] = "<{}>".format(find[i])
        return find

    def unescape(self, msg):
        regex = ["<br \/>", "(?:\\\\[rn])", "(?:\\\\['])", "%25", "\(", "\)"]
        subs = ["\n", "", "'", "%", "%28", "%29"]
        for i in range(len(regex)):
            sub = re.sub(regex[i], subs[i], msg)
            msg = sub
        return msg


def setup(bot):
    n = AdvancedGoogle(bot)
    bot.add_cog(n)
