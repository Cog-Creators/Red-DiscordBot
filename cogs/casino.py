# STD Library
import asyncio
import logging
import logging.handlers
import os
import random
import time
from copy import deepcopy

# Discord imports
import discord
from fractions import Fraction
from operator import itemgetter
from .utils.dataIO import dataIO
from .utils import checks
from discord.ext import commands
from __main__ import send_cmd_help

# Third Party Libraries
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except ImportError:
    tabulateAvailable = False


# Default settings that is created when a server begin's using Casino
server_default = {"System Config": {"Casino Name": "Han Wavel Galactic Casino", "Casino Open": True,
                                    "Chip Name": "Flainian Pobble Beads", "Chip Rate": 1, "Default Payday": 100,
                                    "Payday Timer": 1200, "Threshold Switch": False,
                                    "Threshold": 10000, "Credit Rate": 1, "Version": 1.581
                                    },
                  "Memberships": {},
                  "Players": {},
                  "Games": {"Dice": {"Multiplier": 2.2, "Cooldown": 5, "Open": True, "Min": 50,
                                     "Max": 500, "Access Level": 0},
                            "Coin": {"Multiplier": 1.5, "Cooldown": 5, "Open": True, "Min": 10,
                                     "Max": 10, "Access Level": 0},
                            "Cups": {"Multiplier": 2.2, "Cooldown": 5, "Open": True, "Min": 50,
                                     "Max": 500, "Access Level": 0},
                            "Blackjack": {"Multiplier": 2.2, "Cooldown": 5, "Open": True,
                                          "Min": 50, "Max": 500, "Access Level": 0},
                            "Allin": {"Multiplier": 2.2, "Cooldown": 86400, "Open": True,
                                      "Access Level": 0},
                            "Hi-Lo": {"Multiplier": 1.5, "Cooldown": 5, "Open": True,
                                      "Min": 20, "Max": 20, "Access Level": 0},
                            "War": {"Multiplier": 1.5, "Cooldown": 5, "Open": True,
                                    "Min": 20, "Max": 20, "Access Level": 0},
                            }
                  }

new_user = {"Chips": 100,
            "Membership": None,
            "Pending": 0,
            "Played": {"Dice Played": 0, "Cups Played": 0, "BJ Played": 0, "Coin Played": 0,
                       "Allin Played": 0, "Hi-Lo Played": 0, "War Played": 0},
            "Won": {"Dice Won": 0, "Cups Won": 0, "BJ Won": 0, "Coin Won": 0, "Allin Won": 0,
                    "Hi-Lo Won": 0, "War Won": 0},
            "Cooldowns": {"Dice": 0, "Cups": 0, "Coin": 0, "Allin": 0, "Hi-Lo": 0, "War": 0,
                          "Blackjack": 0, "Payday": 0}
            }

# Deck used for blackjack, and a dictionary to correspond values of the cards.
main_deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace'] * 4


bj_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'Jack': 10,
             'Queen': 10, 'King': 10}

war_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'Jack': 11,
              'Queen': 12, 'King': 13, 'Ace': 14}


class CasinoError(Exception):
    pass


class WipeError(CasinoError):
    pass


class UserAlreadyRegistered(CasinoError):
    pass


class UserNotRegistered(CasinoError):
    pass


class InsufficientChips(CasinoError):
    pass


class NegativeChips(CasinoError):
    pass


class SameSenderAndReceiver(CasinoError):
    pass


class CasinoBank:
    """Holds all of the Casino hooks for integration"""

    def __init__(self, bot, file_path):
        self.memberships = dataIO.load_json(file_path)
        self.bot = bot
        self.patch = 1.581

    def create_account(self, user):
        server = user.server
        path = self.check_server_settings(server)

        if user.id not in path["Players"]:
            default_user = deepcopy(new_user)
            path["Players"][user.id] = default_user
            path["Players"][user.id]["Name"] = user.name
            self.save_system()
            membership = path["Players"][user.id]
            return membership
        else:
            raise UserAlreadyRegistered("{} already has a casino membership".format(user.name))

    def membership_exists(self, user):
        try:
            self.get_membership(user)
        except UserNotRegistered:
            return False
        return True

    def chip_balance(self, user):
        account = self.get_membership(user)
        return account["Chips"]

    def can_bet(self, user, amount):
        account = self.get_membership(user)
        if account["Chips"] >= amount:
            return True
        else:
            raise InsufficientChips("{} does not have enough chips.".format(user.name))

    def set_chips(self, user, amount):
        if amount < 0:
            raise NegativeChips()
        account = self.get_membership(user)
        account["Chips"] = amount
        self.save_system()

    def deposit_chips(self, user, amount):
        amount = int(round(amount))
        if amount < 0:
            raise NegativeChips()
        account = self.get_membership(user)
        account["Chips"] += amount
        self.save_system()

    def withdraw_chips(self, user, amount):
        if amount < 0:
            raise NegativeChips()

        account = self.get_membership(user)
        if account["Chips"] >= amount:
            account["Chips"] -= amount
            self.save_system()
        else:
            raise InsufficientChips("{} does not have enough chips.".format(user.name))

    def transfer_chips(self, sender, receiver, amount):
        if amount < 0:
            raise NegativeChips()

        if sender is receiver:
            raise SameSenderAndReceiver()

        if self.membership_exists(sender) and self.membership_exists(receiver):
            sender_acc = self.get_membership(sender)
            if sender_acc["Chips"] < amount:
                raise InsufficientChips()
            self.withdraw_credits(sender, amount)
            self.deposit_credits(receiver, amount)
        else:
            raise UserNotRegistered()

    def wipe_caisno_server(self, server):
        self.memberships["Servers"].pop(server.id)
        self.save_system

    def wipe_casino_members(self, server):
        self.memberships["Servers"][server.id]["Players"] = {}
        self.save_system()

    def remove_membership(self, user):
        server = user.server
        self.memberships["Servers"][server.id]["Players"].pop(user.id)
        self.save_system()

    def get_membership(self, user):
        server = user.server
        path = self.check_server_settings(server)

        try:
            return path["Players"][user.id]
        except KeyError:
            raise UserNotRegistered()

    def get_all_servers(self):
        return self.memberships["Servers"]

    def get_server_memberships(self, server):
        if server.id in self.memberships["Servers"]:
            members = self.memberships["Servers"][server.id]["Players"]
            return members
        else:
            return []

    def save_system(self):
        dataIO.save_json("data/JumperCogs/casino/casino.json", self.memberships)

    def check_server_settings(self, server):
        if server.id not in self.memberships["Servers"]:
            self.memberships["Servers"][server.id] = server_default
            self.save_system()
            print("Creating default casino settings for Server: {}".format(server.name))
            path = self.memberships["Servers"][server.id]
            return path
        else:  # NOTE Will be moved to a cmd in future patch. Used to update JSON from older version
            path = self.memberships["Servers"][server.id]

            try:
                if path["System Config"]["Version"] < self.patch:
                    path["System Config"]["Version"] = self.patch
                    self.casino_patcher(path)
            except KeyError:
                path["System Config"]["Version"] = self.patch
                self.casino_patcher(path)

            return path

    def casino_patcher(self, path):
        # Add hi-lo to older versions
        if "Hi-Lo" not in path["Games"]:
            hl = {"Hi-Lo": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 20,
                            "Max": 20}}
            path["Games"].update(hl)

        # Add war to older versions
        if "War" not in path["Games"]:
            war = {"War": {"Multiplier": 1.5, "Cooldown": 0, "Open": True, "Min": 50,
                           "Max": 100}}
            path["Games"].update(war)

        # Add membership changes from patch 1.5 to older versions
        trash = ["Membership Lvl 0", "Membership Lvl 1", "Membership Lvl 2",
                 "Membership Lvl 3"]
        new = {"Threshold Switch": False, "Threshold": 10000, "Default Payday": 100,
               "Payday Timer": 1200}

        if "Threshold" not in path["System Config"]:
            path["System Config"].update(new)

        if "Memberships" not in path:
            path["Memberships"] = {}

        # Game access levels added
        for x in path["Games"].values():
            if "Access Level" not in x:
                x["Access Level"] = 0

        if "Min" in path["Games"]["Allin"]:
            path["Games"]["Allin"].pop("Min")

        if "Max" in path["Games"]["Allin"]:
            path["Games"]["Allin"].pop("Max")

        for x in trash:
            if x in path["System Config"]:
                path["System Config"].pop(x)

        for x in path["Players"].keys():
            if "CD" in path["Players"][x]:
                path["Players"][x]["Cooldowns"] = path["Players"][x].pop("CD")
                raw = [(x.split(" ", 1)[0], y) for x, y in
                       path["Players"][x]["Cooldowns"].items()]
                raw.append(("Payday", 0))
                new_dict = dict(raw)
                path["Players"][x]["Cooldowns"] = new_dict

            if "Membership" not in path["Players"][x]:
                path["Players"][x]["Membership"] = None

            if "Pending" not in path["Players"][x]:
                path["Players"][x]["Pending"] = 0

        # Save changes and return updated dictionary.
        self.save_system()


class PluralDict(dict):
    """This class is used to plural strings

    You can plural strings based on the value input when using this class as a dictionary.
    """
    def __missing__(self, key):
        if '(' in key and key.endswith(')'):
            key, rest = key.split('(', 1)
            value = super().__getitem__(key)
            suffix = rest.rstrip(')').split(',')
            if len(suffix) == 1:
                suffix.insert(0, '')
            return suffix[0] if value <= 1 else suffix[1]
        raise KeyError(key)


