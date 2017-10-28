"""Module to manage trivia sessions."""
import asyncio
import time
import random
from collections import Counter
from typing import List
import discord
from redbot.core.bank import deposit_credits
from redbot.core.utils.chat_formatting import box
from .log import LOG

__all__ = ["TriviaSession"]

_REVEAL_MESSAGES = ("I know this one! {}!", "Easy: {}.",
                    "Oh really? It's {} of course.")
_FAIL_MESSAGES = ("To the next one I guess...", "Moving on...",
                  "I'm sure you'll know the answer of the next one.",
                  "\N{PENSIVE FACE} Next one.")


class TriviaSession():
    """Class to run a session of trivia with the user.

    After being instantiated, it can be run with :py:func:`TriviaSession.run`
    and force stopped with :py:func:`TriviaSession.stop`.

    Attributes
    ----------
    ctx : `commands.Context`
        Context object from which this session will be run.
        This object assumes the session was started in `ctx.channel`
        by `ctx.author`.
    question_list : `dict`
        A dict mapping questions (`str`) to answers (`list` of `str`).
    settings : `redbot.core.config.Group`
        Config for the trivia session.
    scores : `collections.Counter`
        A counter with the players as keys, and their scores as values. The
        players are of type :py:class:`discord.Member`.
    count : `int`
        The number of questions which have been asked.
    stopped : `bool`
        Whether or not the trivia session has been stopped.

    """

    def __init__(self,
                 ctx,
                 question_list,
                 settings):
        self.ctx = ctx
        self.question_list = question_list
        self.settings = settings
        self.scores = Counter()
        self.count = 0
        self.stopped = False
        self._last_response = time.perf_counter()

    async def run(self):
        """Run the trivia session."""
        max_score = await self.settings.max_score()
        delay = await self.settings.delay()
        timeout = await self.settings.timeout()
        for question, answers in self._iter_questions():
            self.count += 1
            msg = "**Question number {}!**\n\n{}".format(self.count, question)
            await self.ctx.send(msg)
            result = await self.wait_for_answer(answers, delay, timeout)
            if result is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
            async with self.ctx.typing():
                await asyncio.sleep(3)
        else:
            await self.ctx.send("There are no more questions!")
            await self.end_game()

    def _iter_questions(self):
        questions = tuple(self.question_list.keys())
        for _ in range(len(questions)):
            question = random.choice(questions)
            yield question, self.question_list.pop(question)

    async def wait_for_answer(self,
                              answers: List[str],
                              delay: float,
                              timeout: int):
        """Wait for a correct answer, and then respond.

        Scores are also updated in this method.

        Returns False if waiting was cancelled; this is usually due to the
        session being forcibly stopped.

        Parameters
        ----------
        answers : `list` of `str`
            A list of valid answers to the current question.
        delay : float
            How long users have to respond (in seconds).
        timeout : int
            How long before the session ends due to no responses (in seconds).

        Returns
        -------
        bool
            :code:`True` if the session wasn't interrupted.

        """
        try:
            message = await self.ctx.bot.wait_for(
                "message", check=self.check_answer(answers), timeout=delay)
        except asyncio.TimeoutError:
            if abs(self._last_response - int(time.perf_counter())) >= timeout:
                await self.ctx.send("Guys...? Well, I guess I'll stop then.")
                await self.stop()
            if self.stopped:
                return False
            if await self.settings.reveal_answer():
                reply = random.choice(_REVEAL_MESSAGES).format(answers[0])
            else:
                reply = random.choice(_FAIL_MESSAGES)
            if await self.settings.bot_plays():
                reply += " **+1** for me!"
                self.scores[self.ctx.guild.me] += 1
            await self.ctx.send(reply)
        else:
            self.scores[message.author] += 1
            reply = "You got it {}! **+1** to you!".format(
                message.author.display_name)
            await self.ctx.send(reply)

        if self.stopped:
            return False
        return True

    def check_answer(self, answers: List[str]):
        """Get a predicate to check for correct answers.

        The returned predicate takes a message as its only parameter,
        and returns ``True`` if the message contains any of the
        given answers.

        Parameters
        ----------
        answers : `list` of `str`
            The answers which the predicate must check for.

        Returns
        -------
        function
            The message predicate.

        """

        def _pred(message: discord.Message):
            early_exit = (message.channel != self.ctx.channel
                          or message.author == self.ctx.guild.me)
            if early_exit:
                return False

            self._last_response = time.perf_counter()
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

    async def end_game(self):
        """End the trivia session and display scrores."""
        if self.scores:
            await self.send_table()
        multiplier = await self.settings.payout_multiplier()
        if multiplier > 0:
            await self.pay_winner(multiplier)
        self.stop()

    async def send_table(self):
        """Send a table of scores to the session's channel."""
        table = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            table += "+ {}\t{}\n".format(user, score)
        await self.ctx.send(box(table, lang="diff"))

    def stop(self):
        """Stop the trivia session, without showing scores."""
        self.stopped = True
        self.ctx.bot.dispatch("trivia_end", self)

    async def pay_winner(self, multiplier: float):
        """Pay the winner of this trivia session.

        The winner is only payed if there are at least 3 human contestants.

        Parameters
        ----------
        multiplier : float
            The coefficient of the winner's score, used to determine the amount
            paid.

        """
        (winner, score) = next((tup for tup in self.scores.most_common(1)),
                               (None, None))
        me_ = self.ctx.guild.me
        if winner is not None and winner != me_ and score > 0:
            contestants = list(self.scores.keys())
            if me_ in contestants:
                contestants.remove(me_)
            if len(contestants) >= 3:
                amount = int(multiplier * score)
                if amount > 0:
                    LOG.debug("Paying trivia winner: %d credits --> %s",
                              amount, str(winner))
                    await deposit_credits(winner, int(multiplier * score))
                    await self.ctx.send(
                        "Congratulations, {0}, you have received {1} credits"
                        " for coming first.".format(winner.display_name,
                                                    amount))
