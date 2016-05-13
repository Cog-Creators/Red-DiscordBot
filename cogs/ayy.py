import discord
from discord.ext import commands
import os
from .utils.dataIO import fileIO
from .utils import checks

default_settings = {"SERVER": {"DEFAULT": False}}

class ayy:
    """lmaoing"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/ayy/settings.json", "load")

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def ayy(self, ctx):
        """Toggle lmaoing for this server"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = True
        else:
            self.settings[server.id] = not self.settings[server.id]
        if self.settings[server.id]:
            await self.bot.say('lmaoing enabled'
                               ' for {}'.format(server.name))
            fileIO("data/ayy/settings.json", "save", self.settings)
        else:
            await self.bot.say('lmaoing disabled'
                               ' for {}'.format(server.name))
            fileIO("data/ayy/settings.json", "save", self.settings)

    async def check_ayy(self, message):
        enabled = self.settings.get(message.server.id, False)
        if "ayy" in message.content.split():
            if enabled:
                await self.bot.send_message(message.channel, "lmao")
        elif "shrug" in message.content.split():
            if enabled:
                await self.bot.send_message(message.channel, "¯\_(ツ)_/¯")
        elif "¯\_(ツ)_/¯" in message.content.split():
            if enabled:
                if message.author.id != "158124575706578944":
                     await self.bot.send_message(message.channel, "Fuck you. That's *my* job.")
        elif "k" in message.content.split():
            if enabled:
                await self.bot.send_message(message.channel, ":ok:")
        elif "kkk" in message.content.split():
            if enabled:
                await self.bot.send_message(message.channel, "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/KKK.svg/500px-KKK.svg.png")

def check_folders():
    if not os.path.exists("data/ayy"):
        print("Creating ayy folder...")
        os.makedirs("data/ayy")


def check_files(bot):
    settings = {"ENABLED" : False}
    settings_path = "data/ayy/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default ayy settings.json...")
        fileIO(settings_path, "save", settings)

def setup(bot):
    check_folders()
    check_files(bot)
    n = ayy(bot)
    bot.add_listener(n.check_ayy, "on_message")
    bot.add_cog(n)
