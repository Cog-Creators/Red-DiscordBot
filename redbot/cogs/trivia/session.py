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

_REVEAL_MESSAGES = ("I know this one! {}!", "Easy: {}.", "Oh really? It's {} of course.")
_FAIL_MESSAGES = (
    "To the next one I guess...",
    "Moving on...",
    "I'm sure you'll know the answer of the next one.",
    "\N{PENSIVE FACE} Next one.",
)


class TriviaSession:
    """Class to run a session of trivia with the user.

    To run the trivia session immediately, use `TriviaSession.start` instead of
    instantiating directly.

    Attributes
    ----------
    ctx : `commands.Context`
        Context object from which this session will be run.
        This object assumes the session was started in `ctx.channel`
        by `ctx.author`.
    question_list : `dict`
        A list of tuples mapping questions (`str`) to answers (`list` of
        `str`).
    settings : `dict`
        Settings for the trivia session, with values for the following:
         - ``max_score`` (`int`)
         - ``delay`` (`float`)
         - ``timeout`` (`float`)
         - ``reveal_answer`` (`bool`)
         - ``bot_plays`` (`bool`)
         - ``allow_override`` (`bool`)
         - ``payout_multiplier`` (`float`)
    scores : `collections.Counter`
        A counter with the players as keys, and their scores as values. The
        players are of type `discord.Member`.
    count : `int`
        The number of questions which have been asked.

    """

    def __init__(self, ctx, question_list: dict, settings: dict):
        self.ctx = ctx
        list_ = list(question_list.items())
        random.shuffle(list_)
        self.question_list = list_
        self.settings = settings
        self.scores = Counter()
        self.count = 0
        self._last_response = time.time()
        self._task = None

    @classmethod
    def start(cls, ctx, question_list, settings):
        """Create and start a trivia session.

        This allows the session to manage the running and cancellation of its
        own tasks.

        Parameters
        ----------
        ctx : `commands.Context`
            Same as `TriviaSession.ctx`
        question_list : `dict`
            Same as `TriviaSession.question_list`
        settings : `dict`
            Same as `TriviaSession.settings`

        Returns
        -------
        TriviaSession
            The new trivia session being run.

        """
        session = cls(ctx, question_list, settings)
        loop = ctx.bot.loop
        session._task = loop.create_task(session.run())
        return session

    async def run(self):
        """Run the trivia session.

        In order for the trivia session to be stopped correctly, this should
        only be called internally by `TriviaSession.start`.
        """
        await self._send_startup_msg()
        max_score = self.settings["max_score"]
        delay = self.settings["delay"]
        timeout = self.settings["timeout"]
        for question, answers in self._iter_questions():
            async with self.ctx.typing():
                await asyncio.sleep(3)
            self.count += 1
            msg = "**Question number {}!**\n\n{}".format(self.count, question)
            await self.ctx.send(msg)
            continue_ = await self.wait_for_answer(answers, delay, timeout)
            if continue_ is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
        else:
            await self.ctx.send("There are no more questions!")
            await self.end_game()

    async def _send_startup_msg(self):
        list_names = []
        for idx, tup in enumerate(self.settings["lists"].items()):
            name, author = tup
            if author:
                title = "{} (by {})".format(name, author)
            else:
                title = name
            list_names.append(title)
        num_lists = len(list_names)
        if num_lists > 2:
            # at least 3 lists, join all but last with comma
            msg = ", ".join(list_names[: num_lists - 1])
            # join onto last with "and"
            msg = " and ".join((msg, list_names[num_lists - 1]))
        else:
            # either 1 or 2 lists, join together with "and"
            msg = " and ".join(list_names)
        await self.ctx.send("Starting Trivia: " + msg)

    def _iter_questions(self):
        """Iterate over questions and answers for this session.

        Yields
        ------
        `tuple`
            A tuple containing the question (`str`) and the answers (`tuple` of
            `str`).

        """
        for question, answers in self.question_list:
            answers = _parse_answers(answers)
            yield question, answers

    async def wait_for_answer(self, answers, delay: float, timeout: float):
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
                "message", check=self.check_answer(answers), timeout=delay
            )
        except asyncio.TimeoutError:
            if time.time() - self._last_response >= timeout:
                await self.ctx.send("Guys...? Well, I guess I'll stop then.")
                self.stop()
                return False
            if self.settings["reveal_answer"]:
                reply = random.choice(_REVEAL_MESSAGES).format(answers[0])
            else:
                reply = random.choice(_FAIL_MESSAGES)
            if self.settings["bot_plays"]:
                reply += " **+1** for me!"
                self.scores[self.ctx.guild.me] += 1
            await self.ctx.send(reply)
        else:
            self.scores[message.author] += 1
            reply = "You got it {}! **+1** to you!".format(message.author.display_name)
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
            early_exit = message.channel != self.ctx.channel or message.author == self.ctx.guild.me
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
        multiplier = self.settings["payout_multiplier"]
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
        self.ctx.bot.dispatch("trivia_end", self)

    def force_stop(self):
        """Cancel whichever tasks this session is running."""
        self._task.cancel()
        channel = self.ctx.channel
        LOG.debug("Force stopping trivia session; #%s in %s", channel, channel.guild.id)

    async def pay_winner(self, multiplier: float):
        """Pay the winner of this trivia session.

        The winner is only payed if there are at least 3 human contestants.

        Parameters
        ----------
        multiplier : float
            The coefficient of the winner's score, used to determine the amount
            paid.

        """
        (winner, score) = next((tup for tup in self.scores.most_common(1)), (None, None))
        me_ = self.ctx.guild.me
        if winner is not None and winner != me_ and score > 0:
            contestants = list(self.scores.keys())
            if me_ in contestants:
                contestants.remove(me_)
            if len(contestants) >= 3:
                amount = int(multiplier * score)
                if amount > 0:
                    LOG.debug("Paying trivia winner: %d credits --> %s", amount, str(winner))
                    await deposit_credits(winner, int(multiplier * score))
                    await self.ctx.send(
                        "Congratulations, {0}, you have received {1} credits"
                        " for coming first.".format(winner.display_name, amount)
                    )


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
