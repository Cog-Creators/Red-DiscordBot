#  This will create 2 data folders with 1 JSON file
import os
import asyncio
import random
import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help


class Lottery:
    """Hosts lotteries on the server"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/lottery/system.json"
        self.system = dataIO.load_json(self.file_path)
        self.funny = ["Rigging the system...",
                      "Removing tickets that didn't pay me off...",
                      "Adding fake tickets...", "Throwing out the bad names..",
                      "Switching out the winning ticket...",
                      "Picking from highest bribe...",
                      "Looking for a marked ticket...",
                      "Eeny, meeny, miny, moe...",
                      "I lost the tickets so...",
                      "Stop messaging me, I'm picking...",
                      "May the odds be ever in your favor...",
                      "I'm going to ban that guy who keeps spamming me, 'please!'... ",
                      "Winner winner, chicken dinner...",
                      "Can someone slap the guy who keeps yelling 'Bingo!..."]
        self.version = "2.5.3"

    @commands.group(name="setlottery", pass_context=True)
    async def setlottery(self, ctx):
        """Lottery Settings"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setlottery.command(name="prize", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _prize_setlottery(self, ctx, amount: int):
        """Set's the prize amount for a lottery. Set to 0 to cancel."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if amount > 0:
            settings["Config"]["Lottery Prize"] = True
            settings["Config"]["Prize Amount"] = amount
            dataIO.save_json(self.file_path, self.system)
            msg = "A prize for the next lottery has been set for {} towels".format(amount)
        elif amount == 0:
            settings["Config"]["Lottery Prize"] = False
            settings["Config"]["Prize Amount"] = amount
            dataIO.save_json(self.file_path, self.system)
            msg = "Prize for the next lottery drawing removed."
        else:
            msg = "You can't use negative values."
        await self.bot.say(msg)

    @setlottery.command(name="autofreeze", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _autofreeze_setlottery(self, ctx):
        """Turns on auto account freeze. Will freeze/unfreeze every 60 seconds."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Config"]["Membership Freeze"]:
            settings["Config"]["Membership Freeze"] = False
            msg = "Now turning off auto freeze. Please wait for the previous cycle to expire."
        else:
            settings["Config"]["Membership Freeze"] = True
            msg = ("Now turning on auto freeze. This will cycle through server accounts and "
                   "freeze/unfreeze accounts that require the signup role.")
            self.bot.loop.create_task(self.auto_freeze(ctx, settings))
        await self.bot.say(msg)
        dataIO.save_json(self.file_path, self.system)

    @setlottery.command(name="winners", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _winners_setlottery(self, ctx, winners: int):
        """Set how many winners are drawn. Default 1"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if winners > 0:
            settings["Config"]["Lottery Winners"] = winners
            dataIO.save_json(self.file_path, self.system)
            msg = "{} winners will be drawn for the lottery.".format(winners)
        else:
            msg = "You can't have less than 1 winner."
        await self.bot.say(msg)

    @setlottery.command(name="fun", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _fun_setlottery(self, ctx):
        """Toggles fun text on and off"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Config"]["Fun Text"]:
            settings["Config"]["Fun Text"] = False
            msg = "Fun Text is now disabled."
        else:
            settings["Config"]["Fun Text"] = True
            msg = "Fun Text is now enabled."
        await self.bot.say(msg)
        dataIO.save_json(self.file_path, self.system)

    @setlottery.command(name="role", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _role_setlottery(self, ctx, role: discord.Role):
        """Set the required role for membership sign-up. Default: None"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["Config"]["Signup Role"] = role.name
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("Setting the required role to sign-up to **{}**.\nUnless set to "
                           "**None**, users must be assigned this role to signup!".format(role))

    @commands.group(name="lottery", pass_context=True)
    async def lottery(self, ctx):
        """Lottery Group Command"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @lottery.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_lottery(self):
        """Shows the version of lottery cog you are running."""
        version = self.version
        await self.bot.say("```Python\nYou are running Lottery Cog version {}.```".format(version))

    @lottery.command(name="start", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _start_lottery(self, ctx, restriction=False, timer=0):
        """Starts a lottery. Can optionally restrict participation and set a timer."""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if not settings["Config"]["Lottery Active"]:
            settings["Config"]["Lottery Count"] += 1
            if restriction:
                # Checks if admin set a role to mention, otherwise default to lottery members
                if not settings["Config"]["Signup Role"]:
                    lottery_role = "lottery members"
                else:
                    lottery_role = "@" + settings["Config"]["Signup Role"]
                settings["Config"]["Lottery Member Requirement"] = True
            else:
                lottery_role = "everyone on the server"
            settings["Config"]["Lottery Active"] = True
            dataIO.save_json(self.file_path, self.system)
            if timer:
                # TODO Change timer to time formatter function
                await self.bot.say("A lottery has been started by {}, for {}. It will end in "
                                   "{} seconds.".format(user.name, lottery_role, timer))
                await self.run_timer(timer, ctx.prefix, server, settings)
            else:
                await self.bot.say("A lottery has been started by {}, for "
                                   "{}.".format(user.name, lottery_role))
        else:
            await self.bot.say("I cannot start a new lottery until the current one has ended.")

    @lottery.command(name="end", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _end_lottery(self, ctx):
        """Manually ends an on-going lottery"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        winner_num = settings["Config"]["Lottery Winners"]
        if settings["Config"]["Lottery Active"]:
            if settings["Lottery Players"]:
                players = list(settings["Lottery Players"].keys())
                try:
                    winners = random.sample(players, winner_num)
                except ValueError:  # If there are more winners than players, defaults to everyone
                    print("Warning. More winners than players, so I am making everyone a winner!")
                    player_num = len(settings["Lottery Players"].keys())
                    winners = random.sample(players, player_num)
                mentions = [settings["Lottery Players"][winner]["Mention"] for winner in winners]
                await self.display_lottery_winner(winners, mentions, server, settings)
                self.update_win_stats(settings, winners)
                self.lottery_clear(settings)
            else:
                await self.bot.say("There are no players playing in the lottery. Resetting lottery "
                                   "settings.")
                self.lottery_clear(settings)
        else:
            await self.bot.say("There is no lottery for me to end.")

    @lottery.command(name="play", pass_context=True)
    async def _play_lottery(self, ctx):
        """Enters a user into an on-going lottery."""
        server = ctx.message.server
        user = ctx.message.author
        settings = self.check_server_settings(server)
        if not settings["Config"]["Lottery Active"]:
            await self.bot.say("There is no on-going lottery.")
        elif await self.requirement_check(ctx, settings):
            if user.id not in settings["Lottery Players"]:
                settings["Lottery Players"][user.id] = {"Name": user.name, "Mention": user.mention}
                players = len(settings["Lottery Players"].keys())
                dataIO.save_json(self.file_path, self.system)
                self.update_play_stats(settings, user.id)
                await self.bot.say("{} you have been added to the lottery. "
                                   "Good luck!\nThere are now {} user(s) participating in "
                                   "the lottery".format(user.mention, players))
            else:
                await self.bot.say("You have already entered into the lottery.")

    @lottery.command(name="signup", pass_context=True)
    async def _signup_lottery(self, ctx):
        """Allows a user to sign-up to participate in lotteries"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        role = settings["Config"]["Signup Role"]
        if role:
            if self.role_check(ctx, role, user.id):
                await self.member_creation(user, settings, ctx.prefix)
            else:
                await self.bot.say("You do not have the {} role required to become a "
                                   "member".format(role))
        else:
            await self.member_creation(user, settings, ctx.prefix)

    @lottery.command(name="status", pass_context=True)
    async def _status_lottery(self, ctx):
        """Check if a lottery is active"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Config"]["Lottery Active"]:
            msg = "A lottery is active on this server and "
            if user.id in settings["Lottery Players"]:
                msg += "you have already entered."
            else:
                msg += "you have **not** entered yet."
        else:
            msg = "There are no lotteries running on this server right now."
        await self.bot.say(msg)

    @lottery.command(name="info", pass_context=True)
    async def _info_lottery(self, ctx):
        """General information about this plugin"""
        msg = """```
General Information about Lottery Plugin
=========================================
• When starting a lottery you can optionally set a timer and/or restrict to members only.
• By default anyone can sign-up for lottery membership.
• To retrict sign-ups to a role, type {0}setlottery role.
• {0}lottery stats will show your stats if you are signed-up.
• You can freeze accounts that without the sign-up role periodically using {0}setlottery freeze.
• Autofreeze feature will need to be enabled again if you shutdown your bot.
• Members who have a frozen account will cannot gain stats or participate in member only lotteries.
• Accounts are automatically unfrozen with autofreeze, if they regain the required role again.
• Lotteries can be hosted on different servers with the same bot without conflicts.
• Powerballs have not yet been implemented, but the framework is complete. Ignore powerball stats.
• Anyone can join a lottery without restrictions.```""".format(ctx.prefix)
        await self.bot.say(msg)

    @lottery.command(name="stats", pass_context=True)
    async def _stats_lottery(self, ctx):
        """Shows your membership stats"""
        user = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        role = settings["Config"]["Signup Role"]
        if not settings["Lottery Members"]:
            msg = "There are no Lottery Members on this server."
        elif user.id in settings["Lottery Members"]:
            if not settings["Lottery Members"][user.id]["Account Frozen"]:
                lotteries_played = settings["Lottery Members"][user.id]["Lotteries Played"]
                lotteries_won = settings["Lottery Members"][user.id]["Lotteries Won"]
                if settings["Config"]["Lottery Active"]:
                    lottery_active = "Active"
                else:
                    lottery_active = "Inactive"
                if user.id in settings["Lottery Players"]:
                    participating = "[Yes]"
                else:
                    participating = "No"
                header = "{}'s Lottery Stats on {}".format(user.name, server.name)
                msg = "```ini\n{}\n".format(header) + "=" * len(header)
                msg += "\nLotteries Played:                   {}".format(lotteries_played)
                msg += "\nLotteries Won:                      {}".format(lotteries_won)
                msg += "\nAccount Status:                     Active"
                msg += "\nLottery Status:                     {}".format(lottery_active)
                msg += "\nParticipating:                      {}```".format(participating)
            else:
                msg = ("Your account is frozen. You require the {} role on this server to "
                       "track stats.\nIf you are given back this role, type {}lottery activate "
                       "to restore your account.".format(role, ctx.prefix))
        else:
            msg = "You are not a lottery member. Only members can view/track stats."
        await self.bot.say(msg)

    def add_credits(self, userid, amount, server):
        bank = self.bot.get_cog('Economy').bank
        mobj = server.get_member(userid)
        bank.deposit_credits(mobj, amount)
        msg = "```{} towels have ben deposited into your account.```".format(amount)
        return msg

    def update_play_stats(self, settings, userid):
        if userid in settings["Lottery Members"]:
            settings["Lottery Members"][userid]["Lotteries Played"] += 1
            dataIO.save_json(self.file_path, self.system)

    def update_win_stats(self, settings, winners):
        for winner in winners:
            if winner in settings["Lottery Members"]:
                settings["Lottery Members"][winner]["Lotteries Won"] += 1
        dataIO.save_json(self.file_path, self.system)

    def lottery_clear(self, settings):
        settings["Lottery Players"] = {}
        settings["Config"]["Lottery Prize"] = 0
        settings["Config"]["Lottery Member Requirement"] = False
        settings["Config"]["Lottery Active"] = False
        dataIO.save_json(self.file_path, self.system)

    def role_check(self, ctx, role, userid):
        if userid in [m.id for m in ctx.message.server.members if role.lower() in [str(r).lower()
                      for r in m.roles]]:
            return True
        else:
            return False

    def check_server_settings(self, server):
        if "Config" in self.system.keys():
            self.system = {"Servers": {}}
            print("Old lottery data has been wiped for the new structure. Sorry T.T")
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = {"Config": {"Lottery Count": 0,
                                                            "Lottery Active": False,
                                                            "Fun Text": False,
                                                            "Lottery Winners": 1,
                                                            "Prize Amount": 0,
                                                            "Powerball Active": False,
                                                            "Powerball Reoccuring": True,
                                                            "Powerball Jackpot": 3000,
                                                            "Powerball Ticket Limit": 0,
                                                            "Powerball Ticket Cost": 0,
                                                            "Powerball Winning Ticket": None,
                                                            "Powerball Grace Period": 1,
                                                            "Powerball Day": "Sunday",
                                                            "Powerball Time": "1700",
                                                            "Powerball Combo Payouts": [2.0, 3.0,
                                                                                        10],
                                                            "Powerball Jackpot Type": "Preset",
                                                            "Powerball Jackpot Percentage": 0.31,
                                                            "Powerball Jackpot Multiplier": 2.0,
                                                            "Powerball Jackpot Preset": 500,
                                                            "Signup Role": None,
                                                            "Lottery Member Requirement": False,
                                                            "Membership Freeze": False,
                                                            },
                                                 "Lottery Members": {},
                                                 "Lottery Players": {},
                                                 }
            dataIO.save_json(self.file_path, self.system)
            print("Creating default lottery settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path

    async def requirement_check(self, ctx, settings):
        user = ctx.message.author
        if settings["Config"]["Lottery Member Requirement"]:
            if user.id in settings["Lottery Members"]:
                if settings["Lottery Members"][user.id]["Account Frozen"]:
                    await self.bot.say("Your account is frozen. If you meet the role "
                                       "requirement use {}lottery activate to restore your "
                                       "frozen account.".format(ctx.prefix))
                    return False
                else:
                    return True
            else:
                await self.bot.say("You do not meet the role requirement to participate in "
                                   "this lottery.")
                return False
        else:
            return True

    async def run_timer(self, timer, prefix, server, settings):
        half_time = timer / 2
        quarter_time = half_time / 2
        await asyncio.sleep(half_time)
        if settings["Config"]["Lottery Active"] is True:
            await self.bot.say("{} seconds remaining for the lottery. "
                               "Type {}lottery play to join.".format(half_time, prefix))
            await asyncio.sleep(quarter_time)
            if settings["Config"]["Lottery Active"] is True:
                await self.bot.say("{} seconds remaining for the lottery. "
                                   "Type {}lottery play to join.".format(quarter_time, prefix))
                await asyncio.sleep(quarter_time)
                if settings["Config"]["Lottery Active"] is True:
                    await self.bot.say("The lottery is now ending...")
                    await asyncio.sleep(1)
                    await self.end_lottery_timer(server, settings)

    async def end_lottery_timer(self, server, settings):
        if settings["Config"]["Lottery Active"]:
            if settings["Lottery Players"]:
                winner_num = settings["Config"]["Lottery Winners"]
                players = list(settings["Lottery Players"].keys())
                winners = random.sample(players, winner_num)
                mentions = [settings["Lottery Players"][winner]["Mention"] for winner in winners]
                self.update_win_stats(settings, winners)
                await self.display_lottery_winner(winners, mentions, server, settings)
                self.lottery_clear(settings)
            else:
                await self.bot.say("There are no players in the lottery. The lottery has been "
                                   "cancelled.")
                self.lottery_clear(settings)
        else:
            pass

    async def display_lottery_winner(self, winners, mentions, server, settings):
        await self.bot.say("The winner is...")
        await asyncio.sleep(2)
        if settings["Config"]["Fun Text"]:
            fun_text = random.choice(self.funny)
            await self.bot.say(fun_text)
            await asyncio.sleep(2)
        await self.bot.say("Congratulations {}. You won the lottery!".format(", ".join(mentions)))
        if settings["Config"]["Prize Amount"] > 0:
            prize = settings["Config"]["Prize Amount"]
            await self.deposit_prize(winners, prize, server)
            settings["Config"]["Prize Amount"] = 0
            dataIO.save_json(self.file_path, self.system)

    async def deposit_prize(self, winners, prize, server):
        bank = self.bot.get_cog('Economy').bank
        mobjs = [server.get_member(uid) for uid in winners]
        [bank.deposit_credits(obj, prize) for obj in mobjs]
        await self.bot.say("{} towels have been deposited into {} "
                           "account.".format(prize, "\'s, ".join([user.name for user in mobjs])))

    async def member_creation(self, user, settings, prefix):
        if user.id not in settings["Lottery Members"]:
            settings["Lottery Members"][user.id] = {"Name": user.name,
                                                    "ID": user.id,
                                                    "Lotteries Played": 0,
                                                    "Lotteries Won": 0,
                                                    "Powerballs Played": 0,
                                                    "Powerballs Won": 0,
                                                    "Powerball Tickets": [],
                                                    "Powerball Count": 0,
                                                    "Account Frozen": False}
            dataIO.save_json(self.file_path, self.system)
            msg = ("Lottery Account created for {}. You may now participate in on-going lotteries."
                   "\nCheck your stats with {}lottery stats".format(user.name, prefix))
        else:
            msg = "You are already member."
        await self.bot.say(msg)

    async def auto_freeze(self, ctx, settings):
        server = ctx.message.server
        while settings["Config"]["Membership Freeze"]:
            role = settings["Config"]["Signup Role"]
            print("Loop started for {}".format(server.name))
            if settings["Lottery Members"]:
                users = list(settings["Lottery Members"].keys())
                for user in users:
                    if self.role_check(ctx, role, user):
                        if settings["Lottery Members"][user]["Account Frozen"]:
                            settings["Lottery Members"][user]["Account Frozen"] = False
                        else:
                            pass
                    else:
                        if settings["Lottery Members"][user]["Account Frozen"]:
                            pass
                        else:
                            settings["Lottery Members"][user]["Account Frozen"] = True
            dataIO.save_json(self.file_path, self.system)
            await asyncio.sleep(5)


def check_folders():
    if not os.path.exists("data/JumperCogs"):   # Checks for parent directory for all Jumper cogs
        print("Creating JumperCogs default directory")
        os.makedirs("data/JumperCogs")

    if not os.path.exists("data/JumperCogs/lottery"):
        print("Creating JumperCogs lottery folder")
        os.makedirs("data/JumperCogs/lottery")


def check_files():
    default = {"Servers": {}}

    f = "data/JumperCogs/lottery/system.json"

    if not dataIO.is_valid_json(f):
        print("Adding system.json to data/JumperCogs/lottery/")
        dataIO.save_json(f, default)


def setup(bot):
    check_folders()
    check_files()
    n = Lottery(bot)
    bot.add_cog(n)