class Casino:
    """Play Casino minigames and earn chips that integrate with Economy!

    Any user can join casino by using the casino join command. Casino uses hooks from economy to
    cash in/out chips. You are able to create your own casino name and chip name. Casino comes with
    7 mini games that you can set min/max bets, multipliers, and access levels. Check out all of the
    admin settings by using commands in the setcasino group.

    """

    def __init__(self, bot):
        self.bot = bot
        try:  # This allows you to port accounts from older versions of casino
            self.legacy_path = "data/casino/casino.json"
            self.legacy_system = dataIO.load_json(self.legacy_path)
            self.legacy_available = True
        except FileNotFoundError:
            self.legacy_available = False
        self.file_path = "data/JumperCogs/casino/casino.json"
        self.casino_bank = CasinoBank(bot, self.file_path)
        self.games = ["Blackjack", "Coin", "Allin", "Cups", "Dice", "Hi-Lo", "War"]
        self.version = "1.5.8.1"
        self.cycle_task = bot.loop.create_task(self.membership_updater())

    @commands.group(pass_context=True, no_pm=True)
    async def casino(self, ctx):
        """Casino Group Commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @casino.command(name="join", pass_context=True)
    async def _join_casino(self, ctx):
        """Grants you membership access to the casino"""
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        self.casino_bank.create_account(user)
        name = settings["System Config"]["Casino Name"]
        msg = ("Your membership has been approved! Welcome to {} Casino!\nAs a first time "
               "member we have credited your account with 100 free chips. "
               "\nHave fun!".format(name))
        await self.bot.say(msg)

    @casino.command(name="transfer", pass_context=True)
    async def _transfer_casino(self, ctx):
        """Transfers account info from old casino. Limit 1 transfer per user"""
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)

        if not self.casino_bank.membership_exists(user):
            msg = "I can't transfer data if you already have an account with the new casino."
        elif not self.legacy_available:
            msg = "No legacy file was found. Unable to perform membership transfers."
        elif user.id in self.legacy_system["Players"]:
            await self.bot.say("Account for {} found. Your casino data will be transfered to the "
                               "{} server. After your data is transfered your old data will be "
                               "deleted. I can only transfer data **one time**.\nDo you wish to "
                               "transfer?".format(user.name, user.server.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                msg = "No response, transfer cancelled."
            elif response.content.title() == "No":
                msg = "Transfer cancelled."
            elif response.content.title() == "Yes":
                old_data = self.legacy_system["Players"][user.id]
                player_data = self.player_update(old_data, new_game, path=None)
                transfer = {user.id: player_data}
                settings["Players"].update(transfer)
                self.legacy_system["Players"].pop(user.id)
                dataIO.save_json(self.legacy_path, self.legacy_system)
                self.casino_bank.save_system()
                msg = "Data transfer successful. You can now access your old casino data."
            else:
                msg = "Improper response. Please state yes or no. Cancelling transfer."
        else:
            msg = "Unable to locate your previous data."
        await self.bot.say(msg)

    @casino.command(name="leaderboard", pass_context=True)
    async def _leaderboard_casino(self, ctx, sort="top"):
        """Displays Casino Leaderboard"""
        user = ctx.message.author
        self.casino_bank.check_server_settings(user.server)
        members = self.casino_bank.get_server_memberships(user.server)

        if sort not in ["top", "bottom", "place"]:
            sort = "top"

        if members:
            players = [(x["Name"], x["Chips"]) for x in members.values()]
            pos = [x + 1 for x, y in enumerate(players)]
            if sort == "top":
                style = sorted(players, key=itemgetter(1), reverse=True)
                players, chips = zip(*style)
                data = list(zip(pos, players, chips))
            elif sort == "bottom":
                style = sorted(players, key=itemgetter(1))
                rev_pos = list(reversed(pos))
                players, chips = zip(*style)
                data = list(zip(rev_pos, players, chips))
            elif sort == "place":
                style = sorted([[x["Name"], x["Chips"]] if x["Name"] != user.name
                               else ["[" + x["Name"] + "]", x["Chips"]]
                               for x in members.values()], key=itemgetter(1), reverse=True)
                players, chips = zip(*style)
                data = list(zip(pos, players, chips))
            headers = ["Rank", "Names", "Chips"]
            msg = await self.table_split(user, headers, data, sort)
        else:
            msg = "There are no casino players to show on the leaderboard."
        await self.bot.say(msg)

    @casino.command(name="exchange", pass_context=True)
    async def _exchange_casino(self, ctx, currency: str, amount: int):
        """Exchange chips for towels and towels for chips"""

        # Declare all variables here
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        bank = self.bot.get_cog('Economy').bank
        currency = currency.title()
        chip_rate = settings["System Config"]["Chip Rate"]
        credit_rate = settings["System Config"]["Credit Rate"]
        chip_multiple = Fraction(chip_rate).limit_denominator().denominator
        credit_multiple = Fraction(credit_rate).limit_denominator().denominator
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]

        # Logic checks
        if not self.casino_bank.membership_exists(user):
            msg = ("You need to register to the {} Casino. To register type `{}casino "
                   "join`.".format(casino_name, ctx.prefix))
        elif currency not in ["Chips", "Credits"]:
            msg = "I can only exchange chips or towels, please specify one."

        # Logic for choosing chips
        elif currency == "Chips":
            if amount <= 0 and amount % credit_multiple != 0:
                msg = ("The amount must be higher than 0 and "
                       "a multiple of {}.".format(credit_multiple))
            elif self.casino_bank.can_bet(user, amount):
                self.casino_bank.withdraw_chips(user, amount)
                credits = int(amount * credit_rate)
                bank.deposit_credits(user, credits)
                msg = ("I have exchanged {} {} chips into {} towels.\nThank you for playing at "
                       "{} Casino.".format(amount, chip_name, credits, casino_name))
            else:
                msg = "You don't have that many chips to exchange."

        # Logic for choosing Credits
        elif currency == "Credits":
            if amount <= 0 and amount % chip_multiple != 0:
                msg = "The amount must be higher than 0 and a multiple of {}.".format(chip_multiple)
            elif bank.can_spend(user, amount):
                bank.withdraw_credits(user, amount)
                chip_amount = int(amount * chip_rate)
                self.casino_bank.deposit_chips(user, chip_amount)
                msg = ("I have exchanged {} towels for {} {} chips.\nEnjoy your time at "
                       "{} Casino!".format(amount, chip_amount, chip_name, casino_name))
            else:
                msg = "You don't have that many towels to exchange."

        await self.bot.say(msg)

    @casino.command(name="stats", pass_context=True)
    async def _stats_casino(self, ctx):
        """Shows your casino play stats"""

        # Variables
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        chip_name = settings["System Config"]["Chip Name"]
        casino_name = settings["System Config"]["Casino Name"]
        chip_balance = self.casino_bank.chip_balance(author)
        pending_chips = settings["Players"][author.id]["Pending"]

        # Check for a membership and build the table.
        if self.casino_bank.membership_exists(author):
            player = settings["Players"][author.id]
            wiki = "[Wiki](https://github.com/Redjumpman/Jumper-Cogs/wiki/Casino)"
            membership, benefits = self.get_benefits(settings, player)
            b_msg = ("Access Level: {Access}\nCooldown Reduction: {Cooldown Reduction}\n"
                     "Payday: {Payday}".format(**benefits))
            description = ("{}\nMembership: {}\n{} Chips: "
                           "{}".format(wiki, membership, chip_name, chip_balance))
            color = self.color_lookup(benefits["Color"])

            # Build columns for the table
            games = list(sorted(settings["Games"].keys()))
            played = [x[1] for x in sorted(player["Played"].items(), key=lambda tup: tup[0])]
            won = [x[1] for x in sorted(player["Won"].items(), key=lambda tup: tup[0])]
            cool_items = list(sorted(games + ["Payday"]))
            cooldowns = self.stats_cooldowns(settings, author, cool_items)

            # Build embed
            embed = discord.Embed(colour=color, description=description)
            embed.title = "{} Casino".format(casino_name)
            embed.set_author(name=str(author), icon_url=author.avatar_url)
            embed.add_field(name="Benefits", value=b_msg)
            embed.add_field(name="Pending Chips", value=pending_chips, inline=False)
            embed.add_field(name="Games", value="```Prolog\n{}```".format("\n".join(games)))
            embed.add_field(name="Played",
                            value="```Prolog\n{}```".format("\n".join(map(str, played))))
            embed.add_field(name="Won", value="```Prolog\n{}```".format("\n".join(map(str, won))))
            embed.add_field(name="Cooldown Items",
                            value="```CSS\n{}```".format("\n".join(cool_items)))
            embed.add_field(name="Cooldown Remaining",
                            value="```xl\n{}```".format("\n".join(cooldowns)))

            await self.bot.say(embed=embed)
        else:
            await self.bot.say("You need to register to the {} Casino. To register type `{}casino "
                               "join`.".format(casino_name, ctx.prefix))

    @casino.command(name="info", pass_context=True)
    async def _info_casino(self, ctx):
        """Shows information about the server casino"""

        # Variables
        server = ctx.message.server
        settings = self.casino_bank.check_server_settings(server)
        players = len(self.casino_bank.get_server_memberships(server))
        memberships = len(settings["Memberships"])
        chip_exchange_rate = settings["System Config"]["Chip Rate"]
        credit_exchange_rate = settings["System Config"]["Credit Rate"]
        games = settings["Games"].keys()

        if settings["System Config"]["Threshold Switch"]:
            threshold = settings["Threshold"]
        else:
            threshold = "None"

        # Create the columns through list comprehensions
        multiplier = [subdict["Multiplier"] for subdict in settings["Games"].values()]
        min_bet = [subdict["Min"] if "Min" in subdict else "None"
                   for subdict in settings["Games"].values()]
        max_bet = [subdict["Max"] if "Max" in subdict else "None"
                   for subdict in settings["Games"].values()]
        cooldown = [subdict["Cooldown"] for subdict in settings["Games"].values()]
        cooldown_formatted = [self.time_format(x) for x in cooldown]

        # Determine the ratio calculations for chips and credits
        chip_ratio = str(Fraction(chip_exchange_rate).limit_denominator()).replace("/", ":")
        credit_ratio = str(Fraction(credit_exchange_rate).limit_denominator()).replace("/", ":")

        # If a fraction reduces to 1, we make it 1:1
        if chip_ratio == "1":
            chip_ratio = "1:1"
        if credit_ratio == "1":
            credit_ratio = "1:1"

        # Build the table and send the message
        m = list(zip(games, multiplier, min_bet, max_bet, cooldown_formatted))
        m = sorted(m, key=itemgetter(0))
        t = tabulate(m, headers=["Game", "Multiplier", "Min Bet", "Max Bet", "Cooldown"])
        msg = ("```Python\n{}\n\nCredit Exchange Rate:    {}\nChip Exchange Rate:      {}\n"
               "Casino Members: {}\nServer Memberships: {}\nServer Threshold: "
               "{}```".format(t, credit_ratio, chip_ratio, players, memberships, threshold))
        await self.bot.say(msg)

    @casino.command(name="payday", pass_context=True)
    async def _payday_casino(self, ctx):
        """Gives you some chips"""

        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        chip_name = settings["System Config"]["Chip Name"]
        if self.casino_bank.membership_exists(user):
            cooldown = self.check_cooldowns(user, "Payday", settings)
            if not cooldown:
                if settings["Players"][user.id]["Membership"]:
                    membership = settings["Players"][user.id]["Membership"]
                    amount = settings["Memberships"][membership]["Payday"]
                    self.casino_bank.deposit_chips(user, amount)
                    msg = "You recieved {} {} chips".format(amount, chip_name)
                else:
                    payday = settings["System Config"]["Default Payday"]
                    self.casino_bank.deposit_chips(user, payday)
                    msg = "You recieved {} {} chips. Enjoy!".format(payday, chip_name)
            else:
                msg = cooldown
        else:
            msg = ("You need to register to the {} Casino. To register type `{}casino "
                   "join`.".format(casino_name, prefix))
        await self.bot.say(msg)

    @casino.command(name="balance", pass_context=True)
    async def _balance_casino(self, ctx):
        """Shows your number of chips"""
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        chip_name = settings["System Config"]["Chip Name"]
        balance = self.casino_bank.chip_balance(user)
        await self.bot.say("```Python\nYou have {} {} chips.```".format(balance, chip_name))

    @commands.command(pass_context=True, no_pm=True, aliases=["hl", "hi-lo"])
    async def hilo(self, ctx, choice: str, bet: int):
        """Pick High, Low, Seven. Lo is < 7 Hi is > 7. 6x payout on 7"""

        # Declare variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        chip_name = settings["System Config"]["Chip Name"]
        choice = choice.title()
        choices = ["Hi", "High", "Low", "Lo", "Seven", "7"]
        hilo_data = {"Played": {"Hi-Lo Played": 0}, "Won": {"Hi-Lo Won": 0},
                     "Cooldown": {"Hi-Lo": 0}}

        # Check if casino json file has the hi-lo game, and if not add it.
        if "Hi-Lo Played" not in settings["Players"][user.id]["Played"].keys():
            self.player_update(settings["Players"][user.id], hilo_data)

        # Run a logic check to determine if the user can play the game
        check = self.game_checks(settings, ctx.prefix, user, bet, "Hi-Lo", choice, choices)
        if check:
            msg = check
        else:  # Run the game when the checks return None
            self.casino_bank.withdraw_chips(user, bet)
            settings["Players"][user.id]["Played"]["Hi-Lo Played"] += 1
            await self.bot.say("The dice hit the table and slowly fall into place...")
            die_one = random.randint(1, 6)
            die_two = random.randint(1, 6)
            result = die_one + die_two
            outcome = self.hl_outcome(result)
            await asyncio.sleep(2)

            # Begin game logic to determine a win or loss
            msg = ("The dice landed on {} and {} \n".format(die_one, die_two))
            if choice in outcome:
                msg += ("Congratulations! The outcome was "
                        "{} ({})!".format(outcome[0], outcome[2]))
                settings["Players"][user.id]["Won"]["Hi-Lo Won"] += 1

                # Check for a 7 to give a 12x multiplier
                if outcome[2] == "Seven":
                    amount = bet * 6
                    msg += "\n**BONUS!** 6x multiplier for Seven!"
                else:
                    amount = int(round(bet * settings["Games"]["Hi-Lo"]["Multiplier"]))

                # Check if a threshold is set and withold chips if amount is exceeded
                if self.threshold_check(settings, amount):
                    settings["Players"][user.id]["Pending"] = amount
                    msg += ("```Your winnings exceeded the threshold set on this server. "
                            "The amount of {} {} chips will be withheld until reviewed and "
                            "released by an admin. Do not attempt to play additional games "
                            "exceeding the threshold until this has been cleared.```"
                            "".format(amount, chip_name, user.id))
                    logger.info("{}({}) won {} chips exceeding the threshold. Game "
                                "details:\nPlayer Choice: {}\nPlayer Bet: {}\nGame "
                                "Outcome: {}\n[END OF REPORT]"
                                "".format(user.name, user.id, amount, choice.ljust(10),
                                          str(bet).ljust(10), str(outcome[0]).ljust(10)))
                else:
                    self.casino_bank.deposit_chips(user, amount)
                    msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
            else:
                msg += "Sorry. The outcome was {} ({}).".format(outcome[0], outcome[2])
            # Save the results of the game
            self.casino_bank.save_system()
        # Send a message telling the user the outcome of this command
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def cups(self, ctx, cup: int, bet: int):
        """Pick the cup that is hiding the gold coin. Choose 1, 2, 3, or 4"""

        # Declare variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        choice = cup
        choices = [1, 2, 3, 4]
        chip_name = settings["System Config"]["Chip Name"]

        # Run a logic check to determine if the user can play the game
        check = self.game_checks(settings, ctx.prefix, user, bet, "Cups", choice, choices)
        if check:
            msg = check
        else:  # Run the game when the checks return None
            self.casino_bank.withdraw_chips(user, bet)
            settings["Players"][user.id]["Played"]["Cups Played"] += 1
            outcome = random.randint(1, 4)
            await self.bot.say("The cups start shuffling along the table...")
            await asyncio.sleep(3)

            # Begin game logic to determine a win or loss
            if cup == outcome:
                amount = int(round(bet * settings["Games"]["Cups"]["Multiplier"]))
                settings["Players"][user.id]["Won"]["Cups Won"] += 1
                msg = "Congratulations! The coin was under cup {}!".format(outcome)

                # Check if a threshold is set and withold chips if amount is exceeded
                if self.threshold_check(settings, amount):
                    settings["Players"][user.id]["Pending"] = amount
                    msg += ("Your winnings exceeded the threshold set on this server. "
                            "The amount of {} {} chips will be withheld until reviewed and "
                            "released by an admin. Do not attempt to play additional games "
                            "exceeding the threshold until this has been cleared."
                            "".format(amount, chip_name, user.id))
                    logger.info("{}({}) won {} chips exceeding the threshold. Game "
                                "details:\nPlayer Cup: {}\nPlayer Bet: {}\nGame "
                                "Outcome: {}\n[END OF REPORT]"
                                "".format(user.name, user.id, amount, str(cup).ljust(10),
                                          str(bet).ljust(10), str(outcome).ljust(10)))
                else:
                    self.casino_bank.deposit_chips(user, amount)
                    msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
            else:
                msg = "Sorry! The coin was under cup {}.".format(outcome)
            # Save the results of the game
            self.casino_bank.save_system()
        # Send a message telling the user the outcome of this command
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def coin(self, ctx, choice: str, bet: int):
        """Bet on heads or tails"""

        # Declare variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        choice = choice.title()
        choices = ["Heads", "Tails"]
        chip_name = settings["System Config"]["Chip Name"]

        # Run a logic check to determine if the user can play the game
        check = self.game_checks(settings, ctx.prefix, user, bet, "Coin", choice, choices)
        if check:
            msg = check
        else:  # Run the game when the checks return None
            self.casino_bank.withdraw_chips(user, bet)
            settings["Players"][user.id]["Played"]["Coin Played"] += 1
            outcome = random.choice(["Heads", "Tails"])
            await self.bot.say("The coin flips into the air...")
            await asyncio.sleep(2)

            # Begin game logic to determine a win or loss
            if choice == outcome:
                amount = int(round(bet * settings["Games"]["Coin"]["Multiplier"]))
                msg = "Congratulations! The coin landed on {}!".format(outcome)
                settings["Players"][user.id]["Won"]["Coin Won"] += 1

                # Check if a threshold is set and withold chips if amount is exceeded
                if self.threshold_check(settings, amount):
                    settings["Players"][user.id]["Pending"] = amount
                    msg += ("\nYour winnings exceeded the threshold set on this server. "
                            "The amount of {} {} chips will be withheld until reviewed and "
                            "released by an admin. Do not attempt to play additional games "
                            "exceeding the threshold until this has been cleared."
                            "".format(amount, chip_name, user.id))
                    logger.info("{}({}) won {} chips exceeding the threshold. Game "
                                "details:\nPlayer Choice: {}\nPlayer Bet: {}\nGame "
                                "Outcome: {}\n[END OF REPORT]"
                                "".format(user.name, user.id, amount, choice.ljust(10),
                                          str(bet).ljust(10), outcome[0].ljust(10)))
                else:
                    self.casino_bank.deposit_chips(user, amount)
                    msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
            else:
                msg = "Sorry! The coin landed on {}.".format(outcome)
            # Save the results of the game
            self.casino_bank.save_system()
        # Send a message telling the user the outcome of this command
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def dice(self, ctx, bet: int):
        """Roll 2, 7, 11 or 12 to win."""

        # Declare variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        chip_name = settings["System Config"]["Chip Name"]

        # Run a logic check to determine if the user can play the game
        check = self.game_checks(settings, ctx.prefix, user, bet, "Dice", 1, [1])
        if check:
            msg = check
        else:  # Run the game when the checks return None
            self.casino_bank.withdraw_chips(user, bet)
            settings["Players"][user.id]["Played"]["Dice Played"] += 1
            await self.bot.say("The dice strike the back of the table and begin to tumble into "
                               "place...")
            die_one = random.randint(1, 6)
            die_two = random.randint(1, 6)
            outcome = die_one + die_two
            await asyncio.sleep(2)

            # Begin game logic to determine a win or loss
            msg = "The dice landed on {} and {} \n".format(die_one, die_two)
            if outcome in [2, 7, 11, 12]:
                amount = int(round(bet * settings["Games"]["Dice"]["Multiplier"]))
                settings["Players"][user.id]["Won"]["Dice Won"] += 1

                msg += "Congratulations! The dice landed on {}.".format(outcome)

                # Check if a threshold is set and withold chips if amount is exceeded
                if self.threshold_check(settings, amount):
                    settings["Players"][user.id]["Pending"] = amount
                    msg += ("\nYour winnings exceeded the threshold set on this server. "
                            "The amount of {} {} chips will be withheld until reviewed and "
                            "released by an admin. Do not attempt to play additional games "
                            "exceeding the threshold until this has been cleared."
                            "".format(amount, chip_name, user.id))
                    logger.info("{}({}) won {} chips exceeding the threshold. Game "
                                "details:\nPlayer Bet: {}\nGame "
                                "Outcome: {}\n[END OF FILE]".format(user.name, user.id, amount,
                                                                    str(bet).ljust(10),
                                                                    str(outcome[0]).ljust(10)))
                else:
                    self.casino_bank.deposit_chips(user, amount)
                    msg += "```Python\nYou just won {} {} chips.```".format(amount, chip_name)
            else:
                msg += "Sorry! The result was {}.".format(outcome)
            # Save the results of the game
            self.casino_bank.save_system()
        # Send a message telling the user the outcome of this command
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def war(self, ctx, bet: int):
        """Modified War Card Game."""

        # Declare Variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)

        war_data = {"Played": {"War Played": 0}, "Won": {"War Won": 0},
                    "Cooldown": {"War": 0}}

        # Check if casino json file has the hi-lo game, and if not add it.
        if "War Played" not in settings["Players"][user.id]["Played"].keys():
            self.player_update(settings["Players"][user.id], war_data)

        # Run a logic check to determine if the user can play the game
        check = self.game_checks(settings, ctx.prefix, user, bet, "War", 1, [1])
        if check:
            msg = check
        else:  # Run the game when the checks return None
            self.casino_bank.withdraw_chips(user, bet)
            settings["Players"][user.id]["Played"]["War Played"] += 1
            deck = main_deck[:]  # Make a copy of the deck so we can remove cards that are drawn
            outcome, player_card, dealer_card, amount = await self.war_game(user, settings, deck,
                                                                            bet)
            msg = self.war_results(settings, user, outcome, player_card, dealer_card, amount)
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True, aliases=["bj", "21"])
    async def blackjack(self, ctx, bet: int):
        """Modified Blackjack."""

        # Declare variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)

        # Run a logic check to determine if the user can play the game
        check = self.game_checks(settings, ctx.prefix, user, bet, "Blackjack", 1, [1])
        if check:
            msg = check
        else:  # Run the game when the checks return None
            self.casino_bank.withdraw_chips(user, bet)
            settings["Players"][user.id]["Played"]["BJ Played"] += 1
            deck = main_deck[:]  # Make a copy of the deck so we can remove cards that are drawn
            dhand = self.dealer(deck)
            ph, dh, amt = await self.blackjack_game(dhand, user, bet, ctx, settings, deck)
            msg = self.blackjack_results(settings, user, amt, ph, dh)
        # Send a message telling the user the outcome of this command
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def allin(self, ctx, multiplier: int):
        """It's all or nothing. Bets everything you have."""

        # Declare variables for the game.
        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        chip_name = settings["System Config"]["Chip Name"]
        if self.casino_bank.membership_exists(user):
            bet = int(settings["Players"][user.id]["Chips"])
        else:
            raise UserNotRegistered("You need to register. Type {}casino join.".format(ctx.prefix))
        # Run a logic check to determine if the user can play the game.
        check = self.game_checks(settings, ctx.prefix, user, bet, "Allin", 1, [1])
        if check:
            msg = check
        else:  # Run the game when the checks return None.
            # Setup the game to determine an outcome.
            settings["Players"][user.id]["Played"]["Allin Played"] += 1
            amount = int(round(multiplier * settings["Players"][user.id]["Chips"]))
            balance = self.casino_bank.chip_balance(user)
            outcome = random.randint(0, multiplier + 1)
            self.casino_bank.withdraw_chips(user, balance)
            await self.bot.say("You put all your chips into the machine and pull the lever...")
            await asyncio.sleep(3)

            # Begin game logic to determine a win or loss.
            if outcome == 0:
                self.casino_bank.deposit_chips(user, amount)
                msg = "```Python\nJackpot!! You just won {} {} chips!!```".format(amount, chip_name)
                settings["Players"][user.id]["Won"]["Allin Won"] += 1
            else:
                msg = ("Sorry! Your all or nothing gamble failed and you lost "
                       "{} {} chips.".format(bet, chip_name))
            # Save the results of the game
            self.casino_bank.save_system()
        # Send a message telling the user the outcome of this command
        await self.bot.say(msg)

    @casino.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_casino(self, ctx):
        """Shows current Casino version"""
        await self.bot.say("You are currently running Casino version {}.".format(self.version))

    @casino.command(name="removemembership", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _removemembership_casino(self, ctx, *, membership):
        """Remove a casino membership"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if membership in settings["Memberships"]:
            settings["Memberships"].pop(membership)
            msg = "{} removed from the list of membership.".format(membership)
        else:
            msg = "Could not find a membership with that name."

        await self.bot.say(msg)

    @casino.command(name="createmembership", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _createmembership_casino(self, ctx):
        """Add a casino membership to reward continued play"""

        # Declare variables
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        cancel = ctx.prefix + "cancel"
        requirement_list = ["Days On Server", "Credits", "Chips", "Role"]
        colors = ["blue", "red", "green", "orange", "purple", "yellow", "turquoise", "teal",
                  "magenta"]
        server_roles = [r.name for r in ctx.message.server.roles if r.name != "Bot"]

        # Various checks for the different questions
        check1 = lambda m: m.content.isdigit() and int(m.content) > 0 or m.content == cancel
        check2 = lambda m: m.content.isdigit() or m.content == cancel
        check3 = lambda m: m.content.title() in requirement_list or m.content == cancel
        check4 = lambda m: m.content.isdigit() or m.content in server_roles or m.content == cancel
        check5 = lambda m: m.content.lower() in colors or m.content == cancel

        start = ("Welcome to the membership creation process. This will create a membership to "
                 "provide benefits to your members such as reduced cooldowns and access levels.\n"
                 "You may cancel this process at anytime by typing {}cancel. Let's begin with the "
                 "first question.\n\nWhat is the name of this membership? Examples: Silver, Gold, "
                 "Diamond".format(ctx.prefix))

        # Begin creation process
        await self.bot.say(start)
        name = await self.bot.wait_for_message(timeout=35, author=author)

        if name is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if name.content == cancel:
            await self.bot.say("Membership creation cancelled.")
            return

        if name.content.title() in list(settings["Memberships"].keys()):
            await self.bot.say("A membership with that name already exists. Cancelling creation.")
            return

        await self.bot.say("What is the color for this membership? This color appears in the "
                           "{}casino stats command.\nPlease pick from these colors: "
                           "{}".format(ctx.prefix, ", ".join(colors)))
        color = await self.bot.wait_for_message(timeout=35, author=author, check=check5)

        if color is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if color.content == cancel:
            await self.bot.say("Membership creation cancelled.")
            return

        await self.bot.say("What is the payday amount for this membership?")
        payday = await self.bot.wait_for_message(timeout=35, author=author, check=check1)

        if payday is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if payday.content == cancel:
            await self.bot.say("Membership creation cancelled.")
            return

        await self.bot.say("What is the cooldown reduction for this membership in seconds? 0 for "
                           "none")
        reduction = await self.bot.wait_for_message(timeout=35, author=author, check=check2)

        if reduction is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if reduction.content == cancel:
            await self.bot.say("membership creation cancelled.")
            return

        await self.bot.say("What is the access level for this membership? 0 is the default access "
                           "level for new members. Access levels can be used to restrict access to "
                           "games. See `{}setcasino access` for more info.".format(ctx.prefix))

        access = await self.bot.wait_for_message(timeout=35, author=author, check=check1)

        if access is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if access.content == cancel:
            await self.bot.say("Membership creation cancelled.")
            return

        if int(access.content) in [x["Access"] for x in list(settings["Memberships"].keys())]:
            await self.bot.say("You cannot have memberships with the same access level. Cancelling "
                               "creation.")
            return

        await self.bot.say("What is the requirement for this membership? Available options are:\n"
                           "Days on server, Towels, Chips, or Role\nWhich would you "
                           "like set? You can always remove and add additional requirements later"
                           "using `{0}setcasino addrequirements` and "
                           "`{0}setcasino removerequirements`.".format(ctx.prefix))
        req_type = await self.bot.wait_for_message(timeout=35, author=author, check=check3)

        if req_type is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if req_type.content == cancel:
            await self.bot.say("Membership creation cancelled.")
            return

        await self.bot.say("What is the number of days, chips, towels or role name you would like "
                           "set?")
        req_val = await self.bot.wait_for_message(timeout=35, author=author, check=check4)

        if req_val is None:
            await self.bot.say("You took too long. Cancelling membership creation.")
            return

        if req_val.content == cancel:
            await self.bot.say("Membership creation cancelled.")
            return
        else:

            if req_val.content.isdigit():
                req_val = int(req_val.content)
            else:
                req_val = req_val.content

            params = [name.content, color.content, payday.content, reduction.content,
                      access.content, req_val]
            headers = ["Name:", "Color:", "Payday:", "Cooldown Reduction:", "Access Level:",
                       "Requirement:"]

            msg = "Membership successfully created. Please review the details below.\n"
            msg += "```" + "\n".join("{} {}".format(h, p) for h, p in zip(headers, params)) + "```"
            memberships = {"Payday": int(payday.content), "Access": int(access.content),
                           "Cooldown Reduction": int(reduction.content), "Color": color.content,
                           "Requirements": {req_type.content: req_val}}
            settings["Memberships"][name.content.title()] = memberships
            self.casino_bank.save_system()
            await self.bot.say(msg)

    @casino.command(name="reset", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reset_casino(self, ctx):
        """Resets casino to default settings. Keeps user data"""

        user = ctx.message.author
        settings = self.casino_bank.check_server_settings(user.server)
        await self.bot.say("This will reset casino to it's default settings and keep player data.\n"
                           "Do you wish to reset casino settings?")
        response = await self.bot.wait_for_message(timeout=15, author=user)

        if response is None:
            msg = "No response, reset cancelled."
        elif response.content.title() == "No":
            msg = "Cancelling reset."
        elif response.content.title() == "Yes":
            settings["System Config"] = server_default["System Config"]
            settings["Games"] = server_default["Games"]
            self.casino_bank.save_system()
            msg = "Casino settings reset to default."
        else:
            msg = "Improper response. Cancelling reset."
        await self.bot.say(msg)

    @casino.command(name="toggle", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggle_casino(self, ctx):
        """Opens and closes the casino"""

        server = ctx.message.server
        settings = self.casino_bank.check_server_settings(server)
        casino_name = settings["System Config"]["Casino Name"]

        if settings["System Config"]["Casino Open"]:
            settings["System Config"]["Casino Open"] = False
            msg = "The {} Casino is now closed.".format(casino_name)
        else:
            settings["System Config"]["Casino Open"] = True
            msg = "The {} Casino is now open!".format(casino_name)
        self.casino_bank.save_system()
        await self.bot.say(msg)

    @casino.command(name="approve", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _approve_casino(self, ctx, user: discord.Member):
        """Approve a user's pending chips."""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        chip_name = settings["System Config"]["Chip Name"]
        if self.casino_bank.membership_exists(user):
            amount = settings["Players"][user.id]["Pending"]
            if amount > 0:
                await self.bot.say("{} has a pending amount of {}. Do you wish to approve this "
                                   "amount?".format(user.name, amount))
                response = await self.bot.wait_for_message(timeout=15, author=author)

                if response is None:
                    await self.bot.say("You took too long. Cancelling pending chip approval.")
                    return

                if response.content.title() in ["No", "Cancel", "Stop"]:
                    await self.bot.say("Cancelling pending chip approval.")
                    return

                if response.content.title() in ["Yes", "Approve"]:
                    await self.bot.say("{} approved the pending chips. Sending {} {} chips to "
                                       " {}.".format(author.name, amount, chip_name, user.name))
                    self.casino_bank.deposit_chips(user, amount)
                else:
                    await self.bot.say("Incorrect response. Cancelling pending chip approval.")
                    return
            else:
                await self.bot.say("{} does not have any chips pending.".format(user.name))

    @casino.command(name="removeuser", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _removeuser_casino(self, ctx, user: discord.Member):
        """Remove a user from casino"""
        author = ctx.message.author
        self.casino_bank.check_server_settings(author.server)

        if not self.casino_bank.membership_exists(user):
            msg = "This user is not a member of the casino."
        else:
            await self.bot.say("Are you sure you want to remove player data for {}? Type {} to "
                               "confirm.".format(user.name, user.name))
            response = await self.bot.wait_for_message(timeout=15, author=author)
            if response is None:
                msg = "No response. Player removal cancelled."
            elif response.content.title() == user.name:
                self.casino_bank.remove_membership(user)
                msg = "{}\'s casino data has been removed by {}.".format(user.name, author.name)
            else:
                msg = "Incorrect name. Cancelling player removal."
        await self.bot.say(msg)

    @casino.command(name="wipe", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _wipe_casino(self, ctx, *, servername: str):
        """Wipe casino server data. Case Sensitive"""
        user = ctx.message.author
        servers = self.casino_bank.get_all_servers()

        try:
            server = [self.bot.get_server(x) for x in servers.keys()
                      if self.bot.get_server(x).name == servername][0]
        except IndexError:
            raise WipeError("This server name provided could not be located. Check your spelling "
                            "and remember that names are case sensitive")

        await self.bot.say("This will wipe casino server data.**WARNING** ALL PLAYER DATA WILL "
                           "BE DESTROYED.\nDo you wish to wipe {}?".format(server.name))
        response = await self.bot.wait_for_message(timeout=15, author=user)

        if response is None:
            msg = "No response, casino wipe cancelled."
        elif response.content.title() == "No":
            msg = "Cancelling casino wipe."
        elif response.content.title() == "Yes":
            await self.bot.say("To confirm type the server name: {}".format(server.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                msg = "No response, casino wipe cancelled."
            elif response.content == server.name:
                self.casino_bank.wipe_caisno_server(server)
                msg = "Casino wiped."
            else:
                msg = "Incorrect server name. Cancelling casino wipe."
        else:
            msg = "Improper response. Cancelling casino wipe."

        await self.bot.say(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def setcasino(self, ctx):
        """Configures Casino Options"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setcasino.command(name="threshold", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _threshold_setcasino(self, ctx, threshold: int):
        """Players that exceed this amount require an admin to approve the payout"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if threshold > 0:
            settings["System Config"]["Threshold"] = threshold
            msg = "{} set payout threshold to {}.".format(author.name, threshold)
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
            self.casino_bank.save_system()
        else:
            msg = "Threshold amount needs to be higher than 0."

        await self.bot.say(msg)

    @setcasino.command(name="thresholdtoggle", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _threshholdtoggle_setcasino(self, ctx):
        """Turns on a chip win limit"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if settings["System Config"]["Threshold Switch"]:
            msg = "{} turned the threshold OFF.".format(author.name)
            settings["System Config"]["Threshold Switch"] = False
        else:
            msg = "{} turned the threshold ON.".format(author.name)
            settings["System Config"]["Threshold Switch"] = True

        logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        self.casino_bank.save_system()
        await self.bot.say(msg)

    @setcasino.command(name="payday", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _payday_setcasino(self, ctx, amount: int):
        """Set the default payday amount with no membership

        This amount is what users who have no membership will recieve. If the
        user has a membership it will be based on what payday amount that was set
        for it.
        """

        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        chip_name = settings["System Config"]["Chip Name"]

        if amount >= 0:
            settings["System Config"]["Default Payday"] = amount
            self.casino_bank.save_system()
            msg = "{} set the default payday to {} {} chips.".format(author.name, amount, chip_name)
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        else:
            msg = "You cannot set a negative number to payday."

        await self.bot.say(msg)

    @setcasino.command(name="paydaytimer", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _paydaytimer_setcasino(self, ctx, seconds: int):
        """Set the cooldown on payday

        This timer is not affected by cooldown reduction from membership.
        """

        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if seconds >= 0:
            settings["System Config"]["Payday Timer"] = seconds
            self.casino_bank.save_system()
            time_set = self.time_format(seconds)
            msg = "{} set the default payday to {}.".format(author.name, time_set)
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        else:
            msg = ("You cannot set a negative number to payday timer. That would be like going back"
                   " in time. Which would be totally cool, but I don't understand the physics of "
                   "how it might apply in this case. One would assume you would go back in time to "
                   "the point in which you could recieve a payday, but it is actually quite the "
                   "opposite. You would go back to the point where you were about to claim a "
                   "payday and thus claim it again, but unfortunately your total would not recieve "
                   "a net gain, because you are robbing from yourself. Next time think before you "
                   "do something so stupid.")

        await self.bot.say(msg)

    @setcasino.command(name="multiplier", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _multiplier_setcasino(self, ctx, game: str, multiplier: float):
        """Sets the payout multiplier for casino games"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if game.title() not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif multiplier > 0:
            multiplier = float(abs(multiplier))
            settings["Games"][game.title()]["Multiplier"] = multiplier
            self.casino_bank.save_system()
            msg = "Now setting the payout multiplier for {} to {}".format(game, multiplier)
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        else:
            msg = "Multiplier needs to be higher than 0."

        await self.bot.say(msg)

    @setcasino.command(name="access", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _access_setcasino(self, ctx, game: str, access: int):
        """Set the access level for a game. Default is 0. Used with membership."""

        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        game = game.title()

        if game not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        elif access > 0:
            settings["Games"][game.title()]["Access Level"] = access
            self.casino_bank.save_system()
            msg = "{} changed the access level for {} to {}".format(author.name, game, access)
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        else:
            msg = "Access level must be higher than 0."

        await self.bot.say(msg)

    @setcasino.command(name="reqadd", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reqadd_setcasino(self, ctx, *, membership):
        """Add a requirement to a membership"""

        # Declare variables
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        cancel_message = "You took too long to respond. Cancelling requirement addition."
        requirement_options = ["Days On Server", "Credits", "Chips", "Role"]
        server_roles = [r.name for r in ctx.message.server.roles if r.name != "Bot"]

        # Message checks
        check1 = lambda m: m.content.title() in requirement_options
        check2 = lambda m: m.content.isdigit() and int(m.content) > 0
        check3 = lambda m: m.content in server_roles

        # Begin logic
        if membership not in settings["Memberships"]:
            await self.bot.say("This membership does not exist.")
        else:

            await self.bot.say("Which of these requirements would you like to add to the {} "
                               " membership?\n{}.\nNOTE: You cannot have multiple requirements of "
                               "the same type.".format(membership, ', '.join(requirement_options)))
            rsp = await self.bot.wait_for_message(timeout=15, author=author, check=check1)

            if rsp is None:
                await self.bot.say(cancel_message)
                return

            else:
                # Determine amount for DoS, Credits, or Chips
                if rsp.content.title() != "Role":
                    name = rsp.content.split(' ', 1)[0]
                    await self.bot.say("How many {} are required?".format(name))
                    reply = await self.bot.wait_for_message(timeout=15, author=author, check=check2)

                    if reply is None:
                        await self.bot.say(cancel_message)
                        return
                    else:
                        await self.bot.say("Adding the requirement of {} {} to the membership "
                                           "{}.".format(reply.content, rsp.content, membership))
                        reply = int(reply.content)

                # Determine the role for the requirement
                else:
                    await self.bot.say("Which role would you like set? This role must already be "
                                       "set on server.")
                    reply = await self.bot.wait_for_message(timeout=15, author=author, check=check3)

                    if reply is None:
                        await self.bot.say(cancel_message)
                        return
                    else:
                        await self.bot.say("Adding the requirement role of {} to the membership "
                                           "{}.".format(reply.content, membership))
                        reply = reply.content

                # Add and save the requirement
                key = rsp.content
                reply
                settings["Memberships"][membership]["Requirements"][key] = reply
                self.casino_bank.save_system()

    @setcasino.command(name="reqremove", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reqremove_setcasino(self, ctx, *, membership):
        """Remove a requirement to a membership"""

        # Declare variables
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if membership not in settings["Memberships"]:
            await self.bot.say("This membership does not exist.")
        else:  # Membership was found.
            current_requirements = settings["Memberships"][membership].keys()
            check = lambda m: m.content.title() in current_requirements

            await self.bot.say("The current requirements for this membership are:\n{}\nWhich would "
                               "you like to remove?".format(", ".join(current_requirements)))
            resp = await self.bot.wait_for_message(timeout=15, author=author, check=check)

            if resp is None:
                await self.bot.say("You took too long. Cancelling requirement removal.")
                return
            else:
                settings["Memberships"][membership].pop(resp.title())
                self.casino_bank.save_system()
                await self.bot.say("{} requirement removed from {}.".format(resp.title, membership))

    @setcasino.command(name="balance", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _balance_setcasino(self, ctx, user: discord.Member, chips: int):
        """Sets a Casino member's chip balance"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        chip_name = settings["System Config"]["Chip Name"]
        self.casino_bank.set_chips(user, chips)
        logger.info("SETTINGS CHANGED {}({}) set {}({}) chip balance to "
                    "{}".format(author.name, author.id, user.name, user.id, chips))
        await self.bot.say("```Python\nSetting the chip balance of {} to "
                           "{} {} chips.```".format(user.name, chips, chip_name))

    @setcasino.command(name="exchange", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _exchange_setcasino(self, ctx, rate: float, currency: str):
        """Sets the exchange rate for chips or towels"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if rate <= 0:
            msg = "Rate must be higher than 0. Default is 1."
        elif currency.title() == "Chips":
            settings["System Config"]["Chip Rate"] = rate
            logger.info("{}({}) changed the chip rate to {}".format(author.name, author.id, rate))
            self.casino_bank.save_system()
            msg = "Setting the exchange rate for towels to chips to {}".format(rate)
        elif currency.title() == "Credits":
            settings["System Config"]["Credit Rate"] = rate
            logger.info("SETTINGS CHANGED {}({}) changed the credit rate to "
                        "{}".format(author.name, author.id, rate))
            self.casino_bank.save_system()
            msg = "Setting the exchange rate for chips to towels to {}".format(rate)
        else:
            msg = "Please specify chips or towels"

        await self.bot.say(msg)

    @setcasino.command(name="name", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_setcasino(self, ctx, *, name: str):
        """Sets the name of the Casino."""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        settings["System Config"]["Casino Name"] = name
        self.casino_bank.save_system()
        msg = "Changed the casino name to {}.".format(name)
        logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        await self.bot.say(msg)

    @setcasino.command(name="chipname", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _chipname_setcasino(self, ctx, *, name: str):
        """Sets the name of your Casino chips."""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        settings["System Config"]["Chip Name"] = name
        self.casino_bank.save_system()
        msg = ("Changed the name of your chips to {0}.\nTest Display:\n"
               "```Python\nCongratulations, you just won 50 {0} chips.```".format(name))
        logger.info("SETTINGS CHANGED {}({}) chip name set to "
                    "{}".format(author.name, author.id, name))

        await self.bot.say(msg)

    @setcasino.command(name="cooldown", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cooldown_setcasino(self, ctx, game, seconds: int):
        """Set the cooldown period for casino games"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)

        if game.title() not in self.games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(self.games))
        else:
            settings["Games"][game.title()]["Cooldown"] = seconds
            time_set = self.time_format(seconds)
            self.casino_bank.save_system()
            msg = "Setting the cooldown period for {} to {}".format(game, time_set)
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))

        await self.bot.say(msg)

    @setcasino.command(name="min", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _min_setcasino(self, ctx, game, minbet: int):
        """Set the minimum bet to play a game"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        min_games = [x for x in self.games if x != "Allin"]

        if game.title() not in min_games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(min_games))
        elif minbet < 0:
            msg = "You need to set a minimum bet higher than 0."
        elif minbet < settings["Games"][game.title()]["Max"]:
            settings["Games"][game.title()]["Min"] = minbet
            chips = settings["System Config"]["Chip Name"]
            self.casino_bank.save_system()
            msg = ("Setting the minimum bet for {} to {} {} "
                   "chips.".format(game.title(), minbet, chips))
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        else:
            maxbet = settings["Games"][game.title()]["Max"]
            msg = ("The minimum bet can't bet set higher than the maximum bet of "
                   "{} for {}.".format(maxbet, game.title()))

        await self.bot.say(msg)

    @setcasino.command(name="max", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _max_setcasino(self, ctx, game, maxbet: int):
        """Set the maximum bet to play a game"""
        author = ctx.message.author
        settings = self.casino_bank.check_server_settings(author.server)
        max_games = [x for x in self.games if x != "Allin"]

        if game.title() not in max_games:
            msg = "This game does not exist. Please pick from: {}".format(", ".join(max_games))
        elif maxbet <= 0:
            msg = "You need to set a maximum bet higher than 0."
        elif maxbet > settings["Games"][game.title()]["Min"]:
            settings["Games"][game.title()]["Max"] = maxbet
            chips = settings["System Config"]["Chip Name"]
            self.casino_bank.save_system()
            msg = ("Setting the maximum bet for {} to {} {} "
                   "chips.".format(game.title(), maxbet, chips))
            logger.info("SETTINGS CHANGED {}({}) {}".format(author.name, author.id, msg))
        else:
            minbet = settings["Games"][game.title()]["Min"]
            msg = "The max bet needs be higher than the minimum bet of {}.".format(minbet)

        await self.bot.say(msg)

    async def table_split(self, user, headers, data, sort):
        groups = [data[i:i + 20] for i in range(0, len(data), 20)]
        pages = len(groups)

        if sort == "place":
            name = "[{}]".format(user.name)
            page = next((idx for idx, sub in enumerate(groups) for tup in sub if name in tup), None)
            if not page:
                page = 0
            table = tabulate(groups[page], headers=headers, numalign="left", tablefmt="simple")
            msg = ("```ini\n{}``````Python\nYou are viewing page {} of {}. "
                   "{} casino members.```".format(table, page + 1, pages, len(data)))
            return msg
        elif pages == 1:
            page = 0
            table = tabulate(groups[page], headers=headers, numalign="left", tablefmt="simple")
            msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                   "{} casino members```".format(table, pages, len(data)))
            return msg

        await self.bot.say("There are {} pages of highscores. "
                           "Which page would you like to display?".format(pages))
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            page = 0
        else:
            try:
                page = int(response.content) - 1
                table = tabulate(groups[page], headers=headers, numalign="left", tablefmt="simple")
                msg = ("```ini\n{}``````Python\nYou are viewing page {} of {}. "
                       "{} casino members.```".format(table, page + 1, pages, len(data)))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a number. Defaulting to page 1")
                page = 0
                table = tabulate(groups[page], headers=headers, numalign="left", tablefmt="simple")
                msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                       "{} casino members```".format(table, pages, len(data)))
                return msg

    async def membership_updater(self):
        """Updates user membership based on requirements every 5 minutes"""
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(30)
            while True:
                servers = self.casino_bank.get_all_servers()
                for server in servers.keys():
                    server = [self.bot.get_server(server)][0]
                    settings = self.casino_bank.check_server_settings(server)
                    user_path = self.casino_bank.get_server_memberships(server)
                    users = [server.get_member(user) for user in list(user_path.keys())]
                    if users:
                        for user in users:
                            membership = self.gather_requirements(settings, user)
                            settings["Players"][user.id]["Membership"] = membership
                        self.casino_bank.save_system()
                    else:
                        pass
                await asyncio.sleep(300)  # Wait 5 minutes
        except asyncio.CancelledError:
            pass

    async def war_game(self, user, settings, deck, amount):
        player_card, dealer_card, pc, dc = self.war_draw(deck)
        multiplier = settings["Games"]["War"]["Multiplier"]

        await self.bot.say("The dealer shuffles the deck and deals 1 card face down to the player "
                           "and dealer...")
        await asyncio.sleep(2)
        await self.bot.say("**FLIP!**")
        await asyncio.sleep(1)

        if pc > dc:
            outcome = "Win"
            amount = int(amount * multiplier)
        elif dc > pc:
            outcome = "Loss"
        else:
            check = lambda m: m.content.title() in ["War", "Surrender", "Ffs"]
            await self.bot.say("The player and dealer are both showing a **{}**!\nTHIS MEANS WAR! "
                               "You may choose to surrender and forfiet half your bet, or you can "
                               "go to war.\nYour bet will be doubled, but you will only win on "
                               "half the bet, the rest will be pushed.".format(player_card))
            choice = await self.bot.wait_for_message(timeout=15, author=user, check=check)

            if choice is None or choice.content.title() in ["Surrender", "Ffs"]:
                outcome = "Surrender"
                amount = int(amount / 2)
            elif choice.content.title() == "War":
                self.casino_bank.withdraw_chips(user, amount)
                player_card, dealer_card, pc, dc = self.burn_three(deck)

                await self.bot.say("The dealer burns three cards and deals two cards face down...")
                await asyncio.sleep(3)
                await self.bot.say("**FLIP!**")

                if pc >= dc:
                    outcome = "Win"
                    amount = int(amount * multiplier + amount)
                else:
                    outcome = "Loss"
            else:
                await self.bot.say("Improper response. You are being forced to forfiet.")
                outcome = "Surrender"
                amount = int(amount / 2)

        return outcome, player_card, dealer_card, amount

    async def blackjack_game(self, dh, user, amount, ctx, settings, deck):
        # Setup dealer and player starting hands
        ph = self.draw_two(deck)
        count = self.count_hand(ph)
        # checks used to ensure the player uses the correct input
        check = lambda m: m.content.title() in ["Hit", "Stay", "Double"]
        check2 = lambda m: m.content.title() in ["Hit", "Stay"]

        # End the game if the player has 21 in the starting hand.
        if count == 21:
            return ph, dh, amount

        msg = ("{}\nYour cards: {}\nYour score: {}\nThe dealer shows: "
               "{}\nHit, stay, or double".format(user.mention, ", ".join(ph), count, dh[0]))
        await self.bot.say(msg)
        choice = await self.bot.wait_for_message(timeout=15, author=user, check=check)

        # Stop the blackjack game if the player chooses stay or double.
        if choice is None or choice.content.title() == "Stay":
            return ph, dh, amount
        elif choice.content.title() == "Double":
            # Create a try/except block to catch when people are dumb and don't have enough chips
            try:
                self.casino_bank.withdraw_chips(user, amount)
                amount = amount * 2
                ph = self.draw_card(ph, deck)
                count = self.count_hand(ph)
                return ph, dh, amount
            except InsufficientChips:
                await self.bot.say("Not enough chips. Please choose hit or stay.")
                choice2 = await self.bot.wait_for_message(timeout=15, author=user, check=check2)

                if choice2 is None or choice.content.title() == "Stay":
                    return ph, dh, amount

                elif choice2.content.title() == "Hit":
                    # This breaks PEP8 for DRY but I didn't want to create a sperate coroutine.
                    while count < 21:
                        ph = self.draw_card(ph, deck)
                        count = self.count_hand(ph)

                        if count >= 21:
                            break
                        msg = ("{}\nYour cards: {}\nYour score: {}\nThe dealer shows: "
                               "{}\nHit or stay?".format(user.mention, ", ".join(ph), count, dh[0]))
                        await self.bot.say(msg)
                        resp = await self.bot.wait_for_message(timeout=15, author=user,
                                                               check=check2)

                        if resp is None or resp.content.title() == "Stay":
                            break
                        else:
                            continue
                    # Return player hand & dealer hand when count >= 21 or the player picks stay.
                    return ph, dh, amount

        # Continue game logic in a loop until the player's count is 21 or bust.
        elif choice.content.title() == "Hit":
            while count < 21:
                ph = self.draw_card(ph, deck)
                count = self.count_hand(ph)

                if count >= 21:
                    break
                msg = ("{}\nYour cards: {}\nYour score: {}\nThe dealer shows: "
                       "{}\nHit or stay?".format(user.mention, ", ".join(ph), count, dh[0]))
                await self.bot.say(msg)
                response = await self.bot.wait_for_message(timeout=15, author=user, check=check2)

                if response is None or response.content.title() == "Stay":
                    break
                else:
                    continue
            # Return player hand and dealer hand when count is 21 or greater or player picks stay.
            return ph, dh, amount

    def war_results(self, settings, user, outcome, player_card, dealer_card, amount):
        chip_name = settings["System Config"]["Chip Name"]
        msg = ("======**{}**======\nPlayer Card: {}"
               "\nDealer Card: {}\n".format(user.name, player_card, dealer_card))
        if outcome == "Win":
            settings["Players"][user.id]["Won"]["War Won"] += 1
            # Check if a threshold is set and withold chips if amount is exceeded
            if self.threshold_check(settings, amount):
                settings["Players"][user.id]["Pending"] = amount
                msg += ("Your winnings exceeded the threshold set on this server. "
                        "The amount of {} {} chips will be withheld until reviewed and "
                        "released by an admin. Do not attempt to play additional games "
                        "exceeding the threshold until this has been cleared."
                        "".format(amount, chip_name, user.id))
                logger.info("{}({}) won {} chips exceeding the threshold. Game "
                            "details:\nPlayer Bet: {}\nGame "
                            "Outcome: {}\n[END OF FILE]".format(user.name, user.id, amount,
                                                                str(amount).ljust(10),
                                                                str(outcome[0]).ljust(10)))
            else:
                self.casino_bank.deposit_chips(user, amount)
                msg += ("**\*\*\*\*\*\*Winner!\*\*\*\*\*\***\n```Python\nYou just won {} {} "
                        "chips.```".format(amount, chip_name))

        elif outcome == "Loss":
            msg += "======House Wins!======"
        else:
            self.casino_bank.deposit_chips(user, amount)
            msg = ("======**{}**======\n:flag_white: Surrendered :flag_white:\n==================\n"
                   "{} {} chips returned.".format(user.name, amount, chip_name))

        # Save results and return appropriate outcome message.
        self.casino_bank.save_system()
        return msg

    def blackjack_results(self, settings, user, amount, ph, dh):
        chip_name = settings["System Config"]["Chip Name"]
        dc = self.count_hand(dh)
        pc = self.count_hand(ph)
        msg = ("======**{}**======\nYour hand: {}\nYour score: {}\nDealer's hand: {}\nDealer's "
               "score: {}\n".format(user.name, ", ".join(ph), pc, ", ".join(dh), dc))

        if dc > 21 and pc <= 21 or dc < pc <= 21:
            settings["Players"][user.id]["Won"]["BJ Won"] += 1
            total = int(round(amount * settings["Games"]["Blackjack"]["Multiplier"]))
            # Check if a threshold is set and withold chips if amount is exceeded
            if self.threshold_check(settings, total):
                settings["Players"][user.id]["Pending"] = total
                msg = ("Your winnings exceeded the threshold set on this server. "
                       "The amount of {} {} chips will be withheld until reviewed and "
                       "released by an admin. Do not attempt to play additional games "
                       "exceeding the threshold until this has been cleared."
                       "".format(total, chip_name, user.id))
                logger.info("{}({}) won {} chips exceeding the threshold. Game "
                            "details:\nPlayer Bet: {}\nGame "
                            "Outcome: {}\n[END OF FILE]".format(user.name, user.id, total,
                                                                str(total).ljust(10),
                                                                str(outcome[0]).ljust(10)))
            else:
                msg += ("**\*\*\*\*\*\*Winner!\*\*\*\*\*\***\n```Python\nYou just "
                        "won {} {} chips.```".format(total, chip_name))
                self.casino_bank.deposit_chips(user, total)
        elif pc > 21:
            msg += "======BUST!======"
        elif dc == pc and dc <= 21 and pc <= 21:
            msg += ("======Pushed======\nReturned {} {} chips to your "
                    "account.".format(amount, chip_name))
            amount = int(round(amount))
            self.casino_bank.deposit_chips(user, amount)
        elif dc > pc and dc <= 21:
            msg += "======House Wins!======".format(user.name)
        # Save results and return appropriate outcome message.
        self.casino_bank.save_system()
        return msg

    def draw_two(self, deck):
        hand = random.sample(deck, 2)
        deck.remove(hand[0])
        deck.remove(hand[1])
        return hand

    def draw_card(self, hand, deck):
        card = random.choice(deck)
        deck.remove(card)
        hand.append(card)
        return hand

    def count_hand(self, hand):
        count = sum([bj_values[x] for x in hand if x in bj_values])
        count += sum([1 if x == 'Ace' and count + 11 > 21 else 11
                      if x == 'Ace' and hand.count('Ace') == 1 else 1
                      if x == 'Ace' and hand.count('Ace') > 1 else 0 for x in hand])
        return count

    def dealer(self, deck):
        dh = self.draw_two(deck)
        count = self.count_hand(dh)

        # forces hit if ace in first two cards
        if 'Ace' in dh:
            dh = self.draw_card(dh, deck)
            count = self.count_hand(dh)

        # defines maximum hit score X
        while count < 16:
            self.draw_card(dh, deck)
            count = self.count_hand(dh)
        return dh

    def war_draw(self, deck):
        player_card = random.choice(deck)
        deck.remove(player_card)
        dealer_card = random.choice(deck)
        pc = war_values[player_card]
        dc = war_values[dealer_card]
        return player_card, dealer_card, pc, dc

    def burn_three(self, deck):
        burn_cards = random.sample(deck, 3)

        for x in burn_cards:
            deck.remove(x)

        player_card = random.choice(deck)
        deck.remove(player_card)
        dealer_card = random.choice(deck)
        pc = war_values[player_card]
        dc = war_values[dealer_card]

        return player_card, dealer_card, pc, dc

    def gather_requirements(self, settings, user):
        # Declare variables
        bank = self.bot.get_cog('Economy').bank
        path = settings["Memberships"]
        memberships = settings["Memberships"].keys()
        memberships_met = []
        # Loop through the memberships and their requirements
        for membership in memberships:
            requirements = []
            reqs = path[membership]["Requirements"]
            for req in reqs.keys():

                # If the requirement is a role, run role logic
                if req == "Role":
                    role = path[membership]["Requirements"]["Role"]
                    if role in [r.name for r in user.roles]:
                        requirements.append(True)
                    else:
                        requirements.append(False)
                # If the requirement is a credits, run credit logic
                if req == "Credits":
                    try:
                        user_credits = bank.get_balance(user)
                        if user_credits >= int(path[membership]["Requirements"]["Credits"]):
                            requirements.append(True)
                        else:
                            requirements.append(False)
                    except:  # When a casino member doesn't have a bank account
                        requirements.append(False)

                # If the requirement is a chips, run chip logic
                if req == "Chips":
                    balance = self.casino_bank.chip_balance(user)
                    if balance >= int(path[membership]["Requirements"][req]):
                        requirements.append(True)
                    else:
                        requirements.append(False)

                # If the requirement is a DoS, run DoS logic
                if req == "Days On Server":
                    dos = (ctx.message.timestamp - user.joined_at).days
                    if dos >= path[membership]["Requirements"]["Days On Server"]:
                        requirements.append(True)
                    else:
                        requirements.append(False)

            # You have to meet all the requirements to qualify for the membership
            if all(requirements):
                memberships_met.append((membership, path[membership]["Access"]))
                requirements.clear()
            else:
                requirements.clear()

        # Returns the membership with the highest access value
        if memberships_met:
            try:
                membership = max(memberships_met, key=itemgetter(1))[0]
                return membership
            except ValueError or TypeError:
                return None

        else:  # Returns none if the user has not qualified for any memberships
            return None

    def get_benefits(self, settings, player):
        membership = player["Membership"]
        if player["Membership"]:
            benefits = settings["Memberships"][membership]
        else:
            payday = settings["System Config"]["Default Payday"]
            benefits = {"Cooldown Reduction": 0, "Access": 0,
                        "Payday": payday, "Color": "grey"}
        return membership, benefits

    def threshold_check(self, settings, amount):
        if settings["System Config"]["Threshold Switch"]:
            if amount > settings["System Config"]["Threshold"]:
                return True
            else:
                return False
        else:
            return False

    def hl_outcome(self, dicetotal):
        choices = [(1, "Lo", "Low"), (2, "Lo", "Low"), (3, "Lo", "Low"), (4, "Lo", "Low"),
                   (5, "Lo", "Low"), (6, "Lo", "Low"), (7, "7", "Seven"), (8, "Hi", "High"),
                   (9, "Hi", "High"), (10, "Hi", "High"), (11, "Hi", "High"), (12, "Hi", "High")]
        outcome = choices[dicetotal - 1]
        return outcome

    def minmax_check(self, bet, game, settings):
        mi = settings["Games"][game]["Min"]
        mx = settings["Games"][game]["Max"]

        if mi <= bet <= mx:
            return None
        else:
            if mi != mx:
                msg = ("Your bet needs to be {} or higher, but cannot exceed the "
                       "maximum of {} chips.".format(mi, mx))
            else:
                msg = ("Your bet needs to be exactly {}.".format(mi))
            return msg

    def stats_cooldowns(self, settings, user, cd_list):
        user_membership = settings["Players"][user.id]["Membership"]
        reduction = 0

        # Check for cooldown reduction, if the membership was removed, set the user back to None.
        try:
            if user_membership:
                reduction = settings["Memberships"][user_membership]["Cooldown Reduction"]
        except KeyError:
            settings["Players"][user.id]["Membership"] = None
            self.casino_bank.save_system()

        # Begin cooldown logic calculation
        cooldowns = []
        for method in cd_list:
            base = settings["Players"][user.id]["Cooldowns"][method]

            # Check if method is for a game or for payday
            if method in self.games:
                path = settings["Games"][method]["Cooldown"] - reduction
            else:
                path = settings["System Config"]["Payday Timer"]

            if abs(base - int(time.perf_counter())) >= path:
                cooldowns.append("<<Ready to Play!")
            elif base == 0:
                cooldowns.append("<<Ready to Play!")
            else:
                s = abs(base - int(time.perf_counter()))
                seconds = abs(s - path)
                remaining = self.time_format(seconds, brief=True)
                cooldowns.append(remaining)
        return cooldowns

    def check_cooldowns(self, user, method, settings):
        base = settings["Players"][user.id]["Cooldowns"][method]
        user_membership = settings["Players"][user.id]["Membership"]
        reduction = 0

        # Check for cooldown reduction, if the membership was removed, set the user back to None.
        try:
            if user_membership:
                reduction = settings["Memberships"][user_membership]["Cooldown Reduction"]
        except KeyError:
            settings["Players"][user.id]["Membership"] = None
            self.casino_bank.save_system()
        # Check if method is for a game or for payday
        if method in self.games:
            path = settings["Games"][method]["Cooldown"]
        else:
            path = settings["System Config"]["Payday Timer"]

        # Begin cooldown logic calculation
        if abs(base - int(time.perf_counter())) >= path - reduction:
            settings["Players"][user.id]["Cooldowns"][method] = int(time.perf_counter())
            self.casino_bank.save_system()
            return None
        elif base == 0:
            settings["Players"][user.id]["Cooldowns"][method] = int(time.perf_counter())
            self.casino_bank.save_system()
            return None
        else:
            s = abs(base - int(time.perf_counter()))
            seconds = abs(s - path - reduction)
            remaining = self.time_format(seconds)
            msg = "{} is still on a cooldown. You still have: {}".format(method, remaining)
            return msg

    def access_calculator(self, settings, user):
        user_membership = settings["Players"][user.id]["Membership"]

        if user_membership is None:
            return 0
        else:
            if user_membership in settings["Memberships"]:
                access = settings["Memberships"][user_membership]["Access"]
                return access
            else:
                settings["Players"][user.id]["Membership"] = None
                self.casino_bank.save_system()
                return 0

    def game_checks(self, settings, prefix, user, bet, game, choice, choices):
        casino_name = settings["System Config"]["Casino Name"]
        game_access = settings["Games"][game]["Access Level"]
        # Allin does not require a minmax check, so we set it to None if Allin.
        if game != "Allin":
            minmax_fail = self.minmax_check(bet, game, settings)
        else:
            minmax_fail = None
        # Check for membership first.
        if not self.casino_bank.membership_exists(user):
            msg = ("You need to register to the {} Casino. To register type `{}casino "
                   "join`.".format(casino_name, prefix))
            return msg

        user_access = self.access_calculator(settings, user)
        # Begin logic to determine if the game can be played.
        if choice not in choices:
            msg = "Incorrect response. Accepted response are:\n{}".format(", ".join(choices))
            return msg
        elif not settings["System Config"]["Casino Open"]:
            msg = "The {} Casino is closed.".format(casino_name)
            return msg
        elif game_access > user_access:
            msg = ("{} requires an access level of {}. Your current access level is {}. Obtain a "
                   "higher membership to play this game.")
        elif minmax_fail:
            msg = minmax_fail
            return msg
        elif not self.casino_bank.can_bet(user, bet):
            msg = "You do not have enough chips to cover the bet."
            return msg
        else:
            cd_check = self.check_cooldowns(user, game, settings)
            # Cooldowns are checked last incase another check failed.
            return cd_check

    def color_lookup(self, color):
        colors = {"blue": 0x3366FF, "red": 0xFF0000, "green": 0x00CC33, "orange": 0xFF6600,
                  "purple": 0x663399, "yellow": 0xFFFF00, "teal": 0x009999, "magenta": 0xFF33CC,
                  "turquoise": 0x00FFFF, "grey": 0x666666}
        color = colors[color]
        return color

    def player_update(self, player_data, new_game, path=None):
        """Helper function to add new data into the player's data"""

        if path is None:
            path = []
        for key in new_game:
            if key in player_data:
                if isinstance(player_data[key], dict) and isinstance(new_game[key], dict):
                    self.player_update(player_data[key], new_game[key], path + [str(key)])
                elif player_data[key] == new_game[key]:
                    pass
                else:
                    raise Exception("Conflict at {}".format("".join(path + [str(key)])))
            else:
                player_data[key] = new_game[key]
        self.casino_bank.save_system()

    def time_format(self, seconds, brief=False):
        # Calculate the time and input into a dict to plural the strings later.
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        data = PluralDict({'hour': h, 'minute': m, 'second': s})

        # Determine the remaining time.
        if not brief:
            if h > 0:
                fmt = "{hour} hour{hour(s)}"
                if data["minute"] > 0 and data["second"] > 0:
                    fmt += ", {minute} minute{minute(s)}, and {second} second{second(s)}"
                if data["second"] > 0 == data["minute"]:
                    fmt += ", and {second} second{second(s)}"
                msg = fmt.format_map(data)
            elif h == 0 and m > 0:
                if data["second"] == 0:
                    fmt = "{minute} minute{minute(s)}"
                else:
                    fmt = "{minute} minute{minute(s)}, and {second} second{second(s)}"
                msg = fmt.format_map(data)
            elif m == 0 and h == 0 and s > 0:
                fmt = "{second} second{second(s)}"
                msg = fmt.format_map(data)
            elif m == 0 and h == 0 and s == 0:
                msg = "None"
            # Return remaining time.
        else:

            if h > 0:
                msg = "{}h".format(h)
                if m > 0 and s > 0:
                    msg += ", {}m, and {}s".format(h, m, s)

                if s > 0 and m == 0:
                    msg += "and {}s"
            elif h == 0 and m > 0:
                if s == 0:
                    msg = "{}m".format(m)
                else:
                    msg = "{}m and {}s".format(m, s)
            elif m == 0 and h == 0 and s > 0:
                msg = "{}s".format(s)
            elif m == 0 and h == 0 and s == 0:
                msg = "None"

        return msg

    def __unload(self):
        self.cycle_task.cancel()
        self.casino_bank.save_system()


def check_folders():
    if not os.path.exists("data/JumperCogs/casino"):
        print("Creating data/JumperCogs/casino folder...")
        os.makedirs("data/JumperCogs/casino")


def check_files():
    system = {"Servers": {}}

    f = "data/JumperCogs/casino/casino.json"
    if not dataIO.is_valid_json(f):
        print("Creating default casino.json...")
        dataIO.save_json(f, system)


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("red.casino")
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        # Rotates to a new file every 10mb, up to 5
        handler = logging.handlers.RotatingFileHandler(filename='data/JumperCogs/casino/casino.log',
                                                       encoding='utf-8', backupCount=5,
                                                       maxBytes=100000)
        handler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(message)s',
                                               datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    if tabulateAvailable:
        bot.add_cog(Casino(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
