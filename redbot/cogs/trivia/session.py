"""Module to manage trivia sessions."""
import asyncio
import time
import random
from collections import Counter
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

    After being instantiated, it will be automatically run with
    `TriviaSession.run` and can force stopped with `TriviaSession.stop`.

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
        self._last_response = time.time()
        self._task = ctx.bot.loop.create_task(self.run())

    async def run(self):
        """Run the trivia session.

        This is run as soon as the class is instantiated, and thus should not
        be run directly.
        """
        max_score = await self.settings.max_score()
        delay = await self.settings.delay()
        timeout = float(await self.settings.timeout())
        for question, answers in self._iter_questions():
            self.count += 1
            msg = "**Question number {}!**\n\n{}".format(self.count, question)
            await self.ctx.send(msg)
            continue_ = await self.wait_for_answer(answers, delay, timeout)
            if continue_ is False:
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
        """Iterate over questions and answers for this session.

        As questions are yielded, so too are they removed from
        `TriviaSession.question_list`.

        Yields
        ------
        `tuple`
            A tuple containing the question (`str`) and the answers (`tuple` of
            `str`).

        """
        questions = tuple(self.question_list.keys())
        for _ in range(len(questions)):
            question = random.choice(questions)
            yield (question, _parse_answers(self.question_list.pop(question)))

    async def wait_for_answer(self,
                              answers,
                              delay: float,
                              timeout: float):
        """Wait for a correct answer, and then respond.

        Scores are also updated in this method.

        Returns False if waiting was cancelled; this is usually due to the
        session being forcibly stopped.

        Parameters
        ----------
        answers : `iterable` of `str`
            A list of valid answers to the current question.
        delay : float
            How long users have to respond (in seconds).
        timeout : float
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
            if time.time() - self._last_response >= timeout:
                await self.ctx.send("Guys...? Well, I guess I'll stop then.")
                self.stop()
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
        return True

    def check_answer(self, answers):
        """Get a predicate to check for correct answers.

        The returned predicate takes a message as its only parameter,
        and returns ``True`` if the message contains any of the
        given answers.

        Parameters
        ----------
        answers : `iterable` of `str`
            The answers which the predicate must check for.

        Returns
        -------
        function
            The message predicate.

        """
        answers = tuple(s.lower() for s in answers)
        def _pred(message: discord.Message):
            early_exit = (message.channel != self.ctx.channel
                          or message.author == self.ctx.guild.me)
            if early_exit:
                return False

            self._last_response = time.time()
            guess = message.content.lower()
            for answer in answers:
                if " " in answer and answer in guess:
                    # Exact matching, issue #331
                    return True
                elif any(word == answer for word in guess.split(" ")):
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
        self._task.cancel()
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


def _parse_answers(answers):
    """Parse the raw answers to readable strings.

    The reason this exists is because of YAML's ambiguous syntax. For example,
    if the answer to a question in YAML is ``yes``, YAML will load it as the
    boolean value ``True``, which is not necessarily the desired answer. This
    function aims to undo that for bools, and possibly for numbers in the
    future too.

    Parameters
    ----------
    answers : `iterable` of `str`
        The raw answers loaded from YAML.

    Returns
    -------
    `tuple` of `str`
        The answers in readable/ guessable strings.

    """
    ret = []
    for answer in answers:
        if isinstance(answer, bool):
            if answer is True:
                ret.append("True", "Yes")
            else:
                ret.append("False", "No")
        else:
            ret.append(str(answer))
    # Uniquify list
    seen = set()
    return tuple(x for x in ret if not (x in seen or seen.add(x)))
