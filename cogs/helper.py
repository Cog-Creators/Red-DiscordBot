import discord
import os
import re
import random 
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help

CHARACTERS = {
    "doc" : "doc",
    "doctormario" : "doc",
    "dr.mario" : "doc",
    "drmario" : "doc",
    "mario" : "mario",
    "luigi" : "luigi",
    "bowser" : "bowser",
    "koopa" : "bowser",
    "turtle" : "bowser",
    "peach" : "peach",
    "princesspeach" : "peach",
    "daisy" : "peach",
    "yoshi" : "yoshi",
    "donkeykong" : "dk",
    "dk" : "dk",
    "kong" : "dk",
    "monkey" : "dk",
    "falcon" : "falcon",
    "captainfalcon" : "falcon",
    "cf" : "falcon",
    "cfalcon" : "falcon",
    "capt" : "falcon",
    "captain" : "falcon",
    "c.falcon" : "falcon",
    "douglas" : "falcon",
    "douglasjfalcon" : "falcon",
    "douglasjayfalcon" : "falcon",
    "captaindouglasjfalcon": "falcon",
    "captaindouglasjayfalcon" : "falcon",
    "ganon" : "ganon",
    "ganondorf" : "ganon",
    "falco" : "falco",
    "lombardi" : "falco",
    "falcolombardi" : "falco",
    "bird" : "falco",
    "burd" : "falco",
    "fox" : "fox",
    "mccloud" : "fox",
    "foxmccloud" : "fox",
    "ics" : "ics",
    "iceclimbers" : "ics",
    "nana" : "ics",
    "popo" : "ics",
    "ness" : "ness",
    "kirby" : "kirby",
    "samus" : "samus",
    "samusaran" : "samus",
    "zelda" : "zelda",
    "tetra" : "zelda",
    "princesszelda" : "zelda",
    "sheik" : "sheik",
    "ninja" : "sheik",
    "link" : "link",
    "younglink" : "ylink",
    "yl" : "ylink",
    "ylink" : "ylink",
    "pichu" : "pichu",
    "pikachu" : "pika",
    "pika" : "pika",
    "rat" : "pika",
    "jiggs" : "puff",
    "puff" : "puff",
    "jigglypuff" : "puff",
    "jiggly" : "puff",
    "rondoudou" : "puff",
    "mewtwo" : "m2",
    "m2" : "m2",
    "gnw" : "gnw",
    "gw" : "gnw",
    "gameandwatch" : "gnw",
    "g&w" : "gnw",
    "gdubs" : "gnw",
    "roy" : "roy",
    "marth" : "marth"
}

RESOURCES = "data/resources/"

class Helper:
    """Contains most static-based commands"""

    def __init__(self, bot, resources_folder):
        self.privilege = dataIO.load_json(RESOURCES+"character_privilege.json")
        self.bot = bot
        self.moves = self._load_moves()

    def _load_moves(self):
        return {}

    def _get_move(self, move, character):
        print("getting: "+str(move))
        try:
            return deepcopy(self.moves.move)
        except KeyError:
            print("Couldn't find the move "+str(move))

    # Is guaranteed to be passed valid character names
    def _get_privilege(self, char):
        try:
            info = self.privilege[char]
        except:
            self.privilege[char] = {}
            self.privilege[char]["facts"] = []
            self.privilege[char]["complaints"] = []
            self._save_privilege()
        return deepcopy(self.privilege[char])

    def _get_character(self, character):
        try:
            return CHARACTERS[re.sub(r"\s", '', character.lower())]
        except:
            print("Tried to find a character and failed (tried: \'"+str(character)+"\').")
            raise

    def _save_privilege(self):
        dataIO.save_json(RESOURCES+"character_privilege.json", self.privilege)

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def smash(self, ctx):
        """Changes smash module settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @smash.command(no_pm=False)
    async def frames(self, character : str, move : str):
        """Retrieve the frame data and gfy for a move"""
        await self.bot.say("")

    @commands.group(pass_context=True, no_pm=False, aliases=['fuck','f'], invoke_without_command=True)
    async def screw(self, ctx, *, character : str):
        """Returns a random \"fact\" about a character."""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._screw, character=character)

    # Actually returns the complaint to the channel
    @screw.command(pass_context=True, no_pm=True, hidden=True)
    async def _screw(self, ctx, *, character):
        try:
            char = self._get_character(character)
        except:
            return
        info = self._get_privilege(char)
        if info["complaints"]:
            complaint = random.choice(info["complaints"])
            await self.bot.say("Screw "+char+"...\n"+complaint["entry"])
        else:
            await self.bot.say("Nobody has complained about "+char+" yet. I guess they're fair and balanced?")

    @screw.command(name="add", pass_context=True, no_pm=False)
    async def add_complaint(self, ctx, *, character : str):
        """Tries to add a complaint to a character."""
        try:
            char = self._get_character(character)
        except:
            return
        msg = await self.bot.say("I'm listening. Accepting a complaint for "+char+"...")
        try:
            answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            answer = answer.content
        except:
            await self.bot.edit_message(msg, ":/ Sorry, I got bored and stopped listening... (complaints time out after 60 seconds!)")
            return
        info = self._get_privilege(char)
        self.privilege[char]["complaints"].append( { "entry" : answer } )
        self._save_privilege()
        await self.bot.edit_message("Got it. I didn't realize you feel that way about "+char+".")

    @commands.group(pass_context=True, no_pm=False, aliases=['dyk'], invoke_without_command=True)
    async def fact(self, ctx, *, character : str):
        """Returns a random fact about a character."""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._fact, character=character)

    # Actually return the fact to the channel
    @fact.command(pass_context=True, no_pm=True, hidden=True)
    async def _fact(self, ctx, *, character):
        try:
            char = self._get_character(character)
        except:
            return
        info = self._get_privilege(char)
        if info["facts"]:
            fact = random.choice(info["facts"])
            await self.bot.say("Did you know...\n"+fact["entry"])
        else:
            await self.bot.say("Hmm, I don't know anything about "+char+" yet. You should ~fact add "+char+" and change that!")

    @fact.command(name="add", pass_context=True, no_pm=False)
    async def add_fact(self, ctx, *, character : str):
        """Tries to add a fact about a character."""
        try:
            char = self._get_character(character)
        except:
            return
        msg = await self.bot.say("I'm listening. Tell me something about "+char+"...")
        try:
            answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            answer = answer.content
        except:
            await self.bot.edit_message(msg, "I didn't catch that... I can't wait for more than a minute. Try again?")
            return
        info = self._get_privilege(char)
        self.privilege[char]["facts"].append( { "entry" : answer } )
        self._save_privilege()
        await self.bot.edit_message(msg, "Got it. Good to know, thanks.")

def check_folders():
    if not os.path.exists("data/resources"):
        print("Creating data/resources folder...")
        os.makedirs("data/resources")

def check_files():
    data_dir = "data/resources/"
    melee = data_dir+"frames/melee/"
    files = [data_dir+"character_privilege.json", melee+"chars.json", melee+"jab.json", melee+"da.json", melee+"grab.json", melee+"dtilt.json", melee+"ftilt.json", melee+"utilt.json",melee+"dsmash.json",melee+"fsmash.json",melee+"usmash.json",melee+"nair.json",melee+"dair.json",melee+"fair.json",melee+"uair.json",melee+"bair.json"]
    for path in files:
        if not dataIO.is_valid_json(path):
            print("Creating empty "+str(path)+"...")
            dataIO.save_json(path, {})    

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Helper(bot, RESOURCES))
