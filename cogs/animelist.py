# Developed by Redjumpman for Twentysix26's Redbot.
# Ported from mee6bot to work for Red
# Original credit and design goes to mee6
import aiohttp
import html
import os
import random
import re
from xml.etree import ElementTree as ET

import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from cogs.utils import checks
from __main__ import send_cmd_help

# Username and Password is obtained from myanime list website
# You need to create an account there and input the information below

switcher = ['english', 'score', 'type', 'episodes', 'volumes', 'chapters', 'status', 'type',
            'start_date', 'end_date']


class AnimeList:
    """Fetch info about an anime title"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/animelist/credentials.json"
        self.credentials = dataIO.load_json(self.file_path)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def animeset(self, ctx):
        """Sets your username and password from myanimelist"""
        await self.owner_set(ctx)

    @commands.command(pass_context=True, no_pm=True)
    async def anime(self, ctx, *, title):
        """Shows MAL information on an anime"""
        cmd = "anime"
        await self.search_command(ctx, cmd, title)

    @commands.command(pass_context=True, no_pm=True)
    async def manga(self, ctx, *, title):
        """Shows MAL information on a manga"""
        cmd = "manga"
        await self.search_command(ctx, cmd, title)

    @commands.group(pass_context=True)
    async def mal(self, ctx):
        """MAL Search Commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @mal.command(name="anime", pass_context=True)
    async def _anime_mal(self, ctx, user: discord.Member=None):
        """Lookup another user's MAL for anime"""
        author = ctx.message.author
        cmd = "anime"
        if not user:
            user = author
        await self.fetch_profile(user, author, cmd)

    @mal.command(name="manga", pass_context=True)
    async def _manga_mal(self, ctx, user: discord.Member=None):
        """Lookup another user's MAL for manga"""
        author = ctx.message.author
        cmd = "manga"
        if not user:
            user = author
        await self.fetch_profile(user, author, cmd)

    @mal.command(name="set", pass_context=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def _set_mal(self, ctx, username):
        """Set your MAL username
        You can change your username once every 30 seconds.
        """
        author = ctx.message.author
        if "Users" not in self.credentials:
            self.credentials["Users"] = {}

        self.credentials["Users"][author.id] = username
        dataIO.save_json(self.file_path, self.credentials)
        await self.bot.say("Your MAL is now set to {}".format(username))

    async def search_command(self, ctx, cmd, title):
        if self.verify_credentials():
            await self.fetch_info(ctx, cmd, title)
        else:
            await self.bot.say("The bot owner has not setup their credentials. "
                               "An account on <https://myanimelist.net> is required. "
                               "When the owner is ready, setup this cog with {}animeset "
                               "to enter the credentials".format(ctx.prefix))

    async def fetch_profile(self, user, author, cmd):
        user_name = self.name_lookup(user)
        author_name = self.name_lookup(author)

        url = "https://myanimelist.net/malappinfo.php?u={}&status=all&type=" + cmd
        user_col, user_data = await self.fetch_user_mal(user_name, url, cmd)
        if not user_col:
            return await self.bot.say("I couldn't find a profile with that name.")
        if user == author:
            author_col = "SELF"
        else:
            author_col, _ = await self.fetch_user_mal(author_name, url, cmd)

        await self.send_profile(user, author_col, user_col, user_data, user_name, url, cmd)

    async def send_profile(self, user, author_col, user_col, user_data, user_name, url, cmd):

        if author_col == "SELF":
            share = ['Not Applicable']
            different = ['Not Applicable']
        elif author_col:
            intersect = user_col.intersection(author_col)
            difference = author_col.difference(user_col)
            share = random.sample(intersect, len(intersect) if len(intersect) < 5 else 5)
            if not share:
                share = ["Nothing Mutual"]
            different = random.sample(difference, len(difference) if len(difference) < 5 else 5)
            if not different:
                different = ["Nothing different"]
        else:
            share = ["Author's MAL not set"]
            different = ["Author's MAL not set"]

        if cmd == "anime":
            medium = "Watching"
            emojis = [":film_frames:", ":vhs:", ":octagonal_sign:"]
        else:
            medium = "Reading"
            emojis = [":book:", ":books:", ":bookmark:"]

        link = "https://myanimelist.net/animelist/{}".format(user_name)
        description = ("**{}**\n[{}]({})\nTotal {}: "
                       "{}".format(user.name, user_name, link, cmd.title(), len(user_col)))
        embed = discord.Embed(colour=0x0066FF, description=description)
        embed.title = "My Anime List Profile"
        embed.set_thumbnail(url="https://myanimelist.cdn-dena.com/img/sp/icon/apple-touch-icon-256."
                                "png")
        embed.add_field(name=":calendar_spiral: Days Spent {}".format(medium), value=user_data[4],
                        inline=False)
        embed.add_field(name="{} {}".format(emojis[0], medium), value=user_data[0])
        embed.add_field(name="{} Completed".format(emojis[1]), value=user_data[1])
        embed.add_field(name="{} On Hold".format(emojis[2]), value=user_data[2])
        embed.add_field(name=":wastebasket: Dropped", value=user_data[3])
        embed.add_field(name=":link: Five Shared", value='\n'.join(share), inline=False)
        embed.add_field(name=":trident: Five Different", value='\n'.join(different))
        await self.bot.say(embed=embed)

    async def owner_set(self, ctx):
        await self.bot.whisper("Type your user name. You can reply in this private msg")
        username = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)

        if username is None:
            return await self.bot.whisper("Username and Password setup timed out.")

        await self.bot.whisper("Ok thanks. Now what is your password?")
        password = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)

        if password is None:
            return await self.bot.whisper("Username and Password setup timed out.")

        if await self.credential_verfication(username.content, password.content):
            self.credentials["Password"] = password.content
            self.credentials["Username"] = username.content
            dataIO.save_json(self.file_path, self.credentials)
            await self.bot.whisper("Setup complete. Account details added.\nTry searching for "
                                   "an anime using {}anime".format(ctx.prefix))
            return

    async def fetch_user_mal(self, name, url, cmd):
        with aiohttp.ClientSession() as session:
            async with session.get(url.format(name)) as response:
                data = await response.text()
                try:
                    root = ET.fromstring(data)

                except ET.ParseError:
                    return '', ''

                else:
                    if len(root) == 0:
                        return '', ''

                    collection = {x.find('series_title').text for x in root.findall(cmd)}
                    entry = root.find('myinfo')
                    if cmd == "anime":
                        info = [entry.find(x).text for x in ['user_watching', 'user_completed',
                                                             'user_onhold', 'user_dropped',
                                                             'user_days_spent_watching']]
                        return collection, info
                    else:
                        info = [entry.find(x).text for x in ['user_reading', 'user_completed',
                                                             'user_onhold', 'user_dropped',
                                                             'user_days_spent_watching']]
                        return collection, info

    def name_lookup(self, name):
        try:
            acc_name = self.credentials["Users"][name.id]
            return acc_name
        except KeyError:
            return name.name

    async def credential_verfication(self, username, password):
        auth = aiohttp.BasicAuth(login=username, password=password)
        url = "https://myanimelist.net/api/account/verify_credentials.xml"
        with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(url) as response:
                status = response.status

                if status == 200:
                    return True

                if status == 401:
                    await self.bot.say("Username and Password is incorrect.")
                    return False

                if status == 403:
                    await self.bot.say("Too many failed login attempts. Try putting in the"
                                       "correct credentials after some time has passed.")
                    return False

    async def fetch_info(self, ctx, cmd, title):
        data = await self.get_xml(cmd, title)

        try:
            root = ET.fromstring(data)

        except ET.ParseError:
            return await self.bot.say("I couldn't find anything!")

        else:
            if len(root) == 1:
                entry = root[0]
            else:
                msg = "**Please choose one by giving its number.**\n"
                msg += "\n".join(['{} - {}'.format(n + 1, entry[1].text)
                                  for n, entry in enumerate(root) if n < 10])

                await self.bot.say(msg)

                check = lambda m: m.content.isdigit() and int(m.content) in range(1, len(root) + 1)
                resp = await self.bot.wait_for_message(timeout=15, author=ctx.message.author,
                                                       check=check)
                if resp is None:
                    return

                entry = root[int(resp.content)-1]

            link = 'http://myanimelist.net/{}/{}'.format(cmd, entry.find('id').text)
            desc = "MAL [{}]({})".format(entry.find('title').text, link)
            syn_raw = entry.find('synopsis').text
            title = entry.find('title').text
            if syn_raw:
                replace = {'&quot;': '\"', '<br />': '', '&mdash;': ' - ', '&#039;': '\'',
                           '&ldquo;': '\"', '&rdquo;': '\"', '[i]': '*', '[/i]': '*', '[b]': '**',
                           '[/b]': '**', '[url=': '', ']': ' - ', '[/url]': ''}
                rep_sorted = sorted(replace, key=lambda s: len(s[0]), reverse=True)
                rep_escaped = [re.escape(replacement) for replacement in rep_sorted]
                pattern = re.compile("|".join(rep_escaped), re.I)
                synopsis = pattern.sub(lambda match: replace[match.group(0)],
                                       entry.find('synopsis').text)
            else:
                synopsis = "There is not a synopsis for {}".format(title)

            # Build Embed
            embed = discord.Embed(colour=0x0066FF, description=desc)
            embed.title = title
            embed.set_thumbnail(url=entry.find('image').text)
            embed.set_footer(text=synopsis)

            for k in switcher:
                spec = entry.find(k)
                if spec is not None and spec.text is not None:
                    embed.add_field(name=k.capitalize(),
                                    value=html.unescape(spec.text.replace('<br />', '')))

            await self.bot.say(embed=embed)

    async def get_xml(self, nature, name):
        username = self.credentials["Username"]
        password = self.credentials["Password"]
        name = name.replace(" ", "_")
        auth = aiohttp.BasicAuth(login=username, password=password)
        url = 'https://myanimelist.net/api/{}/search.xml?q={}'.format(nature, name)
        with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(url) as response:
                data = await response.text()
                return data

    def verify_credentials(self):
        username = self.credentials["Username"]
        password = self.credentials["Password"]
        if username == '' or password == '':
            return False
        else:
            return True


def check_folders():
    if not os.path.exists("data/animelist"):
        print("Creating data/animelist folder...")
        os.makedirs("data/animelist")


def check_files():
    system = {"Username": "",
              "Password": ""}

    f = "data/animelist/credentials.json"
    if not dataIO.is_valid_json(f):
        print("Adding animelist credentials.json...")
        dataIO.save_json(f, system)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(AnimeList(bot))
