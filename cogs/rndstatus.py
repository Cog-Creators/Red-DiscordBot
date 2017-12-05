import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from random import choice as rndchoice
import os
import time

class RandomStatus:
    """Cycles random statuses

    If a custom status is already set, it won't change it until
    it's back to none. (!set status)"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/rndstatus/settings.json", "load")
        self.statuses = fileIO("data/rndstatus/statuses.json", "load")
        self.last_change = None

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def rndstatus(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @rndstatus.command(name="set", pass_context=True, no_pm=True)
    async def _set(self, ctx, *statuses : str):
        """Sets Red's random statuses

        Accepts multiple statuses.
        Must be enclosed in double quotes in case of multiple words.
        Example:
        !rndstatus set \"Tomb Raider II\" \"Transistor\" \"with your heart.\"
        Shows current list if empty."""
        current_status = ctx.message.server.me.status
        if statuses == () or "" in statuses:
            await self.bot.whisper("Current statuses: " + " | ".join(self.statuses))
            return
        self.statuses = list(statuses)
        fileIO("data/rndstatus/statuses.json", "save", self.statuses)
        await self.bot.change_presence(status=current_status)
        await self.bot.say("Done. Redo this command with no parameters to see the current list of statuses.")


    @rndstatus.command(pass_context=True)
    async def delay(self, ctx, seconds : int):
        """Sets interval of random status switch

        Must be 20 or superior."""
        if seconds < 20:
            await send_cmd_help(ctx)
            return
        self.settings["DELAY"] = seconds
        fileIO("data/rndstatus/settings.json", "save", self.settings)
        await self.bot.say("Interval set to {}".format(str(seconds)))

    async def switch_status(self, message):
        if not message.channel.is_private:
            current_game = str(message.server.me.game)
            current_status = message.server.me.status

            if self.last_change == None: #first run
                self.last_change = int(time.perf_counter())
                if len(self.statuses) > 0 and (current_game in self.statuses or current_game == "None"):
                    new_game = self.random_status(message)
                    await self.bot.change_presence(game=discord.Game(name=new_game), status=current_status)

            if message.author.id != self.bot.user.id:
                if abs(self.last_change - int(time.perf_counter())) >= self.settings["DELAY"]:
                    self.last_change = int(time.perf_counter())
                    new_game = self.random_status(message)
                    if new_game != None:
                        if current_game != new_game:
                            if current_game in self.statuses or current_game == "None": #Prevents rndstatus from overwriting song's titles or
                                await self.bot.change_presence(game=discord.Game(name=new_game), status=current_status) #custom statuses set with !set status

    def random_status(self, msg):
        current = str(msg.server.me.game)
        new = str(msg.server.me.game)
        if len(self.statuses) > 1:
            while current == new:
                new = rndchoice(self.statuses)
        elif len(self.statuses) == 1:
            new = self.statuses[0]
        else:
            new = None
        return new

def check_folders():
    if not os.path.exists("data/rndstatus"):
        print("Creating data/rndstatus folder...")
        os.makedirs("data/rndstatus")

def check_files():
    settings = {"DELAY" : 300}
    default = ["her Turn()", "Tomb Raider II", "Transistor", "NEO Scavenger", "Python", "with your heart."]

    f = "data/rndstatus/settings.json"
    if not fileIO(f, "check"):
        print("Creating empty settings.json...")
        fileIO(f, "save", settings)

    f = "data/rndstatus/statuses.json"
    if not fileIO(f, "check"):
        print("Creating empty statuses.json...")
        fileIO(f, "save", default)

def setup(bot):
    check_folders()
    check_files()
    n = RandomStatus(bot)
    bot.add_listener(n.switch_status, "on_message")
    bot.add_cog(n)
