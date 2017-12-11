import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from discord.utils import find


class StreamAnnouncer:

    """Configureable stream announcements"""
    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/streamannouncer/settings.json')

    def save_json(self):
        dataIO.save_json("data/streamannouncer/settings.json", self.settings)

    @checks.admin_or_permissions(Manage_server=True)
    @commands.group(name="strannounceset", pass_context=True, no_pm=True,
                    aliases=['strset'])
    async def _strset(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(Manage_server=True)
    @_strset.command(name="output", pass_context=True, no_pm=True)
    async def strset_output(self, ctx):
        """set the output channel to the current channel"""

        server = ctx.message.server
        channel = ctx.message.channel
        if server.id not in self.settings:
            self.settings[server.id] = {"output": None,
                                        "role_id": None}

        if self.settings[server.id]["output"] == channel.id:
            self.settings[server.id]["output"] = None
            await self.bot.say("This channel was set for output already, "
                               "I am removing it now.")
        else:
            self.settings[server.id]["output"] = channel.id
            await self.bot.say("Announcement channel selected.")
        self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @_strset.command(name="role", pass_context=True, no_pm=True)
    async def strset_role(self, ctx, role: discord.Role):
        """set the role required to get an announcement on stream start"""

        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {"output": None,
                                        "role_id": None}

        if self.settings[server.id]["role_id"] == role.id:
            self.settings[server.id]["role_id"] = None
            self.save_json()
            await self.bot.say("That role was set before, removing it")
        else:
            self.settings[server.id]["role_id"] = role.id
            self.save_json()
            await self.bot.say("Role required to be announced set")

    async def on_stream(self, memb_before,  memb_after):
        if memb_after.game is None:
            return
        if memb_after.game.type != 1:
            return
        if memb_before.server.id not in self.settings:
            self.settings[memb_before.server.id] = {"output": None,
                                                    "role_id": None}
            self.save_json()

        server_settings = self.settings[memb_before.server.id]
        if server_settings["output"] is None \
                or server_settings["role_id"] is None:
            return

        streamer_role = find(lambda m: m.id == server_settings["role_id"],
                             memb_before.server.roles)
        dest = find(lambda m: m.id == server_settings["output"],
                    memb_before.server.channels)

        if streamer_role is None or dest is None:
            return

        if streamer_role not in memb_after.roles:
            return

        stream_url = memb_after.game.url

        msg = "{} just started streaming: {}".format(memb_after.mention,
                                                     stream_url)
        await self.bot.send_message(dest, msg)


def check_folder():
    f = 'data/streamannouncer'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/streamannouncer/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})
    f = 'data/streamannouncer/list.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = StreamAnnouncer(bot)
    bot.add_listener(n.on_stream, "on_member_update")
    bot.add_cog(n)
