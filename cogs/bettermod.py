import discord
import json
import os
import datetime
import asyncio

from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import settings as set_roles


class BetterMod:
    """Better moderation commands
    
    Report a bug or ask a question: https://discord.gg/WsTGeQ"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/bettermod/settings.json')
        self.red = dataIO.load_json('data/red/settings.json')

    async def error(self, ctx):
        
        bot_member = ctx.message.server.get_member(self.bot.user.id)
        
        folders = ['data', 'data/bettermod/', 'data/bettermod/history/', 'data/red']
        files = ['data/bettermod/settings.json', 'data/bettermod/history/{}.json'.format(ctx.message.server.id), 'red/settings.json']
        permissions = ['add_reactions', 'embed_links', 'manage_messages']
        message_perm = "Error: missing permissions. I need the following permissions to work:\n"
        message_file = "Error: some files are missing and data might be lost. New files will be recreated. The following files are missing:\n"
        error_perm = None
        error_file = None
        
        for folder in folders:
            if not os.path.exists(folder):
                message_file += "`{}` folder\n".format(folder)
                print("Creating " + folder + " folder...")
                os.makedirs(folder)
                error_file = 1

        for filename in files:
            if not os.path.isfile(filename):
                print("Creating empty {}".format(filename))
                dataIO.save_json(filename, {})
                message_file += "`{}` is missing\n".format(filename)
                error_file = 1
                                   
        for permission in permissions:
            if {x[0]:x[1] for x in ctx.message.channel.permissions_for(ctx.message.server.me)}[permission] is False:
                message_perm += "`{}`\n".format(permission)
                error_perm = 1
           
        if error_perm == 1:
            message_perm += "Please give me the following permissions and try again"
            await self.bot.say(message_perm)

        if error_file == 1:
            message_file += "The files were successfully re-created. Try again your command (you may need to set your local settings again)"
            await self.bot.say(message_file)

        if ctx.message.server.id not in self.settings:
            await self.init(ctx.message.server)
                
    async def init(self, server):
        if server.id not in self.settings:
            self.settings[server.id] = {
                'role': None,
                'proof': False,
                
                'channels': {
                    'general': None,
                    'report': None,
                    'simple-warn': None,
                    'kick-warn': None,
                    'ban-warn': None
                },
            
                'thumbnail' : {
                    'warning_embed_simple': 'https://i.imgur.com/Bl62rGd.png',
                    'warning_embed_kick': 'https://i.imgur.com/uhrYzyt.png',
                    'warning_embed_ban': 'https://i.imgur.com/DfBvmic.png',
                    'report_embed': 'https://i.imgur.com/Bl62rGd.png'
                },
                    
                'colour': {
                    'warning_embed_simple': None,
                    'warning_embed_kick': None,
                    'warning_embed_ban': None,
                    'report_embed': None
                }
            }
        
            try:
                dataIO.save_json('data/bettermod/settings.json', self.settings)
            except:
                await self.error(ctx)
                return
    
    async def add_case(self, level, user, reason, timestamp, server, applied, ctx):
        if not os.path.isfile('data/bettermod/history/{}.json'.format(server.id)):
            print("Creating empty {}".format(server.id))
            try:
                dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), data={})
            except:
                await self.error(ctx)
                return
        
        history = dataIO.load_json('data/bettermod/history/{}.json'.format(server.id))
        
        if user.id not in history:
            history[user.id] = {
                'simple-warn': 0,
                'kick-warn': 0,
                'ban-warn': 0,
                'total-warns': 0
            }
        
        total = history[user.id]['total-warns'] + 1

        history[user.id]['case{}'.format(total)] = {
            'level': 'None',
            'reason': 'None',
            'timestamp': 'None',
            'applied': 1,
            'deleted': 0
        }
            
        history[user.id]['case{}'.format(total)]['level'] = level
        history[user.id]['case{}'.format(total)]['reason'] = reason
        history[user.id]['case{}'.format(total)]['timestamp'] = timestamp
        
        history[user.id]['total-warns'] = total
        
        if level == 'Simple':
            simple_total = history[user.id]['simple-warn'] + 1
            history[user.id]['simple-warn'] = simple_total
        elif level == 'Kick':
            kick_total = history[user.id]['kick-warn'] + 1
            history[user.id]['kick-warn'] = kick_total
        elif level == 'Ban':
            ban_total = history[user.id]['ban-warn'] + 1
            history[user.id]['ban-warn'] = ban_total
        else:
            pass
        
        if applied == 1:
            pass
        else:
            history[user.id]['case{}'.format(total)]['applied'] = 0
        
        try:
            dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), data=history)
        except:
            await self.error(ctx)
            return
            

    async def check_case(self, msg, i, ctx, user):
        
        server = ctx.message.server
        
        if not os.path.isfile('data/bettermod/history/{}.json'.format(server.id)):
            print("Creating empty {}".format(server.id))
            try:
                dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), data={})
            except:
                await self.error(ctx)
                return
        
        try:
            history = dataIO.load_json('data/bettermod/history/{}.json'.format(server.id))
        except:
            await self.error(ctx)
            return
        
        if i is not None:
            if i > history[user.id]['total-warns'] or i<= 0:
                i = 1
    
        if not msg:
            
            if history[user.id]['case{}'.format(str(i))]['deleted'] == 1:
                e = discord.Embed(description="The case {} was deleted".format(str(i)))
                e.set_author(name=user.name, icon_url=user.avatar_url)
            
            else:
                e = discord.Embed(description="Case {} informations".format(str(i)))
                e.set_author(name=user.name, icon_url=user.avatar_url)
                    
                e.add_field(name="Level", value=history[user.id]['case{}'.format(str(i))]['level'], inline=True)
                    
                if history[user.id]['case{}'.format(str(i))]['applied'] == 1:
                    e.add_field(name="Applied", value="Yes", inline=True)
                else:
                    e.add_field(name="Applied", value="No", inline=True)
                    
                e.add_field(name="Date", value=history[user.id]['case{}'.format(str(i))]['timestamp'], inline=True)
                e.add_field(name="Reason", value=history[user.id]['case{}'.format(str(i))]['reason'], inline=False)
            
            try:
                msg = await self.bot.say(embed=e)
            except:
                await self.error(ctx)
                return
                
        try:
            await self.bot.add_reaction(msg, "⬅")
            await self.bot.add_reaction(msg, "❌")
            await self.bot.add_reaction(msg, "➡")
        except:
            await self.error(ctx)
            return
        
        while True:
            
            response = await self.bot.wait_for_reaction(emoji=['❌', '⬅', '➡'], user=ctx.message.author, message=msg, timeout=30)
            await asyncio.sleep(0.2)
            
            if not response:
                try:
                    await self.bot.clear_reactions(msg)
                except:
                    pass
                return
                
            if response.reaction.emoji == '❌':
                try:
                    await self.bot.delete_message(msg)
                    return
                except:
                    await self.error(ctx)
                    return

        
            elif response.reaction.emoji == '➡':
                
                try:
                    await self.bot.remove_reaction(msg, '➡', ctx.message.author)
                except:
                    pass
                
                if i is None:
                    i = 1
                else:
                    i = i + 1
            
                if i > history[user.id]['total-warns']:
                    i = 1
                
                if history[user.id]['case{}'.format(str(i))]['deleted'] == 1:
                    i = i + 1
                
                e = discord.Embed(description="Case {} informations".format(str(i)))
                e.set_author(name=user.name, icon_url=user.avatar_url)
                    
                e.add_field(name="Level", value=history[user.id]['case{}'.format(str(i))]['level'], inline=True)
                    
                if history[user.id]['case{}'.format(str(i))]['applied'] == 1:
                    e.add_field(name="Applied", value="Yes", inline=True)
                else:
                    e.add_field(name="Applied", value="No", inline=True)
    
                e.add_field(name="Date", value=history[user.id]['case{}'.format(str(i))]['timestamp'], inline=True)
                e.add_field(name="Reason", value=history[user.id]['case{}'.format(str(i))]['reason'], inline=False)
                    
                msg = await self.bot.edit_message(msg, embed=e)
                
            else:
                
                try:
                    await self.bot.remove_reaction(msg, '⬅', ctx.message.author)
                except:
                    pass
                
                if i is None:
                    i = history[user.id]['total-warns']
                else:
                    i = i - 1
                    
                if i <= 0:
                    i = history[user.id]['total-warns']
                        
                if history[user.id]['case{}'.format(str(i))]['deleted'] == 1:
                    i = i - 1
            
                e = discord.Embed(description="Case {} informations".format(str(i)))
                e.set_author(name=user.name, icon_url=user.avatar_url)
                
                e.add_field(name="Level", value=history[user.id]['case{}'.format(str(i))]['level'], inline=True)
                
                if history[user.id]['case{}'.format(str(i))]['applied'] == 1:
                    e.add_field(name="Applied", value="Yes", inline=True)
                else:
                    e.add_field(name="Applied", value="No", inline=True)

                e.add_field(name="Date", value=history[user.id]['case{}'.format(str(i))]['timestamp'], inline=True)
                e.add_field(name="Reason", value=history[user.id]['case{}'.format(str(i))]['reason'], inline=False)

                msg = await self.bot.edit_message(msg, embed=e)

    @commands.group(pass_context=True)
    @checks.admin()
    async def bmodset(self, ctx):
        """Bettermod's settings"""
    
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

            server = ctx.message.server
            
            try:
                if server.id not in self.settings:
                    await self.init(server)
            except:
                return
            
            set = self.settings[server.id]
                    
            message = """Current Bettermod's settings on this server:
                
role to mention: {}

channels:
    default: {}
    report: {}
    simple warning: {}
    kick warning: {}
    ban warning: {}
    
colors:
    report: {}
    simple warning: {}
    kick warning: {}
    ban warning: {}
                    
thumbnail's URL pictures:
    report: {}
    simple warning: {}
    kick warning: {}
    ban warning: {}""".format(discord.utils.get(server.roles, id=set['role']), set['channels']['general'], set['channels']['report'],  set['channels']['simple-warn'], set['channels']['kick-warn'], set['channels']['ban-warn'], set['colour']['report_embed'], set['colour']['warning_embed_simple'], set['colour']['warning_embed_kick'], set['colour']['warning_embed_ban'], set['thumbnail']['report_embed'], set['thumbnail']['warning_embed_simple'], set['thumbnail']['warning_embed_kick'], set['thumbnail']['warning_embed_ban'])
                        
            await self.bot.say("```{}```".format(message))

    @bmodset.command(pass_context=True, no_pm=True)
    async def channel(self, ctx, channel : discord.Channel = None):
        """Sets a channel as log"""
    
        if channel is None:
            channel = ctx.message.channel
        else:
            pass
    
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)

        self.settings[server.id]['channels']['general'] = channel.id
        await self.bot.say("Log messages and reports will be send to **" + channel.name + "**.")
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return

    @bmodset.command(pass_context=True, no_pm=True)
    async def mention(self, ctx, role: str = None):
        """Mention a specific role when a report is done.
            
        Give no argument to disable mention."""
        
        if ctx.message.server.id not in self.settings:
            await self.init(ctx.message.server)
    
        if role is None:
            self.settings[ctx.message.server.id]["role"] = None
            
            try:
                dataIO.save_json('data/bettermod/settings.json', self.settings)
            except:
                await self.error(ctx)
            
            await self.bot.say("The role mention is now disabled")

        else:
            
            object = discord.utils.get(ctx.message.server.roles, name=role)
                
            if object is None:
                await self.bot.say("The role cannot be found. Please give exact role name")
                return
                               
            if not object.mentionable:
                await self.bot.say("The role cannot be mentionned. Please modify its settings to enable `Allow anyone to @mention this role`")
                return
            
            self.settings[ctx.message.server.id]["role"] = object.id

            try:
                dataIO.save_json('data/bettermod/settings.json', self.settings)
            except:
                await self.error(ctx)

            await self.bot.say("The role {} will now be mentionned when a report is send".format(object.name))


    @bmodset.command(pass_context=True, no_pm=True)
    async def proof(self, ctx):
        """Enable or disable the proof-needed mode for reports
            
            If this mode is enabled, users will have to attach a file/link in order to report"""

        server = ctx.message.server
        
        if ctx.message.server.id not in self.settings:
            await self.init(ctx.message.server)
                
        if self.settings[server.id]['proof'] == False:
            self.settings[server.id]['proof'] = True
            
            try:
                dataIO.save_json('data/bettermod/settings.json', self.settings)
            except:
                await self.error(ctx)
                return

            await self.bot.say("The proof-needed mode is now enabled. Users will need to attach a link/file to their message in order to report. Type {}bmodset proof` again to disable it")
                
        else:
            self.settings[server.id]['proof'] = False
            
            try:
                dataIO.save_json('data/bettermod/settings.json', self.settings)
            except:
                await self.error(ctx)
                return
        
            await self.bot.say("The proof-needed mode is now disabled. Users will no longer need to attach a link/file to their message. Type {}bmodset proof` again to enable it")
            
            

    @bmodset.group(pass_context=True, no_pm=True)
    async def color(self, ctx):
        """Modify the embed color bar
            
        Please provide an hexadecimal color (same color character chain as discord roles). Example: #ffff = cyan
        Useful website: http://www.color-hex.com
        """

        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await self.bot.send_cmd_help(ctx)
                
    @color.command(pass_context=True, no_pm=True, name="report")
    async def report_color(self, ctx, color: str = '000000'):
        """Set the report embed color bar in the log channel
            
            Please provide an hexadecimal color (same color character chain as discord roles). Example: #ffff = cyan
            Useful website: http://www.color-hex.com
            """
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
    
        try:
            color = color.replace("#", "").replace("0x", "")[:6]
            color = int(color, 16)
        except ValueError:
            color = '000000'
            
        self.settings[server.id]['colour']['report_embed'] = color
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return
        await self.bot.say("New embed color has been registered. If the value is invalid, the color will not change.")

    @color.command(pass_context=True, no_pm=True, name="simple", aliases="1")
    async def simple_warn_color(self, ctx, color: str = '000000'):
        """Set the warning embed color bar in the log channel for the simple type
            
            Please provide an hexadecimal color (same color character chain as discord roles). Example: #ffff = cyan
            Useful website: http://www.color-hex.com
            """
        
        server = ctx.message.server
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)

        try:
            color = color.replace("#", "").replace("0x", "")[:6]
            color = int(color, 16)
        except ValueError:
            color = '000000'
        
        self.settings[server.id]['colour']['warning_embed_simple'] = color
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return
        await self.bot.say("New embed color has been registered. If the value is invalid, the color will not change.")
            

    @color.command(pass_context=True, no_pm=True, name="kick", aliases="2")
    async def kick_warn_color(self, ctx, color: str = '000000'):
        """Set the warning embed color bar in the log channel for the kick type
        
        Please provide an hexadecimal color (same color character chain as discord roles). Example: #ffff = cyan
        Useful website: http://www.color-hex.com
        """
            
        server = ctx.message.server
                
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
                        
        try:
            color = color.replace("#", "").replace("0x", "")[:6]
            color = int(color, 16)
        except ValueError:
            color = '000000'
                                        
        self.settings[server.id]['colour']['warning_embed_kick'] = color
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return
        await self.bot.say("New embed color has been registered. If the value is invalid, the color will not change.")
            
    @color.command(pass_context=True, no_pm=True, name="ban", aliases="3")
    async def ban_warn_color(self, ctx, color: str = '000000'):
        """Set the warning embed color bar in the log channel for the ban type
            
            Please provide an hexadecimal color (same color character chain as discord roles). Example: #ffff = cyan
            Useful website: http://www.color-hex.com
            """
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        try:
            color = color.replace("#", "").replace("0x", "")[:6]
            color = int(color, 16)
        except ValueError:
            color = '000000'
        
        self.settings[server.id]['colour']['warning_embed_ban'] = color
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return
        await self.bot.say("New embed color has been registered. If the value is invalid, the color will not change.")


    @bmodset.group(pass_context=True, no_pm=True)
    async def thumbnail(self, ctx):
        """Set the embed's thumbnail in the modlog"""
    
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await self.bot.send_cmd_help(ctx)

    @thumbnail.command(pass_context=True, no_pm=True, name="report")
    async def report_thumbnail(self, ctx, url: str):
        """Set the picture of the report embed in modlog"""
    
        server = ctx.message.server

        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)

        if not url.endswith(('.jpg', '.png', '.gif')) and not url.startswith(('http://', 'https://')):
            await self.bot.say("The URL given is not valid")
            return

        else:
            try:
                self.settings[server.id]['thumbnail']['report_embed'] = url
                dataIO.save_json('data/bettermod/settings.json', self.settings)
                await self.bot.say("The new thumbnail for the report embed has been set. If the URL is not valid, no thumbnail will be shown in the embed.")
            except:
                await self.error(ctx)
                return


    @thumbnail.command(name="simple", pass_context=True, no_pm=True)
    async def simple_thumbnail(self, ctx, *, url):
        """Set the picture of the simple warning embed in modlog"""
    
        server = ctx.message.server
    
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)

        if not url.endswith(('.jpg', '.png', '.gif')) and not url.startswith(('http://', 'https://')):
            await self.bot.say("The URL given is not valid")
            return
    
        else:
            try:
                self.settings[server.id]['thumbnail']['warning_embed_simple'] = url
                dataIO.save_json('data/bettermod/settings.json', self.settings)
                await self.bot.say("The new thumbnail for the simple warning embed has been set. If the URL is not valid, no thumbnail will be shown in the embed.")
            except:
                await self.error(ctx)
                return
                    
    @thumbnail.command(pass_context=True, no_pm=True, name="kick")
    async def kick_thumbnail(self, ctx, url: str):
        """Set the picture of the kick warning embed in modlog"""
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        if not url.endswith(('.jpg', '.png', '.gif')) and not url.startswith(('http://', 'https://')):
            await self.bot.say("The URL given is not valid")
            return
        
        else:
            try:
                self.settings[server.id]['thumbnail']['warning_embed_kick'] = url
                dataIO.save_json('data/bettermod/settings.json', self.settings)
                await self.bot.say("The new thumbnail for the kick warning embed has been set. If the URL is not valid, no thumbnail will be shown in the embed.")
            except:
                await self.error(ctx)
                return

    @thumbnail.command(pass_context=True, no_pm=True, name="ban")
    async def ban_thumbnail(self, ctx, url: str):
        """Set the picture of the ban warning embed in modlog"""
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
    
        if not url.endswith(('.jpg', '.png', '.gif')) and not url.startswith(('http://', 'https://')):
            await self.bot.say("The URL given is not valid")
            return
        
        else:
            try:
                self.settings[server.id]['thumbnail']['warning_embed_ban'] = url
                dataIO.save_json('data/bettermod/settings.json', self.settings)
                await self.bot.say("The new thumbnail for the ban warning embed has been set. If the URL is not valid, no thumbnail will be shown in the embed.")
            except:
                await self.error(ctx)
                return

    @bmodset.group(pass_context=True, no_pm=True, hidden=True)
    async def channels(self, ctx):
        """Set separately warnings and reports log channels"""

        if not ctx.invoked_subcommand or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await self.bot.send_cmd_help(ctx)


    @channels.command(pass_context=True, no_pm=True, name="report")
    async def report_channel(self, ctx, channel: discord.Channel):
        """Set a separate modlog for reports"""
    
        if channel is None:
            channel = ctx.message.channel
        else:
            pass
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        self.settings[server.id]['channels']['report'] = channel.id
        await self.bot.say("Reports will be send to **" + channel.name + "**.")
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return

    @channels.command(pass_context=True, no_pm=True, name="simple")
    async def simple_warning_channel(self, ctx, channel: discord.Channel):
        """Set a separate modlog for simple warnings"""
        
        if channel is None:
            channel = ctx.message.channel
        else:
            pass
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        self.settings[server.id]['channels']['simple-warn'] = channel.id
        await self.bot.say("Simple warnings will be send to **" + channel.name + "**.")
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return
                    
    @channels.command(pass_context=True, no_pm=True, name="kick")
    async def kick_warning_channel(self, ctx, channel: discord.Channel):
        """Set a separate modlog for kick warnings"""
                            
        if channel is None:
            channel = ctx.message.channel
        else:
            pass
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        self.settings[server.id]['channels']['kick-warn'] = channel.id
        await self.bot.say("Kick warnings will be send to **" + channel.name + "**.")
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return

    @channels.command(pass_context=True, no_pm=True, name="ban")
    async def ban_warning_channel(self, ctx, channel: discord.Channel):
        """Set a separate modlog for simple warnings"""
        
        if channel is None:
            channel = ctx.message.channel
        else:
            pass
        
        server = ctx.message.server
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
            
        self.settings[server.id]['channels']['ban-warn'] = channel.id
        await self.bot.say("Ban warnings will be send to **" + channel.name + "**.")
        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return


    @commands.command(pass_context=True)
    async def report(self, ctx, user: discord.Member, *, reason):
        """Report a user to the moderation team"""
    
        author = ctx.message.author
        server = ctx.message.server
        x = "" # empty string for searching any link leading to a URL in the message
        ok = False # indian coding methods
        words = ctx.message.content.split(' ')
    
        try:
            await self.bot.delete_message(ctx.message)
        except:
            pass

        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        if not self.settings[server.id]['channels']['general'] and not self.settings[server.id]['channels']['report']:
            await self.bot.say("The log channel is not set yet. Please use `" + ctx.prefix + "bmodset channel` to set it. Aborting...")
            return
        else:
            if not self.settings[server.id]['channels']['report']:
                channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['general'])
            else:
                channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['report'])

        if self.settings[server.id]['proof'] == True:
            if ctx.message.attachments == [] and 'http' not in ctx.message.content:
                await self.bot.send_message(author, "Proof-need mode is enabled on this server. Please attach a file or a link to your report in order to send it (screenshot the proof)")
                return

            if ctx.message.attachments !=[]:
                ok = True

            for word in words:
                if word.startswith('http'):
                    ok = True
                    break

            if ok == False:
                await self.bot.send_message(author, "Proof-need mode is enabled on this server. Please attach a file or a link to your report in order to send it (screenshot the proof)")
                return
                
        report = discord.Embed(title="Report", description="A user reported someone for an abusive behaviour")
        report.add_field(name="From", value=author.mention, inline=True)
        report.add_field(name="To", value=user.mention, inline=True)

        report.set_author(name="{}".format(user.name), icon_url=user.avatar_url)
        report.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        report.set_thumbnail(url=self.settings[server.id]['thumbnail']['report_embed'])
        try:
            report.color = discord.Colour(self.settings[server.id]['colour']['report_embed'])
        except:
            pass

        if ctx.message.attachments != []:
            report.set_image(url=ctx.message.attachments[0]['url'])
            report.add_field(name="Reason", value=reason+"\n\n[Click here to see proof URL]({})".format(ctx.message.attachments[0]['url']), inline=False)

        elif 'http' in ctx.message.content:

            for word in words:
                if word.startswith('http'):
                    report.set_image(url=word)
                    report.add_field(name="Reason", value=reason+"\n\n[Click here to see proof URL]({})".format(word), inline=False)
                    break
                    
        elif self.settings[server.id]['proof'] == False:
            report.add_field(name="Reason", value=reason, inline=False)
                        
        
        if self.settings[server.id]["role"] is None:

            try:
                await self.bot.send_message(channel, embed=report)
            except:
                await self.error(ctx)
                    
        else:
            role = discord.utils.get(server.roles, id=self.settings[server.id]["role"])
            try:
                await self.bot.send_message(channel, embed=report, content=role.mention)
            except:
                await self.error(ctx)
        
        await self.bot.say("Your report has been send to the moderation team")



    @commands.group(pass_context=True, no_pm=True)
    @checks.mod()
    async def warn(self, ctx):
        """Send a warning to a user and store it"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.mod_or_permissions(administrator=True)
    @warn.command(pass_context=True, no_pm=True, aliases="1")
    async def simple(self, ctx, user: discord.Member, *, reason: str):
        """Send a warning to the user in DM and store it"""

        try:
            await self.bot.delete_message(ctx.message)
        except:
            pass

        server = ctx.message.server
        author = ctx.message.author
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)

        if not self.settings[server.id]['channels']['general'] and not self.settings[server.id]['channels']['simple-warn']:
            await self.bot.say("The log channel is not set yet. Please use `" + ctx.prefix + "bmodset channel` to set it. Aborting...")
            return

        if not self.settings[server.id]['channels']['simple-warn']:
            channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['general'])
        else:
            channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['simple-warn'])

        if user == self.bot.user:
            await self.bot.say("Why do you want to report me :C I did nothing wrong (I cannot kick or ban myself)")
            return

        elif user.bot:
            await self.bot.say("Why trying to report a bot ? I cannot send message to bots, they cannot see them. Instead, go for the manual way.")
            return

        # This is the embed sent in the moderator log channel
        modlog = discord.Embed(title="Warning", description="A user got a level 1 warning")
        modlog.add_field(name="User", value=user.mention, inline=True)
        modlog.add_field(name="Moderator", value=author.mention, inline=True)
        modlog.add_field(name="Reason", value=reason, inline=False)
        modlog.set_author(name=user.name, icon_url=user.avatar_url)
        modlog.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        modlog.set_thumbnail(url=self.settings[server.id]['thumbnail']['warning_embed_simple'])
        try:
            modlog.color = discord.Colour(self.settings[server.id]['colour']['warning_embed_simple'])
        except:
            pass

        # This is the embed sent to the user
        target = discord.Embed(description="The moderation team set you a level 1 warning")
        target.add_field(name="Moderator", value=author.mention, inline=False)
        target.add_field(name="Reason", value=reason, inline=False)
        target.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        target.set_thumbnail(url=self.settings[server.id]['thumbnail']['warning_embed_simple'])
        try:
            target.color = discord.Colour(self.settings[server.id]['colour']['warning_embed_simple'])
        except:
            pass

        try:
            await self.bot.send_message(user, embed=target)
        except:
            modlog.set_footer(text="I couldn't send a message to this user. He may has blocked messages from this server.")

        await self.bot.send_message(channel, embed=modlog)

        await self.add_case(level='Simple', user=user, reason=reason, timestamp=ctx.message.timestamp.strftime("%d %b %Y %H:%M"), server=server, applied=1, ctx=ctx)


    @checks.mod_or_permissions(administrator=True)
    @warn.command(pass_context=True, no_pm=True, aliases="2")
    async def kick(self, ctx, user: discord.Member, *, reason: str):
        """Send a warning to the user in DM and store it, while kicking him"""
        
        try:
            await self.bot.delete_message(ctx.message)
        except:
            pass
        
        server = ctx.message.server
        author = ctx.message.author
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)
        
        if not self.settings[server.id]['channels']['general'] and not self.settings[server.id]['channels']['kick-warn']:
            await self.bot.say("The log channel is not set yet. Please use `" + ctx.prefix + "chanlog` to set it. Aborting...")
            return
        else:
            if not self.settings[server.id]['channels']['kick-warn']:
                channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['general'])
            else:
                channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['kick-warn'])

        if user == self.bot.user:
            await self.bot.say("Why do you want to report me :C I did nothing wrong (I cannot kick or ban myself)")
            return
        
        elif user.bot:
            await self.bot.say("Why trying to report a bot ? I cannot send message to bots, they cannot see them. Instead, go for the manual way.")
            return
        
        # This is the embed sent in the moderator log channel
        modlog = discord.Embed(title="Warning", description="A user got a level 2 (kick) warning")
        modlog.add_field(name="User", value=user.mention, inline=True)
        modlog.add_field(name="Moderator", value=author.mention, inline=True)
        modlog.add_field(name="Reason", value=reason, inline=False)
        modlog.set_author(name=user.name, icon_url=user.avatar_url)
        modlog.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        modlog.set_thumbnail(url=self.settings[server.id]['thumbnail']['warning_embed_kick'])
        try:
            modlog.color = discord.Colour(self.settings[server.id]['colour']['warning_embed_kick'])
        except:
            pass
        
        # This is the embed sent to the user
        target = discord.Embed(description="The moderation team set you a level 2 (kick) warning")
        target.add_field(name="Moderator", value=author.mention, inline=False)
        target.add_field(name="Reason", value=reason, inline=False)
        target.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        target.set_thumbnail(url=self.settings[server.id]['thumbnail']['warning_embed_kick'])
        try:
            target.color = discord.Colour(self.settings[server.id]['colour']['warning_embed_kick'])
        except:
            pass
        
        try:
            await self.bot.send_message(user, embed=target)
        except:
            modlog.set_footer(text="I couldn't send a message to this user. He may has blocked messages from this server.")
        
        try:
            await self.bot.kick(user)
        except:
            await self.bot.say("I cannot kick this user, he higher than me in the role hierarchy. Aborting...")
            await self.bot.send_message(channel, content="The user was not kick. Check my permissions", embed=modlog)
            await self.add_case(level='Kick', user=user, reason=reason, timestamp=ctx.message.timestamp.strftime("%d %b %Y %H:%M"), server=server, applied=0, ctx=ctx)
            return

        await self.bot.send_message(channel, embed=modlog)

        await self.add_case(level='Kick', user=user, reason=reason, timestamp=ctx.message.timestamp.strftime("%d %b %Y %H:%M"), server=server, applied=1, ctx=ctx)


# add temp ban warning


    @checks.mod_or_permissions(administrator=True)
    @warn.command(pass_context=True, no_pm=True, aliases="3")
    async def ban(self, ctx, user: discord.Member, *, reason: str):
        """Send a warning to the user in DM and store it, while banning him"""
        
        try:
            await self.bot.delete_message(ctx.message)
        except:
            pass
        
        server = ctx.message.server
        author = ctx.message.author
        
        try:
            if server.id not in self.settings:
                await self.init(server)
        except:
            await self.error(ctx)

        if not self.settings[server.id]['channels']['general'] and not self.settings[server.id]['channels']['ban-warn']:
            await self.bot.say("The log channel is not set yet. Please use `" + ctx.prefix + "chanlog` to set it. Aborting...")
            return
        else:
            if not self.settings[server.id]['channels']['ban-warn']:
                channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['general'])
            else:
                channel = discord.utils.get(server.channels, id=self.settings[server.id]['channels']['ban-warn'])
        
        if user == self.bot.user:
            await self.bot.say("Why do you want to report me :C I did nothing wrong (I cannot kick or ban myself)")
            return
        
        elif user.bot:
            await self.bot.say("Why trying to report a bot ? I cannot send message to bots, they cannot see them. Instead, go for the manual way.")
            return
        
        # This is the embed sent in the moderator log channel
        modlog = discord.Embed(title="Warning", description="A user got a level 3 (ban) warning")
        modlog.add_field(name="User", value=user.mention, inline=True)
        modlog.add_field(name="Moderator", value=author.mention, inline=True)
        modlog.add_field(name="Reason", value=reason, inline=False)
        modlog.set_author(name=user.name, icon_url=user.avatar_url)
        modlog.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        modlog.set_thumbnail(url=self.settings[server.id]['thumbnail']['warning_embed_ban'])
        try:
            modlog.color = discord.Colour(self.settings[server.id]['colour']['warning_embed_ban'])
        except:
            pass
        
        # This is the embed sent to the user
        target = discord.Embed(description="The moderation team set you a level 3 (ban) warning")
        target.add_field(name="Moderator", value=author.mention, inline=False)
        target.add_field(name="Reason", value=reason, inline=False)
        target.set_footer(text=ctx.message.timestamp.strftime("%d %b %Y %H:%M"))
        target.set_thumbnail(url=self.settings[server.id]['thumbnail']['warning_embed_ban'])
        try:
            target.color = discord.Colour(self.settings[server.id]['colour']['warning_embed_ban'])
        except:
            pass
        
        try:
            await self.bot.send_message(user, embed=target)
        except:
            modlog.set_footer(text="I couldn't send a message to this user. He may has blocked messages from this server.")

        try:
            await self.bot.ban(user)
        except:
            await self.bot.say("I cannot ban this user, he higher than me in the role hierarchy. Aborting...")
            await self.bot.send_message(channel, content="The user was not ban. Check my permissions", embed=modlog)
            await self.add_case(level='Ban', user=user, reason=reason, timestamp=ctx.message.timestamp.strftime("%d %b %Y %H:%M"), server=server, applied=0, ctx=ctx)
            return

        await self.bot.send_message(channel, embed=modlog)

        await self.add_case(level='Ban', user=user, reason=reason, timestamp=ctx.message.timestamp.strftime("%d %b %Y %H:%M"), server=server, applied=1, ctx=ctx)

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def case(self, ctx):
        """Edit warnings' reasons or remove them"""
    
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)


    @commands.command(pass_context=True)
    async def bcheck(self, ctx, case: int, user: discord.Member = None):
        """Give the sanction and the reason of a specific case
            
            If 0 is given, all of the cases of the user will be given
            You need to be at least moderator to see other's warnings"""
        
        server = ctx.message.server
        author = ctx.message.author
        allowed = False
        
        if not os.path.isfile('data/bettermod/history/{}.json'.format(server.id)):
            print("Creating empty {}".format(server.id))
            try:
                dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), data={})
            except:
                await self.error(ctx)
                return
                    
        try:
            history = dataIO.load_json('data/bettermod/history/{}.json'.format(server.id))
        except:
            await self.error(ctx)
            return
        
        if user is None:
            user = ctx.message.author
            allowed = True

        
        if author == server.owner or author.id == self.bot.settings.owner or author.server_permissions.administrator:
            allowed = True
        
        for role in author.roles:
        
            if server.id not in self.red:
                
                if role.name == self.red['default']['ADMIN_ROLE']:
                    allowed = True
                
                if role.name == self.red['default']['MOD_ROLE']:
                    allowed = True

            else:
                
                if role.name == self.red[server.id]['ADMIN_ROLE']:
                    allowed = True
                if role.name == self.red[server.id]['MOD_ROLE']:
                    allowed = True

                        
        if allowed is False:
            await self.bot.say("You are not allowed to check others's warnings")
            return
        

        if user.id not in history:
            if user != author:
                await self.bot.say("That user doesn't have any warnings yet")
                return
            
            else:
                await self.bot.say("You don't have any warning yet")
                return

        if case < 0 or case > history[user.id]['total-warns']:
            await self.bot.say("That case does not exist")
            return

        if case == 0:

            e = discord.Embed(description="General user infos")
            e.set_author(name=user, icon_url=user.avatar_url)

            e.add_field(name=u"\u2063", value="Total warns: {}\nSimple warns: {}\nKick warns: {}\nBan warns: {}".format(str(history[user.id]['total-warns']), str(history[user.id]['simple-warn']), str(history[user.id]['kick-warn']), str(history[user.id]['ban-warn'])))

            e.set_footer(text="Click on the reaction to see all of the cases")
            
            try:
                msg = await self.bot.say(embed=e)
            except:
                await self.error(ctx)
                return
            
            i = None
            await self.check_case(msg, i, ctx=ctx, user=user)

        else:
            i = case
            await self.check_case(msg=None, i=i, ctx=ctx, user=user)

        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
        except:
            await self.error(ctx)
            return


    @case.command(pass_context=True)
    async def delete(self, ctx, case: int, user: discord.Member):
        """Delete a case"""

        server = ctx.message.server
        if not os.path.isfile('data/bettermod/history/{}.json'.format(server.id)):
            print("Creating empty {}".format(server.id))
            try:
                dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), data={})
            except:
                await self.error(ctx)
                return
    
        try:
            history = dataIO.load_json('data/bettermod/history/{}.json'.format(server.id))
        except:
            await self.erro(ctx)
            return

        if user.id not in history:
            await self.bot.say("That user does not have any warning yet")
            return
        
        if case < 0 or case > history[user.id]['total-warns'] or history[user.id]['case{}'.format(str(case))]['deleted'] == 1:
            await self.bot.say("That case does not exist or is already deleted")
            return
        
        e = discord.Embed(description="User case {} delete".format(str(case)))
        e.set_author(name=user.name, icon_url=user.avatar_url)
        
        e.add_field(name="Reason", value=history[user.id]['case{}'.format(str(case))]['reason'], inline=False)
        
        if history[user.id]['case{}'.format(str(case))]['level'] == "Simple":
            e.add_field(name="Total simple warnings", value="Before: {}\nAfter: {}".format(history[user.id]['simple-warn'], history[user.id]['simple-warn']- 1), inline=True)
        
        elif history[user.id]['case{}'.format(str(case))]['level'] == "Kick":
            e.add_field(name="Total kick warnings", value="Before: {}\nAfter: {}".format(history[user.id]['kick-warn'], history[user.id]['kick-warn'] - 1), inline=True)
        
        elif history[user.id]['case{}'.format(str(case))]['level'] == "Ban":
            e.add_field(name="Total ban warnings", value="Before: {}\nAfter: {}".format(history[user.id]['ban-warn'], history[user.id]['ban-warn'] - 1), inline=True)

        e.add_field(name="Total warnings", value="Before: {}\nAfter: {}".format(history[user.id]['total-warns'], history[user.id]['total-warns'] - 1), inline=True)

        e.set_footer(text="Click on the reaction to confirm changes")


        try:
            msg = await self.bot.say(embed=e)
            await self.bot.add_reaction(msg, "✅")
        except:
            await self.error(ctx)
            return

        response = await self.bot.wait_for_reaction(emoji="✅", user=ctx.message.author, message=msg, timeout=30)
        
        if response is None:
            await self.bot.clear_reactions(msg)
            return

        if response.reaction.emoji == '✅':
            
            if history[user.id]['case{}'.format(str(case))]['level'] == "Simple":
                history[user.id]['simple-warn'] = history[user.id]['simple-warn'] - 1

            elif history[user.id]['case{}'.format(str(case))]['level'] == "Kick":
                history[user.id]['kick-warn'] = history[user.id]['kick-warn'] - 1
        
            elif history[user.id]['case{}'.format(str(case))]['level'] == "Ban":
                history[user.id]['ban-warn'] = history[user.id]['ban-warn'] - 1

            history[user.id]['total-warns'] = history[user.id]['total-warns'] - 1
            history[user.id]['case{}'.format(str(case))]['deleted'] = 1
            try:
                await self.bot.delete_message(msg)
            except:
                await self.error(ctx)
                return
            await self.bot.say("The case {} of {} has been deleted".format(str(case), user.name))

        try:
            dataIO.save_json('data/bettermod/settings.json', self.settings)
            dataIO.save_json('data/bettermod/history/{}.json'.format(ctx.message.server.id), history)
        except:
            await self.error(ctx)
            return
        

    @case.command(pass_context=True)
    async def edit(self, ctx, case: int, user: discord.Member, *, reason):
        """Edit the reason of the specified case"""

        server = ctx.message.server
        if not os.path.isfile('data/bettermod/history/{}.json'.format(server.id)):
            print("Creating empty {}".format(server.id))
            try:
                dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), data={})
            except:
                await self.error(ctx)
                return
    
        try:
            history = dataIO.load_json('data/bettermod/history/{}.json'.format(server.id))
        except:
            await self.erro(ctx)
            return
    
        if user.id not in history:
            await self.bot.say("That user does not have any warning yet")
            return
        
        if case < 0 or case > history[user.id]['total-warns']:
            await self.bot.say("That case does not exist")
            return

        old_reason = history[user.id]['case{}'.format(str(case))]['reason']

        e = discord.Embed(description="User case {} reason change".format(str(case)))
        e.set_author(name=user.name, icon_url=user.avatar_url)

        e.add_field(name="Old reason", value=old_reason, inline=True)
        e.add_field(name="New reason", value=reason, inline=True)
        e.set_footer(text="Click on the reaction to confirm changes")
        
        try:
            msg = await self.bot.say(embed=e)
            await self.bot.add_reaction(msg, "✅")
        except:
            await self.error(ctx)
            return

        response = await self.bot.wait_for_reaction(emoji="✅", user=ctx.message.author, message=msg, timeout=30)

        if response is None:
            await self.bot.clear_reactions(msg)
            return

        if response.reaction.emoji == '✅':
            history[user.id]['case{}'.format(str(case))]['reason'] = reason

        dataIO.save_json('data/bettermod/history/{}.json'.format(server.id), history)
        try:
            await self.bot.delete_message(msg)
        except:
            await self.error(ctx)
            return
        
        await self.bot.say("The new reason has been saved")

