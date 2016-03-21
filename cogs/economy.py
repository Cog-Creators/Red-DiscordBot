import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from random import randint
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import os
import time
import logging
import asyncio

slot_payouts = """Slot machine payouts:
    :two: :two: :six: Bet * 5000
    :four_leaf_clover: :four_leaf_clover: :four_leaf_clover: +1000
    :cherries: :cherries: :cherries: +800
    :two: :six: Bet * 4
    :cherries: :cherries: Bet * 3

    Three symbols: +500
    Two symbols: Bet * 2"""

class Economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        self.bot = bot
        self.bank = fileIO("data/economy/bank.json", "load")
        self.settings = fileIO("data/economy/settings.json", "load")
        self.payday_register = {}

        self.game_state = "null"
        self.players = {}
        
        self.deck = {}
        for suit in ["hearts", "diamonds", "clubs", "spades"]:
            self.deck[suit] = {}
            for i in range(2, 11):
                self.deck[suit][i] = {}
                self.deck[suit][i]["rank"] = str(i)
                self.deck[suit][i]["value"] = i
            
            self.deck[suit][1] = {}
            self.deck[suit][1]["rank"] = "ace"
            self.deck[suit][1]["value"] = 11

            self.deck[suit][11] = {}
            self.deck[suit][11]["rank"] = "jack"
            self.deck[suit][11]["value"] = 10

            self.deck[suit][12] = {}
            self.deck[suit][12]["rank"] = "queen"
            self.deck[suit][12]["value"] = 10

            self.deck[suit][13] = {}
            self.deck[suit][13]["rank"] = "king"
            self.deck[suit][13]["value"] = 10

    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the Twentysix bank"""
        user = ctx.message.author
        if user.id not in self.bank:
            self.bank[user.id] = {"name" : user.name, "balance" : 100}
            fileIO("data/economy/bank.json", "save", self.bank)
            await self.bot.say("{} Account opened. Current balance: {}".format(user.mention, str(self.check_balance(user.id))))
        else:
            await self.bot.say("{} You already have an account at the Twentysix bank.".format(user.mention))

    @_bank.command(pass_context=True)
    async def balance(self, ctx, user : discord.Member=None):
        """Shows balance of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            if self.account_check(user.id):
                await self.bot.say("{} Your balance is: {}".format(user.mention, str(self.check_balance(user.id))))
            else:
                await self.bot.say("{} You don't have an account at the Twentysix bank. Type !register to open one.".format(user.mention, str(self.check_balance(user.id))))
        else:
            if self.account_check(user.id):
                balance = self.check_balance(user.id)
                await self.bot.say("{}'s balance is {}".format(user.name, str(balance)))
            else:
                await self.bot.say("That user has no bank account.")

    @_bank.command(pass_context=True)
    async def transfer(self, ctx, user : discord.Member, sum : int):
        """Transfer credits to other users"""
        author = ctx.message.author
        if author == user:
            await self.bot.say("You can't transfer money to yourself.")
            return
        if sum < 1:
            await self.bot.say("You need to transfer at least 1 credit.")
            return
        if self.account_check(user.id):
            if self.enough_money(author.id, sum):
                self.withdraw_money(author.id, sum)
                self.add_money(user.id, sum)
                logger.info("{}({}) transferred {} credits to {}({})".format(author.name, author.id, str(sum), user.name, user.id))
                await self.bot.say("{} credits have been transferred to {}'s account.".format(str(sum), user.name))
            else:
                await self.bot.say("You don't have that sum in your bank account.")
        else:
            await self.bot.say("That user has no bank account.")

    @_bank.command(name="set", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _set(self, ctx, user : discord.Member, sum : int):
        """Sets money of user's bank account

        Admin/owner restricted."""
        author = ctx.message.author
        done = self.set_money(user.id, sum)
        if done:
            logger.info("{}({}) set {} credits to {} ({})".format(author.name, author.id, str(sum), user.name, user.id))
            await self.bot.say("{}'s credits have been set to {}".format(user.name, str(sum)))
        else:
            await self.bot.say("User has no bank account.")

    @commands.command(pass_context=True, no_pm=True)
    async def payday(self, ctx):
        """Get some free credits"""
        author = ctx.message.author
        id = author.id
        if self.account_check(id):
            if id in self.payday_register:
                seconds = abs(self.payday_register[id] - int(time.perf_counter()))
                if seconds  >= self.settings["PAYDAY_TIME"]: 
                    self.add_money(id, self.settings["PAYDAY_CREDITS"])
                    self.payday_register[id] = int(time.perf_counter())
                    await self.bot.say("{} Here, take some credits. Enjoy! (+{} credits!)".format(author.mention, str(self.settings["PAYDAY_CREDITS"])))
                else:
                    await self.bot.say("{} Too soon. For your next payday you have to wait {}.".format(author.mention, self.display_time(self.settings["PAYDAY_TIME"] - seconds)))
            else:
                self.payday_register[id] = int(time.perf_counter())
                self.add_money(id, self.settings["PAYDAY_CREDITS"])
                await self.bot.say("{} Here, take some credits. Enjoy! (+{} credits!)".format(author.mention, str(self.settings["PAYDAY_CREDITS"])))
        else:
            await self.bot.say("{} You need an account to receive credits.".format(author.mention))

    @commands.command()
    async def leaderboard(self, top : int=10):
        """Prints out the leaderboard

        Defaults to top 10""" #Originally coded by Airenkun - edited by irdumb
        if top < 1:
            top = 10
        bank_sorted = sorted(self.bank.items(), key=lambda x: x[1]["balance"], reverse=True)
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1
        for id in topten:
            highscore += str(place).ljust(len(str(top))+1)
            highscore += (id[1]["name"]+" ").ljust(23-len(str(id[1]["balance"])))
            highscore += str(id[1]["balance"]) + "\n"
            place += 1
        if highscore:
            await self.bot.say("```py\n"+highscore+"```")
        else:
            await self.bot.say("There are no accounts in the bank.")

    @commands.command(pass_context=True)
    async def payouts(self, ctx):
        """Shows slot machine payouts"""
        await self.bot.send_message(ctx.message.author, slot_payouts)

    @commands.command(pass_context=True, no_pm=True)
    async def slot(self, ctx, bid : int):
        """Play the slot machine"""
        author = ctx.message.author
        if self.enough_money(author.id, bid):
            if bid >= self.settings["SLOT_MIN"] and bid <= self.settings["SLOT_MAX"]:
                await self.slot_machine(ctx.message, bid)
            else:
                await self.bot.say("{0} Bid must be between {1} and {2}.".format(author.mention, self.settings["SLOT_MIN"], self.settings["SLOT_MAX"]))
        else:
            await self.bot.say("{0} You need an account with enough funds to play the slot machine.".format(author.mention))

    async def slot_machine(self, message, bid):
        reel_pattern = [":cherries:", ":cookie:", ":two:", ":four_leaf_clover:", ":cyclone:", ":sunflower:", ":six:", ":mushroom:", ":heart:", ":snowflake:"]
        padding_before = [":mushroom:", ":heart:", ":snowflake:"] # padding prevents index errors
        padding_after = [":cherries:", ":cookie:", ":two:"]
        reel = padding_before + reel_pattern + padding_after
        reels = []
        for i in range(0, 3):
            n = randint(3,12)
            reels.append([reel[n - 1], reel[n], reel[n + 1]])
        line = [reels[0][1], reels[1][1], reels[2][1]]

        display_reels = "  " + reels[0][0] + " " + reels[1][0] + " " + reels[2][0] + "\n"
        display_reels += ">" + reels[0][1] + " " + reels[1][1] + " " + reels[2][1] + "\n"
        display_reels += "  " + reels[0][2] + " " + reels[1][2] + " " + reels[2][2] + "\n"

        if line[0] == ":two:" and line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 5000
            await self.bot.send_message(message.channel, "{}{} 226! Your bet is multiplied * 5000! {}! ".format(display_reels, message.author.mention, str(bid)))
        elif line[0] == ":four_leaf_clover:" and line[1] == ":four_leaf_clover:" and line[2] == ":four_leaf_clover:":
            bid += 1000
            await self.bot.send_message(message.channel, "{}{} Three FLC! +1000! ".format(display_reels, message.author.mention))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
            bid += 800
            await self.bot.send_message(message.channel, "{}{} Three cherries! +800! ".format(display_reels, message.author.mention))
        elif line[0] == line[1] == line[2]:
            bid += 500
            await self.bot.send_message(message.channel, "{}{} Three symbols! +500! ".format(display_reels, message.author.mention))
        elif line[0] == ":two:" and line[1] == ":six:" or line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 4
            await self.bot.send_message(message.channel, "{}{} 26! Your bet is multiplied * 4! {}! ".format(display_reels, message.author.mention, str(bid)))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 3
            await self.bot.send_message(message.channel, "{}{} Two cherries! Your bet is multiplied * 3! {}! ".format(display_reels, message.author.mention, str(bid)))
        elif line[0] == line[1] or line[1] == line[2]:
            bid = bid * 2
            await self.bot.send_message(message.channel, "{}{} Two symbols! Your bet is multiplied * 2! {}! ".format(display_reels, message.author.mention, str(bid)))
        else:
            await self.bot.send_message(message.channel, "{}{} Nothing! Lost bet. ".format(display_reels, message.author.mention))
            self.withdraw_money(message.author.id, bid)
            await self.bot.send_message(message.channel, "Credits left: {}".format(str(self.check_balance(message.author.id))))
            return True
        self.add_money(message.author.id, bid)
        await self.bot.send_message(message.channel, "Current credits: {}".format(str(self.check_balance(message.author.id))))

    @commands.group(pass_context=True, no_pm=True)
    async def bj(self, ctx):
        """Play some blackjack"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @bj.command(pass_context=True, no_pm=True)
    async def start(self, ctx):
        """Start a game of blackjack"""
        author = ctx.message.author

        if self.game_state == "null":
            self.players = {}
            await self.bot.say(":moneybag::hearts:`Blackjack started!`:diamonds::moneybag:")
            self.game_state = "pregame"
            await self.blackjack(ctx)
        else:
            await self.bot.say("A blackjack game is already in progress!")

    @bj.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def stop(self, ctx):
        """Stop the current game of blackjack (no refunds)"""
        author = ctx.message.author

        if self.game_state == "null":
            await self.bot.say("There is no game currently running")
        else:
            self.game_state = "null"
            await self.bot.say("Blackjack has been stopped")

    @bj.command(pass_context=True, no_pm=True)
    async def bet(self, ctx, bet: int):
        """Join the game of blackjack with your opening bet"""
        author = ctx.message.author

        if self.enough_money(author.id, bet) and self.game_state == "pregame":
            if bet < self.settings["BLACKJACK_MIN"] and bet > self.settings["BLACKJACK_MAX"]:
                await self.bot.say("{0} bet must be between {1} and {2}.".format(author.mention, self.settings["BLACKJACK_MIN"], self.settings["BLACKJACK_MAX"]))
            else:
                if not (author in self.players.keys()):
                    await self.bot.say("{0} has placed a bet of {1}".format(author.mention, bet))

                else:
                    await self.bot.say("{0} has placed a new bet of {1}".format(author.mention, bet))

                self.players[author] = {}
                self.players[author]["bet"] = bet
                self.players[author]["cards"] = {}

        elif self.game_state == "pregame":
            await self.bot.say("{0}, you need an account with enough funds to play blackjack".format(author.mention))
        elif self.game_state == "null":
            await self.bot.say("There is currently no game running, type `/blackjack start` to begin one")
        else:
            await self.bot.say("There is currently a game in progress, wait for the next game")

    @bj.command(pass_context=True, no_pm=True)
    async def hit(self, ctx):
        if(self.game_state == "game"):
            author = ctx.message.author
            await self.bot.say("``` ```")
            for card in self.players[author]["cards"]:
                rank = self.players[author]["cards"][card]["rank"]
                suit = self.players[author]["cards"][card]["suit"]

                await self.bot.upload("data\economy\playing_cards\\" + rank + "_of_" + suit + ".png")

            card = await self.draw_card(author)
            count = await self.count_hand(author)

            if count == "busted":
                await self.bot.say("{0} has **busted**!".format(author.mention))
                await self.bot.say("``` ```")
            else:
                await self.bot.say("{0} has hit and drawn a {1}, totaling their hand to {3}".format(author.mention, card, count))
                await self.bot.say("``` ```")

    async def blackjack(self, ctx):
        while self.game_state != "null":
            if self.game_state == "pregame":
                await asyncio.sleep(self.settings["BLACKJACK_PRE_GAME_TIME"])

            if self.game_state == "pregame":
                if len(self.players) == 0:
                    await self.bot.say("No bets made, aborting game!")
                    self.game_state = "null"
                else:
                    self.game_state = "drawing"

            if self.game_state == "drawing":
                await self.bot.say("``` ```")
                for player in self.players:
                    
                    card1 = await self.draw_card(player)
                    card2 = await self.draw_card(player)    

                    count = await self.count_hand(player)

                    await self.bot.say("{0} has drawn a {1} and a {2}, totaling to {3}!".format(player.mention, card1, card2, count))
                    await self.bot.say("``` ```")
                
                self.players["dealer"] = {}
                self.players["dealer"]["cards"] = {}

                card = await self.draw_card("dealer")
                await self.bot.upload("data\economy\playing_cards\hidden_card.png")
                await self.bot.say("**The dealer has drawn a {0}!**\n``` ```".format(card))
                self.game_state = "game"

            if self.game_state == "game":
                await asyncio.sleep(self.settings["BLACKJACK_GAME_TIME"])


    async def draw_card(self, player):
        suit = randint(1, 4)
        num = randint(1, 13)

        if suit == 1:
            suit = "hearts"
        elif suit == 2:
            suit = "diamonds"
        elif suit == 3:
            suit = "clubs"
        elif suit == 4:
            suit = "spades"

        rank = self.deck[suit][num]["rank"]

        index = len(self.players[player]["cards"])

        self.players[player]["cards"][index] = {}
        self.players[player]["cards"][index]["suit"] = suit
        self.players[player]["cards"][index]["rank"] = rank
        self.players[player]["cards"][index]["value"] = self.deck[suit][num]["value"]

        await self.bot.upload("data\economy\playing_cards\\" + rank + "_of_" + suit + ".png")

        return self.players[player]["cards"][index]["rank"] + " of " + self.players[player]["cards"][index]["suit"]


    async def count_hand(self, player):
        count = ""
        total = 0
        contains_ace = False

        for num in self.players[player]["cards"]:
            value = self.players[player]["cards"][num]["value"]
            total += value
            if value == 11:
                contains_ace = True

        if total > 21 and contains_ace:
            count = str(total - 10)
        elif contains_ace:
            count = str(total) + " (" + str(total - 10) + ")"
        elif total > 21:
            count = "busted"
        else:
            count = str(total)

        return count

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def economyset(self, ctx):
        """Changes economy module settings"""
        if ctx.invoked_subcommand is None:
            msg = ""
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "\nType help economyset to see the list of commands."
            await self.bot.say(msg)

    @economyset.command()
    async def slotmin(self, bid : int):
        """Minimum slot machine bid"""
        self.settings["SLOT_MIN"] = bid
        await self.bot.say("Minimum bid is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def slotmax(self, bid : int):
        """Maximum slot machine bid"""
        self.settings["SLOT_MAX"] = bid
        await self.bot.say("Maximum bid is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    
    @economyset.command()
    async def blackjackmin(self, bid : int):
        """Minimum blackjack bid"""
        self.settings["BLACKJACK_MIN"] = bid
        await self.bot.say("Minimum bet is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def blackjackmax(self, bid : int):
        """Maximum blackjack bid"""
        self.settings["BLACKJACK_MAX"] = bid
        await self.bot.say("Maximum bet is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def blackjackpregametime(self, time : int):
        """Set the pregame time to join between `/bj start` and the drawing of cards"""
        self.settings["BLACKJACK_PRE_GAME_TIME"] = time
        await self.bot.say("Blackjack pre-game time is now " + str(time))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def blackjackgametime(self, time : int):
        """Set the maximum game time given to hit"""
        self.settings["BLACKJACK_GAME_TIME"] = time
        await self.bot.say("Blackjack maximum game time is now " + str(time))
        fileIO("data/economy/settings.json", "save", self.settings)

    
    @economyset.command()
    async def paydaytime(self, seconds : int):
        """Seconds between each payday"""
        self.settings["PAYDAY_TIME"] = seconds
        await self.bot.say("Value modified. At least " + str(seconds) + " seconds must pass between each payday.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def paydaycredits(self, credits : int):
        """Credits earned each payday"""
        self.settings["PAYDAY_CREDITS"] = credits
        await self.bot.say("Every payday will now give " + str(credits) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    def account_check(self, id):
        if id in self.bank:
            return True
        else:
            return False

    def check_balance(self, id):
        if self.account_check(id):
            return self.bank[id]["balance"]
        else:
            return False

    def add_money(self, id, amount):
        if self.account_check(id):
            self.bank[id]["balance"] = self.bank[id]["balance"] + int(amount)
            fileIO("data/economy/bank.json", "save", self.bank)
        else:
            return False

    def withdraw_money(self, id, amount):
        if self.account_check(id):
            if self.bank[id]["balance"] >= int(amount):
                self.bank[id]["balance"] = self.bank[id]["balance"] - int(amount)
                fileIO("data/economy/bank.json", "save", self.bank)
            else:
                return False
        else:
            return False

    def enough_money(self, id, amount):
        if self.account_check(id):
            if self.bank[id]["balance"] >= int(amount):
                return True
            else:
                return False
        else:
            return False

    def set_money(self, id, amount):
        if self.account_check(id):    
            self.bank[id]["balance"] = amount
            fileIO("data/economy/bank.json", "save", self.bank)
            return True
        else:
            return False

    def display_time(self, seconds, granularity=2): # What would I ever do without stackoverflow?
        intervals = (                              # Source: http://stackoverflow.com/a/24542445
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),    # 60 * 60 * 24
            ('hours', 3600),    # 60 * 60
            ('minutes', 60),
            ('seconds', 1),
            )
        
        result = []

        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])

def check_folders():
    if not os.path.exists("data/economy"):
        print("Creating data/economy folder...")
        os.makedirs("data/economy")

def check_files():
    settings = {"PAYDAY_TIME" : 300, "PAYDAY_CREDITS" : 120, "SLOT_MIN" : 5, "SLOT_MAX" : 100}

    f = "data/economy/settings.json"
    if not fileIO(f, "check"):
        print("Creating default economy's settings.json...")
        fileIO(f, "save", settings)

    f = "data/economy/bank.json"
    if not fileIO(f, "check"):
        print("Creating empty bank.json...")
        fileIO(f, "save", {})

def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("economy")
    if logger.level == 0: # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/economy/economy.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(Economy(bot))