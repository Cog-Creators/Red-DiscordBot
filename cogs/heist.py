#  Heist was created by Redjumpman for Redbot

# Standard Library
import asyncio
import bisect
import os
import random
import string
import time
from ast import literal_eval
from operator import itemgetter

# Discord / Red Bot
import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help

# Third party library requirement
from tabulate import tabulate


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
    """Heist system inspired by Deepbot"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/heist/heist.json"
        self.system = dataIO.load_json(self.file_path)
        self.version = "2.4.01"
        self.patch = 2.41
        self.cycle_task = bot.loop.create_task(self.vault_updater())

    @commands.group(pass_context=True, no_pm=True)
    async def heist(self, ctx):
        """General heist related commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @heist.command(name="themes", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _themelist_heist(self):
        """Lists available themes for heist."""
        themes = [os.path.join(x).replace('.txt', '')
                  for x in os.listdir("data/heist/") if x.endswith(".txt")]
        if len(themes) > 30:
            themes = themes[:30]
        await self.bot.say("Available Themes:```\n{}```".format('\n'.join(themes)))

    @heist.command(name="reset", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reset_heist(self, ctx):
        """Resets heist in case it hangs"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        self.reset_heist(settings)
        await self.bot.say("```Heist has been reset```")

    @heist.command(name="clear", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clear_heist(self, ctx, user: discord.Member):
        """Clears a member of jail and death statuses."""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        self.user_clear(settings, user)
        await self.bot.say("```{} administratively cleared {}```".format(author.name, user.name))

    @heist.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_heist(self):
        """Shows the version of heist you are running"""
        await self.bot.say("You are running Heist version {}.".format(self.version))

    @heist.command(name="targets", pass_context=True)
    async def _targets_heist(self, ctx):
        """Shows a list of targets"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        t_vault = settings["Theme"]["Vault"]

        if len(settings["Targets"].keys()) < 0:
            msg = ("There aren't any targets! To create a target use {}heist "
                   "createtarget .".format(ctx.prefix))
        else:
            target_names = [x for x in settings["Targets"]]
            crews = [int(subdict["Crew"]) for subdict in settings["Targets"].values()]
            success = [str(subdict["Success"]) + "%" for subdict in settings["Targets"].values()]
            vaults = [subdict["Vault"] for subdict in settings["Targets"].values()]
            data = list(zip(target_names, crews, vaults, success))
            table_data = sorted(data, key=itemgetter(1), reverse=True)
            table = tabulate(table_data, headers=["Target", "Max Crew", t_vault, "Success Rate"])
            msg = "```C\n{}```".format(table)

        await self.bot.say(msg)

    @heist.command(name="bailout", pass_context=True)
    async def _bailout_heist(self, ctx, user: discord.Member=None):
        """Specify who you want to pay for release. Defaults to you."""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)

        t_bail = settings["Theme"]["Bail"]
        t_sentence = settings["Theme"]["Sentence"]
        self.account_check(settings, author)

        if user is None:
            player = author
        else:
            self.account_check(settings, user)
            player = user

        if settings["Players"][player.id]["Status"] != "Apprehended":
            return await self.bot.say("{} is not in jail.".format(player.name))

        cost = settings["Players"][player.id]["Bail Cost"]
        if not self.bank_check(settings, author):
            await self.bot.say("You do not have enough to afford the {} amount.".format(t_bail))
            return

        if player.id == author.id:
            msg = ("Do you want to make a {0} amount? It will cost {1} credits. If you are "
                   "caught again, your next {2} and {0} amount will triple. "
                   "Do you still wish to pay the {0} amount?".format(t_bail, cost, t_sentence))
        else:
            msg = ("You are about pay a {2} amount for {0} and it will cost you {1} credits. "
                   "Are you sure you wish to pay {1} for {0}?".format(player.name, cost, t_bail))

        await self.bot.say(msg)
        response = await self.bot.wait_for_message(timeout=15, author=author)

        if response is None:
            await self.bot.say("You took too long. canceling transaction.")
            return

        if response.content.title() == "Yes":
            msg = ("Congratulations {}, you are free! Enjoy your freedom while it "
                   "lasts...".format(player.name))
            self.subtract_costs(author, cost)
            settings["Players"][player.id]["Status"] = "Free"
            settings["Players"][player.id]["OOB"] = True
            self.save_system()
        elif response.content.title() == "No":
            msg = "Canceling transaction."
        else:
            msg = "Incorrect response, canceling transaction."

        await self.bot.say(msg)

    @heist.command(name="createtarget", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _targetadd_heist(self, ctx):
        """Add a target to heist"""

        author = ctx.message.author
        server = ctx.message.server
        settings = self.check_server_settings(server)
        cancel = ctx.prefix + "cancel"
        check = lambda m: m.content.isdigit() and int(m.content) > 0 or m.content == cancel
        start = ("This will walk-through the target creation process. You may cancel this process "
                 "at anytime by typing {}cancel. Let's begin with the first question.\nWhat is the "
                 "name of this target?".format(ctx.prefix))

        await self.bot.say(start)
        name = await self.bot.wait_for_message(timeout=35, author=author)

        if name is None:
            await self.bot.say("You took too long. canceling target creation.")
            return

        if name.content == cancel:
            await self.bot.say("Target creation cancelled.")
            return

        if string.capwords(name.content) in settings["Targets"]:
            await self.bot.say("A target with that name already exists. canceling target "
                               "creation.")
            return

        await self.bot.say("What is the max crew size for this target? Cannot be the same as "
                           "other targets.\n*Crews over this size will go to the next "
                           "largest bank.*")
        crew = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if crew is None:
            await self.bot.say("You took too long. canceling target creation.")
            return

        if crew.content == cancel:
            await self.bot.say("Target creation cancelled.")
            return

        if int(crew.content) in [subdict["Crew"] for subdict in settings["Targets"].values()]:
            await self.bot.say("Group size conflicts with another target. Canceling target "
                               "creation.")
            return

        await self.bot.say("How many starting credits does this target have?")
        vault = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if vault is None:
            await self.bot.say("You took too long. canceling target creation.")
            return

        if vault.content == cancel:
            await self.bot.say("Target creation cancelled.")
            return

        await self.bot.say("What is the maximum number of credits this target can hold?")
        vault_max = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if vault_max is None:
            await self.bot.say("You took too long. canceling target creation.")
            return

        if vault_max.content == cancel:
            await self.bot.say("Target creation cancelled.")
            return

        await self.bot.say("What is the individual chance of success for this target? 1-100")
        check = lambda m: m.content.isdigit() and 0 < int(m.content) <= 100 or m.content == cancel
        success = await self.bot.wait_for_message(timeout=35, author=author, check=check)

        if success is None:
            await self.bot.say("You took too long. canceling target creation.")
            return

        if success.content == cancel:
            await self.bot.say("Target creation cancelled.")
            return
        else:
            msg = ("Target Created.\n```Name:       {}\nGroup:      {}\nVault:      {}\nVault Max: "
                   " {}\nSuccess:    {}%```".format(string.capwords(name.content), crew.content,
                                                    vault.content, vault_max.content,
                                                    success.content)
                   )
            target_fmt = {"Crew": int(crew.content), "Vault": int(vault.content),
                          "Vault Max": int(vault_max.content), "Success": int(success.content)}
            settings["Targets"][string.capwords(name.content)] = target_fmt
            self.save_system()
            await self.bot.say(msg)

    @heist.command(name="edittarget", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _edittarget_heist(self, ctx, *, target: str):
        """Edits a heist target"""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        target = string.capwords(target)

        if target not in settings["Targets"]:
            return await self.bot.say("That target does not exist.")

        keys = [x for x in settings["Targets"][target]]
        keys.append("Name")
        check = lambda m: m.content.title() in keys

        await self.bot.say("Which property of {} would you like to edit?\n"
                           "{}".format(target, ", ".join(keys)))

        response = await self.bot.wait_for_message(timeout=15, author=author, check=check)

        if response is None:
            return await self.bot.say("Canceling removal. You took too long.")

        if response.content.title() == "Name":
            await self.bot.say("What would you like to rename the target to?\n*Cannot be a name "
                               "currently in use.*")
            check2 = lambda m: string.capwords(m.content) not in settings["Targets"]

        elif response.content.title() in ["Vault", "Vault Max"]:
            await self.bot.say("What would you like to set the {} "
                               "to?".format(response.content.title()))
            check2 = lambda m: m.content.isdigit() and int(m.content) > 0

        elif response.content.title() == "Success":
            await self.bot.say("What would you like to change the success rate to?")
            check2 = lambda m: m.content.isdigit() and 0 < int(m.content) <= 100

        elif response.content.title() == "Crew":
            await self.bot.say("What would you like to change the max crew size to?\n Cannot be "
                               "the same as another target and will be the maximum number of "
                               "players for that target.")
            crew_sizes = [subdict["Crew"] for subdict in settings["Targets"].values()]
            check2 = lambda m: m.content.isdigit() and int(m.content) not in crew_sizes

        choice = await self.bot.wait_for_message(timeout=15, author=author, check=check2)

        if choice is None:
            return await self.bot.say("Canceling removal. You took too long.")

        if response.content.title() == "Name":
            new_name = string.capwords(choice.content)
            settings["Targets"][new_name] = settings["Targets"].pop(target)
            self.save_system()
            await self.bot.say("Changed {}'s {} to {}.".format(target, response.content,
                                                               choice.content))
        else:
            settings["Targets"][target][response.content.title()] = int(choice.content)
            self.save_system()
            await self.bot.say("Changed {}'s {} to {}.".format(target, response.content,
                                                               choice.content))

    @heist.command(name="remove", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _remove_heist(self, ctx, *, target: str):
        """Remove a target from the heist list"""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        if string.capwords(target) in settings["Targets"]:
            await self.bot.say("Are you sure you want to remove {} from the list of "
                               "targets?".format(string.capwords(target)))
            response = await self.bot.wait_for_message(timeout=15, author=author)
            if response is None:
                msg = "Canceling removal. You took too long."
            elif response.content.title() == "Yes":
                settings["Targets"].pop(string.capwords(target))
                self.save_system()
                msg = "{} was removed from the list of targets.".format(string.capwords(target))
            else:
                msg = "Canceling target removal."
        else:
            msg = "That target does not exist."
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

        # Theme variables
        theme = settings["Config"]["Theme"]
        t_jail = settings["Theme"]["Jail"]
        t_sentence = settings["Theme"]["Sentence"]
        t_police = settings["Theme"]["Police"]
        t_bail = settings["Theme"]["Bail"]

        time_values = [settings["Config"]["Wait Time"], settings["Config"]["Police Alert"],
                       settings["Config"]["Sentence Base"], settings["Config"]["Death Timer"]]
        timers = list(map(self.time_format, time_values))
        description = ["Heist Version {}".format(self.version), "Theme: {}".format(theme)]
        footer = "Heist was developed by Redjumpman for Red Bot."

        embed = discord.Embed(colour=0x0066FF, description="\n".join(description))
        embed.title = "{} Heist Settings".format(server.name)
        embed.add_field(name="Heist Cost", value=settings["Config"]["Heist Cost"])
        embed.add_field(name="Base {} Cost".format(t_bail), value=settings["Config"]["Bail Base"])
        embed.add_field(name="Crew Gather Time", value=timers[0])
        embed.add_field(name="{} Timer".format(t_police), value=timers[1])
        embed.add_field(name="Base {} {}".format(t_jail, t_sentence), value=timers[2])
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
        oob = settings["Players"][author.id]["OOB"]

        # Theme variables
        t_jail = settings["Theme"]["Jail"]
        t_sentence = settings["Theme"]["Sentence"]

        if settings["Players"][author.id]["Status"] != "Apprehended" or oob:
            await self.bot.say("I can't remove you from {0} if you're not "
                               "*in* {0}.".format(t_jail))
            return

        remaining = self.cooldown_calculator(player_time, base_time)
        if remaining != "No Cooldown":
            await self.bot.say("You still have time on your {}. You still need to wait:\n"
                               "```{}```".format(t_sentence, remaining))
            return

        msg = ("You served your time. Enjoy the fresh air of freedom while you can.")

        if oob:
            msg = "You are no longer on probation! 3x penalty removed."
            settings["Players"][author.id]["OOB"] = False

        settings["Players"][author.id]["Sentence"] = 0
        settings["Players"][author.id]["Time Served"] = 0
        settings["Players"][author.id]["Status"] = "Free"
        self.save_system()

        await self.bot.say(msg)

    @heist.command(name="revive", pass_context=True)
    async def _revive_heist(self, ctx):
        """Revive from the dead!"""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        self.account_check(settings, author)
        player_time = settings["Players"][author.id]["Death Timer"]
        base_time = settings["Config"]["Death Timer"]

        if settings["Players"][author.id]["Status"] == "Dead":
            remainder = self.cooldown_calculator(player_time, base_time)
            if remainder == "No Cooldown":
                settings["Players"][author.id]["Death Timer"] = 0
                settings["Players"][author.id]["Status"] = "Free"
                self.save_system()
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
        avatar = ctx.message.author.avatar_url
        settings = self.check_server_settings(author.server)
        self.account_check(settings, author)
        path = settings["Players"][author.id]

        # Theme variables
        sentencing = "{} {}".format(settings["Theme"]["Jail"], settings["Theme"]["Sentence"])
        t_bail = "{} Cost".format(settings["Theme"]["Bail"])

        # Sentence Time Remaining
        sentence = path["Sentence"]
        time_served = path["Time Served"]
        jail_fmt = self.cooldown_calculator(time_served, sentence)

        # Death Time Remaining
        death_timer = path["Death Timer"]
        base_death_timer = settings["Config"]["Death Timer"]
        death_fmt = self.cooldown_calculator(death_timer, base_death_timer)

        rank = self.criminal_level(path["Criminal Level"])

        embed = discord.Embed(colour=0x0066FF, description=rank)
        embed.title = author.name
        embed.set_thumbnail(url=avatar)
        embed.add_field(name="Status", value=path["Status"])
        embed.add_field(name="Spree", value=path["Spree"])
        embed.add_field(name=t_bail, value=path["Bail Cost"])
        embed.add_field(name=settings["Theme"]["OOB"], value=path["OOB"])
        embed.add_field(name=sentencing, value=jail_fmt)
        embed.add_field(name="Apprehended", value=path["Jail Counter"])
        embed.add_field(name="Death Timer", value=death_fmt)
        embed.add_field(name="Total Deaths", value=path["Deaths"])
        embed.add_field(name="Lifetime Apprehensions", value=path["Total Jail"])

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

        # Theme Variables
        t_crew = settings["Theme"]["Crew"]
        t_heist = settings["Theme"]["Heist"]
        t_vault = settings["Theme"]["Vault"]

        self.account_check(settings, author)
        outcome, msg = self.requirement_check(settings, prefix, author, cost)

        if outcome == "Failed":
            return await self.bot.say(msg)

        if not settings["Config"]["Heist Planned"]:
            self.subtract_costs(author, cost)
            settings["Config"]["Heist Planned"] = True
            settings["Crew"][author.id] = {}
            await self.bot.say("A {4} is being planned by {0}\nThe {4} "
                               "will begin in {1} seconds. Type {2}heist play to join their "
                               "{3}.".format(author.name, wait_time, ctx.prefix, t_crew, t_heist))
            await asyncio.sleep(wait_time)

            if len(settings["Crew"]) <= 1:
                await self.bot.say("You tried to rally a {}, but no one wanted to follow you. The "
                                   "{} has been cancelled.".format(t_crew, t_heist))
                self.reset_heist(settings)
            else:
                await self.heist_game(settings, server, t_heist, t_crew, t_vault)

        else:
            self.subtract_costs(author, cost)
            settings["Crew"][author.id] = {}
            crew_size = len(settings["Crew"])
            await self.bot.say("{0} has joined the {2}.\nThe {2} now has {1} "
                               "members.".format(author.name, crew_size, t_crew))

    @commands.group(pass_context=True, no_pm=True)
    async def setheist(self, ctx):
        """Set different options in the heist config"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @heist.command(name="theme", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _theme_heist(self, ctx, theme):
        """Sets the theme for heist"""
        theme = theme.title()
        server = ctx.message.server
        settings = self.check_server_settings(server)

        if not os.path.exists("data/heist/{}.txt".format(theme)):
            themes = [os.path.join(x).replace('.txt', '')
                      for x in os.listdir("data/heist/") if x.endswith(".txt")]
            msg = ("I could not find a theme with that name. Available Themes:"
                   "```\n{}```".format('\n'.join(themes)))
        else:
            msg = self.theme_loader(settings, theme)

        await self.bot.say(msg)

    @setheist.command(name="output", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _output_setheist(self, ctx, output: str):
        """Change how detailed the starting output is.
        None: Displays just the number of crew members.

        Short: Displays five participants and truncates the rest.

        Long: Shows entire crew list. WARNING Not suitable for
              really big crews.
        """
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if output.title() not in ["None", "Short", "Long"]:
            return await self.bot.say("You must choose \'None\', \'Short\', or \'Long\'.")

        settings["Config"]["Crew Output"] = output.title()
        self.save_system()
        await self.bot.say("Now setting the message output type to {}.".format(output))

    def message_handler(self, settings, crew, players):
        message_type = settings["Config"]["Crew Output"]
        if message_type == "Short":
            name_list = '\n'.join(player.name for player in players[:5])
            message = "{} crew members, including:```\n{}```".format(crew, name_list)
        elif message_type == "Long":
            name_list = '\n'.join(player.name for player in players)
            message = "{} crew members, including:```\n{}```".format(crew, name_list)
        else:
            message = "{} crew members".format(crew)
        return message

    @setheist.command(name="sentence", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _sentence_setheist(self, ctx, seconds: int):
        """Set the base apprehension time when caught"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        t_jail = settings["Theme"]["Jail"]
        t_sentence = settings["Theme"]["Sentence"]

        if seconds > 0:
            settings["Config"]["Sentence Base"] = seconds
            self.save_system()
            time_fmt = self.time_format(seconds)
            msg = "Setting base {} {} to {}.".format(t_jail, t_sentence, time_fmt)
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
            self.save_system()
            msg = "Setting heist cost to {}.".format(cost)
        else:
            msg = "Need a number higher than -1."
        await self.bot.say(msg)

    @setheist.command(name="authorities", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _authorities_setheist(self, ctx, seconds: int):
        """Set the time authorities will prevent heists"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        t_police = settings["Theme"]["Police"]

        if seconds > 0:
            settings["Config"]["Police Alert"] = seconds
            self.save_system()
            time_fmt = self.time_format(seconds)
            msg = "Setting {} alert time to {}.".format(t_police, time_fmt)
        else:
            msg = "Need a number higher than 0."
        await self.bot.say(msg)

    @setheist.command(name="bail", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _bail_setheist(self, ctx, cost: int):
        """Set the base cost of bail"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        t_bail = settings["Theme"]["Bail"]
        if cost >= 0:
            settings["Config"]["Bail Base"] = cost
            msg = "Setting base {} cost to {}.".format(t_bail, cost)
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
            self.save_system()
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
        self.save_system()
        await self.bot.say(msg)

    @setheist.command(name="wait", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _wait_setheist(self, ctx, seconds: int):
        """Set how long a player can gather players"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        t_crew = settings["Theme"]["Crew"]

        if seconds > 0:
            settings["Config"]["Wait Time"] = seconds
            self.save_system()
            time_fmt = self.time_format(seconds)
            msg = "Setting {} gather time to {}.".format(t_crew, time_fmt)
        else:
            msg = "Need a number higher than 0."
        await self.bot.say(msg)

    async def show_results(self, settings, results):
        t_heist = settings["Theme"]["Heist"]
        for result in results:
            await self.bot.say(result)
            await asyncio.sleep(5)
        await self.bot.say("The {} is now over. Distributing player spoils...".format(t_heist))
        await asyncio.sleep(5)

    async def vault_updater(self):
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(20)  # Start-up Time
            while True:
                servers = [x.id for x in self.bot.servers if x.id in self.system["Servers"]]
                for server in servers:
                    for target in self.system["Servers"][server]["Targets"]:
                        vault = self.system["Servers"][server]["Targets"][target]["Vault"]
                        vault_max = self.system["Servers"][server]["Targets"][target]["Vault Max"]
                        if vault < vault_max:
                            increment = min(vault + int(vault_max * 0.04), vault_max)
                            self.system["Servers"][server]["Targets"][target]["Vault"] = increment
                        else:
                            pass
                self.save_system()
                await asyncio.sleep(120)  # task runs every 120 seconds
        except asyncio.CancelledError:
            pass

    async def heist_game(self, settings, server, t_heist, t_crew, t_vault):
        crew = len(settings["Crew"])
        target = self.heist_target(settings, crew)
        settings["Config"]["Heist Start"] = True
        players = [server.get_member(x) for x in settings["Crew"]]
        results = self.game_outcomes(settings, players, target)
        start_output = self.message_handler(settings, crew, players)
        await self.bot.say("Get ready! The {} is starting with {}\nThe {} has decided to "
                           "hit **{}**.".format(t_heist, start_output, t_crew, target))
        await asyncio.sleep(3)
        await self.show_results(settings, results)
        if settings["Crew"]:
            players = [server.get_member(x) for x in settings["Crew"]]
            data = self.calculate_credits(settings, players, target)
            headers = ["Players", "Credits Obtained", "Bonuses", "Total"]
            t = tabulate(data, headers=headers)
            msg = ("The credits collected from the {} was split among the winners:\n```"
                   "C\n{}```".format(t_vault, t))
        else:
            msg = "No one made it out safe."
        settings["Config"]["Alert Time"] = int(time.perf_counter())
        self.reset_heist(settings)
        self.save_system()
        await self.bot.say(msg)

    def __unload(self):
        self.cycle_task.cancel()
        self.shutdown_save()
        self.save_system()

    def theme_loader(self, settings, theme_name):
        keys = ["Jail", "OOB", "Police", "Bail", "Crew", "Sentence", "Heist", "Vault"]

        with open('data/heist/{}.txt'.format(theme_name)) as f:
            data = f.readlines()
            theme = {k[:k.find('=')].strip(): k[k.find('=') + 1:].strip() for k in data if '=' in k}
            print(theme)

        if all(key in theme for key in keys):
            settings["Theme"] = theme
            settings["Config"]["Theme"] = theme_name
            self.save_system()
            return "{} theme found. Heist will now use this for future games.".format(theme_name)
        else:
            return "Some keys were missing in your theme. Please check your txt file."

    def calculate_credits(self, settings, players, target):
        names = [player.name for player in players]
        bonuses = [subdict["Bonus"] for subdict in settings["Crew"].values()]
        vault = settings["Targets"][target]["Vault"]
        credits_stolen = int(int(vault) * 0.75 / len(settings["Crew"]))
        stolen_data = [credits_stolen] * len(settings["Crew"])
        total_winnings = [x + y for x, y in zip(stolen_data, bonuses)]
        settings["Targets"][target]["Vault"] -= credits_stolen * len(settings["Crew"])
        credit_data = list(zip(names, stolen_data, bonuses, total_winnings))
        deposits = list(zip(players, total_winnings))
        self.award_credits(deposits)
        return credit_data

    def save_system(self):
        dataIO.save_json(self.file_path, self.system)

    def calculate_success(self, settings, target):
        success_rate = settings["Targets"][target]["Success"]
        bonus = self.calculate_bonus(settings, target)
        success_chance = int(success_rate) + bonus
        return success_chance

    def calculate_bonus(self, settings, target):
        max_crew = settings["Targets"][target]["Crew"]
        crew = len(settings["Crew"])
        percent = int(100 * crew / max_crew)
        breakpoints = [20, 40, 60, 80, 100]
        bonus_amounts = [0, 1, 2, 3, 4, 5]
        return bonus_amounts[bisect.bisect_left(breakpoints, percent)]

    def game_outcomes(self, settings, players, target):
        success_rate = self.calculate_success(settings, target)
        good_out, bad_out = self.get_theme(settings)
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
        self.save_system()
        return results

    def get_theme(self, settings):
        theme = settings["Config"]["Theme"]
        with open('data/heist/{}.txt'.format(theme)) as f:
            data = f.readlines()
            good = [list(literal_eval(line.replace("|Good| ", "")))
                    for line in data if line.startswith("|Good|")]
            bad = [list(literal_eval(line.replace("|Bad| ", "")))
                   for line in data if line.startswith("|Bad|")]
        return good, bad

    def hardcore_handler(self, user):
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
            sentence_base = settings["Config"]["Sentence Base"]

            if offenses > 1:
                offenses = offenses - 1

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
        groups = sorted([(x, y["Crew"]) for x, y in settings["Targets"].items()], key=itemgetter(1))
        crew_sizes = [x[1] for x in groups]
        breakpoints = [x for x in crew_sizes if x != max(crew_sizes)]
        targets = [x[0] for x in groups]
        return targets[bisect.bisect_left(breakpoints, crew)]

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
            self.hardcore_handler(user)

    def user_clear(self, settings, user):
        settings["Players"][user.id]["Status"] = "Free"
        settings["Players"][user.id]["Criminal Level"] = 0
        settings["Players"][user.id]["Jail Counter"] = 0
        settings["Players"][user.id]["Death Timer"] = 0
        settings["Players"][user.id]["Bail Cost"] = 0
        settings["Players"][user.id]["Sentence"] = 0
        settings["Players"][user.id]["Time Served"] = 0
        settings["Players"][user.id]["OOB"] = False
        self.save_system()

    def reset_heist(self, settings):
        settings["Crew"] = {}
        settings["Config"]["Heist Planned"] = False
        settings["Config"]["Heist Start"] = False
        self.save_system()

    def award_credits(self, deposits):
        for player in deposits:
            bank = self.bot.get_cog('Economy').bank
            bank.deposit_credits(player[0], player[1])

    def subtract_costs(self, author, cost):
        bank = self.bot.get_cog('Economy').bank
        bank.withdraw_credits(author, cost)

    def requirement_check(self, settings, prefix, author, cost):
        # Theme variables
        t_jail = settings["Theme"]["Jail"]
        t_sentence = settings["Theme"]["Sentence"]
        t_police = settings["Theme"]["Police"]
        t_bail = settings["Theme"]["Bail"]
        t_crew = settings["Theme"]["Crew"]
        t_heist = settings["Theme"]["Heist"]

        alert, patrol_time = self.police_alert(settings)
        if not list(settings["Targets"]):
            msg = ("Oh no! There are no targets! To start creating a target, use "
                   "{}heist createtarget.".format(prefix))
            return "Failed", msg
        elif settings["Config"]["Heist Start"]:
            msg = ("A {0} is already underway. Wait for the current one to "
                   "end to plan another {0}.".format(t_heist))
            return "Failed", msg
        elif author.id in settings["Crew"]:
            msg = "You are already in the {}.".format(t_crew)
            return "Failed", msg
        elif settings["Players"][author.id]["Status"] == "Apprehended":
            bail = settings["Players"][author.id]["Bail Cost"]
            sentence_raw = settings["Players"][author.id]["Sentence"]
            time_served = settings["Players"][author.id]["Time Served"]
            remaining = self.cooldown_calculator(sentence_raw, time_served)
            sentence = self.time_format(sentence_raw)
            if remaining == "No Cooldown":
                msg = ("Looks like your {} is over, but you're still in {}! Get released "
                       "released by typing {}heist release .".format(t_sentence, t_jail, prefix))
            else:
                msg = ("You are in {0}. You are serving a {1} of {2}.\nYou can wait out "
                       "your remaining {1} of: {3} or pay {4} credits to finish your "
                       "{5}.".format(t_jail, t_sentence, sentence, remaining, bail, t_bail))
            return "Failed", msg
        elif settings["Players"][author.id]["Status"] == "Dead":
            death_time = settings["Players"][author.id]["Death Timer"]
            base_timer = settings["Config"]["Death Timer"]
            remaining = self.cooldown_calculator(death_time, base_timer)
            if remaining == "No Cooldown":
                msg = ("Looks like you are still dead, but you can revive at anytime by using the "
                       "command {}heist revive .".format(prefix))
            else:
                msg = ("You are dead. You can revive in:\n{}\nUse the command {}heist revive when "
                       "the timer has expired.".format(remaining, prefix))
            return "Failed", msg
        elif not self.bank_check(settings, author):
            msg = ("You do not have enough credits to cover the costs of "
                   "entry. You need {} credits to participate.".format(cost))
            return "Failed", msg
        elif alert == "Hot":
            msg = ("The {} are on high alert after the last target. We should "
                   "wait for things to cool off before hitting another target.\n"
                   "Time Remaining: {}".format(t_police, patrol_time))
            return "Failed", msg
        else:
            return "Success", "Success"

    def police_alert(self, settings):
        police_time = settings["Config"]["Police Alert"]
        alert_time = settings["Config"]["Alert Time"]
        if settings["Config"]["Alert Time"] == 0:
            return "Clear", None
        elif abs(alert_time - int(time.perf_counter())) >= police_time:
            settings["Config"]["Alert Time"] = 0
            self.save_system()
            return "Clear", None
        else:
            s = abs(alert_time - int(time.perf_counter()))
            seconds = abs(s - police_time)
            remaining = self.time_format(seconds)
            return "Hot", remaining

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

    def cooldown_calculator(self, player_time, base_time):
        if abs(player_time - int(time.perf_counter())) >= base_time:
            return "No Cooldown"
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
        else:
            msg = "No Cooldown"
        return msg

    def bank_check(self, settings, user):
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
        status = ["Greenhorn", "Renegade", "Veteran", "Commander", "War Chief", "Legend",
                  "Immortal"]
        breakpoints = [1, 10, 25, 50, 75, 100]
        return status[bisect.bisect_right(breakpoints, level)]

    def account_check(self, settings, author):
        if author.id not in settings["Players"]:
            criminal = {"Name": author.name, "Status": "Free", "Sentence": 0, "Time Served": 0,
                        "Death Timer": 0, "OOB": False, "Bail Cost": 0, "Jail Counter": 0,
                        "Spree": 0, "Criminal Level": 0, "Total Jail": 0, "Deaths": 0}
            settings["Players"][author.id] = criminal
            self.save_system()
        else:
            pass

    def patch_2220(self, path):
        # Check if player data has the war game, and if not add it.
        if "Theme" not in path or not path["Theme"]:
            path["Theme"] = {"Jail": "jail", "OOB": "out on bail", "Police": "Police",
                             "Bail": "bail", "Crew": "crew", "Sentence": "sentence",
                             "Heist": "heist", "Vault": "vault"},
        if "Banks" in path:
            path["Targets"] = path.pop("Banks")
        if "Theme" not in path["Config"]:
            path["Config"]["Theme"] = "Heist"
        if "Crew Output" not in path["Config"]:
            path["Config"]["Crew Ouput"] = "None"
        if "Bail Cost" in path["Config"]:
            path["Config"].pop("Bail Cost")

        for target in path["Targets"]:
            path["Targets"][string.capwords(target)] = path["Targets"].pop(target)

        self.save_system()

    def heist_patcher(self, path):

        if path["Config"]["Version"] < 2.221:
            self.patch_2220(path)

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            default = {"Config": {"Heist Start": False, "Heist Planned": False, "Heist Cost": 100,
                                  "Wait Time": 20, "Hardcore": False, "Police Alert": 60,
                                  "Alert Time": 0, "Sentence Base": 600, "Bail Base": 500,
                                  "Death Timer": 86400, "Theme": "Heist", "Crew Output": "None",
                                  "Version": 2.41},
                       "Theme": {"Jail": "jail", "OOB": "out on bail", "Police": "Police",
                                 "Bail": "bail", "Crew": "crew", "Sentence": "sentence",
                                 "Heist": "heist", "Vault": "vault"},
                       "Players": {},
                       "Crew": {},
                       "Targets": {},
                       }
            self.system["Servers"][server.id] = default
            self.save_system()
            print("Creating Heist settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]

            try:
                if path["Config"]["Version"] < self.patch:
                    self.heist_patcher(path)
                    path["Config"]["Version"] = self.patch
            except KeyError:
                path["Config"]["Version"] = 0
                self.heist_patcher(path)
                path["Config"]["Version"] = self.patch

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
            self.save_system()
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
            self.save_system()
            msg = ("{} casted :trident: `resurrection` :trident: on {} and returned them "
                   "to the living.".format(author.name, user.name))
            action = "True"
        else:
            msg = "Cast failed. {} is still alive.".format(user.name)
            action = None
        return action, msg

    # ==================== End of hooks =====================


def check_folders():
    if not os.path.exists("data/JumperCogs/heist"):
        print("Creating data/JumperCogs/heist folder...")
        os.makedirs("data/JumperCogs/heist")

    if not os.path.exists("data/heist"):
        print("Creating data/heist folder...")
        os.makedirs("data/heist")


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
    bot.add_cog(n)
