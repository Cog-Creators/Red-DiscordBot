import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from collections import namedtuple, defaultdict
from datetime import datetime
from random import randint
from random import choice as randchoice
from copy import deepcopy
from .utils import checks
from cogs.utils.chat_formatting import pagify, box
from __main__ import send_cmd_help
import os
import time
import logging

default_settings = {"PAYDAY_TIME": 180, "PAYDAY_CREDITS": 20,
                    "SLOT_MIN": 3, "SLOT_MAX": 300, "SLOT_TIME": 60,
                    "REGISTER_CREDITS": 0,
                    "HEIST_MIN": 50, "HEIST_MAX": 1000, "HEIST_TIME": 600,
                    "JACKPOT": 10000, "JACKPOT_INITIAL_AMOUNT": 10000, "JACKPOT_INCREASE": 15}
default_shoplist = {"Booster (+2)": 500, "Booster (+3)": 1100, "Booster (+4)": 1800,
                    "Booster (+5)": 2600, "Booster (+6)": 3500, "Booster (+7)": 4500,
                    "Booster (+8)": 5600, "Free Loss (Slots)": 100, "Free Loss (Heists)": 1000}

days_of_the_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
heist_special_effect = ["2x Payday salary!", "Seagulls are gone for the day!", "Double the attempts at heists and slots, half the time between either!", "2x Slot payouts!", "Guards are absent from the bank!", "Heists are worth twice the money!", "Guards are inefficient (The bank had to save some money)!"]

slot_payouts = """Slot machine payouts:
    :six: :six: :six: Bet * 666
    :two: :two: :six: Jackpot!
    :four_leaf_clover: :four_leaf_clover: :four_leaf_clover: +1000
    :cherries: :cherries: :cherries: +800
    :two: :six: Bet * 4
    :cherries: :cherries: Bet * 3

    Three symbols: +500
    Two symbols: Bet * 2
    Nothing: 0; Jackpot += Increment"""

heist_payouts = """Heist payouts are fairly random. You can receive anything between nothing and your bet multiplied by 10, depending on what game you get yourself into.
However, you can also lose pretty much everything. So be aware of what you do."""

class BankError(Exception):
    pass


class AccountAlreadyExists(BankError):
    pass


class NoAccount(BankError):
    pass


class InsufficientBalance(BankError):
    pass


class NegativeValue(BankError):
    pass


class SameSenderAndReceiver(BankError):
    pass


class Bank:

    def __init__(self, bot, file_path):
        self.accounts = dataIO.load_json(file_path)
        self.bot = bot

    def create_account(self, user, *, initial_balance=0):
        server = user.server
        if not self.account_exists(user):
            if server.id not in self.accounts:
                self.accounts[server.id] = {}
            if user.id in self.accounts:  # Legacy account
                balance = self.accounts[user.id]["balance"]
            else:
                balance = initial_balance
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            account = {"name": user.name,
                       "balance": balance,
                       "created_at": timestamp
                       }
            self.accounts[server.id][user.id] = account
            self._save_bank()
            return self.get_account(user)
        else:
            raise AccountAlreadyExists()

    def account_exists(self, user):
        try:
            self._get_account(user)
        except NoAccount:
            return False
        return True

    def withdraw_credits(self, user, amount):
        server = user.server

        if amount < 0:
            raise NegativeValue()

        account = self._get_account(user)
        if account["balance"] >= amount:
            account["balance"] -= amount
            self.accounts[server.id][user.id] = account
            self._save_bank()
        else:
            raise InsufficientBalance()

    def deposit_credits(self, user, amount):
        server = user.server
        if amount < 0:
            raise NegativeValue()
        account = self._get_account(user)
        account["balance"] += amount
        self.accounts[server.id][user.id] = account
        self._save_bank()

    def set_credits(self, user, amount):
        server = user.server
        if amount < 0:
            raise NegativeValue()
        account = self._get_account(user)
        account["balance"] = amount
        self.accounts[server.id][user.id] = account
        self._save_bank()

    def transfer_credits(self, sender, receiver, amount):
        if amount < 0:
            raise NegativeValue()
        if sender is receiver:
            raise SameSenderAndReceiver()
        if self.account_exists(sender) and self.account_exists(receiver):
            sender_acc = self._get_account(sender)
            if sender_acc["balance"] < amount:
                raise InsufficientBalance()
            self.withdraw_credits(sender, amount)
            self.deposit_credits(receiver, amount)
        else:
            raise NoAccount()

    def can_spend(self, user, amount):
        account = self._get_account(user)
        if account["balance"] >= amount:
            return True
        else:
            return False

    def wipe_bank(self, server):
        self.accounts[server.id] = {}
        self._save_bank()

    def get_server_accounts(self, server):
        if server.id in self.accounts:
            raw_server_accounts = deepcopy(self.accounts[server.id])
            accounts = []
            for k, v in raw_server_accounts.items():
                v["id"] = k
                v["server"] = server
                acc = self._create_account_obj(v)
                accounts.append(acc)
            return accounts
        else:
            return []

    def get_all_accounts(self):
        accounts = []
        for server_id, v in self.accounts.items():
            server = self.bot.get_server(server_id)
            if server is None:
                # Servers that have since been left will be ignored
                # Same for users_id from the old bank format
                continue
            raw_server_accounts = deepcopy(self.accounts[server.id])
            for k, v in raw_server_accounts.items():
                v["id"] = k
                v["server"] = server
                acc = self._create_account_obj(v)
                accounts.append(acc)
        return accounts

    def get_balance(self, user):
        account = self._get_account(user)
        return account["balance"]

    def get_account(self, user):
        acc = self._get_account(user)
        acc["id"] = user.id
        acc["server"] = user.server
        return self._create_account_obj(acc)

    def _create_account_obj(self, account):
        account["member"] = account["server"].get_member(account["id"])
        account["created_at"] = datetime.strptime(account["created_at"],
                                                  "%Y-%m-%d %H:%M:%S")
        Account = namedtuple("Account", "id name balance "
                             "created_at server member")
        return Account(**account)

    def _save_bank(self):
        dataIO.save_json("data/economy/bank.json", self.accounts)

    def _get_account(self, user):
        server = user.server
        try:
            return deepcopy(self.accounts[server.id][user.id])
        except KeyError:
            raise NoAccount()


