import discord
import os
import os.path
import json
from .utils import checks
from .utils.dataIO import dataIO
from discord.ext import commands

class Say:
    """Make your bot say or upload something in the channel you want.
    
    Report a bug or ask a question: https://discord.gg/WsTGeQ"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/say/settings.json')

    @commands.group(pass_context=True)
    async def send(self, ctx): # Had to choose something else than say :c have a better idea ?
        if ctx.invoked_subcommand is None:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @send.command(pass_context=True)
    async def here(self, ctx, *, text):
        """Say a message in the actual channel"""
        
        message = ctx.message
        server = message.server
        
        if server.id not in self.settings:
            self.settings[server.id] = {'autodelete': '0'}

        if self.settings[server.id]['autodelete'] == '1':
            await self.bot.delete_message(message)

        else:
            pass

        await self.bot.say(text)

            
    @send.command(pass_context=True)
    async def channel(self, ctx, channel : discord.Channel, *, text):
        """Say a message in the chosen channel"""

        message = ctx.message
        server = message.server
        
        if server.id not in self.settings:
            self.settings[server.id] = {'autodelete': '0'}

        if self.settings[server.id]['autodelete'] == '0' or server.id not in self.settings:
            pass
        
        else:
            await self.bot.delete_message(message)

        await self.bot.send_message(channel, text)

    @send.command(pass_context=True)
    async def upload(self, ctx, file = None, *, comment = None):
        """Upload a file from your local folder"""

        message = ctx.message
        server = message.server
        
        if file == None:
            if os.listdir('data/say/upload') == []:
                await self.bot.say("No files to upload. Put them in `data/say/upload`")
                return
            
            msg = "List of available files to upload:\n\n"
            for file in os.listdir('data/say/upload'):
                msg += "- `{}`\n".format(file)
            await self.bot.say(msg)
            return
        
        if server.id not in self.settings:
            self.settings[server.id] = {'autodelete': '0'}
        
        if '.' not in file:
            for fname in os.listdir('data/say/upload'):
                if fname.startswith(file):
                    file += '.' + fname.partition('.')[2]
                    break

        if os.path.isfile('data/say/upload/{}'.format(file)) is True:
            
            if self.settings[server.id]['autodelete'] == '1':
                await self.bot.delete_message(message)


            if comment is not None:
                await self.bot.upload(fp = path, content = comment)

            else:
                await self.bot.upload(fp = 'data/say/upload/{}'.format(file))
        else:
            await self.bot.say("That file doesn't seem to exist. Make sure it is the good name, try to add the extention (especially if two files have the same name) and if you just added a new file, make sure to reload the cog by typing `" + ctx.prefix + "reload say`")

    @send.command(pass_context=True)
    async def dm(self, ctx, user : discord.Member, *, text):
        """Send a message to the user in direct message. 
            No author mark, send exactly what you wrote"""
    
        server = ctx.message.server
        message= ctx.message
        
        if server.id not in self.settings:
            self.settings[server.id] = {'autodelete': '0'}

        if self.settings[server.id]['autodelete'] == '1':
            await self.bot.delete_message(message)
        
        else:
            pass
        
        
        try:
            await self.bot.send_message(user, text)

        except:
            await self.bot.say("I can't send DM to this user, he may had blocked DM on this server.")


    @checks.serverowner_or_permissions(administrator=True)
    @send.command(pass_context=True)
    async def autodelete(self, ctx):
        """Enable the auto-deletion of the message that invoked the command.
            
        If your bot is fast enough, users won't see at all the message with the command, useful to talk as your bot with long conversations"""
            
        server = ctx.message.server
        
        if server.id not in self.settings:
            self.settings[server.id] = {'autodelete': '0'}
        
        if not ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages:
            await self.bot.say("Error: I need the `Manage messages` permission to enable this function. Aborting...")
            return
        else:
            pass
        
        if self.settings[server.id]['autodelete'] == '0':
            self.settings[server.id]['autodelete'] = '1'
            await self.bot.say("Auto-deletion is now enabled. Note that this will only work on commands of these cog. For further options,look at `" + ctx.prefix + "modset deleterepeat`")

        else:
            self.settings[server.id]['autodelete'] = '0'
            await self.bot.say("Auto-deletion is now disabled")

        dataIO.save_json('data/say/settings.json', self.settings)


def check_folders():
    folders = ('data', 'data/say/', 'data/say/upload/')
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_file():
    contents = {}
    if not os.path.exists('data/say/settings.json'):
        print("Creating empty settings.json")
        dataIO.save_json('data/say/settings.json', contents)

def setup(bot):
    check_folders()
    check_file()
    bot.add_cog(Say(bot))
