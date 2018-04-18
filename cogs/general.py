import discord
from discord.ext import commands
from .utils.chat_formatting import escape_mass_mentions, italics, pagify
from cogs.utils import checks
from random import randint
from random import choice
from enum import Enum
from urllib.parse import quote_plus
import datetime
import time
import aiohttp
import asyncio

settings = {"POLL_DURATION" : 60}


class RPS(Enum):
    rock     = "\N{MOYAI}"
    paper    = "\N{PAGE FACING UP}"
    scissors = "\N{BLACK SCISSORS}"


class RPSParser:
    def __init__(self, argument):
        argument = argument.lower()
        if argument == "rock":
            self.choice = RPS.rock
        elif argument == "paper":
            self.choice = RPS.paper
        elif argument == "scissors":
            self.choice = RPS.scissors
        else:
            raise


class General:
    """General commands."""

    def __init__(self, bot):
        self.bot = bot
        self.stopwatches = {}
        self.ball = ["As I see it, yes", "It is certain", "It is decidedly so", "Most likely", "Outlook good",
                     "Signs point to yes", "Without a doubt", "Yes", "Yes – definitely", "You may rely on it", "Reply hazy, try again",
                     "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
                     "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
        self.poll_sessions = []
        self.owo = ["​✪w✪", "¤w¤", "∅w∅", "⊗w⊗", "⊕w⊕", "∞w∞", "∆w∆", "θwθ", "δwδ", "①w①", "②w②", "③w③", "④w④", "⑤w⑤", "⑥w⑥", "⑦w⑦", "⑧w⑧", "⑨w⑨",
                    "⑩w⑩", "⑴w⑴", "⑵w⑵", "⑶w⑶", "⑷w⑷", "⑸w⑸", "⑹w⑹", "⑺w⑺", "⑻w⑻", "⑼w⑼", "⑽w⑽", "●w●", "○w○",
                    "■w■", "□w□", "★w★", "☆w☆", "◆w◆", "◇w◇", "▷w◁", "◐w◐", "◑w◑", "◐w◑", "◐w◑", "♀w♀", "♂w♂", "♡w♡", "❖w❖", "✞w✞", "©w©", "®w®"
                    "✧w✧", "✦w✦", "✩w✩", "✫w✫", "✬w✬", "✭w✭", "✮w✮", "✯w✯", "✰w✰", "✱w✱", "✲w✲", "✵w✵", "✶w✶", "✷w✷", ">w0",
                    "✸w✸", "※w※","↻w↻", "σwσ", "✹w✹", "✺w✺", "✻w✻", "✼w✼", "✽w✽", "✾w✾", "✿w✿", "❀w❀", "❁w❁", "❂w❂", "❃w❃", "❅w❅",
                    "❆w❆", "❈w❈", "❉w❉", "❊w❊", "❋w❋", "❍w❍", "❏w❏", "❐w❐", "❑w❑", "❒w❒", "◈w◈", "◉w◉", "◊w◊", "○w○", "ФwФ", "фwф", "юwю", "ЮwЮ"
                    "#w#", "@w@", "0w0", ";w;", "¢w¢", "×w×", "°w°", "OwO", "owo", "uwu", "UwU", "QwQ", "ОмО", "ОпО", "ОшО", "OnO", "ДwД", "ЖwЖ", "XwX", "qwq", "dwd", "DwD" "ИwИ", "ーwー"]

        self.owoeyes = ["​✪", "¤", "∅", "⊗", "⊕", "∞", "∆", "θ", "δ", "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨",
                    "⑩", "⑴", "⑵", "⑶", "⑷", "⑸", "⑹", "⑺", "⑻", "⑼", "⑽", "●", "○",
                    "■", "□", "★", "☆", "◆", "◇", "▷", "◁", "◐", "◑", "♀", "♂", "♡", "❖", "✞", "©", "®", ">", "<",
                    "✧", "✦", "✩", "✫", "✬", "✭", "✮", "✯", "✰", "✱", "✲", "✵", "✶", "✷",
                    "✸", "※","↻", "σ", "✹", "✺", "✻", "✼", "✽", "✾", "✿", "❀", "❁", "❂", "❃", "❅",
                    "❆", "❈", "❉", "❊", "❋", "❍", "❏", "❐", "❑", "❒", "◈", "◉", "◊", "○", "Ф", "ф", "ю", "Ю"
                    "#", "@", "0", ";", "¢", "×", "°w°", "O", "o", "u", "U", "Q", "О", "О", "О", "O", "Д", "Ж", "X", "q", "d", "D" "И", "ー"]
 
        self.owomouths = ["w", "п", "ш", "м"]
        self.interactions = ["{0} nuzzled {1}", "{0} gave {1} a hug", "{0} hopped on top of {1} and licked their ears -w-", "{0} whispered {1} a secret...", "{0} booped {1}", "{0} tackled down and {1} snuggled them"]


    @commands.command(pass_context=True, no_pm=True)
    async def int(self, ctx, user : discord.Member=None):
        """Interacts with other users [don't sue me waspy]"""
        author = ctx.message.author
        if not user:
            await self.bot.say("who do you wanna interact with..?")
        else:
            await self.bot.say("**" + choice(self.interactions).format(author.display_name, user.display_name) + "**")

    @commands.command(pass_context=True)
    async def say(self, ctx, *, text):
        """Bot repeats what you tell it to"""
        server = ctx.message.server
        server1 = self.bot.get_server("357238060754272258")
        channel2 = server1.get_channel("409168557147160587")
        channel = ctx.message.channel
        author = ctx.message.author
        lul = discord.Embed(description="**" + author.name + "**: " + text, color=0x4aaae8)
        lul.set_author(name="{} ({})".format(server.name, server.id), icon_url=server.icon_url)
        can_del = channel.permissions_for(server.me).manage_messages
        lul2 = discord.Embed(title="In {} ({}):".format(server.name, server.id), description="**" + author.name + "** attempted a mass ping.\nIn <#" + channel.id + ">", color=0xda004e)
        if "@everyone" in text or "@here" in text: 
            await self.bot.say("nope.")
            await self.bot.send_message(channel2, embed=lul2)
            print(author.name + " attempted to ping everyone.")
        elif not can_del:
            await self.bot.say("I need to be able to delete messages, gimme the `manange messages` permission and try again.")
        else:
            await self.bot.delete_message(ctx.message)
            await self.bot.send_message(channel, text)
            await self.bot.send_message(channel2, embed=lul)
            print(author.name + " said: " + text)
       


    @commands.command(hidden=True)
    async def beep(self):
         msg = await self.bot.say("` `")
         wait = 1.3

         await self.bot.edit_message(msg, "`_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "` `")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`b_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`bo_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boo_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boop_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boop._`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boop. _`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boop. :_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boop. :3_`")
         await asyncio.sleep(wait)
         await self.bot.edit_message(msg, "`boop. :3 `")

 
    @commands.command(name="owomachine", aliases=["owogen"])
    async def owomachine(self):
        """Generates an owo courtesy of skywire"""
        await self.bot.say(choice(self.owo))

    @commands.command()
    async def choose(self, *choices):
        """Chooses between multiple choices.

        To denote multiple choices, you should use double quotes.
        """
        choices = [escape_mass_mentions(c) for c in choices]
        if len(choices) < 2:
            await self.bot.say('Not enough choices to pick from.')
        else:
            await self.bot.say(choice(choices))

    @commands.command(pass_context=True)
    async def roll(self, ctx, number : int = 100):
        """Rolls random number (between 1 and user choice)

        Defaults to 100.
        """
        author = ctx.message.author
        if number > 1:
            n = randint(1, number)
            await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, n))
        else:
            await self.bot.say("{} Maybe higher than 1? ;P".format(author.mention))

    @commands.command(pass_context=True)
    async def flip(self, ctx, user : discord.Member=None):
        """Flips a coin... or a user.

        Defaults to coin.
        """
        if user != None:
            msg = ""
            if user.id == self.bot.user.id:
                user = ctx.message.author
                msg = "Nice try. You think this is funny? How about *this* instead:\n\n"
            char = "abcdefghijklmnopqrstuvwxyz"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
            table = str.maketrans(char, tran)
            name = user.display_name.translate(table)
            char = char.upper()
            tran = "∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name = name.translate(table)
            await self.bot.say(msg + "(╯°□°）╯︵ " + name[::-1])
        else:
            await self.bot.say("*flips a coin and... " + choice(["HEADS!*", "TAILS!*"]))

    @commands.command(pass_context=True)
    async def rps(self, ctx, your_choice : RPSParser):
        """Play rock paper scissors"""
        author = ctx.message.author
        player_choice = your_choice.choice
        red_choice = choice((RPS.rock, RPS.paper, RPS.scissors))
        cond = {
                (RPS.rock,     RPS.paper)    : False,
                (RPS.rock,     RPS.scissors) : True,
                (RPS.paper,    RPS.rock)     : True,
                (RPS.paper,    RPS.scissors) : False,
                (RPS.scissors, RPS.rock)     : False,
                (RPS.scissors, RPS.paper)    : True
               }

        if red_choice == player_choice:
            outcome = None # Tie
        else:
            outcome = cond[(player_choice, red_choice)]

        if outcome is True:
            await self.bot.say("{} You win {}!"
                               "".format(red_choice.value, author.mention))
        elif outcome is False:
            await self.bot.say("{} You lose {}!"
                               "".format(red_choice.value, author.mention))
        else:
            await self.bot.say("{} We're square {}!"
                               "".format(red_choice.value, author.mention))

    @commands.command(name="8", aliases=["8ball"])
    async def _8ball(self, *, question : str):
        """Ask 8 ball a question

        Question must end with a question mark.
        """
        if question.endswith("?") and question != "?":
            await self.bot.say("`" + choice(self.ball) + "`")
        else:
            await self.bot.say("That doesn't look like a question.")

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        """pseudo-ping time"""
        channel = ctx.message.channel
        t1 = time.perf_counter()
        anotherembed = discord.Embed(description="Wait...")
        ayy = await self.bot.say(embed=anotherembed)
        t2 = time.perf_counter()
        t5 = discord.Embed(description="**Pong " + choice(self.owo) + "** `{}ms`".format(round((t2-t1)*1000)))
        await self.bot.edit_message(ayy, embed=t5)

    @commands.command(aliases=["sw"], pass_context=True)
    async def stopwatch(self, ctx):
        """Starts/stops stopwatch"""
        author = ctx.message.author
        if not author.id in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await self.bot.say(author.mention + " Stopwatch started!")
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(datetime.timedelta(seconds=tmp))
            await self.bot.say(author.mention + " Stopwatch stopped! Time: **" + tmp + "**")
            self.stopwatches.pop(author.id, None)

    @commands.command()
    async def lmgtfy(self, *, search_terms : str):
        """Creates a lmgtfy link"""
        search_terms = escape_mass_mentions(search_terms.replace(" ", "+"))
        await self.bot.say("https://lmgtfy.com/?q={}".format(search_terms))

    @commands.command(no_pm=True, hidden=True)
    async def hug(self, user : discord.Member, intensity : int=1):
        """Because everyone likes hugs

        Up to 10 intensity levels."""
        name = italics(user.display_name)
        if intensity <= 0:
            msg = "(っ˘̩╭╮˘̩)っ" + name
        elif intensity <= 3:
            msg = "(っ´▽｀)っ" + name
        elif intensity <= 6:
            msg = "╰(*´︶`*)╯" + name
        elif intensity <= 9:
            msg = "(つ≧▽≦)つ" + name
        elif intensity >= 10:
            msg = "(づ￣ ³￣)づ{} ⊂(´・ω・｀⊂)".format(name)
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def user(self, ctx, *, user: discord.Member=None):
        """Shows users's informations"""
        author = ctx.message.author
        server = ctx.message.server
        if not user:
            user = author

        roles = [x.name for x in user.roles if x.name != "@everyone"]
        
        joined_at = self.fetch_joined_at(user, server)
        since_created = (ctx.message.timestamp - user.created_at).days
        since_joined = (ctx.message.timestamp - joined_at).days
        user_joined = joined_at.strftime("%d %b %Y %H:%M")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")
        member_number = sorted(server.members,
                               key=lambda m: m.joined_at).index(user) + 1

        created_on = "{}\n({} days ago)".format(user_created, since_created)
        joined_on = "{}\n({} days ago)".format(user_joined, since_joined)

        game = "Chilling in **{}** status".format(user.status)

        if user.game is None:
            pass
        elif user.game.url is None:
            game = "Playing **{}**".format(user.game)
        else:
            game = "Streaming: [{}]({})".format(user.game, user.game.url)

        if roles:
            roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                       if x.name != "@everyone"].index)
            roles = ", ".join(roles)
        else:
            roles = "None"

        if user.bot:
           lol = "Bot account :robot:"
        elif user.id == "158750488563679232":
           lol = "Goodest boy :dog:"
        elif user.id == "365255872181567489":
           lol = "\nHey it's me owo"
        else:
           lol = ""

        data = discord.Embed(title=lol, description=game, colour=user.colour)
        data.add_field(name="Joined Discord on", value=created_on)
        data.add_field(name="Joined this server on", value=joined_on)
        data.add_field(name="User Color", value=user.color)
        data.add_field(name="Roles", value=roles, inline=False)
        data.set_footer(text="Member #{} | User ID:{}"
                             "".format(member_number, user.id))

        name = str(user.name)
        name = " ~ ".join((name, user.nick)) if user.nick else name

        if user.avatar_url:
            data.set_author(name=name, icon_url=user.avatar_url)
            data.set_thumbnail(url=user.avatar_url)
        else:
            data.set_author(name=name)

        try:
            await self.bot.say(embed=data)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")

    @commands.command(pass_context=True, no_pm=True)
    async def server(self, ctx):
        """Shows server's informations"""
        server = ctx.message.server
        online = len([m.status for m in server.members
                      if m.status == discord.Status.online or
                      m.status == discord.Status.idle])
        total_users = len(server.members)
        text_channels = len([x for x in server.channels
                             if x.type == discord.ChannelType.text])
        voice_channels = len([x for x in server.channels
                             if x.type == discord.ChannelType.voice])
        passed = (ctx.message.timestamp - server.created_at).days
        created_at = ("Since {}. That's over {} days ago!"
                      "".format(server.created_at.strftime("%d %b %Y %H:%M"),
                                passed))

        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        data = discord.Embed(
            description=created_at,
            colour=discord.Colour(value=colour))
        data.add_field(name="Region", value=str(server.region))
        data.add_field(name="Users", value="{}/{}".format(online, total_users))
        data.add_field(name="Text Channels", value=text_channels)
        data.add_field(name="Voice Channels", value=voice_channels)
        data.add_field(name="Roles", value=len(server.roles))
        data.add_field(name="Owner", value=str(server.owner))
        data.set_footer(text="Server ID: " + server.id, icon_url=server.icon_url)

        if server.icon_url:
            data.set_author(name=server.name, url=server.icon_url)
            data.set_thumbnail(url=server.icon_url)
        else:
            data.set_author(name=server.name)

        try:
            await self.bot.say(embed=data)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")

    @commands.command()
    async def urban(self, *, search_terms : str, definition_number : int=1):
        """Urban Dictionary search

        Definition number must be between 1 and 10"""
        def encode(s):
            return quote_plus(s, encoding='utf-8', errors='replace')

        # definition_number is just there to show up in the help
        # all this mess is to avoid forcing double quotes on the user

        search_terms = search_terms.split(" ")
        try:
            if len(search_terms) > 1:
                pos = int(search_terms[-1]) - 1
                search_terms = search_terms[:-1]
            else:
                pos = 0
            if pos not in range(0, 11): # API only provides the
                pos = 0                 # top 10 definitions
        except ValueError:
            pos = 0

        search_terms = "+".join([encode(s) for s in search_terms])
        url = "http://api.urbandictionary.com/v0/define?term=" + search_terms
        try:
            async with aiohttp.get(url) as r:
                result = await r.json()
            if result["list"]:
                definition = result['list'][pos]['definition']
                example = result['list'][pos]['example']
                defs = len(result['list'])
                msg = ("**Definition #{} out of {}:\n**{}\n\n"
                       "**Example:\n**{}".format(pos+1, defs, definition,
                                                 example))
                msg = pagify(msg, ["\n"])
                for page in msg:
                    await self.bot.say(page)
            else:
                await self.bot.say("Your search terms gave no results.")
        except IndexError:
            await self.bot.say("There is no definition #{}".format(pos+1))
        except:
            await self.bot.say("Error.")
    

    @commands.command(no_pm=True, pass_context=True)
    async def bancheck(self, ctx, user_id: int):
        """Checks for bans on discordservices"""
        if not user_id:
             await self.bot.say("no id specified. try again you hec.")
        try:
            user = await self.bot.get_user_info(user_id)
        except discord.errors.NotFound:
            await self.bot.say("hrrm. I can't match a user to the id you provided.")  
            return
        except:
            await self.bot.say('random error. oof.')
            return       
         
    @commands.command(pass_context=True, no_pm=True)
    async def poll(self, ctx, *text):
        """Starts/stops a poll

        Usage example:
        poll Is this a poll?;Yes;No;Maybe
        poll stop"""
        message = ctx.message
        if len(text) == 1:
            if text[0].lower() == "stop":
                await self.endpoll(message)
                return
        if not self.getPollByChannel(message):
            check = " ".join(text).lower()
            if "@everyone" in check or "@here" in check:
                await self.bot.say("Nice try.")
                return
            p = NewPoll(message, " ".join(text), self)
            if p.valid:
                self.poll_sessions.append(p)
                await p.start()
            else:
                await self.bot.say("poll question;option1;option2 (...)")
        else:
            await self.bot.say("A poll is already ongoing in this channel.")

    async def endpoll(self, message):
        if self.getPollByChannel(message):
            p = self.getPollByChannel(message)
            if p.author == message.author.id: # or isMemberAdmin(message)
                await self.getPollByChannel(message).endPoll()
            else:
                await self.bot.say("Only admins and the author can stop the poll.")
        else:
            await self.bot.say("There's no poll ongoing in this channel.")

    def getPollByChannel(self, message):
        for poll in self.poll_sessions:
            if poll.channel == message.channel:
                return poll
        return False

    async def check_poll_votes(self, message):
        if message.author.id != self.bot.user.id:
            if self.getPollByChannel(message):
                    self.getPollByChannel(message).checkAnswer(message)

    def fetch_joined_at(self, user, server):
        """Just a special case for someone special :^)"""
        if user.id == "96130341705637888" and server.id == "133049272517001216":
            return datetime.datetime(2016, 1, 10, 6, 8, 4, 443000)
        else:
            return user.joined_at

