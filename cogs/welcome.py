import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from .utils.chat_formatting import pagify
from __main__ import send_cmd_help
import os
from random import choice as rand_choice


default_greeting = "Welcome {0.name} to {1.name}!"
default_settings = {"GREETING": [default_greeting], "ON": False,
                    "CHANNEL": None, "WHISPER": False,
                    "BOTS_MSG": None, "BOTS_ROLE": None}
settings_path = "data/welcome/settings.json"


class Welcome:
    """Welcomes new members to the server in the default channel"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO(settings_path, "load")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def welcomeset(self, ctx):
        """Sets welcome module settings"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO(settings_path, "save", self.settings)
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            msg += "Random GREETING: {}\n".format(rand_choice(self.settings[server.id]["GREETING"]))
            msg += "CHANNEL: #{}\n".format(self.get_welcome_channel(server))
            msg += "ON: {}\n".format(self.settings[server.id]["ON"])
            msg += "WHISPER: {}\n".format(self.settings[server.id]["WHISPER"])
            msg += "BOTS_MSG: {}\n".format(self.settings[server.id]["BOTS_MSG"])
            msg += "BOTS_ROLE: {}\n".format(self.settings[server.id]["BOTS_ROLE"])
            msg += "```"
            await self.bot.say(msg)

    @welcomeset.group(pass_context=True, name="msg")
    async def welcomeset_msg(self, ctx):
        """Manage welcome messages
        """
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)
            return

    @welcomeset_msg.command(pass_context=True, name="add", no_pm=True)
    async def welcomeset_msg_add(self, ctx, *, format_msg):
        """Adds a welcome message format for the server to be chosen at random

        {0} is user
        {1} is server
        Default is set to:
            Welcome {0.name} to {1.name}!

        Example formats:
            {0.mention}.. What are you doing here?
            {1.name} has a new member! {0.name}#{0.discriminator} - {0.id}
            Someone new joined! Who is it?! D: IS HE HERE TO HURT US?!"""
        server = ctx.message.server
        self.settings[server.id]["GREETING"].append(format_msg)
        fileIO(settings_path, "save", self.settings)
        await self.bot.say("Welcome message added for the server.")
        await self.send_testing_msg(ctx, msg=format_msg)

    @welcomeset_msg.command(pass_context=True, name="del", no_pm=True)
    async def welcomeset_msg_del(self, ctx):
        """Removes a welcome message from the random message list
        """
        server = ctx.message.server
        author = ctx.message.author
        msg = 'Choose a welcome message to delete:\n\n'
        for c, m in enumerate(self.settings[server.id]["GREETING"]):
            msg += "  {}. {}".format(c, m)
        for page in pagify(msg, ['\n', ' '], shorten_by=20):
            await self.bot.say("```\n{}\n```".format(page))
        answer = await self.bot.wait_for_message(timeout=120, author=author)
        try:
            num = int(answer.content)
            choice = self.settings[server.id]["GREETING"].pop(num)
        except:
            await self.bot.say("That's not a number in the list :/")
            return
        if not self.settings[server.id]["GREETING"]:
            self.settings[server.id]["GREETING"] = [default_greeting]
        fileIO(settings_path, "save", self.settings)
        await self.bot.say("**This message was deleted:**\n{}".format(choice))

    @welcomeset_msg.command(pass_context=True, name="list", no_pm=True)
    async def welcomeset_msg_list(self, ctx):
        """Lists the welcome messages of this server
        """
        server = ctx.message.server
        msg = 'Welcome messages:\n\n'
        for c, m in enumerate(self.settings[server.id]["GREETING"]):
            msg += "  {}. {}".format(c, m)
        for page in pagify(msg, ['\n', ' '], shorten_by=20):
            await self.bot.say("```\n{}\n```".format(page))

    @welcomeset.command(pass_context=True)
    async def toggle(self, ctx):
        """Turns on/off welcoming new users to the server"""
        server = ctx.message.server
        self.settings[server.id]["ON"] = not self.settings[server.id]["ON"]
        if self.settings[server.id]["ON"]:
            await self.bot.say("I will now welcome new users to the server.")
            await self.send_testing_msg(ctx)
        else:
            await self.bot.say("I will no longer welcome new users.")
        fileIO(settings_path, "save", self.settings)

    @welcomeset.command(pass_context=True)
    async def channel(self, ctx, channel : discord.Channel=None):
        """Sets the channel to send the welcome message

        If channel isn't specified, the server's default channel will be used"""
        server = ctx.message.server
        if channel is None:
            channel = ctx.message.server.default_channel
        if not server.get_member(self.bot.user.id
                                 ).permissions_in(channel).send_messages:
            await self.bot.say("I do not have permissions to send "
                               "messages to {0.mention}".format(channel))
            return
        self.settings[server.id]["CHANNEL"] = channel.id
        fileIO(settings_path, "save", self.settings)
        channel = self.get_welcome_channel(server)
        await self.bot.send_message(channel, "I will now send welcome "
                                    "messages to {0.mention}".format(channel))
        await self.send_testing_msg(ctx)

    @welcomeset.group(pass_context=True, name="bot", no_pm=True)
    async def welcomeset_bot(self, ctx):
        """Special welcome for bots"""
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)
            return

    @welcomeset_bot.command(pass_context=True, name="msg", no_pm=True)
    async def welcomeset_bot_msg(self, ctx, *, format_msg=None):
        """Set the welcome msg for bots.

        Leave blank to reset to regular user welcome"""
        server = ctx.message.server
        self.settings[server.id]["BOTS_MSG"] = format_msg
        fileIO(settings_path, "save", self.settings)
        if format_msg is None:
            await self.bot.say("Bot message reset. Bots will now be welcomed as regular users.")
        else:
            await self.bot.say("Bot welcome message set for the server.")
            await self.send_testing_msg(ctx, bot=True)

    # TODO: Check if have permissions
    @welcomeset_bot.command(pass_context=True, name="role", no_pm=True)
    async def welcomeset_bot_role(self, ctx, role: discord.Role=None):
        """Set the role to put bots in when they join.

        Leave blank to not give them a role."""
        server = ctx.message.server
        self.settings[server.id]["BOTS_ROLE"] = role.name if role else role
        fileIO(settings_path, "save", self.settings)
        await self.bot.say("Bots that join this server will "
                           "now be put into the {} role".format(role.name))

    @welcomeset.command(pass_context=True)
    async def whisper(self, ctx, choice: str=None):
        """Sets whether or not a DM is sent to the new user

        Options:
            off - turns off DMs to users
            only - only send a DM to the user, don't send a welcome to the channel
            both - send a message to both the user and the channel

        If Option isn't specified, toggles between 'off' and 'only'
        DMs will not be sent to bots"""
        options = {"off": False, "only": True, "both": "BOTH"}
        server = ctx.message.server
        if choice is None:
            self.settings[server.id]["WHISPER"] = not self.settings[server.id]["WHISPER"]
        elif choice.lower() not in options:
            await send_cmd_help(ctx)
            return
        else:
            self.settings[server.id]["WHISPER"] = options[choice.lower()]
        fileIO(settings_path, "save", self.settings)
        channel = self.get_welcome_channel(server)
        if not self.settings[server.id]["WHISPER"]:
            await self.bot.say("I will no longer send DMs to new users")
        elif self.settings[server.id]["WHISPER"] == "BOTH":
            await self.bot.send_message(channel, "I will now send welcome "
                                        "messages to {0.mention} as well as to "
                                        "the new user in a DM".format(channel))
        else:
            await self.bot.send_message(channel, "I will now only send "
                                        "welcome messages to the new user "
                                        "as a DM".format(channel))
        await self.send_testing_msg(ctx)

    async def member_join(self, member):
        server = member.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO(settings_path, "save", self.settings)
        if not self.settings[server.id]["ON"]:
            return
        if server is None:
            print("Server is None. Private Message or some new fangled "
                  "Discord thing?.. Anyways there be an error, "
                  "the user was {}".format(member.name))
            return

        only_whisper = self.settings[server.id]["WHISPER"] is True
        bot_welcome = member.bot and self.settings[server.id]["BOTS_MSG"]
        bot_role = member.bot and self.settings[server.id]["BOTS_ROLE"]
        msg = bot_welcome or rand_choice(self.settings[server.id]["GREETING"])

        # whisper the user if needed
        if not member.bot and self.settings[server.id]["WHISPER"]:
            try:
                await self.bot.send_message(member, msg.format(member, server))
            except:
                print("welcome.py: unable to whisper {}. Probably "
                      "doesn't want to be PM'd".format(member))
        # grab the welcome channel
        channel = self.get_welcome_channel(server)
        if channel is None:  # complain even if only whisper
            print('welcome.py: Channel not found. It was most '
                  'likely deleted. User joined: {}'.format(member.name))
            return
        # we can stop here
        if only_whisper and not bot_welcome:
            return
        if not self.speak_permissions(server):
            print("Permissions Error. User that joined: "
                  "{0.name}".format(member))
            print("Bot doesn't have permissions to send messages to "
                  "{0.name}'s #{1.name} channel".format(server, channel))
            return
        # try to add role if needed
        if bot_role:
            try:
                role = discord.utils.get(server.roles, name=bot_role)
                await self.bot.add_roles(member, role)
            except:
                print('welcome.py: unable to add {} role to {}. '
                      'Role was deleted, network error, or lacking '
                      'permissions'.format(bot_role, member))
            else:
                print('welcome.py: added {} role to '
                      'bot, {}'.format(role, member))
        # finally, welcome them
        await self.bot.send_message(channel, msg.format(member, server))

    def get_welcome_channel(self, server):
        try:
            return server.get_channel(self.settings[server.id]["CHANNEL"])
        except:
            return None

    def speak_permissions(self, server):
        channel = self.get_welcome_channel(server)
        if channel is None:
            return False
        return server.get_member(self.bot.user.id
                                 ).permissions_in(channel).send_messages

    async def send_testing_msg(self, ctx, bot=False, msg=None):
        server = ctx.message.server
        channel = self.get_welcome_channel(server)
        rand_msg = msg or rand_choice(self.settings[server.id]["GREETING"])
        if channel is None:
            await self.bot.send_message(ctx.message.channel,
                                        "I can't find the specified channel. "
                                        "It might have been deleted.")
            return
        await self.bot.send_message(ctx.message.channel,
                                    "`Sending a testing message to "
                                    "`{0.mention}".format(channel))
        if self.speak_permissions(server):
            msg = self.settings[server.id]["BOTS_MSG"] if bot else rand_msg
            if not bot and self.settings[server.id]["WHISPER"]:
                await self.bot.send_message(ctx.message.author,
                        msg.format(ctx.message.author,server))
            if bot or self.settings[server.id]["WHISPER"] is not True:
                await self.bot.send_message(channel,
                        msg.format(ctx.message.author, server))
        else:
            await self.bot.send_message(ctx.message.channel,
                                        "I do not have permissions "
                                        "to send messages to "
                                        "{0.mention}".format(channel))


def check_folders():
    if not os.path.exists("data/welcome"):
        print("Creating data/welcome folder...")
        os.makedirs("data/welcome")


def check_files():
    f = settings_path
    if not fileIO(f, "check"):
        print("Creating welcome settings.json...")
        fileIO(f, "save", {})
    else:  # consistency check
        current = fileIO(f, "load")
        for k, v in current.items():
            if v.keys() != default_settings.keys():
                for key in default_settings.keys():
                    if key not in v.keys():
                        current[k][key] = default_settings[key]
                        print("Adding " + str(key) +
                              " field to welcome settings.json")
        # upgrade. Before GREETING was 1 string
        for server in current.values():
            if isinstance(server["GREETING"], str):
                server["GREETING"] = [server["GREETING"]]
        fileIO(f, "save", current)


def setup(bot):
    check_folders()
    check_files()
    n = Welcome(bot)
    bot.add_listener(n.member_join, "on_member_join")
    bot.add_cog(n)
