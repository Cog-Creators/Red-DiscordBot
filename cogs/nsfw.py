import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import random

class Nsfw:
    """Nsfw commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def nsfw(self, ctx):
        """Nsfw commands."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help nsfw for info.")

    @nsfw.command(pass_context=True, no_pm=True)
    async def random(self, ctx, args: str):
        """Valid arguments for this command are: yandere, konachan, e621, rule34, lolibooru, danbooru, gelbooru, tbib, xbooru, furrybooru, drunkenpumken"""
        if args == 'yandere':
            try:
                query = ("https://yande.re/post/random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="highres").get("href")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'konachan':
            try:
                query = ("https://konachan.com/post/random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="highres").get("href")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'e621':
            try:
                query = ("https://e621.net/post/random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="highres").get("href")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'rule34':
            try:
                #add highres suppord
                query = ("http://rule34.xxx/index.php?page=post&s=random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="image").get("src")
                await self.bot.say('http:' + image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'lolibooru':
            try:
                query = ("https://lolibooru.moe/post/random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="highres").get("href")
                image = image.replace(" ", "+")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'danbooru':
            try:
                query = ("http://danbooru.donmai.us/posts/random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(itemprop="contentSize").get("href")
                await self.bot.say('http://danbooru.donmai.us' + image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'gelbooru':
            try:
                #fullsize
                query = ("http://www.gelbooru.com/index.php?page=post&s=random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="image").get("src")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'tbib':
            try:
                #fullsize
                query = ("http://www.tbib.org/index.php?page=post&s=random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="image").get("src")
                await self.bot.say("http:" + image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'xbooru':
            try:
                #fullsize
                query = ("http://xbooru.com/index.php?page=post&s=random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="image").get("src")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'furrybooru':
            try:
                #fullsize
                query = ("http://furry.booru.org/index.php?page=post&s=random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="image").get("src")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))
        elif args == 'drunkenpumken':
            try:
                query = ("http://drunkenpumken.booru.org/index.php?page=post&s=random")
                page = await aiohttp.get(query)
                page = await page.text()
                soup = BeautifulSoup(page, 'html.parser')
                image = soup.find(id="image").get("src")
                await self.bot.say(image)
            except Exception as e:
                await self.bot.say(":x: **Error:** `{}`".format(e))

    @nsfw.command(pass_context=True, no_pm=True)
    async def yandere(self, ctx, *tags: str):
        """Yande.re search"""
        print(tags)
        if tags == ():
            await self.bot.say(":warning: Tags are missing.")
        else:
            try:
                tags = ("+").join(tags)
                query = ("https://yande.re/post.json?limit=42&tags=" + tags)
                page = await aiohttp.get(query)
                json = await page.json()
                if json != []:
                    await self.bot.say(random.choice(json)['jpeg_url'])
                else:
                    await self.bot.say(":warning: Yande.re has no images for requested tags.")
            except Exception as e:
                await self.bot.say(":x: `{}`".format(e))

def setup(bot):
    n = Nsfw(bot)
    bot.add_cog(n)