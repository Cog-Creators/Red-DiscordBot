import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from collections import namedtuple, defaultdict, deque
from datetime import datetime
from copy import deepcopy
from .utils import checks
from cogs.utils.chat_formatting import pagify, box
from enum import Enum
from __main__ import send_cmd_help
import sys
import re
import os
import math
import time
import logging
import random
from urllib.request import Request, urlopen
from urllib.error import URLError
from bs4 import BeautifulSoup

default_settings = {"PAYDAY_TIME": 300, "PAYDAY_CREDITS": 100,
                    "SLOT_MIN": 5, "SLOT_MAX": 100, "SLOT_TIME": 5,
                    "REGISTER_CREDITS": 25}


class EconomyError(Exception):
    pass


class OnCooldown(EconomyError):
    pass


class InvalidBid(EconomyError):
    pass


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


NUM_ENC = "\N{COMBINING ENCLOSING KEYCAP}"
SLOTS_CHANNEL = "353262349244956682"
LEADERBOARD_URL = "https://mee6.xyz/levels/258990595723231232"


class SMReel(Enum):
    cherries  = "\N{CHERRIES}"
    cookie    = "\N{COOKIE}"
    #one       = "\N{DIGIT ONE}" + NUM_ENC
    #two       = "\N{DIGIT TWO}" + NUM_ENC
    #three     = "\N{DIGIT THREE}" + NUM_ENC
    #four      = "\N{DIGIT FOUR}" + NUM_ENC
    #five      = "\N{DIGIT FIVE}" + NUM_ENC
    #six       = "\N{DIGIT SIX}" + NUM_ENC
    #seven     = "\N{DIGIT SEVEN}" + NUM_ENC
    #eight     = "\N{DIGIT EIGHT}" + NUM_ENC
    #nine      = "\N{DIGIT NINE}" + NUM_ENC
    #zero      = "\N{DIGIT ZERO}" + NUM_ENC
    flc       = "\N{FOUR LEAF CLOVER}"
    #cyclone   = "\N{CYCLONE}"
    sunflower = "\N{SUNFLOWER}"
    #mushroom  = "\N{MUSHROOM}"
    #heart     = "\N{HEAVY BLACK HEART}"
    snowflake = "\N{SNOWFLAKE}"
    smith     = "<:smithscream:260216228482777088>"
    regi      = "<:regi:260165156464623617>"
    saef      = "<:staysaef:305076370885836801>"
    boots     = "<:bluefox:321124064947208192>"
    melee     = "<:Melee:260154755706257408>"
    fivenine  = "<:buschice:331871719671332866>"

PAYOUTS = {
    (SMReel.fivenine, SMReel.fivenine, SMReel.fivenine) : {
        "payout" : lambda x: math.ceil(x * 5.9 + x),
        "phrase" : "The Dern Best! Your bid has been multiplied * 5.9!"
    },
    (SMReel.flc, SMReel.flc, SMReel.flc) : {
        "payout" : lambda x: x + 1000,
        "phrase" : "Lucky! +1000!"
    },
    (SMReel.smith, SMReel.saef, SMReel.regi) : {
        "payout" : lambda x: x * 50,
        "phrase" : "The Trifecta of Slots! Your bid was multiplied by 50!!"
    },
    (SMReel.cherries, SMReel.cherries, SMReel.cherries) : {
        "payout" : lambda x: x + 500,
        "phrase" : "Three cherries! +500!"
    },
    (SMReel.cherries, SMReel.cherries) : {
        "payout" : lambda x: x * 3 + x,
        "phrase" : "Two cherries! Your bid has been multiplied * 3!"
    },
    "3 symbols" : {
        "payout" : lambda x: x + 500,
        "phrase" : "Three symbols! +500!"
    },
    "2 symbols" : {
        "payout" : lambda x: x * 2 + x,
        "phrase" : "Two symbols! Your bid has been multiplied * 2!"
    },
}

SLOT_PAYOUTS_MSG = (
                    "Slot machine payouts:\n"
                    "{smith.value} {saef.value} {regi.value} Bet * 2000\n"
                    "{fivenine.value} {fivenine.value} {fivenine.value} Bet * 590\n"
                    "{flc.value} {flc.value} {flc.value} +1000\n"
                    "{cherries.value} {cherries.value} {cherries.value} +800\n"
                    "{cherries.value} {cherries.value} Bet * 3\n\n"
                    "Three symbols: +500\n"
                    "Two symbols: Bet * 2".format(**SMReel.__dict__))

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
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
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

