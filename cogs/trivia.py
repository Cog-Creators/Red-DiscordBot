import discord
from discord.ext import commands
from random import randint
from random import choice as randchoice
import datetime
import time
import os
import asyncio

settings = {"TRIVIA_MAX_SCORE" : 10, "TRIVIA_TIMEOUT" : 120,  "TRIVIA_DELAY" : 15, "TRIVIA_BOT_PLAYS" : False}

class Trivia:
    """General commands."""
    def __init__(self, bot):
        self.bot = bot
        self.trivia_sessions = []

    @commands.command(pass_context=True)
    async def trivia(self, ctx, list_name : str=None):
        """Start a trivia session with the specified list

        trivia stop - Ends the current session
        trivia - Shows trivia lists
        """
        message = ctx.message
        if list_name == None:
            await self.triviaList(ctx.message.author)
        elif list_name.lower() == "stop":
            if await getTriviabyChannel(message.channel):
                s = await getTriviabyChannel(message.channel)
                await s.endGame()
                await self.bot.say("`Trivia stopped.`")
            else:
                await self.bot.say("`There's no trivia session ongoing in this channel.`")
        elif not await getTriviabyChannel(message.channel):
            t = TriviaSession(message)
            self.trivia_sessions.append(t)
            await t.loadQuestions(message.content)
        else:
            await self.bot.say("`A trivia session is already ongoing in this channel.`")

    async def triviaList(self, author):
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
                await self.bot.send_message(author, msg)
            else:
                await self.bot.say("There are no trivia lists available.")
        else:
            await self.bot.say("There are no trivia lists available.")

class TriviaSession():
    def __init__(self, message):
        self.gaveAnswer = ["I know this one! {}!", "Easy: {}.", "Oh really? It's {} of course."]
        self.currentQ = None # {"QUESTION" : "String", "ANSWERS" : []}
        self.questionList = ""
        self.channel = message.channel
        self.scoreList = {}
        self.status = None
        self.timer = None
        self.count = 0

    async def loadQuestions(self, msg):
        msg = msg.split(" ")
        if len(msg) == 2:
            _, qlist = msg
            if qlist == "random":
                chosenList = randchoice(glob.glob("data/trivia/*.txt"))
                self.questionList = self.loadList(chosenList)
                self.status = "new question"
                self.timeout = time.perf_counter()
                if self.questionList: await self.newQuestion()
            else:
                if os.path.isfile("data/trivia/" + qlist + ".txt"):
                    self.questionList = self.loadList("data/trivia/" + qlist + ".txt")
                    self.status = "new question"
                    self.timeout = time.perf_counter()
                    if self.questionList: await self.newQuestion()
                else:
                    await triviaManager.bot.say("`There is no list with that name.`")
                    await self.stopTrivia()
        else:
            await triviaManager.bot.say("`trivia [list name]`")

    async def stopTrivia(self):
        self.status = "stop"
        triviaManager.trivia_sessions.remove(self)

    async def endGame(self):
        self.status = "stop"
        if self.scoreList:
            await self.sendTable()
        triviaManager.trivia_sessions.remove(self)

    def loadList(self, qlist):
        with open(qlist, "r", encoding="ISO-8859-1") as f:
            qlist = f.readlines()
        parsedList = []
        for line in qlist:
            if "`" in line and len(line) > 4:
                line = line.replace("\n", "")
                line = line.split("`")
                question = line[0]
                answers = []
                for l in line[1:]:
                    answers.append(l.lower())
                if len(line) >= 2:
                    line = {"QUESTION" : question, "ANSWERS": answers} #string, list
                    parsedList.append(line)
        if parsedList != []:
            return parsedList
        else:
            self.stopTrivia()
            return None

    async def newQuestion(self):
        for score in self.scoreList.values():
            if score == settings["TRIVIA_MAX_SCORE"]:
                await self.endGame()
                return True
        if self.questionList == []:
            await self.endGame()
            return True
        self.currentQ = randchoice(self.questionList)
        self.questionList.remove(self.currentQ)
        self.status = "waiting for answer"
        self.count += 1
        self.timer = int(time.perf_counter())
        await triviaManager.bot.say("**Question number {}!**\n\n{}".format(str(self.count), self.currentQ["QUESTION"]))
        while self.status != "correct answer" and abs(self.timer - int(time.perf_counter())) <= settings["TRIVIA_DELAY"]:
            if abs(self.timeout - int(time.perf_counter())) >= settings["TRIVIA_TIMEOUT"]:
                await triviaManager.bot.say("Guys...? Well, I guess I'll stop then.")
                await self.stopTrivia()
                return True
            await asyncio.sleep(1) #Waiting for an answer or for the time limit
        if self.status == "correct answer":
            self.status = "new question"
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.newQuestion()
        elif self.status == "stop":
            return True
        else:
            msg = randchoice(self.gaveAnswer).format(self.currentQ["ANSWERS"][0])
            if settings["TRIVIA_BOT_PLAYS"]:
                msg += " **+1** for me!"
                self.addPoint(self.bot.user.name)
            self.currentQ["ANSWERS"] = []
            await triviaManager.bot.say(msg)
            await triviaManager.bot.send_typing(self.channel)
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.newQuestion()
        
    async def sendTable(self):
        self.scoreList = sorted(self.scoreList.items(), reverse=True, key=lambda x: x[1]) # orders score from lower to higher
        t = "```Scores: \n\n"
        for score in self.scoreList:
            t += score[0] # name
            t += "\t"
            t += str(score[1]) # score
            t += "\n"
        t += "```"
        await triviaManager.bot.say(t)

    async def checkAnswer(self, message):
        self.timeout = time.perf_counter()
        for answer in self.currentQ["ANSWERS"]:
            if answer in message.content.lower():
                self.currentQ["ANSWERS"] = []
                self.status = "correct answer"
                self.addPoint(message.author.name)
                await triviaManager.bot.send_message(message.channel, "You got it {}! **+1** to you!".format(message.author.name))
                await triviaManager.bot.send_typing(self.channel)
                return True

    def addPoint(self, user):
        if user in self.scoreList:
            self.scoreList[user] += 1
        else:
            self.scoreList[user] = 1

    def getTriviaQuestion(self):
        q = randchoice(list(trivia_questions.keys()))
        return q, trivia_questions[q] # question, answer

async def getTriviabyChannel(channel):
        for t in triviaManager.trivia_sessions:
            if t.channel == channel:
                return t
        return False

async def checkMessages(message):
    if message.author.id != triviaManager.bot.user.id:
        if await getTriviabyChannel(message.channel):
            trvsession = await getTriviabyChannel(message.channel)
            await trvsession.checkAnswer(message)

def setup(bot):
    global triviaManager
    bot.add_listener(checkMessages, "on_message")
    triviaManager = Trivia(bot)
    bot.add_cog(triviaManager)
