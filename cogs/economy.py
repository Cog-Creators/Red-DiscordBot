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
        self.slot_register = {}

        self.game_state = "null"
        self.timer = 0
        self.players = {}
        
        """
        self.players
            player
                cards
                    0
                        rank
                        suit
                        value
                ranks
                standing
                splits
                bet
                blackjack
            dealer
        """

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
                await self.bot.say("{} You don't have an account at the Twentysix bank. Type {}bank register to open one.".format(user.mention, ctx.prefix))
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
            await self.bot.say("{} You need an account to receive credits. Type {}bank register to open one.".format(author.mention, ctx.prefix))

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
            if len(highscore) < 1985:
                await self.bot.say("```py\n"+highscore+"```")
            else:
                await self.bot.say("The leaderboard is too big to be displayed. Try with a lower <top> parameter.")
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
        if not self.account_check(author.id):
            await self.bot.say("{} You need an account to use the slot machine. Type {}bank register to open one.".format(author.mention, ctx.prefix))
            return
        if self.enough_money(author.id, bid):
            if bid >= self.settings["SLOT_MIN"] and bid <= self.settings["SLOT_MAX"]:
                if author.id in self.slot_register:
                    if abs(self.slot_register[author.id] - int(time.perf_counter()))  >= self.settings["SLOT_TIME"]:               
                        self.slot_register[author.id] = int(time.perf_counter())
                        await self.slot_machine(ctx.message, bid)
                    else:
                        await self.bot.say("Slot machine is still cooling off! Wait {} seconds between each pull".format(self.settings["SLOT_TIME"]))
                else:
                    self.slot_register[author.id] = int(time.perf_counter())
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

        if self.game_state == "null":
            self.game_state = "pregame"
            await self.blackjack(ctx)
        else:
            await self.bot.say("A blackjack game is already in progress!")

    @bj.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def stop(self, ctx):
        """Stop the current game of blackjack (no refunds)"""

        if self.game_state == "null":
            await self.bot.say("There is no game currently running")
        else:
            self.game_state = "null"
            await self.bot.say("**Blackjack has been stopped**")

    @bj.command(pass_context=True, no_pm=True)
    async def bet(self, ctx, bet: int):
        """Join the game of blackjack with your opening bet"""
        player = ctx.message.author

        if self.enough_money(player.id, bet) and self.game_state == "pregame":
            if bet < self.settings["BLACKJACK_MIN"] or (bet > self.settings["BLACKJACK_MAX"] and self.settings["BLACKJACK_MAX_ENABLED"]):
                await self.bot.say("{0}, bet must be between {1} and {2}.".format(player.mention, self.settings["BLACKJACK_MIN"], self.settings["BLACKJACK_MAX"]))
            else:
                if not (player in self.players.keys()):
                    await self.bot.say("{0} has placed a bet of {1}".format(player.mention, bet))
                    self.withdraw_money(player.id, bet)

                else:
                    await self.bot.say("{0} has placed a new bet of {1}".format(player.mention, bet))
                    self.add_money(player.id, self.players[player]["hand"][curr_hand]["bet"])
                    self.withdraw_money(player.id, bet)

                self.players[player] = {}
                self.players[player]["curr_hand"] = 0
                self.players[player]["hand"] = {}
                self.players[player]["hand"][0] = {}
                self.players[player]["hand"][0]["card"] = {}
                self.players[player]["hand"][0]["ranks"] = []
                self.players[player]["hand"][0]["bet"] = bet
                self.players[player]["hand"][0]["standing"] = False
                self.players[player]["hand"][0]["blackjack"] = False
                
        
        elif self.game_state == "null":
            await self.bot.say("There is currently no game running, type `/blackjack start` to begin one")
        
        elif self.game_state != "pregame" and self.game_state != "null":
            await self.bot.say("There is currently a game in progress, wait for the next game")

        elif not self.enough_money(player.id, bet):
            await self.bot.say("{0}, you need an account with enough funds to play blackjack".format(player.mention))

    @bj.command(pass_context=True, no_pm=True)
    async def hit(self, ctx):
        """Hit and draw another card"""
        player = ctx.message.author

        card = await self.draw_card(player)
        curr_hand = self.players[player]["curr_hand"]
        ranks = self.players[player]["hand"][curr_hand]["ranks"]
        count = await self.count_hand(player, curr_hand)

        if self.game_state == "game" and self.players[player]["hand"][curr_hand]["standing"] == False:
            
            if count > 21 and len(self.players[player]["hand"]) == self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has **busted**!".format(player.mention))
                self.players[player]["hand"][curr_hand]["standing"] = True
            
            elif count > 21 and len(self.players[player]["hand"]) > self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has **busted** on their current hand! Moving on to next split hand!".format(player.mention))
                self.players[player]["curr_hand"] += 1
                self.players[player]["hand"][curr_hand]["standing"] = True

            elif "ace" in ranks:
                await self.bot.say("{0} has hit and drawn a {1}, totaling their hand to {2} ({3})".format(player.mention, card, str(count), str(count - 10)))

            else:
                await self.bot.say("{0} has hit and drawn a {1}, totaling their hand to {2}".format(player.mention, card, count))

        elif self.game_state != "game":
            await self.bot.say("{0}, you cannot hit right now".format(player.mention))
        
        elif self.players[player]["hand"][curr_hand]["standing"]:
            await self.bot.say("{0}, you are standing and cannot hit".format(player.mention))

    @bj.command(pass_context=True, no_pm=True)
    async def stand(self, ctx):
        """Finishing drawing and stand with your current cards"""
        player = ctx.message.author
        curr_hand = self.players[player]["curr_hand"]
        if self.game_state == "game" and not self.players[player]["hand"][curr_hand]["standing"]:
            count = await self.count_hand(player, self.players[player]["curr_hand"])
            
            if len(self.players[player]["hand"]) == self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has stood with a hand totaling to {1}".format(player.mention, str(count)))
            
            else:
                await self.bot.say("{0} has stood with a hand totaling to {1}. Moving on to next split hand!".format(player.mention, str(count)))
                self.players[player]["curr_hand"] += 1

            self.players[player]["hand"][curr_hand]["standing"] = True

        elif self.game_state != "game":
            await self.bot.say("{0}, you cannot stand right now".format(player.mention))
        
        elif self.players[player]["hand"][curr_hand]["standing"]:
            await self.bot.say("{0}, you are already standing".format(player.mention))


    @bj.command(pass_context=True, no_pm=True)
    async def double(self, ctx):
        """Double your original bet and draw one last card"""
        player = ctx.message.author
        curr_hand = self.players[player]["curr_hand"]
        bet = self.players[player]["hand"][curr_hand]["bet"]

        if self.enough_money(player.id, bet) and not self.players[player]["hand"][curr_hand]["standing"] and self.game_state == "game":
            await self.bot.say("{0} has doubled down, totaling their bet to {1}".format(player.mention, self.players[player]["hand"][curr_hand]["bet"]))

            self.players[player]["hand"][curr_hand]["bet"] += bet
            self.withdraw_money(player.id, bet)
            
            card = await self.draw_card(player)
            count = await self.count_hand(player, self.players[player]["curr_hand"])

            if count > 21 and len(self.players[player]["hand"]) == self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has **busted**!".format(player.mention))
                self.players[player]["hand"][curr_hand]["standing"] = True
            
            elif count > 21 and len(self.players[player]["hand"]) > self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has **busted**! Moving on to next split hand!".format(player.mention))
                self.players[player]["curr_hand"] += 1
                self.players[player]["hand"][curr_hand]["standing"] = True

            elif count < 21 and len(self.players[player]["hand"]) == self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has doubled and drawn a {1}, totaling their hand to {2}".format(player.mention, card, count))
                self.players[player]["hand"][curr_hand]["standing"] = True

            elif count < 21 and len(self.players[player]["hand"]) > self.players[player]["curr_hand"] + 1:
                await self.bot.say("{0} has doubled and drawn a {1}, totaling their hand to {2}. Moving on to next split hand!".format(player.mention, card, count))
                self.players[player]["curr_hand"] += 1
                self.players[player]["hand"][curr_hand]["standing"] = True

        elif self.game_state != "game":
            await self.bot.say("{0}, you cannot double down right now!".format(player.mention))

        elif self.players[player]["hand"][curr_hand]["standing"]:
            await self.bot.say("{0}, you are standing and cannot double!".format(player.mention))
        
        elif not self.enough_money(player.id, bet):
            await self.bot.say("{0}, you do not have enough money to double down!".format(player.mention))
        

    @bj.command(pass_context=True, no_pm=True)
    async def split(self, ctx):
        """Split your hand into two seperate hands if you have two cards of the same rank"""
        player = ctx.message.author
        
        curr_hand = self.players[player]["curr_hand"]
        cards = self.players[player]["hand"][curr_hand]["card"]

        if (cards[0]["value"] == 11 and cards[1]["value"] == 1) or (cards[0]["value"] == 1 and cards[1]["value"] == 11): #reset aces to orginal value
            cards[0]["value"] = 11
            cards[0]["rank"] = "ace"

            cards[1]["value"] = 11
            cards[1]["rank"] = "ace"
        
        if cards[0]["value"] == cards[1]["value"] and len(cards) == 2 and self.game_state == "game" and not self.players[player]["hand"][curr_hand]["standing"]:
            await self.bot.say("{0} has split their {1}'s! Play through your first hand and stand to begin your next!".format(player.mention, cards[0]["value"]))
            hand_index = len(self.players[player]["hand"])
            
            self.players[player]["hand"][hand_index] = {}
            self.players[player]["hand"][hand_index]["card"] = {}
            self.players[player]["hand"][hand_index]["ranks"] = []
            self.players[player]["hand"][hand_index]["bet"] = self.players[player]["hand"][curr_hand]["bet"]
            self.players[player]["hand"][hand_index]["standing"] = False
            self.players[player]["hand"][hand_index]["blackjack"] = False

            self.players[player]["hand"][hand_index]["card"][0] = cards[1]
            del cards[1]

        elif self.game_state != "game":
            await self.bot.say("{0}, you cannot split right now!".format(player.mention))

        elif self.players[player]["hand"][curr_hand]["standing"]:
            await self.bot.say("{0}, you are standing and cannot split!".format(player.mention))

        elif len(cards) != 2:
            await self.bot.say("{0}, you may only split with two cards!".format(player.mention))
  
        elif cards[0]["value"] != cards[1]["value"]:
            await self.bot.say("{0}, you may only split with two cards of the same value!".format(player.mention))


    async def blackjack(self, ctx):
        while self.game_state != "null":
            if self.game_state == "pregame":
                self.players = {}
                self.timer = 0
                await self.bot.say(":moneybag::hearts:`Blackjack started!`:diamonds::moneybag:")
                await asyncio.sleep(self.settings["BLACKJACK_PRE_GAME_TIME"])

            if self.game_state == "pregame":
                if len(self.players) == 0:
                    await self.bot.say("No bets made, aborting game!")
                    self.game_state = "null"
                else:
                    self.game_state = "drawing"

            if self.game_state == "drawing":
                for player in self.players:
                    
                    card1 = await self.draw_card(player)
                    card2 = await self.draw_card(player)    

                    curr_hand = self.players[player]["curr_hand"]
                    ranks = self.players[player]["hand"][curr_hand]["ranks"]
                    count = await self.count_hand(player, curr_hand)

                    if "ace" in ranks and ("jack" in ranks or "queen" in ranks or "king" in ranks):
                        await self.bot.say("{0} has a **blackjack**!".format(player.mention))
                        self.players[player]["hand"][curr_hand]["blackjack"] = True
                        self.players[player]["hand"][curr_hand]["standing"] = True

                    elif "ace" in ranks:
                        await self.bot.say("{0} has drawn a {1} and a {2}, totaling to {3} ({4})!".format(player.mention, card1, card2, str(count), str(count-10)))

                    else:
                        await self.bot.say("{0} has drawn a {1} and a {2}, totaling to {3}!".format(player.mention, card1, card2, str(count)))
                    
                    await asyncio.sleep(1)

                self.players["dealer"] = {}
                self.players["dealer"]["curr_hand"] = 0
                self.players["dealer"]["hand"] = {}
                self.players["dealer"]["hand"][0] = {}
                self.players["dealer"]["hand"][0]["card"] = {}
                self.players["dealer"]["hand"][0]["ranks"] = []

                card = await self.draw_card("dealer")
                await self.bot.upload("data\economy\playing_cards\hidden_card.png")
                await self.bot.say("**The dealer has drawn a {0}!**".format(card))
                self.game_state = "game"

            if self.game_state == "game":
                all_stood = True
                for player in self.players:
                    for hand in self.players[player]["hand"]:
                        if player != "dealer" and not self.players[player]["hand"][hand]["standing"]:
                            all_stood = False

                if self.timer < self.settings["BLACKJACK_GAME_TIME"] and not all_stood:
                    self.timer += 1
                    await asyncio.sleep(1)
                elif all_stood or self.timer >= self.settings["BLACKJACK_GAME_TIME"]:
                    self.game_state = "endgame"

            if self.game_state == "endgame":

                card = await self.draw_card("dealer")
                dealer_count = await self.count_hand("dealer", 0)
                ranks = self.players["dealer"]["hand"][0]["ranks"]
                blackjack = False

                if "ace" in ranks and ("jack" in ranks or "queen" in ranks or "king" in ranks) and len(self.players["dealer"]["hand"][curr_hand]["ranks"]) == 2:
                    blackjack = True

                if dealer_count <= 21 and not blackjack: #if dealer has a normal hand, no bust
                    if "ace" in ranks and dealer_count < 17:
                        await self.bot.say("**The dealer has drawn a {0}, totaling his hand to {1} ({2})!**".format(card, str(dealer_count), str(dealer_count - 10)))
                    else:
                        await self.bot.say("**The dealer has drawn a {0}, totaling his hand to {1}!**".format(card, str(dealer_count)))

                
                if blackjack: #if dealer has blackjack
                    await self.bot.say("**The dealer has a blackjack!**")
                    
                    for player in self.players:
                        if player != "dealer":
                            for hand in self.players[player]["hand"]:
                                if self.players[player]["hand"][hand]["blackjack"]:
                                    self.add_money(player.id, self.players[player]["hand"][hand]["bet"])
                                    await self.bot.say("{0} ties dealer and pushes!".format(player.mention))
                                else:
                                    await self.bot.say("{0} loses with a score of {1}".format(player.mention, str(count)))

                    self.game_state = "pregame"
                    await asyncio.sleep(3)

                elif dealer_count > 21: #if dealer busts
                    await self.bot.say("**The dealer has busted!**")
                    for player in self.players:
                        if player != "dealer":
                            for hand in self.players[player]["hand"]:
                                count = await self.count_hand(player, hand)
                                if self.players[player]["hand"][hand]["blackjack"]:
                                    self.add_money(player.id, self.players[player]["hand"][hand]["bet"] * 2.5)
                                    await self.bot.say("{0} beats dealer with a blackjack and wins **{2}**!".format(player.mention, str(count), self.players[player]["hand"][hand]["bet"] * 1.5))
                                elif count <= 21:
                                    self.add_money(player.id, self.players[player]["hand"][hand]["bet"] * 2)
                                    await self.bot.say("{0} doesn't bust with a score of {1} and wins **{2}**!".format(player.mention, str(count), self.players[player]["hand"][hand]["bet"]))
                                else:
                                    await self.bot.say("{0} busted and wins nothing".format(player.mention))
                    
                    self.game_state = "pregame"
                    await asyncio.sleep(3)

                elif dealer_count >= 17: #if dealer stands
                    await self.bot.say("**The dealer stands at {0}!**".format(dealer_count))
                    for player in self.players:
                        if player != "dealer":
                            for hand in self.players[player]["hand"]:
                                count = await self.count_hand(player, hand)
                                if self.players[player]["hand"][hand]["blackjack"]:
                                    self.add_money(player.id, self.players[player]["hand"][hand]["bet"] * 2.5)
                                    await self.bot.say("{0} beats dealer with a blackjack and wins **{2}**!".format(player.mention, str(count), self.players[player]["hand"][hand]["bet"] * 1.5))
                                elif count > 21:
                                    await self.bot.say("{0} busted and wins nothing".format(player.mention))
                                elif count > dealer_count:
                                    self.add_money(player.id, self.players[player]["hand"][hand]["bet"] * 2)
                                    await self.bot.say("{0} beats dealer with a score of {1} and wins **{2}**!".format(player.mention, str(count), self.players[player]["hand"][hand]["bet"]))
                                elif count == dealer_count:
                                    self.add_money(player.id, self.players[player]["hand"][hand]["bet"])
                                    await self.bot.say("{0} ties dealer and pushes!".format(player.mention))
                                else:
                                    await self.bot.say("{0} loses with a score of {1}".format(player.mention, str(count)))

                    self.game_state = "pregame"
                    await asyncio.sleep(3)

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

        curr_hand = self.players[player]["curr_hand"]
        card_index = len(self.players[player]["hand"][curr_hand]["card"])

        self.players[player]["hand"][curr_hand]["card"][card_index] = {}
        self.players[player]["hand"][curr_hand]["card"][card_index]["suit"] = suit
        self.players[player]["hand"][curr_hand]["card"][card_index]["rank"] = rank
        self.players[player]["hand"][curr_hand]["card"][card_index]["value"] = self.deck[suit][num]["value"]
        self.players[player]["hand"][curr_hand]["ranks"].append(rank)

        await self.count_hand(player, curr_hand) #to change ace names and values in the "ranks" table, don't actually need the count

        await self.bot.upload("data\economy\playing_cards\\" + rank + "_of_" + suit + ".png")

        if rank == "small_ace":
            rank = "ace"

        return rank + " of " + suit

    async def count_hand(self, player, curr_hand):
        count = 0
        cards = self.players[player]["hand"][curr_hand]["card"]

        for card in cards:
            count += cards[card]["value"]

        for card in cards:
            if count > 21:
                if cards[card]["value"] == 11:
                    cards[card]["value"] = 1
                    cards[card]["rank"] = "small_ace"
                    count -= 10

                    self.players[player]["hand"][curr_hand]["ranks"] = []
                    for card in self.players[player]["hand"][curr_hand]["card"]:
                        self.players[player]["hand"][curr_hand]["ranks"].append(self.players[player]["hand"][curr_hand]["card"][card]["rank"])
                    break

        return count

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def economyset(self, ctx):
        """Changes economy module settings"""
        if ctx.invoked_subcommand is None:
            msg = "```"
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "\nType {}help economyset to see the list of commands.```".format(ctx.prefix)
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
    async def slottime(self, seconds : int):
        """Seconds between each slots use"""
        self.settings["SLOT_TIME"] = seconds
        await self.bot.say("Cooldown is now " + str(seconds) + " seconds.")
        fileIO("data/economy/settings.json", "save", self.settings)

    
    @economyset.command()
    async def bjminbet(self, bet : int):
        """Minimum blackjack bet"""
        self.settings["BLACKJACK_MIN"] = bid
        await self.bot.say("Minimum bet is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def bjmaxbet(self, bet : int):
        """Maximum blackjack bet"""
        self.settings["BLACKJACK_MAX"] = bid
        await self.bot.say("Maximum bet is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def bjmaxbettoggle(self):
        """Toggle the use of a maximum blackjack bid"""
        self.settings["BLACKJACK_MAX_ENABLED"] = not self.settings["BLACKJACK_MAX_ENABLED"]
        if self.settings["BLACKJACK_MAX_ENABLED"]:
            await self.bot.say("Maximum bet is now enabled.")
        else:
            await self.bot.say("Maximum bet is now disabled.")

        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def bjpretime(self, time : int):
        """Set the pregame time for players to bet"""
        self.settings["BLACKJACK_PRE_GAME_TIME"] = time
        await self.bot.say("Blackjack pre-game time is now " + str(time))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def bjgametime(self, time : int):
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
    settings = {
    "PAYDAY_TIME" : 300,
    "PAYDAY_CREDITS" : 120,
    "SLOT_MIN" : 5,
    "SLOT_MAX" : 100,
    "SLOT_TIME" : 0,
    "BLACKJACK_MIN" : 10,
    "BLACKJACK_MAX" : 5000,
    "BLACKJACK_MAX_ENABLED" : False,
    "BLACKJACK_GAME_TIME" : 60,
    "BLACKJACK_PRE_GAME_TIME" : 15
    }

    f = "data/economy/settings.json"
    if not fileIO(f, "check"):
        print("Creating default economy's settings.json...")
        fileIO(f, "save", settings)
    else: #consistency check
        current = fileIO(f, "load")
        if current.keys() != settings.keys():
            for key in settings.keys():
                if key not in current.keys():
                    current[key] = settings[key]
                    print("Adding " + str(key) + " field to economy settings.json")
            fileIO(f, "save", current)

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
