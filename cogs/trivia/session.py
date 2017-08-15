"""Module to manage trivia sessions."""

# This is a direct copy from V2's trivia cog by TwentySix.
#  Only very minor changes have been made so far to port
#  over to V3.

import asyncio
import time
from random import choice
from collections import Counter
import discord
from core import config as real_config
from core.bot import Red
from core.utils.chat_formatting import box

_REVEAL_MESSAGES = ("I know this one! {}!",
                    "Easy: {}.",
                    "Oh really? It's {} of course.")

_FAIL_MESSAGES = ("To the next one I guess...",
                  "Moving on...",
                  "I'm sure you'll know the answer of the next one.",
                  "\N{PENSIVE FACE} Next one.")

class TriviaSession():
    """A Trivia Session."""

    def __init__(self, bot: Red, trivia_list, message: discord.Message,
                 settings: real_config.Group):
        self.bot = bot
        self.current_line = None # {"QUESTION" : "String", "ANSWERS" : []}
        self.question_list = trivia_list
        self.channel = message.channel
        self.starter = message.author
        self.scores = Counter()
        self.status = "new question"
        self.timeout = time.perf_counter()
        self.count = 0
        self.settings = settings

    async def stop_trivia(self):
        """Stops the trivia session, without showing scores."""
        self.status = "stop"
        self.bot.dispatch("trivia_end", self)

    async def end_game(self):
        """Ends the trivia session and displays scrores."""
        if self.scores:
            await self.send_table()
        await self.stop_trivia()

    async def new_question(self):
        """Ask the next question."""
        for score in self.scores.values():
            if score == await self.settings.max_score():
                await self.end_game()
                return True
        if self.question_list == []:
            await self.end_game()
            return True
        self.current_line = choice(self.question_list)
        self.question_list.remove(self.current_line)
        self.status = "waiting for answer"
        self.count += 1
        msg = "**Question number {}!**\n\n{}".format(self.count, self.current_line.question)
        await self.channel.send(msg)
        await self._wait_for_answer()

    async def _wait_for_answer(self):
        delay = await self.settings.delay()
        try:
            message = await self.bot.wait_for("message", check=self.check_answer, timeout=delay)
        except asyncio.TimeoutError:
            if abs(self.timeout - int(time.perf_counter())) >= await self.settings.timeout():
                await self.channel.send("Guys...? Well, I guess I'll stop then.")
                await self.stop_trivia()
            if self.status == "stop":
                return True
            if await self.settings.reveal_answer():
                reply = choice(_REVEAL_MESSAGES).format(self.current_line.answers[0])
            else:
                reply = choice(_FAIL_MESSAGES)
            if await self.settings.bot_plays():
                reply += " **+1** for me!"
                self.scores[self.bot.user] += 1
            await self.channel.send(reply)
        else:
            self.status = "correct answer"
            self.scores[message.author] += 1
            reply = "You got it {}! **+1** to you!".format(message.author.display_name)
            await self.channel.send(reply)
            
        self.current_line = None
        self.status = "new question"
        async with self.channel.typing():
            await asyncio.sleep(3)
        if not self.status == "stop":
            await self.new_question()

    async def send_table(self):
        """Send a table of scores to the session's channel."""
        table = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            table += "+ {}\t{}\n".format(user, score)
        await self.channel.send(box(table, lang="diff"))

    def check_answer(self, message: discord.Message):
        """Check if a message is an answer to the current question."""
        early_exit = (message.channel != self.channel or
                      message.author == self.channel.guild.me or
                      self.current_line is None)
        if early_exit:
            return False

        self.timeout = time.perf_counter()

        for answer in self.current_line.answers:
            answer = answer.lower()
            guess = message.content.lower()
            if " " not in answer:  # Exact matching, issue #331
                guess = guess.split(" ")
                for word in guess:
                    if word == answer:
                        return True
            else:  # The answer has spaces, we can't be as strict
                if answer in guess:
                    return True
        return False
