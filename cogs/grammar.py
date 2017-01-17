# noinspection PyUnresolvedReferences
import discord
from discord.ext import commands
from cogs.utils import checks

__author__ = "ScarletRav3n"

# TODO: Find a better way to trigger a/an's

b = False


class Grammar:
    """Fix those mistakes"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def grammar(self, on_off: str):
        """Toggle ^ caret"""
        f = on_off.lower()
        global b
        if f == "on":
            await self.bot.say("Deleting carets is now ON." +
                               "\n`Make sure I have the 'manage_messages' " +
                               "permission`")
            b = True
        elif f == "off":
            await self.bot.say("Deleting carets is now OFF.")
            b = False
        else:
            await self.bot.say("I need an ON or OFF state.")

    async def on_message(self, m):
        k = m.content.lower()
        for x in self.bot.command_prefix:
            if x in m.content:
                return
            # elif " a a" in k: # a/an
            #    p = "an*"
            # elif " a e" in k:
            #    p = "an*"
            # elif " a o" in k:
            #    p = "an*"
            # elif " a u" in k:
            #    p = "an*"
            # elif " a i" in k:
            #    p = "an*"
            elif "your a " in k:  # your/there
                p = "you're*"
            elif "your an " in k:
                p = "you're*"
            elif "your on " in k:
                p = "you're*"
            elif "their not" in k:
                p = "they're*"
            elif "their a " in k:
                p = "they're*"
            elif "their an " in k:
                p = "they're*"
            elif "theres a " in k:
                p = "there's*"
            elif "theres an " in k:
                p = "there's*"
            elif "tommorrow" in k:  # spelling
                p = "tomorrow*"
            elif "begining" in k:
                p = "beginning*"
            elif "litteral" in k:
                p = "literal*"
            elif "dont " in k:  # aphostrophes
                p = "don't*"
            elif "didnt " in k:
                p = "didn't*"
            elif "cant " in k:
                p = "can't*"
            elif "wont " in k:
                p = "won't*"
            elif "isnt " in k:
                p = "isn't*"
            elif "its not" in k:
                p = "it's*"
            elif "laif" in k:  # stupid broken english patch start here
                p = "life*"
            elif "stronk" in k:
                p = "strong*"
            elif "noice" in k:
                p = "nice*"
            elif "lood" in k:
                p = "lewd*"
            elif "^" in m.content:  # caret
                if b is True:
                    await self.bot.delete_message(m)
                return
            await self.bot.send_message(m.channel, p)


def setup(bot):
    n = Grammar(bot)
    bot.add_cog(n)