class NewPoll():
    def __init__(self, message, text, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.poll_sessions = main.poll_sessions
        msg = [ans.strip() for ans in text.split(";")]
        if len(msg) < 2: # Needs at least one question and 2 choices
            self.valid = False
            return None
        else:
            self.valid = True
        self.already_voted = []
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}
        i = 1
        for answer in msg: # {id : {answer, votes}}
            self.answers[i] = {"ANSWER" : answer, "VOTES" : 0}
            i += 1

    async def start(self):
        msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
        for id, data in self.answers.items():
            msg += "{}. *{}*\n".format(id, data["ANSWER"])
        msg += "\nType the number to vote!"
        await self.client.send_message(self.channel, msg)
        await asyncio.sleep(settings["POLL_DURATION"])
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for data in self.answers.values():
            msg += "*{}* - {} votes\n".format(data["ANSWER"], str(data["VOTES"]))
        await self.client.send_message(self.channel, msg)
        self.poll_sessions.remove(self)

    def checkAnswer(self, message):
        try:
            i = int(message.content)
            if i in self.answers.keys():
                if message.author.id not in self.already_voted:
                    data = self.answers[i]
                    data["VOTES"] += 1
                    self.answers[i] = data
                    self.already_voted.append(message.author.id)
        except ValueError:
            pass

def setup(bot):
    n = General(bot)
    bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)
