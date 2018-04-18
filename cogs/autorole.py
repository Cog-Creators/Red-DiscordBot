import discord
from discord.ext import commands
from cogs.utils import checks
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
import random
import string
import os


class Autorole:
    """Autorole commands."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/autorole/settings.json"
        self.settings = dataIO.load_json(self.file_path)
        self.users = {}
        self.messages = {}

    def _get_server_from_id(self, serverid):
        return discord.utils.get(self.bot.servers, id=serverid)

    def _set_default(self, server):
        self.settings[server.id] = {
            "ENABLED": False,
            "ROLE": None,
            "AGREE_CHANNEL": None,
            "AGREE_MSG": None
        }
        dataIO.save_json(self.file_path, self.settings)

    async def _no_perms(self, server):
        m = ("It appears that you haven't given this "
             "bot enough permissions to use autorole. "
             "The bot requires the \"Manage Roles\" and "
             "the \"Manage Messages\" permissions in"
             "order to use autorole. You can change the "
             "permissions in the \"Roles\" tab of the "
             "server settings.")
        await self.bot.send_message(server, m)

    async def on_message(self, message):
        server = message.server
        user = message.author
        if server is None:
            return
        if server.id not in self.settings:
            self._set_default(server)
            return
        try:
            if self.settings[server.id]["AGREE_CHANNEL"] is not None:
                pass
            else:
                return
        except:
            return

        try:
            if message.content == self.users[user.id]:
                roleid = self.settings[server.id]["ROLE"]
                try:
                    roles = server.roles
                except AttributeError:
                    print("This server has no roles... what even?\n")
                    return

                role = discord.utils.get(roles, id=roleid)
                try:
                    await self.bot.add_roles(user, role)
                    await self.bot.delete_message(message)
                    if user.id in self.messages:
                        self.messages.pop(user.id, None)
                except discord.Forbidden:
                    if server.id in self.settings:
                        await self._no_perms(server)
        except KeyError:
            return

    async def _agree_maker(self, member):
        server = member.server
        self.last_server = server
        await self._verify_json(None)
        key = ''.join(random.choice(string.ascii_uppercase +
                                    string.digits) for _ in range(6))
        # <3 Stackoverflow http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python/23728630#23728630
        self.users[member.id] = key
        ch = discord.utils.get(
            self.bot.get_all_channels(),
            id=self.settings[server.id]["AGREE_CHANNEL"])
        msg = self.settings[server.id]["AGREE_MSG"]
        try:
            msg = msg.format(key=key,
                             member=member,
                             name=member.name,
                             mention=member.mention,
                             server=server.name)
        except Exception as e:
            self.bot.logger.error(e)

        try:
            msg = await self.bot.send_message(member, msg)
        except discord.Forbidden:
            msg = await self.bot.send_message(ch, msg)
        except discord.HTTPException:
            return
        self.messages[member.id] = msg

    async def _auto_give(self, member):
        server = member.server
        try:
            roleid = self.settings[server.id]["ROLE"]
            roles = server.roles
        except KeyError:
            return
        except AttributeError:
            print("This server has no roles... what even?\n")
            return
        role = discord.utils.get(roles, id=roleid)
        try:
            await self.bot.add_roles(member, role)
        except discord.Forbidden:
            if server.id in self.settings:
                await self._no_perms(server)

    async def _verify_json(self, e, *a, **k):
        s = self.last_server
        if len(self.settings[s.id].keys()) >= 4:
            return
        try:
            _d = self.settings[s.id]
        except KeyError:
            self._set_default(s)
        _k = _d.keys()

        # Fix any potential JSON issues because I break things a lot
        if "ENABLED" not in _k:
            self._set_default(s)
            print("Please stop messing with the autorole JSON\n")
            return
        if "ROLE" not in _k:
            self._set_default(s)
            print("Please stop messing with the autorole JSON\n")
            return
        if "AGREE_CHANNEL" not in _k:
            self.settings[s.id]["AGREE_CHANNEL"] = None
        if "AGREE_MSG" not in _k:
            self.settings[s.id]["AGREE_MSG"] = None

    async def _roler(self, member):
        server = member.server
        self.last_server = server  # In case something breaks
        if server.id not in self.settings:
            self._set_default(server)

        if self.settings[server.id]["ENABLED"] is True:
            try:
                if self.settings[server.id]["AGREE_CHANNEL"] is not None:
                    await self._agree_maker(member)
                else:  # Immediately give the new user the role
                    await self._auto_give(member)
            except KeyError as e:
                self.last_server = server
                await self._verify_json(e)

    @commands.group(name="autorole", pass_context=True, no_pm=True)
    async def autorole(self, ctx):
        """Change settings for autorole

        Requires the manage roles permission"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {
                "ENABLED": False,
                "ROLE": None,
                "AGREE_CHANNEL": None,
                "AGREE_MSG": None
            }
            dataIO.save_json(self.file_path, self.settings)
        if "AGREE_MSG" not in self.settings[server.id].keys():
            self.settings[server.id]["AGREE_MSG"] = None
            dataIO.save_json(self.file_path, self.settings)

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            try:
                await self.bot.say("```Current autorole state: {}```".format(
                    self.settings[server.id]["ENABLED"]))
            except KeyError:
                self._set_default(server)

    @autorole.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def toggle(self, ctx):
        """Enables/Disables autorole"""
        server = ctx.message.server
        if self.settings[server.id]["ROLE"] is None:
            await self.bot.say("You haven't set a role to give to new users! "
                               "Use `{}autorole role \"role\"` to set it!"
                               .format(ctx.prefix))
        else:
            if self.settings[server.id]["ENABLED"] is True:
                self.settings[server.id]["ENABLED"] = False
                await self.bot.say("Autorole is now disabled.")
                dataIO.save_json(self.file_path, self.settings)
            else:
                self.settings[server.id]["ENABLED"] = True
                await self.bot.say("Autorole is now enabled.")
                dataIO.save_json(self.file_path, self.settings)

    @autorole.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx, role: discord.Role):
        """Set role for autorole to assign.

        Use quotation marks around the role if it contains spaces."""
        server = ctx.message.server
        self.settings[server.id]["ROLE"] = role.id
        em = discord.Embed(description="<:success:350172481186955267> Autorole set to " + role.mention, color=role.color)
        await self.bot.say(embed=em)
        dataIO.save_json(self.file_path, self.settings)

    @autorole.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def agreement(self, ctx, channel: str,
                        *, msg: str=None):
        """Set the channel and message that will be used for accepting the rules.
        This is not needed and is completely optional

        Entering only \"clear\" will disable this."""
        server = ctx.message.server

        if not channel:
            await self.bot.send_cmd_help(ctx)
            return

        if channel.startswith("<#"):
            channel = channel[2:-1]

        if channel == "clear":
            self.settings[server.id]["AGREE_CHANNEL"] = None
            await self.bot.say("Agreement channel cleared")
        else:
            ch = discord.utils.get(server.channels, name=channel)
            if ch is None:
                ch = discord.utils.get(server.channels, id=channel)
            if ch is None:
                await self.bot.say("Channel not found!")
                return
            try:
                self.settings[server.id]["AGREE_CHANNEL"] = ch.id
            except AttributeError as e:
                await self.bot.say("Something went wrong...")
            if msg is None:
                msg = "{name} please enter this code: {key}"
            self.settings[server.id]["AGREE_MSG"] = msg
            await self.bot.say("Agreement channel "
                               "set to {}".format(ch.name))
        dataIO.save_json(self.file_path, self.settings)


def check_folders():
    if not os.path.exists("data/autorole"):
        print("Creating data/autorole folder...")
        os.makedirs("data/autorole")


def check_files():

    f = "data/autorole/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default autorole's settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()

    n = Autorole(bot)
    bot.add_cog(n)
    bot.add_listener(n._roler, "on_member_join")
    bot.add_listener(n._verify_json, "on_error")
