import discord
from discord.ext import commands
import pytz
from pytz import all_timezones
from pytz import country_timezones
from datetime import datetime
from .utils.dataIO import fileIO
from .utils import checks
import os
from __main__ import send_cmd_help

'http://pytz.sourceforge.net/'
'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones'
'https://github.com/newvem/pytz'

class Timezone:
    """Gets times across the world..."""

    def __init__(self, bot):
        self.bot = bot
        self.usertime = fileIO("data/timezone/users.json", "load")

    @commands.group(pass_context=True, no_pm=True)
    async def time(self, ctx):
        """Checks the time.

    For the list of supported timezones, see here: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @time.group(pass_context=True, no_pm=True)
    async def tz(self, ctx, *, tz):
        """Gets the time in any timezone"""
        try:
            if tz == "":
                time = datetime.now()
                fmt = '**%H:%M** %d-%B-%Y'
                await self.bot.say("Current system time: " + time.strftime(fmt))
            else:
                fmt = '**%H:%M** %d-%B-%Y ***%Z (UTC%z)***'
                if "'" in tz:
                    tz = tz.replace("'", "")
                if len(tz) > 4 and "/" not in tz:
                    await self.bot.say("Error: Incorrect format. Use:\n **Continent/City** with correct capitals. e.g. `America/New_York`\n See the full list of supported timezones here:\n <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>")
                else:
                    time = datetime.now(pytz.timezone(tz))
                    await self.bot.say(time.strftime(fmt))
        except Exception as e:
            e = str(e)
            msg = "**Error:** " + e + " is an unsupported timezone."
            await self.bot.say(msg)


    @time.command(pass_context=True, no_pm=True)
    async def user(self, ctx, user : discord.Member=None):
        """Shows the current time for user."""
        if not user:
            await self.bot.say("**That isn't a user!**")
        else:
            if self.account_check(user.id):
                tz = self.check_time(user.id)
                time = datetime.now(pytz.timezone(tz))
                fmt = '**%H:%M** %d-%B-%Y ***%Z (UTC%z)***'
                time = time.strftime(fmt)
                await self.bot.say("{}'s current time is: {}".format(user.name, str(time)))
            else:
                await self.bot.say("That user hasn't set their timezone.")

    @time.command(pass_context=True, no_pm=True)
    async def me(self, ctx):
        """Sets your timezone. For various things. 
        Usage: !time me Continent/City"""
        user = ctx.message.author
        tz = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+1:])
        tz = tz[3:]
        if tz in all_timezones:
            exist = True
        else:
            exist = False
        if tz == "":
            if user.id not in self.usertime:
                await self.bot.say("You haven't set your timezone. Do `!time me Continent/City`")
            else:
                msg = "Your current timezone is ***"+str(self.check_time(user.id))+".***"
                await self.bot.say(msg)
                time = datetime.now(pytz.timezone(str(self.check_time(user.id))))
                fmt = '**%H:%M** %d-%B-%Y ***%Z (UTC%z)***'
                time = time.strftime(fmt)
                msg = "The current time is: " + time
                await self.bot.say(msg)
        elif exist == True:
            if "'" in tz:
                tz = tz.replace("'", "")
            self.usertime[user.id] = tz
            fileIO("data/timezone/users.json", "save", self.usertime)
            await self.bot.say('Successfully set your timezone.')
        else:
            await self.bot.say("**Error:** Unrecognised timezone. Try `!time me Continent/City`")

    @time.command(pass_context=True, no_pm=True)
    async def iso(self, ctx, *, code):
        """Looks up ISO3166 country codes and gives you a supported timezone."""
        #code = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+1:])
        #print(code)
        #code = code[4:]
        if code == "":
            await self.bot.say("That doesn't look like a country code!")
        else:
            if code in country_timezones:
                exist = True
            else:
                exist = False
            if exist == True:
                msg = "Supported timezones for ***" + code + ":***\n"
                tz = str(country_timezones(code))
                tz = tz[:-1]
                tz = tz[1:]
                msg += tz
                msg +="\n**Use** `!time Continent/City` **to display the current time in " + code + ".**"
                await self.bot.say(msg)
            else:
                await self.bot.say("That code isn't supported. For a full list, see here: <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>")

    def account_check(self, id):
        if id in self.usertime:
            return True
        else:
            return False

    def check_time(self, id):
        if self.account_check(id):
            return self.usertime[id]
        else:
            return False

def check_folders():
    if not os.path.exists("data/timezone"):
        print("Creating data/timezone folder...")
        os.makedirs("data/timezone")

def check_files():

    f = "data/timezone/users.json"
    if not fileIO(f, "check"):
        print("Creating default timezone's users.json...")
        fileIO(f, "save", {})


def setup(bot):
    try:
        import pytz
    except:
        raise ModuleNotFound("PYTZ not found. Do pip3 install --upgrade pytz")
        self.bot.say("PYTZ not found. Do `pip3 install --upgrade pytz`")

    check_folders()
    check_files()
    bot.add_cog(Timezone(bot))
