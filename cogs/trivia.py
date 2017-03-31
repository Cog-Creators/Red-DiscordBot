from discord.ext import commands
from random import choice
from .utils.dataIO import dataIO
from .utils import checks
from .utils.chat_formatting import box
import time
import os
import asyncio
import chardet


class Trivia:
    """General commands."""
    def __init__(self, bot):
        self.bot = bot
        self.trivia_sessions = []
        self.file_path = "data/trivia/settings.json"
        self.settings = dataIO.load_json(self.file_path)

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def triviaset(self, ctx):
        """Change trivia settings"""
        if ctx.invoked_subcommand is None:
            msg = "```\n"
            for k, v in self.settings.items():
                msg += "{}: {}\n".format(k, v)
            msg += "```\nSee {}help triviaset to edit the settings".format(ctx.prefix)
            await self.bot.say(msg)

    @triviaset.command()
    async def maxscore(self, score : int):
        """Points required to win"""
        if score > 0:
            self.settings["TRIVIA_MAX_SCORE"] = score
            dataIO.save_json(self.file_path, self.settings)
            await self.bot.say("Points required to win set to {}".format(str(score)))
        else:
            await self.bot.say("Score must be superior to 0.")

    @triviaset.command()
    async def timelimit(self, seconds : int):
        """Maximum seconds to answer"""
        if seconds > 4:
            self.settings["TRIVIA_DELAY"] = seconds
            dataIO.save_json(self.file_path, self.settings)
            await self.bot.say("Maximum seconds to answer set to {}".format(str(seconds)))
        else:
            await self.bot.say("Seconds must be at least 5.")

    @triviaset.command()
    async def botplays(self):
        """Red gains points"""
        if self.settings["TRIVIA_BOT_PLAYS"] is True:
            self.settings["TRIVIA_BOT_PLAYS"] = False
            await self.bot.say("Alright, I won't embarass you at trivia anymore.")
        else:
            self.settings["TRIVIA_BOT_PLAYS"] = True
            await self.bot.say("I'll gain a point everytime you don't answer in time.")
        dataIO.save_json(self.file_path, self.settings)

    @commands.group(pass_context=True, invoke_without_command=True)
    async def trivia(self, ctx, list_name: str):
        """Start a trivia session with the specified list"""
        message = ctx.message
        session = self.get_trivia_by_channel(message.channel)
        if not session:
            t = TriviaSession(self.bot, message.channel, self.settings)
            self.trivia_sessions.append(t)
            await t.load_questions(list_name)
        else:
            await self.bot.say("A trivia session is already ongoing in this channel.")

    @trivia.group(name="stop", pass_context=True)
    async def trivia_stop(self, ctx):
        """Stops an ongoing trivia session"""
        session = self.get_trivia_by_channel(ctx.message.channel)
        if session:
            await session.end_game()
            await self.bot.say("Trivia stopped.")
        else:
            await self.bot.say("There's no trivia session ongoing in this channel.")

    @trivia.group(name="list")
    async def trivia_list(self):
        """Shows available trivia lists"""
        lists = os.listdir("data/trivia/")
        lists = [l for l in lists if l.endswith(".txt") and " " not in l]
        lists = [l.replace(".txt", "") for l in lists]

        if lists:
            msg = "+ Available trivia lists\n\n" + ", ".join(lists)
            msg = box(msg, lang="diff")
            if len(lists) < 100:
                await self.bot.say(msg)
            else:
                await self.bot.whisper(msg)
        else:
            await self.bot.say("There are no trivia lists available.")

    def get_trivia_by_channel(self, channel):
        for t in self.trivia_sessions:
            if t.channel == channel:
                return t
        return None

    async def on_message(self, message):
        if message.author != self.bot.user:
            session = self.get_trivia_by_channel(message.channel)
            if session:
                await session.check_answer(message)

    async def on_trivia_end(self, instance):
        if instance in self.trivia_sessions:
            self.trivia_sessions.remove(instance)


