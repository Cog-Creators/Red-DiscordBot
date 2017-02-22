from discord.ext import commands
from cogs.utils import checks
from .utils.dataIO import dataIO
import os
import aiohttp
import re #chem

API = "https://cleverbot.io/1.0"
API_CREATE = API + "/create"
API_ASK    = API + "/ask"


class CleverbotError(Exception):
    pass


class NoCredentials(CleverbotError):
    pass


class APIError(CleverbotError):
    pass


class Cleverbot():
    """Cleverbot"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/cleverbot/settings.json")
        self.instances = {}

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    async def cleverbot(self, ctx, *, message):
        """Talk with cleverbot"""
        author = ctx.message.author
        try:
            result = await self.get_response(author, message)
        except NoCredentials:
            await self.bot.say("The owner needs to set the credentials first.\n"
                               "See: `{}cleverbot apikey`".format(ctx.prefix))
        except APIError:
            await self.bot.say("Error contacting the API.")
        else:
            await self.bot.say(result)

    @cleverbot.command()
    @checks.is_owner()
    async def toggle(self):
        """Toggles reply on mention"""
        self.settings["TOGGLE"] = not self.settings["TOGGLE"]
        if self.settings["TOGGLE"]:
            await self.bot.say("I will reply on mention.")
        else:
            await self.bot.say("I won't reply on mention anymore.")
        dataIO.save_json("data/cleverbot/settings.json", self.settings)

    @cleverbot.command()
    @checks.is_owner()
    async def apikey(self, user: str, key: str):
        """Sets credentials to be used with cleverbot.io

        You can get them from https://cleverbot.io/keys
        Use this command in direct message to keep your
        credentials secret"""
        self.settings["user"] = user
        self.settings["key"] = key
        dataIO.save_json("data/cleverbot/settings.json", self.settings)
        await self.bot.say("Credentials set.")

    async def create_instance(self, author):
        session = aiohttp.ClientSession()
        payload = self.get_credentials()

        async with session.post(API_CREATE, data=payload) as r:
            if r.status != 200:
                raise APIError()
            data = await r.json()
        await session.close()
        if data["status"] == "success":  # because bools are too mainstream
            self.instances[author.id] = data["nick"]
            return data["nick"]
        else:
            raise APIError()

    async def get_response(self, author, text):
        session = aiohttp.ClientSession()
        payload = self.get_credentials()
        payload["nick"] = self.instances.get(author.id,
                                             await self.create_instance(author))
        payload["text"] = text
        async with session.post(API_ASK, data=payload) as r:
            if r.status != 200:
                raise APIError()
            data = await r.json()
        await session.close()
        if data["status"] == "success":  # because bools are too mainstream
            return data["response"]
        else:
            raise APIError()

    def get_credentials(self):
        try:
            return {'user': self.settings["user"],
                    'key': self.settings["key"]}
        except KeyError:
            raise NoCredentials()

    async def on_message(self, message):
        if not self.settings["TOGGLE"] or message.server is None:
            return

        if not self.bot.user_allowed(message):
            return

        author = message.author
        channel = message.channel

        if message.author.id != self.bot.user.id:
#            regexp = re.compile(r'\b[mM][aA][rR][vV][iI][nN]\b') #FoxLovesYou
#            if regexp.search(message.content.lower()) is not None: #FoxLovesYou
            to_strip = "@" + author.server.me.display_name + " "
            text = message.clean_content
            if not text.startswith(to_strip):
                return
            text = text.replace(to_strip, "", 1)
            await self.bot.send_typing(channel)
            try:
                response = await self.get_response(author, text)
            except NoCredentials:
                await self.bot.send_message(channel, "The owner needs to set the credentials first.\n"
                                                     "See: `[p]cleverbot apikey`")
            except APIError:
                await self.bot.send_message(channel, "Error contacting the my Speach Matrix Try again later.")
            else:
                await self.bot.send_message(channel, response)


def check_folders():
    if not os.path.exists("data/cleverbot"):
        print("Creating data/cleverbot folder...")
        os.makedirs("data/cleverbot")


def check_files():
    f = "data/cleverbot/settings.json"
    data = {"TOGGLE" : True}
    if not dataIO.is_valid_json(f):
        dataIO.save_json(f, data)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Cleverbot(bot))
