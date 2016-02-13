import discord
from discord.ext import commands
from .utils import checks
from .utils.dataIO import fileIO
import __main__
import os

class Mod:
    """Moderation tools."""

    def __init__(self, bot):
        self.bot = bot
        self.whitelist_list = fileIO("data/mod/whitelist.json", "load")
        self.blacklist_list = fileIO("data/mod/blacklist.json", "load")
        self.ignore_list = fileIO("data/mod/ignorelist.json", "load")

    @commands.command(no_pm=True)
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, user : discord.Member):
        """Kicks user."""
        try:
            await self.bot.kick(user)
            await self.bot.say("Done. That felt good.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command(no_pm=True)
    @checks.admin_or_permissions(ban_members=True)
    async def ban(self, user : discord.Member, purge_msg : int=0):
        """Bans user and deletes last X days worth of messages.

        Minimum 0 days, maximum 7. Defaults to 0."""
        if purge_msg < 0 or purge_msg > 7:
            await self.bot.say("Invalid days. Must be between 0 and 7.")
            return
        try:
            await self.bot.ban(user, days)
            await self.bot.say("Done. It was about time.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def cleanup(self, ctx):
        """Deletes messages.

        cleanup messages [number]
        cleanup user [name/mention] [number]
        cleanup text \"Text here\" [number]"""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help cleanup for info.")

    @cleanup.command(pass_context=True, no_pm=True)
    async def text(self, ctx, text : str, number : int):
        """Deletes last X messages matching the specified text.

        Example:
        cleanup text \"test\" 5

        Remember to use double quotes."""
        message = ctx.message
        cmdmsg = message
        if number > 0 and number < 10000:
            while True:
                new = False
                async for x in self.bot.logs_from(message.channel, limit=100, before=message):
                    if number == 0: 
                        await self.bot.delete_message(cmdmsg)
                        return
                    if text in x.content:
                        await self.bot.delete_message(x)
                        number -= 1
                    new = True
                    message = x
                if not new or number == 0: 
                    await self.bot.delete_message(cmdmsg)
                    break

    @cleanup.command(pass_context=True, no_pm=True)
    async def user(self, ctx, name : discord.Member, number : int):
        """Deletes last X messages from specified user.

        Examples:
        cleanup user @\u200bTwentysix 2
        cleanup user Red 6"""
        message = ctx.message
        cmdmsg = message
        if number > 0 and number < 10000:
            while True:
                new = False
                async for x in self.bot.logs_from(message.channel, limit=100, before=message):
                    if number == 0: 
                        await self.bot.delete_message(cmdmsg)
                        return
                    if x.author.id == name.id:
                        await self.bot.delete_message(x)
                        number -= 1
                    new = True
                    message = x
                if not new or number == 0: 
                    await self.bot.delete_message(cmdmsg)
                    break

    @cleanup.command(pass_context=True, no_pm=True)
    async def messages(self, ctx, number : int):
        """Deletes last X messages.

        Example:
        cleanup messages 26"""
        channel = ctx.message.channel
        if number > 0 and number < 10000:
            async for x in self.bot.logs_from(channel, limit=number+1):
                await self.bot.delete_message(x)

    @commands.group(pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def blacklist(self, ctx):
        """Bans user from using the bot"""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help blacklist for info.")

    @blacklist.command(name="add")
    async def _blacklist_add(self, user : discord.Member):
        """Adds user to bot's blacklist"""
        if user.id not in self.blacklist_list:
            self.blacklist_list.append(user.id)
            fileIO("data/mod/blacklist.json", "save", self.blacklist_list)
            await self.bot.say("User has been added to blacklist.")
        else:
            await self.bot.say("User is already blacklisted.")

    @blacklist.command(name="remove")
    async def _blacklist_remove(self, user : discord.Member):
        """Removes user to bot's blacklist"""
        if user.id in self.blacklist_list:
            self.blacklist_list.remove(user.id)
            fileIO("data/mod/blacklist.json", "save", self.blacklist_list)
            await self.bot.say("User has been removed from blacklist.")
        else:
            await self.bot.say("User is not in blacklist.")

    
    @commands.group(pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def whitelist(self, ctx):
        """Users who will be able to use the bot"""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help whitelist for info.")

    @whitelist.command(name="add")
    async def _whitelist_add(self, user : discord.Member):
        """Adds user to bot's whitelist"""
        if user.id not in self.whitelist_list:
            if not self.whitelist_list: 
                msg = "\nAll users not in whitelist will be ignored (owner, admins and mods excluded)"
            else:
                msg = ""
            self.whitelist_list.append(user.id)
            fileIO("data/mod/whitelist.json", "save", self.whitelist_list)
            await self.bot.say("User has been added to whitelist." + msg)
        else:
            await self.bot.say("User is already whitelisted.")

    @whitelist.command(name="remove")
    async def _whitelist_remove(self, user : discord.Member):
        """Removes user to bot's whitelist"""
        if user.id in self.whitelist_list:
            self.whitelist_list.remove(user.id)
            fileIO("data/mod/whitelist.json", "save", self.whitelist_list)
            await self.bot.say("User has been removed from whitelist.")
        else:
            await self.bot.say("User is not in whitelist.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx):
        """Adds servers/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            
            await self.bot.say(self.count_ignored() + "Type help ignore for info.")

    @ignore.command(name="channel", pass_context=True)
    async def ignore_channel(self, ctx, channel : discord.Channel=None):
        """Ignores channel

        Defaults to current one"""
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(current_ch.id)
                fileIO("data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")
        else:
            if channel.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(channel.id)
                fileIO("data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")


    @ignore.command(name="server", pass_context=True)
    async def ignore_server(self, ctx):
        """Ignores current server"""
        server = ctx.message.server
        if server.id not in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].append(server.id)
            fileIO("data/mod/ignorelist.json", "save", self.ignore_list)
            await self.bot.say("This server has been added to the ignore list.")
        else:
            await self.bot.say("This server is already being ignored.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx):
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await self.bot.say(self.count_ignored() + "Type help unignore for info.")

    @unignore.command(name="channel", pass_context=True)
    async def unignore_channel(self, ctx, channel : discord.Channel=None):
        """Removes channel from ignore list

        Defaults to current one"""
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(current_ch.id)
                fileIO("data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("This channel has been removed from the ignore list.")
            else:
                await self.bot.say("This channel is not in the ignore list.")
        else:
            if channel.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(channel.id)
                fileIO("data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("Channel removed from ignore list.")
            else:
                await self.bot.say("That channel is not in the ignore list.")


    @unignore.command(name="server", pass_context=True)
    async def unignore_server(self, ctx):
        """Removes current server from ignore list"""
        server = ctx.message.server
        if server.id in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].remove(server.id)
            fileIO("data/mod/ignorelist.json", "save", self.ignore_list)
            await self.bot.say("This server has been removed from the ignore list.")
        else:
            await self.bot.say("This server is not in the ignore list.")

    def count_ignored(self):
        msg = "```Currently ignoring:\n"
        msg += str(len(self.ignore_list["CHANNELS"])) + " channels\n"
        msg += str(len(self.ignore_list["SERVERS"])) + " servers\n```\n"
        return msg


def check_folders():
    folders = ("data", "data/mod/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_files():
    ignore_list = {"SERVERS" : [], "CHANNELS" : []}

    if not os.path.isfile("data/mod/blacklist.json"):
        print("Creating empty blacklist.json...")
        fileIO("data/mod/blacklist.json", "save", [])

    if not os.path.isfile("data/mod/whitelist.json"):
        print("Creating empty whitelist.json...")
        fileIO("data/mod/whitelist.json", "save", [])

    if not os.path.isfile("data/mod/ignorelist.json"):
        print("Creating empty ignorelist.json...")
        fileIO("data/mod/ignorelist.json", "save", ignore_list)

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Mod(bot))