def check_folders():
    folders = ('data', 'data/bettermod/', 'data/bettermod/history/')
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    ignore_list = {'SERVERS': [], 'CHANNELS': []}
    
    files = {
        'settings.json'         : {}
    }
    
    for filename, value in files.items():
        if not os.path.isfile('data/bettermod/{}'.format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json('data/bettermod/{}'.format(filename), value)


def check_version_settings():
    
    settings = dataIO.load_json('data/bettermod/settings.json')
    
    if "version" not in settings: # json body not up-to-date
        
        settings['version'] = "1.1"
        
        for server in settings:
            if server != "version":
                
                # Add here new body
                settings[server]['role'] = None
            
        dataIO.save_json('data/bettermod/settings.json', settings)
        print("Json body of data/bettermod/settings.json was successfully updated")


    if settings['version'] == "1.1": # json body not up-to-date
    
        settings['version'] = "1.2"
    
        for server in settings:
            if server != "version":
            
                # Add here new body
                
                if settings[server]['thumbnail']['report_embed'] == 'https://cdn.discordapp.com/attachments/303988901570150401/360466192781017088/report.png':
                    settings[server]['thumbnail']['report_embed'] = 'https://i.imgur.com/Bl62rGd.png'
                
                if settings[server]['thumbnail']['warning_embed_simple'] == 'https://cdn.discordapp.com/attachments/303988901570150401/360466192781017088/report.png':
                    settings[server]['thumbnail']['warning_embed_simple'] = 'https://i.imgur.com/Bl62rGd.png'
                
                if settings[server]['thumbnail']['warning_embed_kick'] == 'https://cdn.discordapp.com/attachments/303988901570150401/360466190956494858/kick.png':
                    settings[server]['thumbnail']['warning_embed_kick'] = 'https://i.imgur.com/uhrYzyt.png'
                
                if settings[server]['thumbnail']['warning_embed_ban'] == 'https://media.discordapp.net/attachments/303988901570150401/360466189979222017/ban.png':
                    settings[server]['thumbnail']['warning_embed_ban'] = 'https://i.imgur.com/DfBvmic.png'
            
        dataIO.save_json('data/bettermod/settings.json', settings)
        print("Json body of data/bettermod/settings.json was successfully updated")

    if settings['version'] == "1.2":

        settings['version'] = "1.3"

        for server in settings:
            if server != "version":
                
                try:
                    settings[server]['channels'] = {
                        "general": settings[server]['mod-log'],
                        "report": None,
                        "simple-warn": None,
                        "kick-warn": None,
                        "ban-warn": None
                    }
                except KeyError:
                    pass

        dataIO.save_json('data/bettermod/settings.json', settings)
        print("Json body of data/bettermod/settings.json was successfully updated")

    if settings['version'] == "1.3":

        settings['version'] = "1.4"

        for server in settings:
            if server != "version":

                settings[server]['proof'] = False

        dataIO.save_json('data/bettermod/settings.json', settings)
        print("Json body of data/bettermod/settings.json was successfully updated")


def check_version_history():
    
    for file in os.listdir('data/bettermod/history'):
        if file.endswith('.json'):
            file_json = dataIO.load_json('data/bettermod/history/{}'.format(file))
            if "version" not in file_json: # a log file is not up-to-date (usually means all the files aren't up-to-date)
                file_json['version'] = "1.1"
                    
                # Add here new body
                
                dataIO.save_json('data/bettermod/history/{}'.format(file), file_json)
                print("Json body of data/bettermod/history/{} was successfully updated".format(file))


def setup(bot):
    check_folders()
    check_files()
    check_version_settings()
    check_version_history()
    bot.add_cog(BetterMod(bot))
