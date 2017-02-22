#  Heist was created by Redjumpman for Redbot

# Standard Library
import asyncio
import os
import random
import time
from bisect import bisect
from operator import itemgetter

# Discord / Red Bot
import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help

# Third party library requirement
try:
    from tabulate import tabulate
    tabulateAvailable = True
except ImportError:
    tabulateAvailable = False

good = [["{} had the car gassed up and ready to go. +25 credits.", 25],
        ["{} cut the power to the bank. +50 credits.", 50],
        ["{} erased the video footage. +50 credits.", 50],
        ["{} hacked the security system and put it on a loop feed. +75 credits.", 75],
        ["{} stopped the teller from triggering the silent alarm. +50 credits.", 50],
        ["{} knocked out the local security. +50 credits.", 50],
        ["{} stopped a local from being a hero +50 credits.", 50],
        ["{} got the police negotiator to deliver everyone pizza. +25 credits.", 25],
        ["{} brought masks of former presidents to hide our identity. +25 credits.", 25],
        ["{} found an escape route. +25 credits.", 25],
        ["{} brought extra ammunition for the crew. +25 credits.", 25],
        ["{} cut through that safe like butter. +25 credits.", 25],
        ["{} kept the hostages under control. +25 credits.", 25],
        ["{} created a distraction to get the crew out. +50 credits.", 50],
        ["{} improvised under pressure and got the crew out. +50 credits.", 50],
        ["{} counter sniped a sniper. +100 credits.", 100],
        ["{} distracted the guard. +25 credits.", 25],
        ["{} brought a Go-Bag for the team. +25 credits.", 25],
        ["{} found a secret stash in the deposit box room. +50 credits.", 50],
        ["{} found a box of jewelry on a civilian. +25 credits.", 25]]

bad = [["A shoot out with local authorities began and {0} was hit...but survived!", "Apprehended"],
       ["The cops dusted for finger prints and later arrested {0}.", "Apprehended"],
       ["{0} thought they could double cross the crew and paid for it.", "Dead"],
       ["{0} blew a tire in the getaway car.", "Apprehended"],
       ["{0}'s gun jammed while fighting local security, and was knocked out.", "Apprehended"],
       ["{0} held off the police while the crew was making their getaway.", "Apprehended"],
       ["A hostage situation went south, and {0} was captured.", "Apprehended"],
       ["{0} showed up to the heist high as kite, and was subsequently caught.", "Apprehended"],
       ["{0}'s bag of money contained exploding blue ink and was later caught.", "Apprehended"],
       ["{0} was sniped by a swat sniper.", "Dead"],
       ["The crew decided to shaft {0}.", "Dead"],
       ["Evidence was later found at {0}'s place' linking them to the heist.", "Apprehended"],
       ["The crew missed a CCTV camera that identified {0} and they were caught.", "Apprehended"],
       ["{0} forgot the escape plan, and took the route leading to the police.", "Apprehended"],
       ["{0} was hit and killed by friendly fire.", "Dead"],
       ["Security system's redundancies caused {0} to be identified.", "Apprehended"],
       ["{0} accidentally revealed their identity to the teller.", "Apprehended"],
       ["The swat team released sleeping gas, {0} is sleeping like a baby.", "Apprehended"],
       ["'FLASH BANG OUT!', was the last thing {0} heard.", "Apprehended"],
       ["'GRENADE OUT!', {0} is now sleeping with the fishes.", "Dead"],
       ["{0} tripped a laser wire and was caught.", "Apprehended"],
       ["One of the hostages later identified {0} from the heist.", "Apprehended"],
       ["During the power outage, police caught {0} in the confusion.", "Apprehended"],
       ["{0} was left behind for slowing down the crew, due to a leg wound.", "Apprehended"],
       ["Someone snitched and {0} was arrested.", "Apprehended"],
       ["Before the crew could intervene a guard tazed {0} and is now out cold.", "Apprehended"],
       ["Swat came through the vents, and neutralized {0}.", "Apprehended"]]


# Thanks stack overflow http://stackoverflow.com/questions/21872366/plural-string-formatting
class PluralDict(dict):
    def __missing__(self, key):
        if '(' in key and key.endswith(')'):
            key, rest = key.split('(', 1)
            value = super().__getitem__(key)
            suffix = rest.rstrip(')').split(',')
            if len(suffix) == 1:
                suffix.insert(0, '')
            return suffix[0] if value <= 1 else suffix[1]
        raise KeyError(key)