class Experience:
    """Experience

    Tracks mee6 ranks and integrates it into Economy"""

    def __init__(self, bot, file_path):
        self.leaderboard = dataIO.load_json(file_path)
        self.file_path = file_path
        self.bot = bot
       
    #TODO recreate the functionality of mee6's ranks plugin and
    #     demolish this horrible nonsense.
    async def update_leaderboard(self, server):
        req = Request(LEADERBOARD_URL, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            html = urlopen(req).read()
        except URLError as e:
            if hasattr(e, 'reason'):
                print('We failed to reach a server.')
                print('Reason: ', e.reason)
                sys.exit(1)
            elif hasattr(e, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)
                sys.exit(1)

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find("div", { "class" : "list-group" } )
        plaintext = ""

        for entry in table.find_all("h3"):
           plaintext += entry.get_text()+"\n"
        
        fixedtext = os.linesep.join([s for s in plaintext.splitlines() if s])
        fixedtext = re.sub(r'(\s)(#\d{4})', r'\2', fixedtext)

        length = (((fixedtext.count('\n')+1)/3))

        for index in range(int(length)):
            rank = re.sub('#', '', fixedtext.splitlines()[index*3])
            #Format from mee6: Nickname#dddd
            user = fixedtext.splitlines()[(index*3)+1]
            level = re.sub('Level ', '', fixedtext.splitlines()[(index*3)+2])
            print(user+" rank: "+str(rank))
            
            members = server.members
            for member in members:
                fullname = member.name+"#"+str(member.discriminator)
                if fullname == user:
                    user = member.id
            if user not in self.leaderboard:
                self.leaderboard[user] = {}
            self.leaderboard[user]["level"] = int(level)
            self.leaderboard[user]["rank"] = int(rank)

        dataIO.save_json(self.file_path, self.leaderboard)
        await self.bot.say("Internal leaderboards have been updated.")

    def get_payday_multiplier(self, user):
        acc = self._get_user(user)
        if 1 <= acc["rank"] <= 10:
            return 10
        if acc["level"] < 5:
            return 1
        if 5 <= acc["level"] < 10:
            return 2
        if 10 <= acc["level"] < 20:
            return 3
        if 20 <= acc["level"] < 30:
            return 4
        if 30 <= acc["level"] < 40:
            return 5
        if 40 <= acc["level"] < 50:
            return 6
        if 50 <= acc["level"]:
            return 7

    def _get_user(self, user):
        try:
            return deepcopy(self.leaderboard[user])
        except KeyError:
            raise NoAccount()

class Economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        global default_settings
        self.bot = bot
        self.bank = Bank(bot, "data/economy/bank.json")
        self.xp = Experience(bot, "data/economy/experience.json")
        self.file_path = "data/economy/settings.json"
        self.settings = dataIO.load_json(self.file_path)
        if "PAYDAY_TIME" in self.settings:  # old format
            default_settings = self.settings
            self.settings = {}
        self.settings = defaultdict(lambda: default_settings, self.settings)
        self.payday_register = defaultdict(dict)
        self.slot_register = defaultdict(dict)
    
    def is_slots():
        def predicate(ctx):
            return ctx.message.channel.id == SLOTS_CHANNEL
        return commands.check(predicate)
       
    @commands.command(name="update_xp_table", pass_context=True, no_pm=False)
    #@check.role_or_permissions("BOT") TODO
    async def updateXPTable(self, ctx):
        await self.xp.update_leaderboard(ctx.message.server)
 
    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the bank"""
        settings = self.settings[ctx.message.server.id]
        author = ctx.message.author
        credits = 0
        if ctx.message.server.id in self.settings:
            credits = settings.get("REGISTER_CREDITS", 0)
        try:
            account = self.bank.create_account(author, initial_balance=credits)
            await self.bot.say("{} Account opened. Current balance: {}"
                               "".format(author.mention, account.balance))
        except AccountAlreadyExists:
            await self.bot.say("{} You already have an account at the"
                               " NC Melee bank.".format(author.mention))

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
                                   " NC Melee bank. Type `{}bank register`"
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

    @_bank.command(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(administrator=True)
    async def reset(self, ctx, confirmation: bool=False):
        """Deletes all server's bank accounts"""
        if confirmation is False:
            await self.bot.say("This will delete all bank accounts on "
                               "this server.\nIf you're sure, type "
                               "{}bank reset yes".format(ctx.prefix))
        else:
            self.bank.wipe_bank(ctx.message.server)
            await self.bot.say("All bank accounts of this server have been "
                               "deleted.")

    async def _payday(self, server, author, id):
        multiplier = self.xp.get_payday_multiplier(str(author.id))
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if (int((now - midnight).total_seconds()) % 9) == 0:
            self.bank.deposit_credits(author, self.settings[
                                      server.id]["PAYDAY_CREDITS"]*100)
            self.payday_register[server.id][
                id] = int(time.perf_counter())
            await self.bot.say(
                "$Mike has blessed {} with a bonus payday! (+{}"
                " credits! (x100 $Mike bonus!!)".format(
                    author.mention,
                    str(self.settings[server.id]["PAYDAY_CREDITS"])))
        else:
            self.bank.deposit_credits(author, self.settings[
                                      server.id]["PAYDAY_CREDITS"]*multiplier)
            self.payday_register[server.id][
                id] = int(time.perf_counter())
            if multiplier == 10:
                await self.bot.say(
                    "{} Here, take some credits. Enjoy! (+{}"
                    " credits!\n_x{} bonus for being in the top 10!_"
                    " Use !levels for current Mee6 ranks!))".format(
                        author.mention,
                        str(self.settings[server.id]["PAYDAY_CREDITS"]*multiplier),
                        str(multiplier)))
            else:
                await self.bot.say(
                    "{} Here, take some credits. Enjoy! (+{}"
                    " credits! (x{} !rank bonus))".format(
                        author.mention,
                        str(self.settings[server.id]["PAYDAY_CREDITS"]*multiplier),
                        str(multiplier)))

    @commands.command(pass_context=True, no_pm=True)
    @is_slots()
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
                    await self._payday(server, author, id)
                else:
                    dtime = self.display_time(
                        self.settings[server.id]["PAYDAY_TIME"] - seconds)
                    await self.bot.say(
                        "{} Too soon. For your next payday you have to"
                        " wait {}.".format(author.mention, dtime))
            else:
                self.payday_register[server.id][id] = int(time.perf_counter())
                await self._payday(server, author, id)
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
        """Prints out the server's leaderboard

        Defaults to top 10"""
        # Originally coded by Airenkun - edited by irdumb
        server = ctx.message.server
        if top < 1:
            top = 10
        bank_sorted = sorted(self.bank.get_server_accounts(server),
                             key=lambda x: x.balance, reverse=True)
        bank_sorted = [a for a in bank_sorted if a.member] #  exclude users who left
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1
        for acc in topten:
            highscore += str(place).ljust(len(str(top)) + 1)
            highscore += (str(acc.member.display_name) + " ").ljust(23 - len(str(acc.balance)))
            highscore += str(acc.balance) + "\n"
            place += 1
        if highscore != "":
            for page in pagify(highscore, shorten_by=12):
                await self.bot.say(box(page, lang="py"))
        else:
            await self.bot.say("There are no accounts in the bank.")

    @leaderboard.command(name="global")
    async def _global_leaderboard(self, top: int=10):
        """Prints out the global leaderboard

        Defaults to top 10"""
        if top < 1:
            top = 10
        bank_sorted = sorted(self.bank.get_all_accounts(),
                             key=lambda x: x.balance, reverse=True)
        bank_sorted = [a for a in bank_sorted if a.member] #  exclude users who left
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
            highscore += ("{} |{}| ".format(acc.member, acc.server)
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

    @commands.command()
    @is_slots()
    async def payouts(self):
        """Shows slot machine payouts"""
        await self.bot.say(SLOT_PAYOUTS_MSG)

    @commands.command(pass_context=True, no_pm=True)
    @is_slots()
    async def slot(self, ctx, bid: int):
        """Play the slot machine"""
        author = ctx.message.author
        server = author.server
        settings = self.settings[server.id]
        valid_bid = settings["SLOT_MIN"] <= bid and bid <= settings["SLOT_MAX"]
        slot_time = settings["SLOT_TIME"]
        last_slot = self.slot_register.get(author.id)
        now = datetime.utcnow()
        try:
            if last_slot:
                if (now - last_slot).seconds < slot_time:
                    raise OnCooldown()
            if not valid_bid:
                raise InvalidBid()
            if not self.bank.can_spend(author, bid):
                raise InsufficientBalance
            await self.slot_machine(author, bid)
        except NoAccount:
            await self.bot.say("{} You need an account to use the slot "
                               "machine. Type `{}bank register` to open one."
                               "".format(author.mention, ctx.prefix))
        except InsufficientBalance:
            await self.bot.say("{} You need an account with enough funds to "
                               "play the slot machine.".format(author.mention))
        except OnCooldown:
            await self.bot.say("Slot machine is still cooling off! Wait {} "
                               "seconds between each pull".format(slot_time))
        except InvalidBid:
            await self.bot.say("Bid must be between {} and {}."
                               "".format(settings["SLOT_MIN"],
                                         settings["SLOT_MAX"]))

    async def slot_machine(self, author, bid):
        default_reel = deque(SMReel)
        reels = []
        self.slot_register[author.id] = datetime.utcnow()
        for i in range(3):
            default_reel.rotate(random.randint(-999, 999)) # weeeeee
            new_reel = deque(default_reel, maxlen=3) # we need only 3 symbols
            reels.append(new_reel)                   # for each reel
        rows = ((reels[0][0], reels[1][0], reels[2][0]),
                (reels[0][1], reels[1][1], reels[2][1]),
                (reels[0][2], reels[1][2], reels[2][2]))

        slot = "~~\n~~" # Mobile friendly
        for i, row in enumerate(rows): # Let's build the slot to show
            sign = "  "
            if i == 1:
                sign = ">"
            slot += "{}{} {} {}\n".format(sign, *[c.value for c in row])

        payout = PAYOUTS.get(rows[1])
        if not payout:
            # Checks for two-consecutive-symbols special rewards
            payout = PAYOUTS.get((rows[1][0], rows[1][1]),
                     PAYOUTS.get((rows[1][1], rows[1][2]))
                                )
        if not payout:
            # Still nothing. Let's check for 3 generic same symbols
            # or 2 consecutive symbols
            has_three = rows[1][0] == rows[1][1] == rows[1][2]
            has_two = (rows[1][0] == rows[1][1]) or (rows[1][1] == rows[1][2])
            if has_three:
                payout = PAYOUTS["3 symbols"]
            elif has_two:
                payout = PAYOUTS["2 symbols"]

        if payout:
            then = self.bank.get_balance(author)
            pay = payout["payout"](bid)
            now = then - bid + pay
            self.bank.set_credits(author, now)
            await self.bot.say("{}\n{} {}\n\nYour bid: {}\n{} → {}!"
                               "".format(slot, author.mention,
                                         payout["phrase"], bid, then, now))
        else:
            then = self.bank.get_balance(author)
            self.bank.withdraw_credits(author, bid)
            now = then - bid
            await self.bot.say("{}\n{} Nothing!\nYour bid: {}\n{} → {}!"
                               "".format(slot, author.mention, bid, then, now))

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
        await self.bot.say("Minimum bid is now {} credits.".format(bid))
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def slotmax(self, ctx, bid: int):
        """Maximum slot machine bid"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_MAX"] = bid
        await self.bot.say("Maximum bid is now {} credits.".format(bid))
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def slottime(self, ctx, seconds: int):
        """Seconds between each slots use"""
        server = ctx.message.server
        self.settings[server.id]["SLOT_TIME"] = seconds
        await self.bot.say("Cooldown is now {} seconds.".format(seconds))
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def paydaytime(self, ctx, seconds: int):
        """Seconds between each payday"""
        server = ctx.message.server
        self.settings[server.id]["PAYDAY_TIME"] = seconds
        await self.bot.say("Value modified. At least {} seconds must pass "
                           "between each payday.".format(seconds))
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def paydaycredits(self, ctx, credits: int):
        """Credits earned each payday"""
        server = ctx.message.server
        self.settings[server.id]["PAYDAY_CREDITS"] = credits
        await self.bot.say("Every payday will now give {} credits."
                           "".format(credits))
        dataIO.save_json(self.file_path, self.settings)

    @economyset.command(pass_context=True)
    async def registercredits(self, ctx, credits: int):
        """Credits given on registering an account"""
        server = ctx.message.server
        if credits < 0:
            credits = 0
        self.settings[server.id]["REGISTER_CREDITS"] = credits
        await self.bot.say("Registering an account will now give {} credits."
                           "".format(credits))
        dataIO.save_json(self.file_path, self.settings)

    # What would I ever do without stackoverflow?
    def display_time(self, seconds, granularity=2):
        intervals = (  # Source: http://stackoverflow.com/a/24542445
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
    
    f = "data/economy/experience.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty experience.json...")
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
