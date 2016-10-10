import discord
from discord.ext import commands
from random import randint
from random import choice as randchoice
from .utils.dataIO import dataIO
from .utils import checks
import datetime
import time
import os
import asyncio

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

    @commands.command(pass_context=True)
    async def trivia(self, ctx, list_name : str=None):
        """Start a trivia session with the specified list

        trivia stop - Ends the current session
        trivia - Shows trivia lists
        """
        message = ctx.message
        if list_name == None:
            await self.trivia_list(ctx.message.author)
        elif list_name.lower() == "stop":
            if await get_trivia_by_channel(message.channel):
                s = await get_trivia_by_channel(message.channel)
                await s.end_game()
                await self.bot.say("Trivia stopped.")
            else:
                await self.bot.say("There's no trivia session ongoing in this channel.")
        elif not await get_trivia_by_channel(message.channel):
            t = TriviaSession(message, self.settings)
            self.trivia_sessions.append(t)
            await t.load_questions(message.content)
        else:
            await self.bot.say("A trivia session is already ongoing in this channel.")

    async def trivia_list(self, author):
        msg = "**Available trivia lists:** \n\n```"
        lists = os.listdir("data/trivia/")
        if lists:
            clean_list = []
            for txt in lists:
                if txt.endswith(".txt") and " " not in txt:
                    txt = txt.replace(".txt", "")
                    clean_list.append(txt)
            if clean_list:
                for i, d in enumerate(clean_list):
                    if i % 4 == 0 and i != 0:
                        msg = msg + d + "\n"
                    else:
                        msg = msg + d + "\t"
                msg += "```"
                if len(clean_list) > 100:
                    await self.bot.send_message(author, msg)
                else:
                    await self.bot.say(msg)
            else:
                await self.bot.say("There are no trivia lists available.")
        else:
            await self.bot.say("There are no trivia lists available.")

class TriviaSession():
    def __init__(self, message, settings):
        self.gave_answer = ["I know this one! {}!", "Easy: {}.", "Oh really? It's {} of course."]
        self.current_q = None # {"QUESTION" : "String", "ANSWERS" : []}
        self.question_list = ""
        self.channel = message.channel
        self.score_list = {}
        self.status = None
        self.timer = None
        self.count = 0
        self.settings = settings

    async def load_questions(self, msg):
        msg = msg.split(" ")
        if len(msg) == 2:
            _, qlist = msg
            if qlist == "random":
                chosen_list = randchoice(glob.glob("data/trivia/*.txt"))
                self.question_list = self.load_list(chosen_list)
                self.status = "new question"
                self.timeout = time.perf_counter()
                if self.question_list: await self.new_question()
            else:
                if os.path.isfile("data/trivia/" + qlist + ".txt"):
                    self.question_list = await self.load_list("data/trivia/" + qlist + ".txt")
                    self.status = "new question"
                    self.timeout = time.perf_counter()
                    if self.question_list: await self.new_question()
                else:
                    await trivia_manager.bot.say("There is no list with that name.")
                    await self.stop_trivia()
        else:
            await trivia_manager.bot.say("trivia [list name]")

    async def stop_trivia(self):
        self.status = "stop"
        trivia_manager.trivia_sessions.remove(self)

    async def end_game(self):
        self.status = "stop"
        if self.score_list:
            await self.send_table()
        trivia_manager.trivia_sessions.remove(self)

    async def load_list(self, qlist):
        with open(qlist, "r", encoding="ISO-8859-1") as f:
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
        self.current_q = randchoice(self.question_list)
        self.question_list.remove(self.current_q)
        self.status = "waiting for answer"
        self.count += 1
        self.timer = int(time.perf_counter())
        msg = "**Question number {}!**\n\n{}".format(str(self.count), self.current_q["QUESTION"])
        try:
            await trivia_manager.bot.say(msg)
        except:
            await asyncio.sleep(0.5)
            await trivia_manager.bot.say(msg)

        while self.status != "correct answer" and abs(self.timer - int(time.perf_counter())) <= self.settings["TRIVIA_DELAY"]:
            if abs(self.timeout - int(time.perf_counter())) >= self.settings["TRIVIA_TIMEOUT"]:
                await trivia_manager.bot.say("Guys...? Well, I guess I'll stop then.")
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
            msg = randchoice(self.gave_answer).format(self.current_q["ANSWERS"][0])
            if self.settings["TRIVIA_BOT_PLAYS"]:
                msg += " **+1** for me!"
                self.add_point(trivia_manager.bot.user.name)
            self.current_q["ANSWERS"] = []
            try:
                await trivia_manager.bot.say(msg)
                await trivia_manager.bot.send_typing(self.channel)
            except:
                await asyncio.sleep(0.5)
                await trivia_manager.bot.say(msg)
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
        await trivia_manager.bot.say(t)

    async def check_answer(self, message):
        if message.author.id != trivia_manager.bot.user.id:
            self.timeout = time.perf_counter()
            if self.current_q is not None:
                for answer in self.current_q["ANSWERS"]:
                    if answer in message.content.lower():
                        self.current_q["ANSWERS"] = []
                        self.status = "correct answer"
                        self.add_point(message.author.name)
                        msg = "You got it {}! **+1** to you!".format(message.author.name)
                        try:
                            await trivia_manager.bot.send_typing(self.channel)
                            await trivia_manager.bot.send_message(message.channel, msg)
                        except:
                            await asyncio.sleep(0.5)
                            await trivia_manager.bot.send_message(message.channel, msg)
                        return True

    def add_point(self, user):
        if user in self.score_list:
            self.score_list[user] += 1
        else:
            self.score_list[user] = 1

    def get_trivia_question(self):
        q = randchoice(list(trivia_questions.keys()))
        return q, trivia_questions[q] # question, answer

async def get_trivia_by_channel(channel):
        for t in trivia_manager.trivia_sessions:
            if t.channel == channel:
                return t
        return False

async def check_messages(message):
    if message.author.id != trivia_manager.bot.user.id:
        if await get_trivia_by_channel(message.channel):
            trvsession = await get_trivia_by_channel(message.channel)
            await trvsession.check_answer(message)


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
    global trivia_manager
    check_folders()
    check_files()
    bot.add_listener(check_messages, "on_message")
    trivia_manager = Trivia(bot)
    bot.add_cog(trivia_manager)
