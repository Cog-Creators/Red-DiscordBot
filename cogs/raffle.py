# Developed by Redjumpman for Redbot
# This cog requires no library installs
# If you have issues contact Redjumpman#2375 on Discord
import uuid
import os
import random
import asyncio
from .utils import checks
from discord.ext import commands
from .utils.dataIO import dataIO
from __main__ import send_cmd_help


class Raffle:
    """Raffle system where you buy tickets with points"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/raffle/raffle.json"
        self.raffle = dataIO.load_json(self.file_path)

    @commands.group(name="raffle", pass_context=True)
    async def _raffle(self, ctx):
        """Raffle Commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def start(self, ctx):
        """Starts a raffle"""
        user = ctx.message.author
        if not self.raffle["Config"]["Active"]:
            self.raffle["Config"]["Active"] = True
            dataIO.save_json(self.file_path, self.raffle)
            msg = ("@everyone a raffle has been started by {}\nUse the command {}raffle buy to "
                   "purchase tickets".format(user.name, ctx.prefix))
        else:
            msg = "A raffle is currently active. End the current one to start a new one."
        await self.bot.say(msg)

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def end(self, ctx):
        """Ends a raffle"""
        if self.raffle["Config"]["Active"]:
            self.raffle["Config"]["Active"] = False
            tickets = self.raffle["Config"]["Tickets"]
            winning_ticket = random.choice(tickets)
            winner = []
            for subdict in self.raffle["Players"]:
                if winning_ticket in self.raffle["Players"][subdict]["Tickets"]:
                    winner.append(subdict)
            mention = "<@" + winner[0] + ">"
            await self.bot.say("The winner of the raffle is...")
            await asyncio.sleep(3)
            await self.bot.say(mention + "! Congratulations, you have won!")
            self.raffle["Config"]["Tickets"] = []
            self.raffle["Players"] = {}
            dataIO.save_json(self.file_path, self.raffle)
        else:
            await self.bot.say("You need to start a raffle for me to end one!")

    @_raffle.command(pass_context=True, no_pm=True)
    async def buy(self, ctx, number: int):
        """Buys raffle ticket(s)"""
        user = ctx.message.author
        bank = self.bot.get_cog('Economy').bank
        code = str(uuid.uuid4())
        ticket_cost = self.raffle["Config"]["Cost"]
        max_tickets = self.raffle["Config"]["Max Tickets"]
        credits = ticket_cost * number
        if number < 0:
            msg = "You need to pick a number higher than 0"
        elif not self.raffle["Config"]["Active"]:
            msg = "There is not a raffle currently active"
        elif not bank.can_spend(user, credits):
            msg = ("You do not have enough points to purchase that many raffle tickets\nRaffle "
                   "tickets cost {} points each.".format(ticket_cost))
        elif number > max_tickets and max_tickets != 0:
            msg = ("You can't purchase that many tickets. A maximum of {} tickets per "
                   "user.".format(max_tickets))
        elif user.id in self.raffle["Players"]:
            user_tickets = len(self.raffle["Players"][user.id]["Tickets"])
            if user_tickets + number > max_tickets:
                msg = ("You can't purchase that many tickets. A maximum of {} tickets per user.\n "
                       "You currently have {} tickets.".format(max_tickets, user_tickets))
            else:
                bank.withdraw_credits(user, credits)
                self.raffle["Players"][user.id]["Tickets"] += [code] * number
                self.raffle["Config"]["Tickets"] += [code] * number
                user_tickets = len(self.raffle["Players"][user.id]["Tickets"])
                self.raffle["Players"][user.id]["Total Tickets"] = user_tickets
                msg = ("{} has purchased {} raffle tickets for "
                       "{}".format(user.mention, number, credits))
                dataIO.save_json(self.file_path, self.raffle)
        else:
            bank.withdraw_credits(user, credits)
            self.raffle["Players"][user.id] = {}
            self.raffle["Players"][user.id] = {"Tickets": []}
            self.raffle["Players"][user.id]["Tickets"] += [code] * number
            tickets_num = len(self.raffle["Players"][user.id]["Tickets"])
            self.raffle["Players"][user.id]["Total Tickets"] = tickets_num
            self.raffle["Config"]["Tickets"] += [code] * number
            msg = "{} has purchased {} raffle tickets for {}".format(user.mention, number, credits)
            dataIO.save_json(self.file_path, self.raffle)
        await self.bot.say(msg)

    @_raffle.command(pass_context=True, no_pm=True)
    async def check(self, ctx):
        """Shows you the number of raffle tickets you bought"""
        user = ctx.message.author
        if user.id in self.raffle["Players"]:
            tickets = self.raffle["Players"][user.id]["Tickets"]
            amount = str(len(tickets))
            await self.bot.say("You currently have " + amount + " tickets")
        else:
            await self.bot.say("You have not bought any tickets for the raffle.")

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def cost(self, ctx, price: int):
        """Sets the cost of raffle tickets"""
        self.raffle["Config"]["Cost"] = price
        dataIO.save_json(self.file_path, self.raffle)
        msg = "```Python\nThe price for 1 raffle ticket is now set to {}```".format(price)
        await self.bot.say(msg)

    @_raffle.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def tmax(self, ctx, number: int):
        """Number of tickets each person can buy. 0 for infinite"""
        self.raffle["Config"]["Max Tickets"] = number
        dataIO.save_json(self.file_path, self.raffle)
        await self.bot.say("The max tickets each user can buy is now {}".format(number))


def check_folders():
    if not os.path.exists("data/raffle"):
        print("Creating data/raffle folder...")
        os.makedirs("data/raffle")


def check_files():
    system = {"Players": {},
              "Config": {"Tickets": [],
                         "Cost": 50,
                         "Active": False,
                         "Max Tickets": 0}}
    f = "data/raffle/raffle.json"
    if not dataIO.is_valid_json(f):
        print("Creating default raffle/raffle.json...")
        dataIO.save_json(f, system)
    else:  # consistency check
        current = dataIO.load_json(f)
        if current["Config"].keys() != system["Config"].keys():
            for key in system["Config"].keys():
                if key not in current["Config"].keys():
                    current["Config"][key] = system["Config"][key]
                    print("Adding " + str(key) +
                          " field to raffle raffle.json")
            dataIO.save_json(f, current)


def setup(bot):
    check_folders()
    check_files()
    n = Raffle(bot)
    bot.add_cog(n)
