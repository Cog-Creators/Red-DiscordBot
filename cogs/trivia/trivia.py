"""Module for Trivia cog."""
# from random import choice
# import time
# import asyncio
# import chardet
# from collections import Counter, namedtuple
# import discord
from discord.ext import commands
from core import Config, checks
from core.bot import Red
from core.utils.chat_formatting import box
from . import LOG

UNIQUE_ID = 0xb3c0e453

class Trivia:
    """Play trivia with friends!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.trivia_sessions = []
        self.conf = Config.get_conf(self,
                                    identifier=UNIQUE_ID,
                                    force_registration=True)

        self.conf.register_guild(
            max_score=10,
            timeout=120,
            delay=15,
            bot_plays=False,
            reveal_answer=True
        )

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def triviaset(self, ctx: commands.Context):
        """Manage trivia settings."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            settings_dict = self.conf.guild(ctx.guild).defaults
            settings_dict.update(self.conf.guild(ctx.guild).all())
            msg = box("**Current settings**\n"
                      "Red gains points: {bot_plays}\n"
                      "Seconds to answer: {delay}\n"
                      "Points to win: {max_score}\n"
                      "Reveal answer on timeout: {reveal_answer}\n"
                      "".format(**settings_dict), lang="py")
            await ctx.send(msg)

    @triviaset.command(name="maxscore")
    async def triviaset_max_score(self, ctx: commands.Context, score: int):
        """Points required to win."""
        if score < 0:
            await ctx.send("Score must be greater than 0.")
            return
        settings = self.conf.guild(ctx.guild)
        await settings.max_score.set(score)
        await ctx.send("Points required to win set to {}.".format(score))

    @triviaset.command(name="timelimit")
    async def triviaset_delay(self, ctx: commands.Context, seconds: int):
        """Maximum seconds to answer a question."""
        if seconds < 4:
            await ctx.send("Must be greater than 4 seconds.")
            return
        settings = self.conf.guild(ctx.guild)
        await settings.delay.set(seconds)
        await ctx.send("Maximum seconds to answer set to {}.".format(seconds))

    @triviaset.command(name="botplays")
    async def trivaset_bot_plays(self, ctx: commands.Context):
        """Red gains points.

        This is a toggle. If enabled, Red will gain a point if
         no one guesses correctly.
        """
        settings = self.conf.guild(ctx.guild)
        enabled = not settings.bot_plays()
        await settings.bot_plays.set(enabled)
        await ctx.send("I'll gain a point everytime you don't answer in time."
                       if enabled else
                       "Alright, I won't embarass you at trivia anymore.")

    @triviaset.command(name="revealanswer")
    async def trivaset_reveal_answer(self, ctx: commands.Context):
        """Reveals answer to question on timeout.

        This is a toggle. If enabled, Red will reveal the answer if no
         one guesses correctly.
        """
        settings = self.conf.guild(ctx.guild)
        enabled = not settings.reveal_answer()
        await settings.reveal_answer.set(enabled)
        await ctx.send("I'll reveal the answer if no one knows it."
                       if enabled else
                       "I won't reveal the answer to the questions anymore.")