class TriviaSession():
    def __init__(self, bot, channel, settings):
        self.bot = bot
        self.gave_answer = ["I know this one! {}!", "Easy: {}.", "Oh really? It's {} of course."]
        self.current_q = None # {"QUESTION" : "String", "ANSWERS" : []}
        self.question_list = ""
        self.channel = channel
        self.score_list = {}
        self.status = None
        self.timer = None
        self.count = 0
        self.settings = settings

    async def load_questions(self, filename):
        path = "data/trivia/{}.txt".format(filename)
        if os.path.isfile(path):
            self.question_list = await self.load_list(path)
            self.status = "new question"
            self.timeout = time.perf_counter()
            if self.question_list:
                await self.new_question()
        else:
            await self.bot.say("There is no list with that name.")
            await self.stop_trivia()

    async def stop_trivia(self):
        self.status = "stop"
        self.bot.dispatch("trivia_end", self)

    async def end_game(self):
        self.status = "stop"
        if self.score_list:
            await self.send_table()
        self.bot.dispatch("trivia_end", self)

    def guess_encoding(self, trivia_list):
        with open(trivia_list, "rb") as f:
            try:
                return chardet.detect(f.read())["encoding"]
            except:
                return "ISO-8859-1"

    async def load_list(self, qlist):
        encoding = self.guess_encoding(qlist)
        with open(qlist, "r", encoding=encoding) as f:
            qlist = f.readlines()
        parsed_list = []
        for line in qlist:
            if "`" in line and len(line) > 4:
                line = line.replace("\n", "")
                line = line.split("`")
                question = line[0]
                answers = []
                for l in line[1:]:
                    answers.append(l.lower().strip())
                if len(line) >= 2:
                    line = {"QUESTION" : question, "ANSWERS": answers} #string, list
                    parsed_list.append(line)
        if parsed_list != []:
            return parsed_list
        else:
            await self.stop_trivia()
            return None

    async def new_question(self):
        for score in self.score_list.values():
            if score == self.settings["TRIVIA_MAX_SCORE"]:
                await self.end_game()
                return True
        if self.question_list == []:
            await self.end_game()
            return True
        self.current_q = choice(self.question_list)
        self.question_list.remove(self.current_q)
        self.status = "waiting for answer"
        self.count += 1
        self.timer = int(time.perf_counter())
        msg = "**Question number {}!**\n\n{}".format(str(self.count), self.current_q["QUESTION"])
        try:
            await self.bot.say(msg)
        except:
            await asyncio.sleep(0.5)
            await self.bot.say(msg)

        while self.status != "correct answer" and abs(self.timer - int(time.perf_counter())) <= self.settings["TRIVIA_DELAY"]:
            if abs(self.timeout - int(time.perf_counter())) >= self.settings["TRIVIA_TIMEOUT"]:
                await self.bot.say("Guys...? Well, I guess I'll stop then.")
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
            msg = choice(self.gave_answer).format(self.current_q["ANSWERS"][0])
            if self.settings["TRIVIA_BOT_PLAYS"]:
                msg += " **+1** for me!"
                self.add_point(self.bot.user.name)
            self.current_q["ANSWERS"] = []
            try:
                await self.bot.say(msg)
                await self.bot.send_typing(self.channel)
            except:
                await asyncio.sleep(0.5)
                await self.bot.say(msg)
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.new_question()

    async def send_table(self):
        self.score_list = sorted(self.score_list.items(), reverse=True, key=lambda x: x[1]) # orders score from lower to higher
        t = "```Scores: \n\n"
        for score in self.score_list:
            t += score[0] # name
            t += "\t"
            t += str(score[1]) # score
            t += "\n"
        t += "```"
        await self.bot.say(t)

    async def check_answer(self, message):
        if message.author.id != self.bot.user.id:
            self.timeout = time.perf_counter()
            if self.current_q is not None:
                for answer in self.current_q["ANSWERS"]:
                    if answer in message.content.lower():
                        self.current_q["ANSWERS"] = []
                        self.status = "correct answer"
                        self.add_point(message.author.name)
                        msg = "You got it {}! **+1** to you!".format(message.author.name)
                        try:
                            await self.bot.send_typing(self.channel)
                            await self.bot.send_message(message.channel, msg)
                        except:
                            await asyncio.sleep(0.5)
                            await self.bot.send_message(message.channel, msg)
                        return True

    def add_point(self, user):
        if user in self.score_list:
            self.score_list[user] += 1
        else:
            self.score_list[user] = 1


def check_folders():
    folders = ("data", "data/trivia/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    settings = {"TRIVIA_MAX_SCORE" : 10, "TRIVIA_TIMEOUT" : 120,  "TRIVIA_DELAY" : 15, "TRIVIA_BOT_PLAYS" : False}

    if not os.path.isfile("data/trivia/settings.json"):
        print("Creating empty settings.json...")
        dataIO.save_json("data/trivia/settings.json", settings)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Trivia(bot))
