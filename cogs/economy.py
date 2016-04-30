import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
from random import randint
from random import randrange
from random import choice as randchoice
from operator import itemgetter, attrgetter
import os
import time
import logging
import asyncio

game_payouts = """Slot machine payouts:
    :two: :two: :six: Bet * 5000
    :four_leaf_clover: :four_leaf_clover: :four_leaf_clover: +1000
    :cherries: :cherries: :cherries: +800
    :two: :six: Bet * 4
    :cherries: :cherries: Bet * 3

    Three symbols: +500
    Two symbols: Bet * 2

    Dice payouts:
    Bet * 4

    Coin flip payouts:
    Bet * 2

    All In payouts:
    Bet * Multiplier

    Heist payout:
    1 Crew Member = 1% of current bot balance
    < 5 Crew Members = 5% of current bot balance
    < 10 Crew Members = 10% of current bot balance
    < 15 Crew Members = 25% of current bot balance
    < 20 Crew Members = 50% of current bot balance
    > 20 Crew Members = 100% of current bot balance 
    """

class Economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        self.bot = bot
        self.bank = fileIO("data/economy/bank.json", "load")
        self.settings = fileIO("data/economy/settings.json", "load")
        self.payday_register = {}
        self.slot_register = {}
        self.allin_register = {}
        self.coin_register = {}
        self.dice_register = {}
        self.heist = []
        self.heistcounter = 0
        self.joinable = False

    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the credits bank"""
        user = ctx.message.author
        if self.bot.user.id not in self.bank:
            self.bank[self.bot.user.id] = {"name" : self.bot.user.name, "balance": 0}
            fileIO("data/economy/bank.json", "save", self.bank)
        if user.id not in self.bank:
            self.bank[user.id] = {"name" : user.name, "balance" : 100}
            fileIO("data/economy/bank.json", "save", self.bank)
            await self.bot.say("{} Account opened. Current balance: {} {}".format(user.mention, str(self.check_balance(user.id)), self.settings["CURRENCY_NAME"]))
        else:
            await self.bot.say("{} You already have an account at the {} bank.".format(user.mention, self.settings["CURRENCY_NAME"]))

    @_bank.command(pass_context=True)
    async def balance(self, ctx, user : discord.Member=None):
        """Shows balance of user.
        Defaults to yours."""
        for id in self.bank:
            membername = discord.utils.get(ctx.message.server.members, id=id)
            self.update_name(id, str(membername))
        if self.bot.user.id not in self.bank:
            self.bank[self.bot.user.id] = {"name" : self.bot.user.name, "balance": 0}
            fileIO("data/economy/bank.json", "save", self.bank)
        if not user:
            user = ctx.message.author
            if self.account_check(user.id):
                await self.bot.say("{} Your balance is: {}".format(user.mention, str(self.check_balance(user.id))))
            else:
                await self.bot.say("{} You don't have an account at the {} bank. Type !register to open one.".format(user.mention, self.bot.user.name))
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
        elif self.bot.user.id == user.id:
            await self.bot.say("I don't need your charity.")
            return
        if sum < 1:
            await self.bot.say("You need to transfer at least 1 {}.".format(self.settings["CURRENCY_NAME"]))
            return
        if self.account_check(user.id):
            if self.enough_money(author.id, sum):
                self.withdraw_money(author.id, sum)
                self.add_money(user.id, sum)
                logger.info("{}({}) transferred {} {} to {}({})".format(author.name, author.id, str(sum), self.settings["CURRENCY_NAME"], user.name, user.id))
                await self.bot.say("{} {} have been transferred to {}'s account.".format(str(sum), self.settings["CURRENCY_NAME"], user.name))
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
            logger.info("{}({}) set {} {} to {} ({})".format(author.name, author.id, str(sum), self.settings["CURRENCY_NAME"], user.name, user.id))
            await self.bot.say("{}'s {} have been set to {}".format(user.name, self.settings["CURRENCY_NAME"], str(sum)))
        else:
            await self.bot.say("User has no bank account.")
                
    @commands.command(pass_context=True, no_pm=True)
    async def payday(self, ctx):
        """Get some free credits"""
        author = ctx.message.author
        id = author.id
        amount = self.check_balance(id)
        if self.account_check(id):
            if amount < 10000:
                if id in self.payday_register:
                    seconds = abs(self.payday_register[id] - int(time.perf_counter()))
                    if seconds  >= self.settings["PAYDAY_TIME"]: 
                        self.add_money(id, self.settings["PAYDAY_CREDITS"])
                        self.payday_register[id] = int(time.perf_counter())
                        await self.bot.say("{} Here, take some {}. Enjoy! (+{} {}!)".format(author.mention, self.settings["CURRENCY_NAME"], str(self.settings["PAYDAY_CREDITS"]), self.settings["CURRENCY_NAME"]))
                        self.update_name(id, author.name)
                    else:
                        await self.bot.say("{} Too soon. For your next payday you have to wait {}.".format(author.mention, self.display_time(self.settings["PAYDAY_TIME"] - seconds)))
                else:
                        self.payday_register[id] = int(time.perf_counter())
                        self.add_money(id, self.settings["PAYDAY_CREDITS"])
                        await self.bot.say("{} Here, take some {}. Enjoy! (+{} {}!)".format(author.mention, self.settings["CURRENCY_NAME"], str(self.settings["PAYDAY_CREDITS"]), self.settings["CURRENCY_NAME"]))
                        self.update_name(id, author.name)
            else:
                await self.bot.say("{} You cannot receive payday since you already have more than 10000 {}.".format(author.mention, self.settings["CURRENCY_NAME"]))
        else:
            await self.bot.say("{} You need an account to receive {}. (!bank register)".format(author.mention, self.settings["CURRENCY_NAME"]))

    @commands.command(name="leaderboard", pass_context=True)#adapted from Canule's four in a row.
    async def _leaderboard(self, ctx, page: int=-1):
        """Shows the leaderboard."""
        user = ctx.message.author
        page -= 1
        #for id in self.bank:
        #    membername = discord.utils.get(ctx.message.server.members, id=id)
        #    self.update_name(id, str(membername)[:-5])
        try:
            resultRankings = await self.get_rankings(ctx, user.id)# Returns{"topScore": array(userId/Score), "userIdRank": string(userId)}
            topScore = resultRankings["topScore"]
            userIdRank = resultRankings["userIdRank"]
            playerAmount = len(self.bank) - 2
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        # Put players and their earned points in to a table.
        msgHeader = "```erlang\nPosition |   Username                          |  {}\n---------------------------------------------------------\n".format(self.settings["CURRENCY_NAME"])
        if data and playerAmount >= 1:
            pages = []
            totalPages = 0
            usr = 0
            rank = 0
            userFound = False
            userFoundPage = False
            msg = ""
            while (usr < playerAmount):
                w=usr+10
                while (w > usr):
                    if usr >= playerAmount:
                        break
                    ul = len(topScore[usr][2])
                    sp = '                                 '# Discord username max length = 32 +1
                    sp = sp[ul:]
                    sn = '     '
                    if usr+1 >= 10: sn = '    '
                    if usr+1 >= 100: sn = '   '
                    if usr+1 >= 1000: sn = '  '
                    if user.id == topScore[usr][rank]:
                        msg = msg+"#({}){}| » {} |  ({})\n".format(usr+1, sn, topScore[usr][2]+sp, topScore[usr][1])
                        userFound = True
                        userFoundPage = totalPages
                    else:
                        msg = msg+"#({}){}|   {} |  ({})\n".format(usr+1, sn, topScore[usr][2]+sp, topScore[usr][1])
                    usr += 1
                pages.append(msg)
                totalPages += 1
                msg = ""
            # Determine what page to show.
            if page <= -1:# Show page with user.
                selectPage = userFoundPage
            elif page >= totalPages:
                selectPage = totalPages-1# Flood -1
            elif page in range(0, totalPages):
                selectPage = page
            else:# Show page 0
                selectPage = 0
            await self.bot.say( "{}{}\nTotal players:({})\nPage:({}/{})```".format(msgHeader, pages[selectPage], playerAmount, selectPage+1, totalPages))
        else:
            await self.bot.say( "No accounts in the bank.".format(user.mention))

    # Retuns a list of top scores.
    async def get_rankings(self, ctx, userId=None):
        user = ctx.message.author
        # Get all earned points of players.
        topScore = []
        if len(self.bank) - 2 >= 1:
            for id in self.bank:
                if id != self.bot.user.id and id != "120242625809743876":
                    points = self.bank[id]["balance"]
                    userName = self.bank[id]["name"]
                    topScore.append((id, points, userName))            
            topScore = sorted(topScore, key=itemgetter(1), reverse=True)
        # Get player rank.
        userIdRank = 0
        for index, id in enumerate(topScore):
            if id[0] == user.id:
                userIdRank = index+1
                break
        return {"topScore": topScore, "userIdRank": userIdRank}

    @commands.command(pass_context=True)
    async def payouts(self, ctx):
        """Shows casino game payouts"""
        await self.bot.send_message(ctx.message.author, game_payouts)

    @commands.command(pass_context=True, no_pm=True)
    async def slot(self, ctx, bid : int):
        """Play the slot machine"""
        author = ctx.message.author
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
                await self.bot.say("{} Bid must be between {} and {}.".format(author.mention, self.settings["SLOT_MIN"], self.settings["SLOT_MAX"]))
        else:
            await self.bot.say("{} You need an account with enough funds to play the slot machine.".format(author.mention))

    async def slot_machine(self, message, bid):
        self.withdraw_money(message.author.id, bid)
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
            await self.bot.send_message(message.channel, "{} 226! Your bet is multiplied * 5000! {}! ".format(display_reels, str(bid)))
        elif line[0] == ":four_leaf_clover:" and line[1] == ":four_leaf_clover:" and line[2] == ":four_leaf_clover:":
            bid += 1000
            await self.bot.send_message(message.channel, "{} Three FLC! +1000! ".format(display_reels))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
            bid += 800
            await self.bot.send_message(message.channel, "{} Three cherries! +800! ".format(display_reels))
        elif line[0] == line[1] == line[2]:
            bid += 500
            await self.bot.send_message(message.channel, "{} Three symbols! +500! ".format(display_reels))
        elif line[0] == ":two:" and line[1] == ":six:" or line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 4
            await self.bot.send_message(message.channel, "{} 26! Your bet is multiplied * 4! {}! ".format(display_reels, str(bid)))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 3
            await self.bot.send_message(message.channel, "{} Two cherries! Your bet is multiplied * 3! {}! ".format(display_reels, str(bid)))
        elif line[0] == line[1] or line[1] == line[2]:
            bid = bid * 2
            await self.bot.send_message(message.channel, "{} Two symbols! Your bet is multiplied * 2! {}! ".format(display_reels, str(bid)))
        else:
            await self.bot.send_message(message.channel, "{} Nothing! Lost bet. ".format(display_reels))
            await self.bot.send_message(message.channel, "{} {} left: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))
            self.add_money(self.bot.user.id, bid)
            return True
        self.add_money(message.author.id, bid)
        await self.bot.send_message(message.channel, "{} Current {}: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))

    @commands.command(pass_context=True, no_pm=True)
    async def allin(self, ctx, multiplier : int):
        """High stakes all in"""
        author = ctx.message.author
        id = author.id
        if self.enough_money_allin(author.id):
            if multiplier >= 1:
                if author.id in self.allin_register:
                    if abs(self.allin_register[author.id] - int(time.perf_counter()))  >= self.settings["ALLIN_TIME"]:               
                        self.allin_register[author.id] = int(time.perf_counter())
                        await self.allin_machine(ctx.message,  multiplier)
                    else:
                        await self.bot.say("All in machine is still cooling off! Wait {} seconds between each pull".format(self.settings["ALLIN_TIME"]))
                else:
                    self.allin_register[author.id] = int(time.perf_counter())
                    await self.allin_machine(ctx.message, multiplier)
            else:
                await self.bot.say("{} Multiplier must be higher than 1.".format(author.mention))
        else:
            await self.bot.say("{} You need at least 1000 {} to go all in.".format(author.mention, self.settings["CURRENCY_NAME"]))

    async def allin_machine(self, message, multiplier):
        odds = randrange(0, multiplier + 1)
        bid = int(self.bank[message.author.id]["balance"])
        self.withdraw_money(message.author.id, bid)
        if odds == 0:
            bid = bid * multiplier
            await self.bot.send_message(message.channel, "{} You won! Your bet is multiplied by * {}!".format(message.author.mention, str(multiplier)))
        else:
            await self.bot.send_message(message.channel, "{} Nothing! Back to the mines with you.".format(message.author.mention))
            await self.bot.send_message(message.channel, " {} left: {}".format(self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))
            self.add_money(self.bot.user.id, bid)
            return True
        self.add_money(message.author.id, bid)
        await self.bot.send_message(message.channel, "{} Current {}: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))

    @commands.command(pass_context=True, no_pm=True)
    async def dice(self, ctx, bid : int):
        """Roll the dice and get a 2, 7, 11 or 12 to win."""
        author = ctx.message.author
        if self.enough_money(author.id, bid):
            if bid >= self.settings["DICE_MIN"] and bid <= self.settings["DICE_MAX"]:
                if author.id in self.dice_register:
                    if abs(self.dice_register[author.id] - int(time.perf_counter()))  >= self.settings["DICE_TIME"]:               
                        self.dice_register[author.id] = int(time.perf_counter())
                        await self.dice_roll(ctx.message, bid)
                    else:
                        await self.bot.say("Dice roll machine is still cooling off! Wait {} seconds between each roll.".format(self.settings["DICE_TIME"]))
                else:
                    self.dice_register[author.id] = int(time.perf_counter())
                    await self.dice_roll(ctx.message, bid)
            else:
                await self.bot.say("{} Bid must be between {} and {}.".format(author.mention, self.settings["DICE_MIN"], self.settings["DICE_MAX"]))

    async def dice_roll(self, message, bid):
        self.withdraw_money(message.author.id, bid)
        d1 = randrange(1, 7)
        d2 = randrange(1, 7)
        dsum = d1 + d2
        await self.bot.send_message(message.channel, "Roll is {} ".format(dsum))
        if dsum == 2 or dsum == 7 or dsum == 11 or dsum == 12:
            bid = bid * 4
            await self.bot.send_message(message.channel, "You won! Your bet is multiplied by * 4! ")
        else:
            await self.bot.send_message(message.channel, "Nothing! Lost bet. ")
            await self.bot.send_message(message.channel, "{} {} left: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))
            self.add_money(self.bot.user.id, bid)
            return True
        self.add_money(message.author.id, bid)
        await self.bot.send_message(message.channel, "{} Current {}: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))

    @commands.command(pass_context=True, no_pm=True)
    async def coin(self, ctx, choice : str, bid : int):
        author = ctx.message.author
        if self.enough_money(author.id, bid):
            if bid >= self.settings["COIN_MIN"] and bid <= self.settings["COIN_MAX"]:
                if choice.lower() == "heads" or choice.lower() == "tails":
                    if author.id in self.coin_register:
                        if abs(self.coin_register[author.id] - int(time.perf_counter()))  >= self.settings["COIN_TIME"]:               
                            self.coin_register[author.id] = int(time.perf_counter())
                            await self.coin_flip(ctx.message, choice, bid)
                        else:
                            await self.bot.say("Coin flip machine is still cooling off! Wait {} seconds between each flip.".format(self.settings["COIN_TIME"]))
                    else:
                        self.coin_register[author.id] = int(time.perf_counter())
                        await self.coin_flip(ctx.message, choice, bid)
                else:
                    await self.bot.say("{} You need to pick heads or tails.".format(author.mention))
            else:
                await self.bot.say("{} Bid must be between {} and {}.".format(author.mention, self.settings["COIN_MIN"], self.settings["COIN_MAX"]))

    async def coin_flip(self, message, choice, bid):
        self.withdraw_money(message.author.id, bid)
        coinbot = ["heads", "tails"]
        botchoice = randchoice(coinbot)
        await self.bot.send_message(message.channel, "{} The flip shows {}.".format(message.author.mention, botchoice))
        if choice == botchoice:
            bid = bid * 2
            await self.bot.send_message(message.channel, "You won! Your bet is multiplied by * 2! ")
        else:
            await self.bot.send_message(message.channel, "Nothing! Lost bet. ")
            await self.bot.send_message(message.channel, "{} {} left: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))
            self.add_money(self.bot.user.id, bid)
            return True
        self.add_money(message.author.id, bid)
        await self.bot.send_message(message.channel, "{} Current {}: {}".format(message.author.mention, self.settings["CURRENCY_NAME"], str(self.check_balance(message.author.id))))

    async def debtpayment(self):
        payday_delay = 60

        while "Economy" in self.bot.cogs:
            for id in self.bank:
                if self.check_balance(id) < 0:
                    self.add_money(id, self.settings["PAYDAY_CREDITS"])
            await asyncio.sleep(payday_delay)

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions()
    async def economyset(self, ctx):
        """Changes economy module settings"""
        if ctx.invoked_subcommand is None:
            msg = "```"
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "\nType help economyset to see the list of commands.```"
            await self.bot.say(msg)

    @economyset.command()
    async def slotmin(self, bid : int):
        """Minimum slot machine bid"""
        self.settings["SLOT_MIN"] = bid
        await self.bot.say("Minimum bid is now " + str(bid) + " {}.".format(self.settings["CURRENCY_NAME"]))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def slotmax(self, bid : int):
        """Maximum slot machine bid"""
        self.settings["SLOT_MAX"] = bid
        await self.bot.say("Maximum bid is now " + str(bid) + " {}.".format(self.settings["CURRENCY_NAME"]))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def dicemin(self, bid : int):
        """Minimum dice roll bid"""
        self.settings["DICE_MIN"] = bid
        await self.bot.say("Minimum bid is now " + str(bid) + " {}.".format(self.settings["CURRENCY_NAME"]))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def dicemax(self, bid : int):
        """Maximum dice roll bid"""
        self.settings["DICE_MAX"] = bid
        await self.bot.say("Maximum bid is now " + str(bid) + " {}.".format(self.settings["CURRENCY_NAME"]))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def coinmin(self, bid : int):
        """Minimum coin flip bid"""
        self.settings["COIN_MIN"] = bid
        await self.bot.say("Minimum bid is now " + str(bid) + " {}.".format(self.settings["CURRENCY_NAME"]))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def coinmax(self, bid : int):
        """Maximum coin flip bid"""
        self.settings["COIN_MAX"] = bid
        await self.bot.say("Maximum bid is now " + str(bid) + " {}.".format(self.settings["CURRENCY_NAME"]))
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
        await self.bot.say("Every payday will now give " + str(credits) + " {}.".format(self.settings["CURRENCY_NAME"]))
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def currencyname(self, currency : str):
        """Name of your currency"""
        self.settings["CURRENCY_NAME"] = currency
        await self.bot.say("Your currency will now be called " + str(currency) + ".")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def heistduration(self, time : int):
        """How long recruitment for heists take"""
        self.settings["HEIST_DURATION"] = time
        await self.bot.say("Heist recruitment time is now " + str(time) + ".")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def heisttime(self, seconds : int):
        """Seconds between each payday"""
        self.settings["HEIST_COOLDOWN"] = seconds
        await self.bot.say("Value modified. At least " + str(seconds) + " seconds must pass between each heist.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def slottime(self, seconds : int):
        """Seconds between each slots use"""
        self.settings["SLOT_TIME"] = seconds
        await self.bot.say("Cooldown is now " + str(seconds) + " seconds.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def allintime(self, seconds : int):
        """Seconds between each allin use"""
        self.settings["ALLIN_TIME"] = seconds
        await self.bot.say("Cooldown is now " + str(seconds) + " seconds.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def dicetime(self, seconds : int):
        """Seconds between each slots use"""
        self.settings["DICE_TIME"] = seconds
        await self.bot.say("Cooldown is now " + str(seconds) + " seconds.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def cointime(self, seconds : int):
        """Seconds between each slots use"""
        self.settings["COIN_TIME"] = seconds
        await self.bot.say("Cooldown is now " + str(seconds) + " seconds.")
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

    def update_name(self, id, name):
        if self.account_check(id):
            self.bank[id]["name"] = name
            fileIO("data/economy/bank.json", "save", self.bank)
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
            self.bank[id]["balance"] = self.bank[id]["balance"] - int(amount)
            fileIO("data/economy/bank.json", "save", self.bank)
        else:
            return False

    def set_money(self, id, amount):
        if self.account_check(id):      
            self.bank[id]["balance"] = amount
            fileIO("data/economy/bank.json", "save", self.bank)
            return True
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

    def enough_money_allin(self, id):
        if self.account_check(id):
            if self.bank[id]["balance"] >= 1000:
                return True
            else:
                return False
        else:
            return False

    def display_time(self, seconds, granularity=2): # What would I ever do without stackoverflow?
        intervals = (                               # Source: http://stackoverflow.com/a/24542445
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

    @commands.command(name="heist", pass_context=True, no_pm=True)
    async def _heist(self, ctx):
        """Starts a heist to steal the bot's money, if a heist already in progress use this to join the current heist. Payouts found using !payouts"""
        message = ctx.message
        seconds = abs(self.heistcounter - int(time.perf_counter()))
        if seconds >= self.settings["HEIST_COOLDOWN"]: 
            if self.enough_money(self.bot.user.id, 100):
                if self.account_check(message.author.id):
                    if not self.getHeistByChannel(message):
                        bh = NewHeist(message, self)
                        self.heist.append(bh)
                        await bh.start(self)
                    else:
                        if self.joinable == True:
                            if message.author.id != self.bot.user.id:
                                if self.getHeistByChannel(message):
                                    if message.author.id not in self.getHeistByChannel(message).already_joined:
                                        await self.bot.say("{} has joined the crew.".format(message.author.name))
                                    self.getHeistByChannel(message).joinHeist(message)
                        else:
                            await self.bot.say("{} You cannot join a heist in progress.".format(message.author.mention))
                else:
                    await self.bot.say("{} You need an account to participate in a heist. (!bank register)".format(message.author.mention, self.settings["CURRENCY_NAME"]))
            else:
                await self.bot.say("There isn't enough money to steal from {}.".format(self.bot.user.name))
        else:
            await self.bot.say("{} Too soon. For the next heist you need to wait {}.".format(message.author.mention, self.display_time(self.settings["HEIST_COOLDOWN"] - seconds)))

    def getHeistByChannel(self, message):
        for heist in self.heist:
            if heist.channel == message.channel:
                return heist
        return False

