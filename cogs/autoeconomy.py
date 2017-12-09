import asyncio
import discord
import os
from __main__ import send_cmd_help
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from discord.ext import commands

default_settings = {"CHANNEL": None,
                    "DEBUG": False,
                    "TOGGLE": False,
                    }


class AutoEconomy:
    """Auto-registers new users to the bank. Must have Economy loaded."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/autoeconomy/settings.json')
        self.banksettings = dataIO.load_json('data/economy/settings.json')
        self.version = "0.1.1b"

    async def save_settings(self):
        dataIO.save_json('data/autoeconomy/settings.json', self.settings)

    async def _data_check(self, ctx):
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = deepcopy(default_settings)
            self.settings[server.id]["CHANNEL"] = ctx.message.channel.id
            await self.save_settings()
        econ_cog = self.bot.get_cog('Economy')
        if not econ_cog:
            await self.bot.say("You must have Economy loaded to use this cog. \nAny settings saved will not work until the cog is loaded.")
            return

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(pass_context=True)
    async def autoeconomy(self, ctx):
        """Configuration options for auto-registering Economy accounts."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @autoeconomy.command(pass_context=True, name="debug", no_pm=True)
    async def autoeconomy_debug(self, ctx):
        """Toggle autoeconomy debug messages."""
        server = ctx.message.server
        await self._data_check(ctx)
        self.settings[server.id]["DEBUG"] = not self.settings[server.id]["DEBUG"]
        if self.settings[server.id]["DEBUG"]:
            await self.bot.say("Debug messages on.")
        else:
            await self.bot.say("Debug messages off.")
        await self.save_settings()

    @autoeconomy.command(pass_context=True, name="channel", no_pm=True)
    async def autoeconomy_channel(self, ctx, channel: discord.Channel):
        """Set a channel for the debug messages."""
        server = ctx.message.server
        await self._data_check(ctx)
        if not server.me.permissions_in(channel).send_messages:
            await self.bot.say("No permissions to speak in that channel.")
            return
        self.settings[server.id]["CHANNEL"] = channel.id
        await self.save_settings()
        await self.bot.send_message(channel, "This channel will be used for debug messages.")

    @autoeconomy.command(pass_context=True, name="toggle", no_pm=True)
    async def autoeconomy_toggle(self, ctx):
        """Toggle autoeconomy on the server."""
        server = ctx.message.server
        await self._data_check(ctx)
        self.settings[server.id]["TOGGLE"] = not self.settings[server.id]["TOGGLE"]
        if self.settings[server.id]["TOGGLE"]:
            await self.bot.say("New users will automatically be registered for a bank account.")
        else:
            await self.bot.say("No longer auto-registering new users.")
        await self.save_settings()

    @autoeconomy.command(name="version", pass_context=True, hidden=True)
    async def autoeconomy_version(self):
        """Displays the autoeconomy version."""
        await self.bot.say("autoeconomy version {}.".format(self.version))

    async def on_member_join(self, member):
        server = member.server
        if server.id not in self.settings:
            self.settings[server.id] = deepcopy(default_settings)
            await self.save_settings()
        if not self.settings[server.id]["TOGGLE"]:
            return
        channel = self.settings[server.id]["CHANNEL"]
        channel_object = self.bot.get_channel(channel)
        econ_cog = self.bot.get_cog('Economy')
        if not econ_cog:
            return
        bank = self.bot.get_cog('Economy').bank
        try:
            bank.create_account(member)
        except Exception:
            if self.settings[server.id]["DEBUG"]:
                await self.bot.send_message(channel_object, "Economy account already exists for {}.".format(member.name))
                return
        if self.banksettings[server.id]["REGISTER_CREDITS"]:
            reg_credits = self.banksettings[server.id]["REGISTER_CREDITS"]
            bank.deposit_credits(member, reg_credits)
            if self.settings[server.id]["DEBUG"]:
                await self.bot.send_message(channel_object, "Bank account opened for {} and initial credits given.".format(member.name))
                return


def check_folders():
    if not os.path.exists('data/autoeconomy/'):
        os.mkdir('data/autoeconomy/')


def check_files():
    if not dataIO.is_valid_json('data/autoeconomy/settings.json'):
        defaults = {}
        dataIO.save_json('data/autoeconomy/settings.json', defaults)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(AutoEconomy(bot))
