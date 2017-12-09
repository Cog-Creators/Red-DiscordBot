import os
import traceback
import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import pagify, box

FOLDER_PATH = "data/errorlogs"
SETTINGS_PATH = "{}/log_channels.json".format(FOLDER_PATH)
DEFAULT_SETTINGS = []
ENABLE = "enable"
DISABLE = "disable"

class ErrorLogs():
    """Logs traceback of command errors in specified channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channels = dataIO.load_json(SETTINGS_PATH)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def logerrors(self, ctx: commands.Context):
        """Toggle error logging in this channel."""
        channel = ctx.message.channel
        task = ENABLE
        if channel.id in self.log_channels:
            task = DISABLE
        await self.bot.say("This will {} error logging in this channel. Are you sure about this? Type `yes` to agree".format(task))
        message = await self.bot.wait_for_message(author=ctx.message.author)
        if message is not None and message.content == 'yes':
            if task == ENABLE:
                self.log_channels.append(channel.id)
            elif task == DISABLE:
                self.log_channels.remove(channel.id)
            dataIO.save_json(SETTINGS_PATH, self.log_channels)
            await self.bot.say("Error logging {}d.".format(task))
        else:
            await self.bot.say("The operation was cancelled.")

    @commands.command(name="raise", pass_context=True)
    @checks.is_owner()
    async def _raise(self, ctx: commands.Context):
        """Raise an exception. If you want to handle the exception, use 'true'."""
        await self.bot.say("I am raising an error right now.")
        raise Exception()

    async def _on_command_error(self, error, ctx: commands.Context):
        """Fires when a command error occurs."""
        if not self.log_channels or not isinstance(error, commands.CommandInvokeError):
            return
        destinations = [c for c in self.bot.get_all_channels() if c.id in self.log_channels]
        destinations += [c for c in self.bot.private_channels if c.id in self.log_channels]
        error_title = "Exception in command `{}` ¯\_(ツ)_/¯".format(ctx.command.qualified_name)
        log = "".join(traceback.format_exception(type(error), error,
                                                    error.__traceback__))
        channel = ctx.message.channel
        embed = discord.Embed(title=error_title, colour=discord.Colour.red(), timestamp=ctx.message.timestamp)
        embed.add_field(name="Invoker", value="{}\n({})".format(ctx.message.author.mention, str(ctx.message.author)))
        embed.add_field(name="Content", value=ctx.message.content)
        _channel_disp = "Private channel" if channel.is_private else "{}\n({})".format(channel.mention, channel.name)
        embed.add_field(name="Channel", value=_channel_disp)
        if not channel.is_private:
            embed.add_field(name="Server", value=ctx.message.server.name)
        for channel in destinations:
            try:
                await self.bot.send_message(channel, embed=embed)
            except discord.errors.Forbidden: # If bot can't embed
                msg = ("Invoker: {}\n"
                       "Content: {}\n"
                       "Channel: {}".format(str(ctx.message.author), ctx.message.content, _channel_disp))
                if not channel.is_private:
                    msg += "\nServer : {}".format(ctx.message.server.name)
                await self.bot.send_message(channel, box(msg))
            for page in pagify(log):
                await self.bot.send_message(channel, box(page, lang="py"))

def check_folders():
    if not os.path.exists(FOLDER_PATH):
            print("Creating " + FOLDER_PATH + " folder...")
            os.makedirs(FOLDER_PATH)

def check_files():
    if dataIO.is_valid_json(SETTINGS_PATH) is False:
        print('Creating json: log_channels.json')
        dataIO.save_json(SETTINGS_PATH, DEFAULT_SETTINGS)

def setup(bot):
    check_folders()
    check_files()
    n = ErrorLogs(bot)
    bot.add_listener(n._on_command_error, 'on_command_error')
    bot.add_cog(n)