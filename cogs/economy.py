import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from collections import namedtuple, defaultdict
from datetime import datetime
from random import randint
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import os
import time
import logging

default_settings = {"PAYDAY_TIME" : 300, "PAYDAY_CREDITS" : 120, "SLOT_MIN" : 5, "SLOT_MAX" : 100, "SLOT_TIME" : 0}

slot_payouts = """Slot machine payouts:
    :two: :two: :six: Bet * 5000
    :four_leaf_clover: :four_leaf_clover: :four_leaf_clover: +1000
    :cherries: :cherries: :cherries: +800
    :two: :six: Bet * 4
    :cherries: :cherries: Bet * 3

    Three symbols: +500
    Two symbols: Bet * 2"""


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
            if user.id in self.accounts: # Legacy account
                balance = self.accounts[user.id]["balance"]
            else:
                balance = initial_balance
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            account = {"name" : user.name,
                       "balance" : balance,
                       "created_at" : timestamp
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
            if server is None:# Servers that have since been left will be ignored
                continue      # Same for users_id from the old bank format
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

class Economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        global default_settings
        self.bot = bot
        self.bank = Bank(bot, "data/economy/bank.json")
        self.file_path = "data/economy/settings.json"
        self.settings = dataIO.load_json(self.file_path)
        if "PAYDAY_TIME" in self.settings: #old format
            default_settings = self.settings
            self.settings = {}
        self.settings = defaultdict(lambda: default_settings, self.settings)
        self.payday_register = defaultdict(dict)
        self.slot_register = defaultdict(dict)

    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the Twentysix bank"""
        user = ctx.message.author
        try:
            account = self.bank.create_account(user)
            await self.bot.say("{} Account opened. Current balance: {}".format(user.mention,
                account.balance))
        except AccountAlreadyExists:
            await self.bot.say("{} You already have an account at the Twentysix bank.".format(user.mention))

    @_bank.command(pass_context=True)
    async def balance(self, ctx, user : discord.Member=None):
        """Shows balance of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your balance is: {}".format(user.mention, self.bank.get_balance(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Twentysix bank."
                 " Type {}bank register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s balance is {}".format(user.name, self.bank.get_balance(user)))
            except NoAccount:
                await self.bot.say("That user has no bank account.")

    @_bank.command(pass_context=True)
    async def transfer(self, ctx, user : discord.Member, sum : int):
        """Transfer credits to other users"""
        author = ctx.message.author
        try:
            self.bank.transfer_credits(author, user, sum)
            logger.info("{}({}) transferred {} credits to {}({})".format(
                author.name, author.id, sum, user.name, user.id))
            await self.bot.say("{} credits have been transferred to {}'s account.".format(sum, user.name))
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
    async def _set(self, ctx, user : discord.Member, sum : int):
        """Sets credits of user's bank account

        Admin/owner restricted."""
        author = ctx.message.author
        try:
            self.bank.set_credits(user, sum)
            logger.info("{}({}) set {} credits to {} ({})".format(author.name, author.id, str(sum), user.name, user.id))
            await self.bot.say("{}'s credits have been set to {}".format(user.name, str(sum)))
        except NoAccount:
            await self.bot.say("User has no bank account.")

    @commands.command(pass_context=True, no_pm=True)
    async def payday(self, ctx): # TODO
        """Get some free credits"""
        author = ctx.message.author
        server = author.server
        id = author.id
        if self.bank.account_exists(author):
            if id in self.payday_register[server.id]:
                seconds = abs(self.payday_register[server.id][id] - int(time.perf_counter()))
                if seconds  >= self.settings[server.id]["PAYDAY_TIME"]:
                    self.bank.deposit_credits(author, self.settings[server.id]["PAYDAY_CREDITS"])
                    self.payday_register[server.id][id] = int(time.perf_counter())
                    await self.bot.say("{} Here, take some credits. Enjoy! (+{} credits!)".format(author.mention, str(self.settings[server.id]["PAYDAY_CREDITS"])))
                else:
                    await self.bot.say("{} Too soon. For your next payday you have to wait {}.".format(author.mention, self.display_time(self.settings[server.id]["PAYDAY_TIME"] - seconds)))
            else:
                self.payday_register[server.id][id] = int(time.perf_counter())
                self.bank.deposit_credits(author, self.settings[server.id]["PAYDAY_CREDITS"])
                await self.bot.say("{} Here, take some credits. Enjoy! (+{} credits!)".format(author.mention, str(self.settings[server.id]["PAYDAY_CREDITS"])))
        else:
            await self.bot.say("{} You need an account to receive credits. Type {}bank register to open one.".format(author.mention, ctx.prefix))

    @commands.group(pass_context=True)
    async def leaderboard(self, ctx):
        """Server / global leaderboard

        Defaults to server"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._server_leaderboard)

    @leaderboard.command(name="server", pass_context=True)
    async def _server_leaderboard(self, ctx, top : int=10):
        """Prints out the server's leaderboard

        Defaults to top 10""" #Originally coded by Airenkun - edited by irdumb
        server = ctx.message.server
        if top < 1:
            top = 10
        bank_sorted = sorted(self.bank.get_server_accounts(server),
         key=lambda x: x.balance, reverse=True)
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1
        for acc in topten:
            highscore += str(place).ljust(len(str(top))+1)
            highscore += (acc.name+" ").ljust(23-len(str(acc.balance)))
            highscore += str(acc.balance) + "\n"
            place += 1
        if highscore:
            if len(highscore) < 1985:
                await self.bot.say("```py\n"+highscore+"```")
            else:
                await self.bot.say("The leaderboard is too big to be displayed. Try with a lower <top> parameter.")
        else:
            await self.bot.say("There are no accounts in the bank.")

    @leaderboard.command(name="global")
    async def _global_leaderboard(self, top : int=10):
        """Prints out the global leaderboard

        Defaults to top 10"""
        if top < 1:
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
            highscore += str(place).ljust(len(str(top))+1)
            highscore += ("{} |{}| ".format(acc.name, acc.server.name)).ljust(23-len(str(acc.balance)))
            highscore += str(acc.balance) + "\n"
            place += 1
        if highscore:
            if len(highscore) < 1985:
                await self.bot.say("```py\n"+highscore+"```")
            else:
                await self.bot.say("The leaderboard is too big to be displayed. Try with a lower <top> parameter.")
        else:
            await self.bot.say("There are no accounts in the bank.")

    def already_in_list(self, accounts, user):
        for acc in accounts:
            if user.id == acc.id:
                return True
        return False

    @commands.command()
    async def payouts(self):
        """Shows slot machine payouts"""
        await self.bot.whisper(slot_payouts)

    @commands.command(pass_context=True, no_pm=True)
    async def slot(self, ctx, bid : int):
        """Play the slot machine"""
        author = ctx.message.author
        server = author.server
        if not self.bank.account_exists(author):
            await self.bot.say("{} You need an account to use the slot machine. Type {}bank register to open one.".format(author.mention, ctx.prefix))
            return
        if self.bank.can_spend(author, bid):
            if bid >= self.settings[server.id]["SLOT_MIN"] and bid <= self.settings[server.id]["SLOT_MAX"]:
                if author.id in self.slot_register:
                    if abs(self.slot_register[author.id] - int(time.perf_counter()))  >= self.settings[server.id]["SLOT_TIME"]:
                        self.slot_register[author.id] = int(time.perf_counter())
                        await self.slot_machine(ctx.message, bid)
                    else:
                        await self.bot.say("Slot machine is still cooling off! Wait {} seconds between each pull".format(self.settings[server.id]["SLOT_TIME"]))
                else:
                    self.slot_register[author.id] = int(time.perf_counter())
                    await self.slot_machine(ctx.message, bid)
            else:
                await self.bot.say("{0} Bid must be between {1} and {2}.".format(author.mention, self.settings[server.id]["SLOT_MIN"], self.settings[server.id]["SLOT_MAX"]))
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

        display_reels = "~~\n~~  " + reels[0][0] + " " + reels[1][0] + " " + reels[2][0] + "\n"
        display_reels += ">" + reels[0][1] + " " + reels[1][1] + " " + reels[2][1] + "\n"
        display_reels += "  " + reels[0][2] + " " + reels[1][2] + " " + reels[2][2] + "\n"

        if line[0] == ":two:" and line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 5000
            slotMsg = "{}{} 226! Your bet is multiplied * 5000! {}! ".format(display_reels, message.author.mention, str(bid))
        elif line[0] == ":four_leaf_clover:" and line[1] == ":four_leaf_clover:" and line[2] == ":four_leaf_clover:":
            bid += 1000
            slotMsg = "{}{} Three FLC! +1000! ".format(display_reels, message.author.mention)
        elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
            bid += 800
            slotMsg = "{}{} Three cherries! +800! ".format(display_reels, message.author.mention)
        elif line[0] == line[1] == line[2]:
            bid += 500
            slotMsg = "{}{} Three symbols! +500! ".format(display_reels, message.author.mention)
        elif line[0] == ":two:" and line[1] == ":six:" or line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 4
            slotMsg = "{}{} 26! Your bet is multiplied * 4! {}! ".format(display_reels, message.author.mention, str(bid))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 3
            slotMsg = "{}{} Two cherries! Your bet is multiplied * 3! {}! ".format(display_reels, message.author.mention, str(bid))
        elif line[0] == line[1] or line[1] == line[2]:
            bid = bid * 2
            slotMsg = "{}{} Two symbols! Your bet is multiplied * 2! {}! ".format(display_reels, message.author.mention, str(bid))
        else:
            slotMsg = "{}{} Nothing! Lost bet. ".format(display_reels, message.author.mention)
            self.bank.withdraw_credits(message.author, bid)
            slotMsg += "\n" + " Credits left: {}".format(self.bank.get_balance(message.author))
            await self.bot.send_message(message.channel, slotMsg)
            return True
        self.bank.deposit_credits(message.author, bid)
        slotMsg += "\n" + " Current credits: {}".format(self.bank.get_balance(message.author))
        await self.bot.send_message(message.channel, slotMsg)

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
    async def slotmin(self, ctx, bid : int):
        """Minimum slot machine bid"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_MIN"] = bid
        await self.bot.say("Minimum bid is now " + str(bid) + " credits.")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def slotmax(self, ctx, bid : int):
        """Maximum slot machine bid"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_MAX"] = bid
        await self.bot.say("Maximum bid is now " + str(bid) + " credits.")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def slottime(self, ctx, seconds : int):
        """Seconds between each slots use"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_TIME"] = seconds
        await self.bot.say("Cooldown is now " + str(seconds) + " seconds.")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def paydaytime(self, ctx, seconds : int):
        """Seconds between each payday"""
        server = ctx.message.server
        self.settings[server.id]["PAYDAY_TIME"] = seconds
        await self.bot.say("Value modified. At least " + str(seconds) + " seconds must pass between each payday.")
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def paydaycredits(self, ctx, credits : int):
        """Credits earned each payday"""
        server = ctx.message.server
        self.settings[server.id]["PAYDAY_CREDITS"] = credits
        await self.bot.say("Every payday will now give " + str(credits) + " credits.")
        dataIO.save_json(self.file_path, self.settings)

    def display_time(self, seconds, granularity=2):  # What would I ever do without stackoverflow?
        intervals = (                                # Source: http://stackoverflow.com/a/24542445
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

    f = "data/economy/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default economy's settings.json...")
        dataIO.save_json(f, {})

    f = "data/economy/bank.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty bank.json...")
        dataIO.save_json(f, {})


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("red.economy")
    if logger.level == 0:  # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/economy/economy.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(Economy(bot))
