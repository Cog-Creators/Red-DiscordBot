"""Module to manage trivia sessions."""
import asyncio
import time
from random import choice, shuffle
from collections import Counter
from typing import List
import discord
from discord.ext.commands import Context
from core import config as realconfig
from core.utils.chat_formatting import box

_REVEAL_MESSAGES = ("I know this one! {}!",
                    "Easy: {}.",
                    "Oh really? It's {} of course.")
_FAIL_MESSAGES = ("To the next one I guess...",
                  "Moving on...",
                  "I'm sure you'll know the answer of the next one.",
                  "\N{PENSIVE FACE} Next one.")

class TriviaSession():
    """A Trivia Session. After being instantiated, it can be run with :func:`run`
     and force stopped with :func:`stop_trivia`.

    .. py:attribute:: ctx

        Context object from which this session will be run. It assumes the session was started
         in `ctx.channel` by `ctx.author`.

    .. py:attribute:: trivia_list

        List of tuples containing `(question, answers)` pairs. `question` must be a single string,
         where as `answers` is a list of strings.

    .. py:attribute:: settings

        A :py:class:`.core.config.Group` object which contains the settings for the trivia session.
    """

    def __init__(self, ctx: Context, trivia_list: List[tuple], settings: realconfig.Group):
        self.ctx = ctx
        shuffle(trivia_list)
        self.question_list = trivia_list
        self.settings = settings
        self.scores = Counter()
        self.last_response = time.perf_counter()
        self.count = 0
        self.stopped = False

    def stop_trivia(self):
        """Stops the trivia session, without showing scores."""
        self.stopped = True
        self.ctx.bot.dispatch("trivia_end", self)

    async def end_game(self):
        """Ends the trivia session and displays scrores."""
        if self.scores:
            await self.send_table()
        self.stop_trivia()

    async def run(self):
        """Run the trivia session."""
        max_score = await self.settings.max_score()
        delay = await self.settings.delay()
        timeout = await self.settings.timeout()
        for question, answers in self.question_list:
            async with self.ctx.typing():
                await asyncio.sleep(3)
            self.count += 1
            msg = "**Question number {}!**\n\n{}".format(self.count, question)
            await self.ctx.send(msg)
            result = await self._wait_for_answer(answers, delay, timeout)
            if result is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
        else:
            await self.ctx.send("There are no more questions!")
            await self.end_game()

    async def _wait_for_answer(self, answers: List[str], delay: float, timeout: int):
        """Waits for an answer.

        Returns False if waiting was cancelled; a user probably forced the trivia
         session to stop.

        :param List[str] answers:
            A list of valid answers.
        :param float delay:
            How long users have to respond (in seconds).
        :param int timeout:
            How long before the session ends due to no responses (in seconds).
        :return:
            True if the session wasn't interrupted.
        :rtype: bool
        """
        try:
            message = await self.ctx.bot.wait_for("message",
                                                  check=self.check_answer(answers),
                                                  timeout=delay)
        except asyncio.TimeoutError:
            if abs(self.last_response - int(time.perf_counter())) >= timeout:
                await self.ctx.send("Guys...? Well, I guess I'll stop then.")
                await self.stop_trivia()
            if self.stopped:
                return False
            if await self.settings.reveal_answer():
                reply = choice(_REVEAL_MESSAGES).format(answers[0])
            else:
                reply = choice(_FAIL_MESSAGES)
            if await self.settings.bot_plays():
                reply += " **+1** for me!"
                self.scores[self.ctx.guild.me] += 1
            await self.ctx.send(reply)
        else:
            self.scores[message.author] += 1
            reply = "You got it {}! **+1** to you!".format(message.author.display_name)
            await self.ctx.send(reply)

        if self.stopped:
            return False
        return True

    async def send_table(self):
        """Send a table of scores to the session's channel."""
        table = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            table += "+ {}\t{}\n".format(user, score)
        await self.ctx.send(box(table, lang="diff"))

    def check_answer(self, answers: List[str]):
        """Returns a `discord.Message` predicate to check for the given answers."""
        def _pred(message: discord.Message):
            early_exit = (message.channel != self.ctx.channel or
                          message.author == self.ctx.guild.me)
            if early_exit:
                return False

            self.last_response = time.perf_counter()
            for answer in answers:
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
        return _pred