class Heist:
    """Bankheist system inspired by Deepbot"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/heist/heist.json"
        self.system = dataIO.load_json(self.file_path)
        self.version = "2.0.8.1"
        self.cycle_task = bot.loop.create_task(self.vault_updater())

    @commands.group(pass_context=True, no_pm=True)
    async def heist(self, ctx):
        """General heist related commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @heist.command(name="reset", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reset_heist(self, ctx):
        """Resets heist incase it hangs"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.reset_heist(settings)
        await self.bot.say("```Heist has been reset```")

    @heist.command(name="clear", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clear_heist(self, ctx, user: discord.Member):
        """Clears a member of jail and death."""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        self.user_clear(settings, user)
        await self.bot.say("```{} administratively cleared {}```".format(author.name, user.name))

    @heist.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_heist(self, ctx):
        """Shows the version of heist you are running"""
        await self.bot.say("You are running Heist version {}.".format(self.version))

    @heist.command(name="banks", pass_context=True)
    async def _banks_heist(self, ctx):
        """Shows a list of banks"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if len(settings["Banks"].keys()) < 0:
            msg = ("There aren't any banks! To create a bank use {}heist "
                   "createbank .".format(ctx.prefix))
        else:
            bank_names = [x for x in settings["Banks"]]
            crews = [subdict["Crew"] - 1 for subdict in settings["Banks"].values()]
            success = [str(subdict["Success"]) + "%" for subdict in settings["Banks"].values()]
            vaults = [subdict["Vault"] for subdict in settings["Banks"].values()]
            data = list(zip(bank_names, crews, vaults, success))
            table_data = sorted(data, key=itemgetter(1), reverse=True)
            table = tabulate(table_data, headers=["Bank", "Max Crew", "Vault", "Success Rate"])
            msg = "```Python\n{}```".format(table)
        await self.bot.say(msg)

    @heist.command(name="bailout", pass_context=True)
    async def _bailout_heist(self, ctx, user: discord.Member=None):
        """Specify who you want to bailout. Defaults to you."""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        if not user:
            user = author
        if settings["Players"][user.id]["Status"] == "Apprehended":
            cost = settings["Players"][user.id]["Bail Cost"]
            if not self.bank_check(settings, user, cost):
                await self.bot.say("You do not have enough credits to afford the bail amount.")
                return

            if user.id == author.id:
                msg = ("Do you want to make bail? It will cost {} credits. If you are caught "
                       "robbing a bank while out on bail your next sentence and bail amount will "
                       "triple. Do you still wish to make bail?".format(cost))
            else:
                msg = ("You are about to make bail for {0} and it will cost you {1} credits. "
                       "Are you sure you wish to pay {1} for {0}?".format(user.name, cost))

            await self.bot.say(msg)
            response = await self.bot.wait_for_message(timeout=15, author=author)

            if response is None:
                await self.bot.say("You took too long. Cancelling transaction.")
                return

            if response.content.title() == "Yes":
                msg = ("Congratulations {} you are free! Enjoy your freedom while it "
                       "lasts...".format(user.name))
                self.subtract_costs(settings, author, cost)
                print("Author ID :{}\nUser ID :{}".format(author.id, user.id))
                settings["Players"][user.id]["Status"] = "Free"
                settings["Players"][user.id]["OOB"] = True
                dataIO.save_json(self.file_path, self.system)
            elif response.content.title() == "No":
                msg = "Cancelling transaction."
            else:
                msg = "Incorrect response, cancelling transaction."
            await self.bot.say(msg)

    @heist.command(name="createbank", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _bankadd_heist(self, ctx):
        """Add a bank to heist"""

        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        cancel = ctx.prefix + "cancel"
        check = lambda m: m.content.isdigit() and int(m.content) > 0 or m.content == cancel
        start = ("This will walkthrough the bank creation process. You may cancel this process at "
                 "anytime by typing {}cancel. Let's begin with the first question.\nWhat is the "
                 "name of this bank?".format(ctx.prefix))

        await self.bot.say(start)
        name = await self.bot.wait_for_message(timeout=35, author=author)

        if name is None:
            await self.bot.say("You took too long. Cancelling bank creation.")
            return

        if name.content == cancel:
            await self.bot.say("Bank creation cancelled.")
            return

        if name.content.title() in list(settings["Banks"].keys()):
            await self.bot.say("A bank with that name already exists. Cancelling bank creation.")
            return

        await self.bot.say("What is the max crew size for this bank? Cannot be the same as other "
                           "banks.")
        crew = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if crew is None:
            await self.bot.say("You took too long. Cancelling bank creation.")
            return

        if crew.content == cancel:
            await self.bot.say("Bank creation cancelled.")
            return

        if int(crew.content) + 1 in [subdict["Crew"] for subdict in settings["Banks"].values()]:
            await self.bot.say("Crew size conflicts with another bank. Cancelling bank creation.")
            return

        await self.bot.say("How many starting credits are in the vault of this bank?")
        vault = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if vault is None:
            await self.bot.say("You took too long. Cancelling bank creation.")
            return

        if vault.content == cancel:
            await self.bot.say("Bank creation cancelled.")
            return

        await self.bot.say("What is the maximum number of credits this bank can hold?")
        vault_max = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if vault_max is None:
            await self.bot.say("You took too long. Cancelling bank creation.")
            return

        if vault_max.content == cancel:
            await self.bot.say("Bank creation cancelled.")
            return

        await self.bot.say("What is the individual chance of success for this bank? 1-100")
        check = lambda m: m.content.isdigit() and 0 < int(m.content) <= 100 or m.content == cancel
        success = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if success is None:
            await self.bot.say("You took too long. Cancelling bank creation.")
            return

        if success.content == cancel:
            await self.bot.say("Bank creation cancelled.")
            return
        else:
            msg = ("Bank Created.\n```Name:       {}\nCrew:       {}\nVault:      {}\nVault Max:  "
                   "{}\nSuccess:    {}%```".format(name.content.title(), crew.content,
                                                   vault.content, vault_max.content,
                                                   success.content)
                   )
            bank_fmt = {"Crew": int(crew.content) + 1, "Vault": int(vault.content),
                        "Vault Max": int(vault_max.content), "Success": int(success.content)}
            settings["Banks"][name.content.title()] = bank_fmt
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say(msg)

    @heist.command(name="remove", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _remove_heist(self, ctx, *, bank: str):
        """Remove a bank from the heist list"""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if bank.title() in settings["Banks"].keys():
            await self.bot.say("Are you sure you want to remove {} from the list of "
                               "banks?".format(bank.title()))
            response = await self.bot.wait_for_message(timeout=15, author=author)
            if response is None:
                msg = "Cancelling removal. You took too long."
            elif response.content.title() == "Yes":
                settings["Banks"].pop(bank.title())
                dataIO.save_json(self.file_path, self.system)
                msg = "{} was removed from the list of banks.".format(bank.title())
            else:
                msg = "Cancelling bank removal."
        else:
            msg = "That bank does not exist."
        await self.bot.say(msg)

    @heist.command(name="info", pass_context=True)
    async def _info_heist(self, ctx):
        """Shows the Heist settings for this server."""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if settings["Config"]["Hardcore"]:
            hardcore = "ON"
        else:
            hardcore = "OFF"
        wait = settings["Config"]["Wait Time"]
        heist_cost = settings["Config"]["Heist Cost"]
        bail = settings["Config"]["Bail Base"]
        police = settings["Config"]["Police Alert"]
        sentence = settings["Config"]["Sentence Base"]
        death = settings["Config"]["Death Timer"]
        timers = list(map(self.time_format, [wait, police, sentence, death]))
        description = "{} Heist Settings".format(server.name)
        footer = "Heist was developed by Redjumpman for Red Bot."

        embed = discord.Embed(colour=0x0066FF, description=description)
        embed.title = "Heist Version {}".format(self.version)
        embed.add_field(name="Heist Cost", value=heist_cost)
        embed.add_field(name="Base Bail Cost", value=bail)
        embed.add_field(name="Crew Gather Time", value=timers[0])
        embed.add_field(name="Police Timer", value=timers[1])
        embed.add_field(name="Base Jail Sentence", value=timers[2])
        embed.add_field(name="Death Timer", value=timers[3])
        embed.add_field(name="Hardcore Mode", value=hardcore)
        embed.set_footer(text=footer)

        await self.bot.say(embed=embed)

    @heist.command(name="release", pass_context=True)
    async def _release_heist(self, ctx):
        """Removes you from jail or clears bail status if sentence served."""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        player_time = settings["Players"][author.id]["Time Served"]
        base_time = settings["Players"][author.id]["Sentence"]
        OOB = settings["Players"][author.id]["OOB"]

        if settings["Players"][author.id]["Status"] == "Apprehended" or OOB:
            remaining = self.cooldown_calculator(settings, player_time, base_time)
            if remaining:
                msg = ("You still have time on your sentence. You still need to wait:\n"
                       "```{}```".format(remaining))
            else:
                msg = "You served your time. Enjoy the fresh air of freedom while you can."
                if OOB:
                    msg = "Hmmm. I guess your free of all charges. But I'll be watching you!"
                    settings["Players"][author.id]["OOB"] = False
                settings["Players"][author.id]["Sentence"] = 0
                settings["Players"][author.id]["Time Served"] = 0
                settings["Players"][author.id]["Status"] = "Free"
                dataIO.save_json(self.file_path, self.system)
        else:
            msg = "I can't remove you from jail if your not *in* jail."
        await self.bot.say(msg)

    @heist.command(name="revive", pass_context=True)
    async def _revive_heist(self, ctx):
        """Revive from the dead!"""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.account_check(settings, author)
        player_time = settings["Players"][author.id]["Death Timer"]
        base_time = settings["Config"]["Death Timer"]

        if settings["Players"][author.id]["Status"] == "Dead":
            remainder = self.cooldown_calculator(settings, player_time, base_time)
            if not remainder:
                settings["Players"][author.id]["Death Timer"] = 0
                settings["Players"][author.id]["Status"] = "Free"
                dataIO.save_json(self.file_path, self.system)
                msg = "You have risen from the dead!"
            else:
                msg = ("You can't revive yet. You still need to wait:\n"
                       "```{}```".format(remainder))
        else:
            msg = "You still have a pulse. I can't revive someone who isn't dead."
        await self.bot.say(msg)

    @heist.command(name="stats", pass_context=True)
    async def _stats_heist(self, ctx):
        """Shows your Heist stats"""
        author = ctx.message.author
        server = ctx.message.server
        avatar = ctx.message.author.avatar_url
        settings = self.check_server_settings(server)
        self.account_check(settings, author)

        status = settings["Players"][author.id]["Status"]
        sentence = settings["Players"][author.id]["Sentence"]
        time_served = settings["Players"][author.id]["Time Served"]
        jail_fmt = self.cooldown_calculator(settings, time_served, sentence)
        bail = settings["Players"][author.id]["Bail Cost"]
        jail_counter = settings["Players"][author.id]["Jail Counter"]
        death_timer = settings["Players"][author.id]["Death Timer"]
        base_death_timer = settings["Config"]["Death Timer"]
        death_fmt = self.cooldown_calculator(settings, death_timer, base_death_timer)
        spree = settings["Players"][author.id]["Spree"]
        probation = settings["Players"][author.id]["OOB"]
        total_deaths = settings["Players"][author.id]["Deaths"]
        total_jail = settings["Players"][author.id]["Total Jail"]
        level = settings["Players"][author.id]["Criminal Level"]
        rank = self.criminal_level(level)

        embed = discord.Embed(colour=0x0066FF, description=rank)
        embed.title = author.name
        embed.set_thumbnail(url=avatar)
        embed.add_field(name="Status", value=status)
        embed.add_field(name="Spree", value=spree)
        embed.add_field(name="Cost of Bail", value=bail)
        embed.add_field(name="Out on Bail", value=probation)
        embed.add_field(name="Jail Sentence", value=jail_fmt)
        embed.add_field(name="Apprehended", value=jail_counter)
        embed.add_field(name="Death Timer", value=death_fmt)
        embed.add_field(name="Total Deaths", value=total_deaths)
        embed.add_field(name="Lifetime Apprehensions", value=total_jail)

        await self.bot.say(embed=embed)

    @heist.command(name="play", pass_context=True)
    async def _play_heist(self, ctx):
        """This begins a Heist"""
        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        cost = settings["Config"]["Heist Cost"]
        wait_time = settings["Config"]["Wait Time"]
        prefix = ctx.prefix
        self.account_check(settings, author)
        outcome, msg = self.requirement_check(settings, prefix, author, cost)

        if not outcome:
            await self.bot.say(msg)
        elif not settings["Config"]["Heist Planned"]:
            self.subtract_costs(settings, author, cost)
            settings["Config"]["Heist Planned"] = True
            settings["Crew"][author.id] = {}
            await self.bot.say("A heist is being planned by {}\nThe heist "
                               "begin in {} seconds. Type {}heist play to join"
                               " their crew.".format(author.name, wait_time, ctx.prefix))
            await asyncio.sleep(wait_time)
            if len(settings["Crew"].keys()) <= 1:
                await self.bot.say("You tried to rally a crew, but no one "
                                   "wanted to follow you. The heist has been "
                                   "cancelled.")
                self.reset_heist(settings)
            else:
                crew = len(settings["Crew"])
                target = self.heist_target(settings, crew)
                good_out = good[:]
                bad_out = bad[:]
                settings["Config"]["Heist Start"] = True
                players = [server.get_member(x) for x in list(settings["Crew"])]
                results = self.game_outcomes(settings, good_out, bad_out, players, target)
                await self.bot.say("Lock and load. The heist is starting\nThe crew has decided "
                                   "to hit **{}**.".format(target))
                await asyncio.sleep(3)
                await self.show_results(settings, server, results, target)
                if settings["Crew"]:
                    players = [server.get_member(x) for x in list(settings["Crew"])]
                    data = self.calculate_credits(settings, players, target)
                    headers = ["Criminals", "Credits Stolen", "Bonuses", "Total"]
                    t = tabulate(data, headers=headers)
                    msg = ("The credits stolen from the vault was split among the winners:\n```"
                           "Python\n{}```".format(t))
                else:
                    msg = "No one made it out safe. The good guys win."
                await self.bot.say(msg)
                settings["Config"]["Alert"] = int(time.perf_counter())
                self.reset_heist(settings)
                dataIO.save_json(self.file_path, self.system)
        else:
            self.subtract_costs(settings, author, cost)
            settings["Crew"][author.id] = {}
            crew_size = len(settings["Crew"])
            await self.bot.say("{} has joined the crew.\nThe crew now has {} "
                               "members.".format(author.name, crew_size))

    @commands.group(pass_context=True, no_pm=True)
    async def setheist(self, ctx):
        """Set different options in the heist config"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setheist.command(name="sentence", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _sentence_setheist(self, ctx, seconds: int):
        """Set the base jail time when caught"""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if seconds > 0:
            settings["Config"]["Sentence Base"] = seconds
            dataIO.save_json(self.file_path, self.system)
            time_fmt = self.time_format(seconds)
            msg = "Setting base jail sentence to {}.".format(time_fmt)
        else:
            msg = "Need a number higher than 0."
        await self.bot.say(msg)

    @setheist.command(name="cost", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _cost_setheist(self, ctx, cost: int):
        """Set the cost to play heist"""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if cost >= 0:
            settings["Config"]["Heist Cost"] = cost
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting heist cost to {}.".format(cost)
        else:
            msg = "Need a number higher than -1."
        await self.bot.say(msg)

    @setheist.command(name="police", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _police_setheist(self, ctx, seconds: int):
        """Set the time police will prevent heists"""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if seconds > 0:
            settings["Config"]["Police Alert"] = seconds
            dataIO.save_json(self.file_path, self.system)
            time_fmt = self.time_format(seconds)
            msg = "Setting police alert to {}.".format(time_fmt)
        else:
            msg = "Need a number higher than 0."
        await self.bot.say(msg)

    @setheist.command(name="bail", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _bail_setheist(self, ctx, cost: int):
        """Set the base cost of bail"""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if cost >= 0:
            settings["Config"]["Bail Cost"] = cost
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting base bail cost to {}.".format(cost)
        else:
            msg = "Need a number higher than -1."
        await self.bot.say(msg)

    @setheist.command(name="death", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _death_setheist(self, ctx, seconds: int):
        """Set how long players are dead"""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if seconds > 0:
            settings["Config"]["Death Timer"] = seconds
            dataIO.save_json(self.file_path, self.system)
            time_fmt = self.time_format(seconds)
            msg = "Setting death timer to {}.".format(time_fmt)
        else:
            msg = "Need a number higher than 0."
        await self.bot.say(msg)

    @setheist.command(name="hardcore", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _hardcore_setheist(self, ctx):
        """Set game to hardcore mode. Deaths will wipe credits and chips."""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if settings["Config"]["Hardcore"]:
            settings["Config"]["Hardcore"] = False
            msg = "Hardcore mode now OFF."
        else:
            settings["Config"]["Hardcore"] = True
            msg = "Hardcore mode now ON! **Warning** death will result in credit **and chip wipe**."
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say(msg)

    @setheist.command(name="wait", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _wait_setheist(self, ctx, seconds: int):
        """Set how long a player can gather crew"""
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if seconds > 0:
            settings["Config"]["Wait Time"] = seconds
            dataIO.save_json(self.file_path, self.system)
            time_fmt = self.time_format(seconds)
            msg = "Setting crew gather time to {}.".format(time_fmt)
        else:
            msg = "Need a number higher than 0."
        await self.bot.say(msg)

    async def show_results(self, settings, server, results, target):
        for result in results:
            await self.bot.say(result)
            await asyncio.sleep(5)
        await self.bot.say("The Heist is now over. Give me a moment to count your credits.")
        await asyncio.sleep(5)

    async def vault_updater(self):
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(15)  # Start-up Time
            while True:
                servers = [x.id for x in self.bot.servers if x.id in self.system["Servers"].keys()]
                for serverid in servers:
                    for bank in list(self.system["Servers"][serverid]["Banks"].keys()):
                        vault = self.system["Servers"][serverid]["Banks"][bank]["Vault"]
                        vault_max = self.system["Servers"][serverid]["Banks"][bank]["Vault Max"]
                        if vault < vault_max:
                            increment = min(vault + 45, vault_max)
                            self.system["Servers"][serverid]["Banks"][bank]["Vault"] = increment
                        else:
                            pass
                dataIO.save_json(self.file_path, self.system)
                await asyncio.sleep(120)  # task runs every 120 seconds
        except asyncio.CancelledError:
            pass

    def __unload(self):
        self.cycle_task.cancel()
        self.shutdown_save()
        dataIO.save_json(self.file_path, self.system)

    def calculate_credits(self, settings, players, target):
        names = [player.name for player in players]
        bonuses = [subdict["Bonus"] for subdict in settings["Crew"].values()]
        vault = settings["Banks"][target]["Vault"]
        credits_stolen = int(vault * 0.75 / len(settings["Crew"].keys()))
        stolen_data = [credits_stolen] * len(settings["Crew"].keys())
        total_winnings = [x + y for x, y in zip(stolen_data, bonuses)]
        settings["Banks"][target]["Vault"] -= credits_stolen
        credit_data = list(zip(names, stolen_data, bonuses, total_winnings))
        deposits = list(zip(players, total_winnings))
        self.award_credits(deposits)
        return credit_data

    def game_outcomes(self, settings, good_out, bad_out, players, target):
        success_rate = settings["Banks"][target]["Success"]
        results = []
        for player in players:
            chance = random.randint(1, 100)
            if chance <= success_rate:
                good_thing = random.choice(good_out)
                good_out.remove(good_thing)
                settings["Crew"][player.id] = {"Name": player.name, "Bonus": good_thing[1]}
                settings["Players"][player.id]["Spree"] += 1
                results.append(good_thing[0].format(player.name))
            else:
                bad_thing = random.choice(bad_out)
                dropout_msg = bad_thing[0] + "```\n{0} dropped out of the game.```"
                self.failure_handler(settings, player, bad_thing[1])
                settings["Crew"].pop(player.id)
                bad_out.remove(bad_thing)
                results.append(dropout_msg.format(player.name))
        dataIO.save_json(self.file_path, self.system)
        return results

    def hardcore_handler(self, settings, user):
        bank = self.bot.get_cog('Economy').bank
        balance = bank.get_balance(user)
        bank.withdraw_credits(user, balance)
        try:
            casino = self.bot.get_cog('Casino')
            chip_balance = casino.chip_balance(user)
            casino.withdraw_chips(user, chip_balance)
        except AttributeError:
            print("Casino cog was not loaded or you are running an older version, "
                  "thus chips were not removed.")

    def failure_handler(self, settings, user, status):
        settings["Players"][user.id]["Spree"] = 0

        if status == "Apprehended":
            settings["Players"][user.id]["Jail Counter"] += 1
            bail_base = settings["Config"]["Bail Base"]
            offenses = settings["Players"][user.id]["Jail Counter"]
            sentence_base = settings["Config"]["Bail Base"]

            sentence = sentence_base * offenses
            bail = bail_base * offenses
            if settings["Players"][user.id]["OOB"]:
                bail = bail * 3

            settings["Players"][user.id]["Status"] = "Apprehended"
            settings["Players"][user.id]["Bail Cost"] = bail
            settings["Players"][user.id]["Sentence"] = sentence
            settings["Players"][user.id]["Time Served"] = int(time.perf_counter())
            settings["Players"][user.id]["OOB"] = False
            settings["Players"][user.id]["Total Jail"] += 1
            settings["Players"][user.id]["Criminal Level"] += 1
        else:
            self.run_death(settings, user)

    def heist_target(self, settings, crew):
        groups = sorted([(x, y["Crew"]) for x, y in settings["Banks"].items()], key=itemgetter(1))
        crew_sizes = [x[1] for x in groups]
        breakpoints = [x for x in crew_sizes if x != max(crew_sizes)]
        banks = [x[0] for x in groups]
        return banks[bisect(breakpoints, crew)]

    def run_death(self, settings, user):
        settings["Players"][user.id]["Criminal Level"] = 0
        settings["Players"][user.id]["OOB"] = False
        settings["Players"][user.id]["Bail Cost"] = 0
        settings["Players"][user.id]["Sentence"] = 0
        settings["Players"][user.id]["Status"] = "Dead"
        settings["Players"][user.id]["Deaths"] += 1
        settings["Players"][user.id]["Jail Counter"] = 0
        settings["Players"][user.id]["Death Timer"] = int(time.perf_counter())
        if settings["Config"]["Hardcore"]:
            self.hardcore_handler(settings, user)

    def user_clear(self, settings, user):
        settings["Players"][user.id]["Status"] = "Free"
        settings["Players"][user.id]["Criminal Level"] = 0
        settings["Players"][user.id]["Jail Counter"] = 0
        settings["Players"][user.id]["Death Timer"] = 0
        settings["Players"][user.id]["Bail Cost"] = 0
        settings["Players"][user.id]["Sentence"] = 0
        settings["Players"][user.id]["Time Served"] = 0
        settings["Players"][user.id]["OOB"] = False
        dataIO.save_json(self.file_path, self.system)

    def reset_heist(self, settings):
        settings["Crew"] = {}
        settings["Config"]["Heist Planned"] = False
        settings["Config"]["Heist Start"] = False
        dataIO.save_json(self.file_path, self.system)

    def award_credits(self, deposits):
        for player in deposits:
            bank = self.bot.get_cog('Economy').bank
            bank.deposit_credits(player[0], player[1])

    def subtract_costs(self, settings, author, cost):
        bank = self.bot.get_cog('Economy').bank
        bank.withdraw_credits(author, cost)

    def requirement_check(self, settings, prefix, author, cost):
        (alert, remaining) = self.police_alert(settings)
        if not list(settings["Banks"]):
            msg = ("Oh no! There are no banks! To start creating a bank, use "
                   "{}heist createbank.".format(prefix))
            return None, msg
        elif settings["Config"]["Heist Start"]:
            msg = ("A heist is already underway. Wait for the current one to "
                   "end to plan another heist.")
            return None, msg
        elif author.id in settings["Crew"]:
            msg = "You are already in the crew."
            return None, msg
        elif settings["Players"][author.id]["Status"] == "Apprehended":
            bail = settings["Players"][author.id]["Bail Cost"]
            sentence_raw = settings["Players"][author.id]["Sentence"]
            time_served = settings["Players"][author.id]["Time Served"]
            remaining = self.cooldown_calculator(settings, sentence_raw, time_served)
            sentence = self.time_format(sentence_raw)
            if remaining:
                msg = ("You are in jail. You are serving a sentence of {}.\nYou can wait out your "
                       "remaining sentence of: {} or pay {} credits to post "
                       "bail.".format(sentence, remaining, bail))
            else:
                msg = ("You have finished serving your sentence, but your still in jail! Get the "
                       "warden to sign your release by typing {}heist release .".format(prefix))
            return None, msg
        elif settings["Players"][author.id]["Status"] == "Dead":
            death_time = settings["Players"][author.id]["Death Timer"]
            base_timer = settings["Config"]["Death Timer"]
            remaining = self.cooldown_calculator(settings, death_time, base_timer)
            if remaining:
                msg = ("You are dead. You can revive in:\n{}\nUse the command {}heist revive when "
                       "the timer has expired.".format(remaining, prefix))
            else:
                msg = ("Looks like you are still dead, but you can revive at anytime by using the "
                       "command {}heist revive .".format(prefix))
            return None, msg
        elif not self.bank_check(settings, author, cost):
            msg = ("You do not have enough credits to cover the costs of "
                   "entry. You need {} credits to participate.".format(cost))
            return None, msg
        elif not (alert):
            msg = ("The police is on high alert after the last job. We should "
                   "wait for things to cool off before hitting another bank.\n"
                   "Time Remaning: {}".format(remaining))
            return None, msg
        else:
            return "True", ""

    def police_alert(self, settings):
        police_time = settings["Config"]["Police Alert"]
        alert_time = settings["Config"]["Alert Time"]
        if settings["Config"]["Alert Time"] == 0:
            return "True", None
        elif abs(alert_time - int(time.perf_counter())) >= police_time:
            settings["Config"]["Alert Time"] == 0
            dataIO.save_json(self.file_path, self.system)
            return "True", None
        else:
            s = abs(alert_time - int(time.perf_counter()))
            seconds = abs(s - police_time)
            amount = self.time_format(seconds)
            return None, amount

    def shutdown_save(self):
        for server in self.system["Servers"]:
            death_time = self.system["Servers"][server]["Config"]["Death Timer"]
            for player in self.system["Servers"][server]["Players"]:
                player_death = self.system["Servers"][server]["Players"][player]["Death Timer"]
                player_sentence = self.system["Servers"][server]["Players"][player]["Time Served"]
                sentence = self.system["Servers"][server]["Players"][player]["Sentence"]

                if player_death > 0:
                    s = abs(player_death - int(time.perf_counter()))
                    seconds = abs(s - death_time)
                    self.system["Servers"][server]["Players"][player]["Death Timer"] = seconds

                if player_sentence > 0:
                    s = abs(player_sentence - int(time.perf_counter()))
                    seconds = abs(s - sentence)
                    self.system["Servers"][server]["Players"][player]["Time Served"] = seconds

    def cooldown_calculator(self, settings, player_time, base_time):
        if abs(player_time - int(time.perf_counter())) >= base_time:
            return None
        else:
            s = abs(player_time - int(time.perf_counter()))
            seconds = abs(s - base_time)
            time_remaining = self.time_format(seconds)
            return time_remaining

    def time_format(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        data = PluralDict({'hour': h, 'minute': m, 'second': s})
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
            msg = "No cooldown"
        return msg

    def bank_check(self, settings, user, amount):
        bank = self.bot.get_cog('Economy').bank
        amount = settings["Config"]["Heist Cost"]
        if bank.account_exists(user):
            if bank.can_spend(user, amount):
                return True
            else:
                return False
        else:
            return False

    def criminal_level(self, level):
        status = ["Innocent", "Bank Robber", "Notorious", "Serial", "Most Wanted",
                  "Criminal Mastermind"]
        breakpoints = [1, 10, 25, 50, 100]
        return status[bisect(breakpoints, level)]

    def account_check(self, settings, author):
        if author.id not in settings["Players"]:
            criminal = {"Name": author.name, "Status": "Free", "Sentence": 0, "Time Served": 0,
                        "Death Timer": 0, "OOB": False, "Bail Cost": 0, "Jail Counter": 0,
                        "Spree": 0, "Criminal Level": 0, "Total Jail": 0, "Deaths": 0}
            settings["Players"][author.id] = criminal
            dataIO.save_json(self.file_path, self.system)
        else:
            pass

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            default = {"Config": {"Heist Start": False, "Heist Planned": False, "Heist Cost": 100,
                                  "Wait Time": 20, "Hardcore": False, "Police Alert": 60,
                                  "Alert Time": 0, "Sentence Base": 600, "Bail Base": 500,
                                  "Death Timer": 86400},
                       "Players": {},
                       "Crew": {},
                       "Banks": {},
                       }
            self.system["Servers"][server.id] = default
            dataIO.save_json(self.file_path, self.system)
            print("Creating Heist settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path

    # =========== Commission hooks =====================

    def reaper_hook(self, server, author, user):
        settings = self.check_server_settings(server)
        self.account_check(settings, user)
        if settings["Players"][user.id]["Status"] == "Dead":
            msg = "Cast failed. {} is dead.".format(user.name)
            action = None
        else:
            self.run_death(settings, user)
            dataIO.save_json(self.file_path, self.system)
            msg = ("{} casted :skull: `death` :skull: on {} and sent them "
                   "to the graveyard.".format(author.name, user.name))
            action = "True"
        return action, msg

    def cleric_hook(self, server, author, user):
        settings = self.check_server_settings(server)
        self.account_check(settings, user)
        if settings["Players"][user.id]["Status"] == "Dead":
            settings["Players"][user.id]["Death Timer"] = 0
            settings["Players"][user.id]["Status"] = "Free"
            dataIO.save_json(self.file_path, self.system)
            msg = ("{} casted :trident: `resurrection` :trident: on {} and returned them "
                   "to the living.".format(author.name, user.name))
            action = "True"
        else:
            msg = "Cast failed. {} is alive.".format(user.name)
            action = None
        return action, msg


def check_folders():
    if not os.path.exists("data/JumperCogs/heist"):
        print("Creating data/JumperCogs/heist folder...")
        os.makedirs("data/JumperCogs/heist")


def check_files():
    default = {"Servers": {}}

    f = "data/JumperCogs/heist/heist.json"
    if not dataIO.is_valid_json(f):
        print("Creating default heist.json...")
        dataIO.save_json(f, default)


def setup(bot):
    check_folders()
    check_files()
    n = Heist(bot)
    if tabulateAvailable:
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate' in command prompt.")