class SetParser:
    def __init__(self, argument):
        allowed = ("+", "-")
        if argument and argument[0] in allowed:
            try:
                self.sum = int(argument)
            except:
                raise
            if self.sum < 0:
                self.operation = "withdraw"
            elif self.sum > 0:
                self.operation = "deposit"
            else:
                raise
            self.sum = abs(self.sum)
        elif argument.isdigit():
            self.sum = int(argument)
            self.operation = "set"
        else:
            raise


class Economy:
    """Economy - Blue variant

    Extender module for Economy
    More fun with imaginary currency!"""

    def __init__(self, bot):
        global default_settings
        global default_shoplist
        self.bot = bot
        self.bank = Bank(bot, "data/economy/bank.json")
        self.file_path = "data/economy/settings.json"
        self.shop_path = "data/economy/shoplist.json"
        self.settings = dataIO.load_json(self.file_path)
        self.shoplist = dataIO.load_json(self.shop_path)
        if "PAYDAY_TIME" in self.settings:  # old format
            default_settings = self.settings
            self.settings = {}
        self.settings = defaultdict(lambda: default_settings, self.settings)
        self.shoplist = defaultdict(lambda: default_shoplist, self.shoplist)
        self.payday_register = defaultdict(dict)
        self.slot_register = defaultdict(dict)
        self.heist_register = defaultdict(dict)
        self.weekday = datetime.today().weekday()
        self.heist_day = days_of_the_week[self.weekday]
        self.heist_special = heist_special_effect[self.weekday]

    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the Twentysix bank"""
        user = ctx.message.author
        credits = 0
        if ctx.message.server.id in self.settings:
            credits = self.settings[ctx.message.server.id].get("REGISTER_CREDITS", 0)
        try:
            account = self.bank.create_account(user)
            await self.bot.say("{} Account opened. Current balance: {}\nUse the `payday` command to gain free coins.".format(
                user.mention, account.balance))
        except AccountAlreadyExists:
            await self.bot.say("{} You already have an account at the"
                               " Twentysix bank.".format(user.mention))

    @_bank.command(pass_context=True)
    async def balance(self, ctx, user: discord.Member=None):
        """Shows balance of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your balance is: {}".format(
                    user.mention, self.bank.get_balance(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the"
                                   " Twentysix bank. Type `{}bank register`"
                                   " to open one.".format(user.mention,
                                                          ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s balance is {}".format(
                    user.name, self.bank.get_balance(user)))
            except NoAccount:
                await self.bot.say("That user has no bank account.")

    @_bank.command(pass_context=True)
    async def transfer(self, ctx, user: discord.Member, sum: int):
        """Transfer credits to other users"""
        author = ctx.message.author
        try:
            self.bank.transfer_credits(author, user, sum)
            logger.info("{}({}) transferred {} credits to {}({})".format(
                author.name, author.id, sum, user.name, user.id))
            await self.bot.say("{} credits have been transferred to {}'s"
                               " account.".format(sum, user.name))
        except NegativeValue:
            await self.bot.say("You need to transfer at least 1 credit.")
        except SameSenderAndReceiver:
            await self.bot.say("You can't transfer credits to yourself.")
        except InsufficientBalance:
            await self.bot.say("You don't have that sum in your bank account.")
        except NoAccount:
            await self.bot.say("That user has no bank account.")

    @_bank.command(name="set", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _set(self, ctx, user: discord.Member, credits: SetParser):
        """Sets credits of user's bank account. See help for more operations

        Passing positive and negative values will add/remove credits instead

        Examples:
            bank set @Twentysix 26 - Sets 26 credits
            bank set @Twentysix +2 - Adds 2 credits
            bank set @Twentysix -6 - Removes 6 credits"""
        author = ctx.message.author
        try:
            if credits.operation == "deposit":
                self.bank.deposit_credits(user, credits.sum)
                logger.info("{}({}) added {} credits to {} ({})".format(
                    author.name, author.id, credits.sum, user.name, user.id))
                await self.bot.say("{} credits have been added to {}"
                                   "".format(credits.sum, user.name))
            elif credits.operation == "withdraw":
                self.bank.withdraw_credits(user, credits.sum)
                logger.info("{}({}) removed {} credits to {} ({})".format(
                    author.name, author.id, credits.sum, user.name, user.id))
                await self.bot.say("{} credits have been withdrawn from {}"
                                   "".format(credits.sum, user.name))
            elif credits.operation == "set":
                self.bank.set_credits(user, credits.sum)
                logger.info("{}({}) set {} credits to {} ({})"
                            "".format(author.name, author.id, credits.sum,
                                      user.name, user.id))
                await self.bot.say("{}'s credits have been set to {}".format(
                    user.name, credits.sum))
        except InsufficientBalance:
            await self.bot.say("User doesn't have enough credits.")
        except NoAccount:
            await self.bot.say("User has no bank account.")

    @commands.command(pass_context=True, no_pm=True)
    async def payday(self, ctx):
        """Get some free credits"""
        author = ctx.message.author
        server = author.server
        id = author.id
        if self.bank.account_exists(author):
            if id in self.payday_register[server.id]:
                seconds = abs(self.payday_register[server.id][
                              id] - int(time.perf_counter()))
                if seconds >= self.settings[server.id]["PAYDAY_TIME"]:
                    if self.weekday == 0:
                        self.bank.deposit_credits(author, self.settings[server.id]["PAYDAY_CREDITS"] * 2)
                        self.payday_register[server.id][id] = int(time.perf_counter())
                        await self.bot.say("{} - I'm willing to give you a whole bunch of credits. Enjoy! (+**{}** credits!)".format(author.mention,str(self.settings[server.id]["PAYDAY_CREDITS"] * 2)))
                        return True
                    self.bank.deposit_credits(author, self.settings[
                                              server.id]["PAYDAY_CREDITS"])
                    self.payday_register[server.id][
                        id] = int(time.perf_counter())
                    await self.bot.say(
                        "{} - I'm willing to give you some credits. Enjoy! (+{}"
                        " credits!)".format(
                            author.mention,
                            str(self.settings[server.id]["PAYDAY_CREDITS"])))
                else:
                    dtime = self.display_time(
                        self.settings[server.id]["PAYDAY_TIME"] - seconds)
                    await self.bot.say(
                        "{} - Too soon. For your next payday you have to"
                        " wait {}.".format(author.mention, dtime))
            else:
                if self.weekday == 0:
                    self.bank.deposit_credits(author, self.settings[server.id]["PAYDAY_CREDITS"] * 2)
                    self.payday_register[server.id][id] = int(time.perf_counter())
                    await self.bot.say("{} - The coin bakery is crazy generous today! Enjoy the share! (+**{}** credits!)".format(author.mention,str(self.settings[server.id]["PAYDAY_CREDITS"] * 2)))
                    return True
                self.payday_register[server.id][id] = int(time.perf_counter())
                self.bank.deposit_credits(author, self.settings[
                                          server.id]["PAYDAY_CREDITS"])
                await self.bot.say(
                    "{} - Here, take some credits. Fresh from the coin bakery. Enjoy! (+{} credits!)".format(
                        author.mention,
                        str(self.settings[server.id]["PAYDAY_CREDITS"])))
        else:
            await self.bot.say("{} You need an account to receive credits."
                               " Type `{}bank register` to open one.".format(
                                   author.mention, ctx.prefix))

    @commands.group(pass_context=True)
    async def leaderboard(self, ctx):
        """Server / global leaderboard

        Defaults to server"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._server_leaderboard)

    @leaderboard.command(name="server", pass_context=True)
    async def _server_leaderboard(self, ctx, top: int=10):
        """Prints out the server's leaderboard; no less than 10

        Defaults to top 10"""
        # Originally coded by Airenkun - edited by irdumb
        server = ctx.message.server
        if top < 10:
            top = 10
        bank_sorted = sorted(self.bank.get_server_accounts(server),
                             key=lambda x: x.balance, reverse=True)
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1
        for acc in topten:
            highscore += str(place).ljust(len(str(top)) + 1)
            highscore += (acc.name + " ").ljust(30 - len(str(acc.balance)))
            highscore += str(acc.balance) + "\n"
            place += 1
        if highscore != "":
            for page in pagify(highscore, shorten_by=12):
                await self.bot.say(box(page, lang="py"))
        else:
            await self.bot.say("There are no accounts in the bank.")

    @leaderboard.command(name="global")
    async def _global_leaderboard(self, top: int=10):
        """Prints out the global leaderboard; no less than 10

        Defaults to top 10"""
        if top < 10:
            top = 10
        bank_sorted = sorted(self.bank.get_all_accounts(),
                             key=lambda x: x.balance, reverse=True)
        unique_accounts = []
        for acc in bank_sorted:
            if not self.already_in_list(unique_accounts, acc):
                unique_accounts.append(acc)
        if len(unique_accounts) < top:
            top = len(unique_accounts)
        topten = unique_accounts[:top]
        highscore = ""
        place = 1
        for acc in topten:
            highscore += str(place).ljust(len(str(top)) + 1)
            highscore += ("{} |{}| ".format(acc.name, acc.server.name)
                          ).ljust(23 - len(str(acc.balance)))
            highscore += str(acc.balance) + "\n"
            place += 1
        if highscore != "":
            for page in pagify(highscore, shorten_by=12):
                await self.bot.say(box(page, lang="py"))
        else:
            await self.bot.say("There are no accounts in the bank.")

    def already_in_list(self, accounts, user):
        for acc in accounts:
            if user.id == acc.id:
                return True
        return False

    @commands.group(pass_context=True)
    async def payouts(self, ctx):
        """Shows various game payouts

        Defaults to slots"""
        if ctx.invoked_subcommand is None:
            await self.bot.whisper(slot_payouts)

    @payouts.command(name="slots")
    async def slotpayouts(self):
        """Shows slot machine payouts"""
        await self.bot.whisper(slot_payouts)

    @payouts.command(name="heist")
    async def heistpayouts(self):
        """Shows heist payouts"""
        await self.bot.whisper(heist_payouts)

    @commands.command(pass_context=True, no_pm=True)
    async def slot(self, ctx, bid: int):
        """Play the slot machine"""
        author = ctx.message.author
        server = author.server
        if not self.bank.account_exists(author):
            await self.bot.say("{} You need an account to use the slot machine. Type `{}bank register` to open one.".format(author.mention, ctx.prefix))
            return
        if self.bank.can_spend(author, bid):
            if bid >= self.settings[server.id]["SLOT_MIN"] and bid <= self.settings[server.id]["SLOT_MAX"]:
                if author.id in self.slot_register:
                    if self.weekday == 2:
                        if abs(self.slot_register[author.id] - int(time.perf_counter())) >= self.settings[server.id]["SLOT_TIME"]/2:
                            self.slot_register[author.id] = int(
                                time.perf_counter())
                            await self.slot_machine(ctx.message, bid)
                        else:
                            await self.bot.say("Slot machine is still cooling off! Wait {} seconds between each pull".format(int(self.settings[server.id]["SLOT_TIME"]/2)))
                    else:
                        if abs(self.slot_register[author.id] - int(time.perf_counter())) >= self.settings[server.id]["SLOT_TIME"]:
                            self.slot_register[author.id] = int(
                                time.perf_counter())
                            await self.slot_machine(ctx.message, bid)
                        else:
                            await self.bot.say("Slot machine is still cooling off! Wait {} seconds between each pull".format(self.settings[server.id]["SLOT_TIME"]))
                else:
                    self.slot_register[author.id] = int(time.perf_counter())
                    await self.slot_machine(ctx.message, bid)
            elif bid < 5 and bid > 0:
                await self.bot.say("{} - You think we're running a charity here? I think I have the perfect idea what to do with this input... Take those credits and NOT roll for you!\nNext time, remember the minimum bid is {} credits.".format(author.mention, self.settings[server.id]["SLOT_MIN"]))
                if self.bank.can_spend(author, bid):
                    self.bank.withdraw_credits(author, bid)
                    await self.bot.say("\n{} - Current credits: {}".format(author.name, self.bank.get_balance(author)))
                else:
                    await self.bot.say("...unless you can't even do THAT. Well, I guess you're lucky this time.")
            elif bid == 0:
                await self.bot.say("Are you trying to troll literally everyone in chat here?\nHey, guys, {} is trying to betray you here! He wants to use the slots for no input at all! Should we fine him? What about the minimum entry? Yeah, that'll do. That's five credits please!".format(author.mention))
                if self.bank.can_spend(author, 5):
                    self.bank.withdraw_credits(author, 5)
                    await self.bot.say("\n{} - Current credits: {}".format(author.name, self.bank.get_balance(author)))
                else:
                    await self.bot.say("...unless you can't even do THAT. Well, I guess you're lucky this time.")
            elif bid < 0:
                await self.bot.say("Okay, I can smell trolls when they try taking apart the slots. Negative input? Really? How about all your coins for a change?".format(author.mention))
                if self.bank.get_balance(author) != 0:
                    self.bank.withdraw_credits(author, self.bank.get_balance(author))
                    await self.bot.say("\n{} - Current credits: {}".format(author.name, self.bank.get_balance(author)))
                else:
                    await self.bot.say("Unless you just have NO CREDITS AT ALL. God freaking dammit. Can I just ask **everyone** to throw a credit at this person so I can rip them off?")
            else:
                await self.bot.say("{} Bid is allowed to be {} at most.".format(author.mention, self.settings[server.id]["SLOT_MAX"]))
        else:
            await self.bot.say("{0} You need an account with enough funds to play the slot machine.".format(author.mention))

    async def slot_machine(self, message, bid):
        reel_pattern = [":cherries:", ":cookie:", ":two:", ":four_leaf_clover:",
                        ":cyclone:", ":sunflower:", ":six:", ":mushroom:", ":heart:", ":snowflake:"]
        # padding prevents index errors
        padding_before = [":mushroom:", ":heart:", ":snowflake:"]
        padding_after = [":cherries:", ":cookie:", ":two:"]
        reel = padding_before + reel_pattern + padding_after
        reels = []
        for i in range(0, 3):
            n = randint(3, 12)
            reels.append([reel[n - 1], reel[n], reel[n + 1]])
        line = [reels[0][1], reels[1][1], reels[2][1]]

        display_reels = "~~\n~~  " + \
            reels[0][0] + " " + reels[1][0] + " " + reels[2][0] + "\n"
        display_reels += ">" + reels[0][1] + " " + \
            reels[1][1] + " " + reels[2][1] + "\n"
        display_reels += "  " + reels[0][2] + " " + \
            reels[1][2] + " " + reels[2][2] + "\n"
        
        jackpot = self.settings[message.author.server.id]["JACKPOT"]
        jackpot_init = self.settings[message.author.server.id]["JACKPOT_INITIAL_AMOUNT"]
        jackpot_inc = self.settings[message.author.server.id]["JACKPOT_INCREASE"]
        if self.weekday == 3:
            jackpot_inc = jackpot_inc * 2

        increase = ""

        if line[0] == ":six:" and line[1] == line[0] and line[2] == line[0]:
            bid = bid * 666
            if self.weekday == 3:
                bid = bid * 2
                increase = " ***and doubled***!"
            slotMsg = "{}{} - Uh oh... ***Your bet is multiplied by the devil's number{}!***\nThat's a whopping total of **{}** credits!".format(display_reels, message.author.mention, increase, str(bid))
        elif line[0] == ":two:" and line[1] == ":two:" and line[2] == ":six:":
            bid = jackpot
            slotMsg = "{}\n**JACKPOT! 226! --- JACKPOT! 226! --- JACKPOT! 226!\n{} has just won the grand total of {} coins!!**\n\n*(The jackpot has been reset to {} coins.)*".format(
                display_reels, message.author.mention, str(jackpot), str(jackpot_init))
            jackpot = jackpot_init
            self.settings[message.author.server.id]["JACKPOT"] = jackpot
            dataIO.save_json(self.file_path, self.settings)
        elif line[0] == ":four_leaf_clover:" and line[1] == ":four_leaf_clover:" and line[2] == ":four_leaf_clover:":
            bid += 1000
            increase = "1000"
            if self.weekday == 3:
                bid += 1000
                increase = "**2000**"
            slotMsg = "{}{} - Three FLC! +{}! ".format(
                display_reels, message.author.mention, increase)
        elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
            bid += 800
            increase = "800"
            if self.weekday == 3:
                bid += 800
                increase = "**1600**"
            slotMsg = "{}{} - Three cherries! +{}! ".format(
                display_reels, message.author.mention, increase)
        elif line[0] == line[1] == line[2]:
            bid += 500
            increase = "500"
            if self.weekday == 3:
                bid += 500
                increase = "**1000**"
            slotMsg = "{}{} - Three symbols! +{}! ".format(
                display_reels, message.author.mention, increase)
        elif line[0] == ":two:" and line[1] == ":six:" or line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 4
            increase = "x 4"
            if self.weekday == 3:
                bid = bid * 2
                increase = "x **8**!"
            slotMsg = "{}{} - 26! Your bet is multiplied {}! {}! ".format(
                display_reels, message.author.mention, increase, str(bid))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 3
            increase = "x 3"
            if self.weekday == 3:
                bid = bid * 2
                increase = "x **6**!"
            slotMsg = "{}{} - Two cherries! Your bet is multiplied {}! {}! ".format(
                display_reels, message.author.mention, increase, str(bid))
        elif line[0] == line[1] or line[1] == line[2]:
            bid = bid * 2
            increase = "x 2"
            if self.weekday == 3:
                bid = bid * 2
                increase = "x **4**!"
            slotMsg = "{}{} - Two symbols! Your bet is multiplied {}! {}! ".format(
                display_reels, message.author.mention, increase, str(bid))
        else:
            jackpot += jackpot_inc
            slotMsg = "{}{} - Nothing! Lost bet.\nThe pot has increased by {} to {}.".format(
                display_reels, message.author.mention, str(jackpot_inc), str(jackpot))
            self.settings[message.author.server.id]["JACKPOT"] = jackpot
            dataIO.save_json(self.file_path, self.settings)
            self.bank.withdraw_credits(message.author, bid)
            slotMsg += "\n" + \
                "{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
            await self.bot.send_message(message.channel, slotMsg)
            return True
        self.bank.deposit_credits(message.author, bid)
        slotMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, slotMsg)

    @commands.command(pass_context=True, no_pm=True)
    async def heist(self, ctx, bid: int):
        """Try to rob a bank through one of many methods
        in an attempt to increase your virtual riches"""
        message = ctx.message
        author = message.author
        server = author.server
        
        if not self.bank.account_exists(author):
            await self.bot.say("{} You need an account to do any heists. Type `{}bank register` to open one.".format(author.mention, ctx.prefix))
            return
        if self.bank.can_spend(author, bid):
            if bid >= self.settings[server.id]["HEIST_MIN"] and bid <= self.settings[server.id]["HEIST_MAX"]:
                if author.id in self.heist_register:
                    if self.weekday == 2:
                        if abs(self.heist_register[author.id] - int(time.perf_counter())) >= self.settings[server.id]["HEIST_TIME"]/2:
                            self.heist_register[author.id] = int(
                                time.perf_counter())
                            await self.start_heist(ctx.message, bid)
                        else:
                            await self.bot.say("You already tried a heist fairly recently! Wait {} seconds before trying again.".format(int(self.settings[server.id]["HEIST_TIME"]/2)))
                    else:
                        if abs(self.heist_register[author.id] - int(time.perf_counter())) >= self.settings[server.id]["HEIST_TIME"]:
                            self.heist_register[author.id] = int(
                                time.perf_counter())
                            await self.start_heist(ctx.message, bid)
                        else:
                            await self.bot.say("You already tried a heist fairly recently! Wait {} seconds before trying again.".format(self.settings[server.id]["HEIST_TIME"]))
                else:
                    self.heist_register[author.id] = int(time.perf_counter())
                    await self.start_heist(ctx.message, bid)
            else:
                await self.bot.say("{0} Bid must be between {1} and {2}.".format(author.mention, self.settings[server.id]["HEIST_MIN"], self.settings[server.id]["HEIST_MAX"]))
        else:
            await self.bot.say("{0} You need an account with enough funds to participate in heists.".format(author.mention))

    async def start_heist(self, message, bid):
        # Decides on a random game.
        while True:
            gameNumber = randint(1, 6)
            if gameNumber == 1:
                await self.heist_game1(message, bid)
                break
            elif gameNumber == 2:
                if self.weekday != 4:
                    await self.heist_game2(message, bid)
                    break
            elif gameNumber == 3:
                if self.weekday != 1:
                    randomChance = randint(1, 100)
                    if randomChance > 80:
                        await self.heist_game3(message, bid)
                        break
            elif gameNumber == 4:
                await self.heist_game4(message, bid)
                break
            elif gameNumber == 5:
                randomChance = randint(1, 100)
                if randomChance > 40:
                    await self.heist_game5(message, bid)
                    break
            elif gameNumber == 6:
                randomChance = randint(1, 100)
                if randomChance >= 75:
                  await self.heist_game6(message, bid)
                  break

    async def heist_game1(self, message, bid):
        rps_drawshare = round(bid/8)
        if self.weekday == 5:
            rps_drawshare = rps_drawshare * 2
        # Rock - Paper - Scissors (Easiest to implement)
        author = message.author
        rpsSelf = randint(0,2)
        rpsEnemy = randint(0,2)
        icons = [":new_moon:", ":newspaper2:", ":scissors:"]
        names = ["Rock", "Paper", "Scissors"]
        heistMsg = "{} attempts robbing a virtual bank (again).\nThis time, they".format(author.mention)
        heistMsg += " decide to go for a gambling approach against the bank's manager.\n\n**-- Rock, Paper, Scissors --**"
        heistMsg += "\nResults:\n{}: {} ({})\nBank manager: {} ({})\n".format(author.name, icons[rpsSelf], names[rpsSelf], icons[rpsEnemy], names[rpsEnemy])
        if rpsSelf == rpsEnemy:
            bid = rps_drawshare
            heistMsg += "**Draw!** The bank manager sighs in relief and gives {} a small share of {} credits so they leave the bank alone for a while.".format(
                author.name, str(bid))
        elif rpsSelf == 0 and rpsEnemy == 2 or rpsSelf == 1 and rpsEnemy == 0 or rpsSelf == 2 and rpsEnemy == 1:
            bid = bid * 2
            increase = 2
            if self.weekday == 5:
                increase = 4
                bid = bid * 2
            heistMsg += "**Win!** As a result, {} left the bank with *{}x their bet*, gaining them {} credits.".format(
                author.name, increase, str(bid))
        else:
            heistMsg += "**Loss!** As a result, {} left the bank with *their bet gone to the bank*, costing them {} credits.".format(
                author.name, str(bid))
            self.bank.withdraw_credits(message.author, bid)
            heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
            await self.bot.send_message(message.channel, heistMsg)
            return True
        self.bank.deposit_credits(message.author, bid)
        heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, heistMsg)

    async def heist_game2(self, message, bid):
        die1 = randint(1, 6)
        die2 = randint(1, 6)
        playerStrength = die1 + die2
        enemyStrength = randint(7, 11)
        if self.weekday == 6:
            enemyStrength = randint(5, 9)
        heistMsg = "{} attempts robbing a virtual bank (again). This time, it's".format(message.author.mention)
        heistMsg += " a brute-force attempt: Breaking through the manager, **100% Orange Juice** style.\n(*Just imagine they have a \"Rush\" card and bear with the author of this script, okay?*)\n\n"
        heistMsg += "Results:\n:game_die: {}: {} + {} = {} strength\n:game_die: Guard patrol strength (to beat): **{}**\n".format(message.author.name, str(die1), str(die2), str(playerStrength), str(enemyStrength))
        if playerStrength > enemyStrength:
            bid = bid * 2
            if self.weekday == 5:
                bid = bid * 2
            heistMsg += "**Win!** And thanks to their victory, {} got out of the bank with {} more credits than they went in with.".format(message.author.name, str(bid))
            self.bank.deposit_credits(message.author, bid)
            heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
            await self.bot.send_message(message.channel, heistMsg)
            return True
        if playerStrength == enemyStrength:
            heistMsg += "**Draw!** And due to that, the guard barely "
        else:
            heistMsg += "**Loss!** Due to that, the guard "
        heistMsg += "managed to drag {} out of the bank and into the nearest police station, where they had to give off their bet, {} credits.".format(
            message.author.name, str(bid))
        self.bank.withdraw_credits(message.author, bid)
        heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, heistMsg)

    async def heist_game3(self, message, bid):
        playerDie = randint(1, 6)
        enemyDie = randint(3, 6)
        heistMsg = "{} would have liked to attempt robbing a virtual bank (as per usual), but has suddenly been interrupted by a seagull with a :game_die: in its mouth. Uh, oh.\n\n".format(message.author.mention)
        heistMsg += "Results:\n:game_die: {} strength: {} strength\n:game_die: Seagull strength: **{}**\n".format(message.author.name, str(playerDie), str(enemyDie))
        if playerDie < enemyDie:
            heistMsg += "**Loss!** The seagull was stronger than {}, grabbing his bet and flying off with it.".format(message.author.name)
            self.bank.withdraw_credits(message.author, bid)
            heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
            await self.bot.send_message(message.channel, heistMsg)
            return True
        elif playerDie == enemyDie:
            heistMsg += "**Draw!**"
        else:
            heistMsg += "**Win!**"
        heistMsg += " The seagull flew away, leaving the bid of {} be as it is - ".format(
            message.author.name)
        heistMsg += "However, the surprise attack was a bit too much to take (what if it stirred up the cops!?)"
        heistMsg += ", and they retreated back into their hideout.\n{} - *Standby for next heist attempt...*".format(message.author.name)
        await self.bot.send_message(message.channel, heistMsg)

    async def heist_game4(self, message, bid):
        traplist = ["Lasers", "Matrix maze", "Puzzle", "Robot guards", "Sniper dodging", "Turtle riding", "Strong rivers", "Avoid Nitori!", "Avoid the undefined machinery!"]
        heistMsg = "{} wanted to rob a bank, but (somehow) manages to get himself trapped in Nitori's lab instead. Good job.\n".format(message.author.mention)
        heistMsg += "The traps in her lab are pretty elaborate and can only be avoided with some high luck.\n"
        heistMsg += "There's a total of five traps in her lab that they have to avoid - if they fail three or cannot break the tough door at the end, they alarm the guards and fail.\n\n"
        
        result = ""
        fails = 0
        failAll = False
        for i in range(0, 5):
            trap = randchoice(traplist)
            fail = randint(1, 6)
            failThisStr = "Dodged!"
            if trap != "Avoid Nitori!":
                if fail > 4:
                    failThisStr = "*FAILED*"
                    fails += 1
                    if fails > 2:
                        failAll = True
            else:
                if fail > 2:
                    failThisStr = "*FAILED*"
                    fails += 1
                    if fails > 2:
                        failAll = True
            result += "**Trap {}: {}** - *{}* ({} / 6) = {} Fails\n".format(str(i+1), trap, failThisStr, str(7-fail), str(fails))

        if fails == 0:
            failDoor = 50
        elif fails == 1:
            failDoor = 37
        elif fails == 2:
            failDoor = 25
        else:
            failDoor = 0
        
        fail = randint(1, 100)
        if fail < failDoor:
            failAll = True
            result += "...But none of that mattered, because despite their excellent skill in breaking doors, they **did not manage to break the lab door open**.\n"
        result += "**Last Trap: The door** - :game_die: *{}/100* :game_die: (Failed if *<{}%*!)".format(str(fail), str(failDoor))
        heistMsg += result
        
        if failAll == True:
            heistMsg += "\n\nNitori decided to spare the traitor after finding them (because they failed), however, they insisted on taking away their bet."
            self.bank.withdraw_credits(message.author, bid)
            heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        else:
            if self.weekday == 5:
                bid = bid * 2
            extraBid = bid * (5 - fails)
            heistMsg += "\n\nThus, they came out with {} more credits than they went in with. Well, and an angry Nitori when she finds out that her lab's been broken.".format(str(extraBid))
            self.bank.deposit_credits(message.author, extraBid)
            heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, heistMsg)

    async def heist_game5(self, message, bid):
        bidStr = str(bid)
        self.bank.withdraw_credits(message.author, bid)
        bidNew = 0
        while bid > 0:
            bidNew = (bidNew*10) + bid%10
            bid //= 10
        self.bank.deposit_credits(message.author, bidNew)
        heistMsg = "{} tried heading for the bank in an attempt to heist it, but suddenly got interrupted by Seija Kijin!\nIn her usual fashion, she reverses the bid of {} to {} and then returns it to them.".format(message.author.mention, bidStr, str(bidNew))
        heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, heistMsg)

    async def heist_game6(self, message, bid):
        soulList = ["http://danbooru.donmai.us/data/__original_drawn_by_nanase_nao__c2bd8991990e79c7a5ad2ba9093e64cf.jpg",
                    "http://danbooru.donmai.us/data/__original_drawn_by_nanase_nao__06191b95f0fb2a532b8b390c64b71b6a.jpg",
                    "http://danbooru.donmai.us/data/__northern_ocean_hime_kantai_collection_drawn_by_nanase_nao__d009830f46ae882e58d0ba33fef694fa.jpg",
                    "http://danbooru.donmai.us/data/__kirisame_marisa_touhou_drawn_by_nanase_nao__ac3054c69c418c44b2f84fbdff05b639.jpg",
                    "http://danbooru.donmai.us/data/__hibiki_and_verniy_kantai_collection_drawn_by_nanase_nao__d7f3fa8ab6509f8d57ccf100c9fb327d.jpg"]
        heistMsg = "{}\nA stranger approaches {} as they try to go for a heist - It turns out said stranger is an evil soul... Even if they have a friendly look about them.".format(randchoice(soulList), message.author.mention)

        if self.weekday == 5:
            bid = bid * 2
        
        if self.bank.can_spend(message.author, bid * 3):
            bidAtRisk = bid * 3
        else:
            bidAtRisk = self.bank.get_balance(message.author)
        heistMsg += "\nSaid soul decides to put their gambling skills to the test and puts **{} credits** at the risk of loss - or win.".format(str(bidAtRisk))
        heistMsg += "\nThe soul hands them a d20 - and give them three tries to reach 45."
        die1 = randint(1, 20)
        die2 = randint(1, 20)
        die3 = randint(1, 20)
        total = die1 + die2 + die3
        heistMsg += "\n\n:game_die: {} rolls {}, {}, and {} for a total of {}.".format(message.author.name, str(die1), str(die2), str(die3), str(total))
        if total >= 45:
            self.bank.withdraw_credits(message.author, bid)
            heistMsg += "\nThe soul is quite amazed at {}'s skills and thus gives them {} credits in return.".format(message.author.name, str(bidAtRisk))
            self.bank.deposit_credits(message.author, bidAtRisk)
        else:
            self.bank.withdraw_credits(message.author, bidAtRisk)
            heistMsg += "\nSadly, {}'s luck isn't enough to beat the soul's rigged dice and thus loses {} credits.".format(message.author.name, str(bidAtRisk))
        heistMsg += "\n{} - Current credits: {}".format(message.author.name, self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, heistMsg)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def heistall(self, ctx, bid: int):
        """A random bank heist for everyone!

        Only admins can start these up."""
        if self.weekday == 5:
            bid = bid * 2
        message = ctx.message
        waitTime = randint(10, 15)
        await self.bot.say("There's now a heist going on for **everyone**, thanks to {}, for a grand total of **{}** credits!\nWe're selecting a random winner in **{}** seconds!\n\n(The bot will *not* be available during this time, please don't spam commands or I will spam messages across the channel once the wait is over!)".format(message.author.mention, str(bid), str(waitTime)))
        while waitTime > 0:
            time.sleep(1)
            waitTime -= 1
        winner = None
        stopIterate = False
        while True:
            for k in message.server.members:
                rnd = randint(1, 11)
                if self.bank.account_exists(k) and rnd < 3:
                    winner = k
                    stopIterate = True
                    break
            if stopIterate:
                break
        self.bank.deposit_credits(winner, bid)
        await self.bot.say("And the lucky winner is...\n**{}!** They won a total of {} credits for... being here! :diamond_shape_with_a_dot_inside:".format(winner.name, str(bid)))
        
    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def economyset(self, ctx):
        """Changes economy module settings"""
        server = ctx.message.server
        settings = self.settings[server.id]
        if ctx.invoked_subcommand is None:
            msg = "```"
            for k, v in settings.items():
                msg += "{}: {}\n".format(k, v)
            msg += "```"
            await send_cmd_help(ctx)
            await self.bot.say(msg)

    @economyset.command(pass_context=True)
    async def slotmin(self, ctx, bid: int):
        """Minimum slot machine bid"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_MIN"] = bid
        await self.bot.say("**Minimum slot bet:** " + str(bid) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def slotmax(self, ctx, bid: int):
        """Maximum slot machine bid"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_MAX"] = bid
        await self.bot.say("**Maximum slot bet:** " + str(bid) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def slottime(self, ctx, seconds: int):
        """Seconds between each slots use"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_TIME"] = seconds
        await self.bot.say("**Slot machine cooldown:** " + str(seconds) + " seconds")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def jackpotinit(self, ctx, jackpot: int):
        """Initial pot"""
        server = ctx.message.server
        self.settings[server.id]["JACKPOT_INITIAL_AMOUNT"] = jackpot
        await self.bot.say("**Jackpot reset value:** " + str(jackpot) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def jackpotcurrent(self, ctx, jackpot: int):
        """Current pot"""
        server = ctx.message.server
        self.settings[server.id]["JACKPOT"] = jackpot
        await self.bot.say("**Jackpot now:** " + str(jackpot) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def jackpotinc(self, ctx, jackpot: int):
        """Pot increase upon loss"""
        server = ctx.message.server
        self.settings[server.id]["JACKPOT_INCREASE"] = jackpot
        await self.bot.say("**Jackpot increase:** " + str(jackpot) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def heistmin(self, ctx, bid: int):
        """Minimum heist bet"""
        server = ctx.message.server
        self.settings[server.id]["HEIST_MIN"] = bid
        await self.bot.say("**Minimum heist bet:** " + str(bid) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def heistmax(self, ctx, bid: int):
        """Maximum heist bet"""
        server = ctx.message.server
        self.settings[server.id]["HEIST_MAX"] = bid
        await self.bot.say("**Maximum heist bet:** " + str(bid) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def heisttime(self, ctx, seconds: int):
        """Seconds between each heist"""
        server = ctx.message.server
        self.settings[server.id]["HEIST_TIME"] = seconds
        await self.bot.say("**Heist cooldown:** " + str(seconds) + " seconds")
        dataIO.save_json(self.file_path, self.settings)
        
    @economyset.command(pass_context=True)
    async def paydaytime(self, ctx, seconds: int):
        """Seconds between each payday"""
        server = ctx.message.server
        self.settings[server.id]["PAYDAY_TIME"] = seconds
        await self.bot.say("**Payday cooldown:** " + str(seconds) + " seconds")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def paydaycredits(self, ctx, creds: int):
        """Credits earned each payday"""
        server = ctx.message.server
        self.settings[server.id]["PAYDAY_CREDITS"] = creds
        await self.bot.say("**Payday salary:** " + str(creds) + " credits")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def registercredits(self, ctx, credits: int):
        """Credits given on registering an account (BROKEN)"""
        server = ctx.message.server
        if credits < 0:
            credits = 0
        self.settings[server.id]["REGISTER_CREDITS"] = credits
        await self.bot.say("Registering an account will now give {} credits.\n...Although this is completely **broken** and I don't know why you're changing this.".format(credits))
        dataIO.save_json(self.file_path, self.settings)

    @commands.command()
    async def economyspecial(self):
        """Find out today's Economy special effect

        Could be a payday boost, slot boost, or a few other things"""
        specialsEmbed = discord.Embed(colour = discord.Colour(value=int("DDDDFF", 16)))
        specialsEmbed.add_field(name=days_of_the_week[self.weekday], value=heist_special_effect[self.weekday])

        specialsEmbed.set_author(name="Economy Blue", url="https://discord.gg/EvcHVc6", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Dollar_Sign.svg/500px-Dollar_Sign.svg.png")
        specialsEmbed.set_footer(text="Today's special effect")
        try:
            await self.bot.say(embed=specialsEmbed)
        except discord.HTTPException:
            await self.bot.say("[Economy Blue]\nToday is **{}**\nToday's special effect: **{}**".format(self.heist_day, self.heist_special))

    @commands.command()
    async def economyspecials(self):
        """Find out all special effects"""
        specialsEmbed = discord.Embed(colour = discord.Colour(value=int("DDDDFF", 16)))
        specialsString = "[Economy Blue]\n**Special Effects**"
        for i in range(0,7):
            spday = days_of_the_week[i]
            speff = heist_special_effect[i]
            specialsEmbed.add_field(name=days_of_the_week[i], value=heist_special_effect[i])
            specialsString += "\n{}: {}".format(days_of_the_week[i], heist_special_effect[i])

        specialsEmbed.set_author(name="Economy Blue", url="https://discord.gg/EvcHVc6", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Dollar_Sign.svg/500px-Dollar_Sign.svg.png")
        specialsEmbed.set_footer(text="Special Effects List")
        try:
            await self.bot.say(embed=specialsEmbed)
        except discord.HTTPException:
            await self.bot.say(specialsString)
    
    @commands.command()
    async def reloadspecial(self):
        """Set the proper weekday so special effects work as intended"""
        newWeekday = datetime.today().weekday()
        if self.weekday != newWeekday:
            self.weekday = datetime.today().weekday()
            self.heist_day = days_of_the_week[self.weekday]
            self.heist_special = heist_special_effect[self.weekday]
            await self.bot.say("Special effect reloaded. Use the `economyspecial` command to find out what it is.")
        else:
            await self.bot.say("The special effect is **still** the same, Pute la grande. Here's my system time:\n" + datetime.now().strftime('%A, %b %d %Y @ %I:%M:%S %p (UTC+0100)'))

##    @commands.group(pass_context=True, no_pm=True)
##    async def shop(self, ctx):
##        """List shop items or buy an item!"""
##        if ctx.invoked_subcommand is None:
##            msg = "```"
##            for k, v in self.shoplist:
##                msg += "{}: {}\n".format(k, v)
##            msg += "```"
##            await self.bot.say(msg)

    def display_time(self, seconds, granularity=2):
        intervals = (
            ('weeks', 604800),
            ('days', 86400),
            ('hours', 3600),
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

    f = "data/economy/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default economy's settings.json...")
        dataIO.save_json(f, {})

    f = "data/economy/bank.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty bank.json...")
        dataIO.save_json(f, {})

    f = "data/economy/shoplist.json"
    if not dataIO.is_valid_json(f):
        print("Creating default shoplist.json...")
        dataIO.save_json(f, {})

    f = "data/economy/shopitems.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty shopitems.json...")
        dataIO.save_json(f, {})


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("red.economy")
    if logger.level == 0:
        # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename='data/economy/economy.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(Economy(bot))
