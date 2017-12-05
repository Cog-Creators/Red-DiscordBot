from discord.ext import commands
import discord
import os
from .utils import checks
from .utils.dataIO import dataIO


class Lockdown():
    """Locks down the current server"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/lockdown/settings.json")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def lockdown(self, ctx):
        "Toggles the lockdown mode"
        server = ctx.message.server
        mod = self.bot.settings.get_server_mod(server)
        admin = self.bot.settings.get_server_admin(server)
        role_list = [role for role in server.roles if role.name != mod and role.name != admin]
        if server.id in self.settings:
            for channel in server.channels:
                if channel.id in self.settings[server.id]["channels"] and\
                        self.settings[server.id]["channels"][channel.id]:
                    for role in role_list:
                        cur_role_perms = channel.overwrites_for(role)
                        cur_role_perms.send_messages = False
                        print("Editing channel permissions for {}".format(role.name))
                        await self.bot.edit_channel_permissions(channel, role, cur_role_perms)
                    bot_perms = channel.overwrites_for(server.me)
                    bot_perms_edited = False
                    if not bot_perms.read_messages:
                        bot_perms.read_messages = True
                        bot_perms_edited = True
                    if not bot_perms.send_messages:
                        bot_perms.send_messages = True
                        bot_perms_edited = True
                    if bot_perms_edited:
                        await self.bot.edit_channel_permissions(channel, server.me, bot_perms)
            await self.bot.say(
                "Server is locked down. You can unlock the server by doing {}unlockdown".format(
                    ctx.prefix
                )
            )
        else:
            await self.bot.say("No settings available for this server!")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def unlockdown(self, ctx):
        """Ends the lockdown for this server"""
        server = ctx.message.server
        mod = self.bot.settings.get_server_mod(server)
        admin = self.bot.settings.get_server_admin(server)
        role_list = [role for role in server.roles if role.name != mod and role.name != admin]
        if server.id in self.settings:
            for channel in server.channels:
                if channel.id in self.settings[server.id]["channels"] and\
                        self.settings[server.id]["channels"][channel.id]:
                    for role in role_list:
                        cur_role_perms = channel.overwrites_for(role)
                        cur_role_perms.send_messages = None
                        print("Editing channel permissions for {}".format(role.name))
                        await self.bot.edit_channel_permissions(channel, role, cur_role_perms)
            await self.bot.say("Server has been unlocked!")
        else:
            await self.bot.say("No settings available for this server!")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def lockdownset(self, ctx):
        """Settings for lockdown"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @lockdownset.command(pass_context=True, no_pm=True)
    async def channel(self, ctx, channel: discord.Channel, status: str):
        """Sets whether or not the channel will be
           locked down if a lockdown is turned on
           Options for status are on or off"""
        server = ctx.message.server
        new_status = None
        if status.lower() != "on" and status.lower() != "off":
            await self.bot.say("Invalid status specified!")
            return
        else:
            if status.lower() == "on":
                new_status = True
            else:
                new_status = False
        if server.id not in self.settings:
            self.settings[server.id] = {}
        if "channels" not in self.settings[server.id]:
            self.settings[server.id]["channels"] = {}
        if channel.id not in self.settings[server.id]["channels"]:
            self.settings[server.id]["channels"][channel.id] = None
        self.settings[server.id]["channels"][channel.id] = new_status
        dataIO.save_json("data/lockdown/settings.json", self.settings)
        await self.bot.say("New status for {} set!".format(channel.mention))


def check_folder():
    if not os.path.isdir("data/lockdown"):
        os.mkdir("data/lockdown")


def check_file():
    if not dataIO.is_valid_json("data/lockdown/settings.json"):
        dataIO.save_json("data/lockdown/settings.json", {})


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Lockdown(bot))
