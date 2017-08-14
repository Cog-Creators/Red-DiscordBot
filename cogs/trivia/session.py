"""Module to manage trivia sessions."""

# This is a direct copy from V2's trivia cog by TwentySix.
#  Only very minor changes have been made so far to port
#  over to V3.

import asyncio
import time
from random import choice
from collections import Counter
from core.utils.chat_formatting import box

class TriviaSession():
    """A Trivia Session."""

    def __init__(self, bot, trivia_list, message, settings):
        self.bot = bot
        self.reveal_messages = ("I know this one! {}!",
                                "Easy: {}.",
                                "Oh really? It's {} of course.")
        self.fail_messages = ("To the next one I guess...",
                              "Moving on...",
                              "I'm sure you'll know the answer of the next one.",
                              "\N{PENSIVE FACE} Next one.")
        self.current_line = None # {"QUESTION" : "String", "ANSWERS" : []}
        self.question_list = trivia_list
        self.channel = message.channel
        self.starter = message.author
        self.scores = Counter()
        self.status = "new question"
        self.timer = None
        self.timeout = time.perf_counter()
        self.count = 0
        self.settings = settings

    async def stop_trivia(self):
        self.status = "stop"
        self.bot.dispatch("trivia_end", self)

    async def end_game(self):
        if self.scores:
            await self.send_table()
        await self.stop_trivia()

    async def new_question(self):
        for score in self.scores.values():
            if score == self.settings["max_score"]:
                await self.end_game()
                return True
        if self.question_list == []:
            await self.end_game()
            return True
        self.current_line = choice(self.question_list)
        self.question_list.remove(self.current_line)
        self.status = "waiting for answer"
        self.count += 1
        self.timer = int(time.perf_counter())
        msg = "**Question number {}!**\n\n{}".format(self.count, self.current_line.question)
        await self.channel.send(msg)

        while self.status != "correct answer" and abs(self.timer - int(time.perf_counter())) <= self.settings["delay"]:
            if abs(self.timeout - int(time.perf_counter())) >= self.settings["timeout"]:
                await self.channel.send("Guys...? Well, I guess I'll stop then.")
                await self.stop_trivia()
                return True
            await asyncio.sleep(1) #Waiting for an answer or for the time limit
        if self.status == "correct answer":
            self.status = "new question"
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.new_question()
        elif self.status == "stop":
            return True
        else:
            if self.settings["reveal_answer"]:
                msg = choice(self.reveal_messages).format(self.current_line.answers[0])
            else:
                msg = choice(self.fail_messages)
            if self.settings["bot_plays"]:
                msg += " **+1** for me!"
                self.scores[self.bot.user] += 1
            self.current_line = None
            await self.channel.send(msg)
            await self.channel.trigger_typing()
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.new_question()

    async def send_table(self):
        t = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            t += "+ {}\t{}\n".format(user, score)
        await self.channel.send(box(t, lang="diff"))

    async def check_answer(self, message):
        if message.author == self.bot.user:
            return
        elif self.current_line is None:
            return

        self.timeout = time.perf_counter()
        has_guessed = False

        for answer in self.current_line.answers:
            answer = answer.lower()
            guess = message.content.lower()
            if " " not in answer:  # Exact matching, issue #331
                guess = guess.split(" ")
                for word in guess:
                    if word == answer:
                        has_guessed = True
            else:  # The answer has spaces, we can't be as strict
                if answer in guess:
                    has_guessed = True

        if has_guessed:
            self.current_line = None
            self.status = "correct answer"
            self.scores[message.author] += 1
            msg = "You got it {}! **+1** to you!".format(message.author.display_name)
            await self.channel.send(msg)