class NewHeist():
    def __init__(self, message, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.heist = main.heist
        self.bank = main.check_balance(self.client.user.id)
        self.economy = main
        self.settings = main.settings
        self.already_joined = []
        self.already_joined.append(self.author)
        self.crew_members = []
        self.crew_members.append(message.author.name)

    async def start(self, main):
        msg = "**HEIST RECRUITMENT STARTED!**\nYou have {} seconds to join the heist using !heist.".format(self.settings["HEIST_DURATION"])
        main.joinable = True
        await self.client.send_message(self.channel, msg)
        await asyncio.sleep(self.settings["HEIST_DURATION"])
        await self.endRecruitment(main)

    async def endRecruitment(self, main):
        msg = "**HEIST RECRUITMENT ENDED!**"
        main.joinable = False
        await self.client.send_message(self.channel, msg)
        await self.startheist(main)

    async def startheist(self, main):
        msg = "Crew Members: "
        msg += ", ".join(self.crew_members)
        await self.client.send_message(self.channel, msg)
        msg = "Target: "
        if len(self.crew_members) == 1:
            loot = int(self.bank * 0.01)
            msg += "Level 1 Vault\nValue: {} {}".format(loot, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            level = 0
        elif 5 > len(self.crew_members) > 1:
            loot = int(self.bank * 0.05)
            msg += "Level 2 Vault\nValue: {} {}".format(loot, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            level = 1
        elif 10 > len(self.crew_members) >= 5:
            loot = int(self.bank * 0.1)
            msg += "Level 3 Vault\nValue: {} {}".format(loot, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            level = 2
        elif 15 > len(self.crew_members) >= 10:
            loot = int(self.bank * 0.25)
            msg += "Level 4 Vault\nValue: {} {}".format(loot, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            level = 3
        elif 20 > len(self.crew_members) >= 15:
            loot = int(self.bank * 0.50)
            msg += "Level 5 Vault\nValue: {} {}".format(loot, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            level = 4
        elif len(self.crew_members) >= 20:
            loot = int(self.bank)
            msg += "Level 6 Vault\nValue: {} {}".format(loot, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            level = 5
        msg = "**HEIST IN PROGRESS...**"
        await self.client.send_message(self.channel, msg)
        bail = int((loot / 2.5)/len(self.crew_members))
        lootsplit = int(loot / len(self.crew_members))
        if level <= 1:
            odds = randrange(0, 10)
        elif level == 2:
            odds = randrange(0, 20)
        elif level == 3:
            odds = randrange(0, 40)
        elif level == 4:
            odds = randrange(0, 80)
        elif level == 5:
            odds = randrange(0, 160)
        await asyncio.sleep(10)
        if odds <= len(self.crew_members) - 1:
            msg = "You have successfully stolen {} from {}!\n\nTime to split up the loot.\n\nEach person gets {} {}.".format(loot, self.client.user.name, lootsplit, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            main.withdraw_money(self.client.user.id, loot)
            msg = "Each member of the crew gets {} {}".format(loot, self.settings["CURRENCY_NAME"])
            for id in self.already_joined:
                main.add_money(id, lootsplit)
        else:
            msg = "You have been unsuccessful in stealing from {}.\n\nAll crew members have been deducted {} {} to make bail.".format(self.client.user.name, bail, self.settings["CURRENCY_NAME"])
            await self.client.send_message(self.channel, msg)
            for id in self.already_joined:
                main.withdraw_money(id, bail)
                print(main.check_balance(id))
                main.add_money(self.client.user.id, bail)
        self.heist.remove(self)
        main.heistcounter = int(time.perf_counter())

    def joinHeist(self, message):
        if message.author.id not in self.already_joined:
            self.already_joined.append(message.author.id)
            self.crew_members.append(message.author.name)

def check_folders():
    if not os.path.exists("data/economy"):
        print("Creating data/economy folder...")
        os.makedirs("data/economy")

def check_files():
    settings = {"PAYDAY_TIME" : 300, "PAYDAY_CREDITS" : 500, "SLOT_MIN" : 10, "SLOT_MAX" : 100, "DICE_MIN": 100, "DICE_MAX": 500, "COIN_MIN" : 10, "COIN_MAX" : 10, "CURRENCY_NAME" : "Credits", "HEIST_DURATION" : 300, "HEIST_COOLDOWN" : 300, "SLOT_TIME" : 0, "ALLIN_TIME" : 0, "COIN_TIME" : 0, "DICE_TIME" : 0}

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
        print("Creating default bank.json...")
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
    n = Economy(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.debtpayment())
    bot.add_cog(n)