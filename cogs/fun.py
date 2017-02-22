# noinspection PyUnresolvedReferences
import discord
from discord.ext import commands
from random import randint
from random import choice

__author__ = "ScarletRav3n"


class Fun:
    """fun random commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def sword(self, ctx, *, user: discord.Member):
        """Sword Duel!"""
        author = ctx.message.author
        if user.id == self.bot.user.id:
            await self.bot.say("I'm not the fighting kind")
        else:
            await self.bot.say(author.mention + " and " + user.mention + " dueled for " + str(randint(2, 120)) +
                               " gruesome hours! It was a long, heated battle, but " +
                               choice([author.mention, user.mention]) + " came out victorious!")

    @commands.command(pass_context=True)
    async def love(self, ctx, user: discord.Member):
        """Found your one true love?"""
        author = ctx.message.author
        if user.id == self.bot.user.id:
            await self.bot.say("I am not capable of loving like you can. I'm sorry.")
        else:
            await self.bot.say(author.mention + " is capable of loving " + user.mention + " a whopping " + str(randint(0, 100)) + "%!")

    @commands.command(pass_context=True)
    async def squat(self, ctx):
        """How is your workout going?"""
        author = ctx.message.author
        await self.bot.say(author.mention + " puts on their game face and does " + str(randint(2, 1000)) +
                           " squats in " + str(randint(4, 90)) + " minutes. Wurk it!")

    @commands.command(pass_context=True)
    async def pizza(self, ctx):
        """How many slices of pizza have you eaten today?"""
        author = ctx.message.author
        await self.bot.say(author.mention + " has eaten " + str(randint(2, 120)) + " slices of pizza today.")

    @commands.command(pass_context=True)
    async def bribe(self, ctx):
        """Find out who is paying under the table"""
        author = ctx.message.author
        await self.bot.say(author.mention + " has bribed " + self.bot.user.mention + " with " +
                           str(randint(10, 10000)) + " dollars!")

    @commands.command(pass_context=True)
    async def daddy(self, ctx):
        author = ctx.message.author
        await self.bot.say("I'm kink shaming you, " + author.mention)

    @commands.command()
    async def calculated(self):
        await self.bot.say("That was " + str(randint(0, 100)) + "% calculated!")

    @commands.command()
    async def butts(self):
        await self.bot.say("ლ(́◉◞౪◟◉‵ლ)")

    @commands.command(name="commands")
    async def _commands(self):
        await self.bot.say("Don't tell me what to do.")

    @commands.command()
    async def flirt(self):
        await self.bot.say("xoxoxoxoxo ;)) ))) hey b a b e ; ; ;))) ) ;)")

    @commands.command()
    async def updog(self):
        await self.bot.say("What's updog?")


def setup(bot):
    n = Fun(bot)
    bot.add_cog(n)
