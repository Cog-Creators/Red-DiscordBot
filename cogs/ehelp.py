import asyncio
from discord.ext import commands
import discord
import inspect
import importlib
import sys
import traceback
import re
import unicodedata
import datetime
import unicodedata
from random import randint
from random import choice as randchoice
mentions_transforms = {
    '@everyone': '@\u200beveryone',
    '@here': '@\u200bhere'
}

mention_pattern = re.compile('|'.join(mentions_transforms.keys()))
class helpc:
    """Embed OP Help"""
    def __init__(self, bot):
        self.bot = bot


    @commands.command(pass_context=True, hidden=True)
    async def help(self, ctx, *commands : str):
        """Shows This Command"""
        def repl(obj):
            return mentions_transforms.get(obj.group(0), '')
        channel = ctx.message.channel
        author = ctx.message.author
        destination = author if self.bot.pm_help else channel
        my = ctx.message.server.me if not channel.is_private else self.bot.user
        #If no argument is passed, hopefully this will list all the commands (except hidden ones)
        if len(commands) == 0:
            pages = self.bot.formatter.format_help_for(ctx, self.bot)
        elif len(commands) == 1:
            #First we will see if it is a cog name, then we will check for a command
            name = mention_pattern.sub(repl, commands[0])
            command = None
            if name in self.bot.cogs:
                #It is not a command but a cog
                command = self.bot.cogs[name]
            else:
                #It is a command and not a cog
                command = self.bot.commands.get(name)
                if command is None:
                    try:
                        await self.bot.send_message(destination, embed = discord.Embed(title = "Error \U0000274e", description =  self.bot.command_not_found.format(name), colour =0x90181e))
                    except discord.Forbidden:
                        await self.bot.send_message(destination, self.bot.command_not_found.format(name))
                    return

            pages = self.bot.formatter.format_help_for(ctx, command)
        else:
            name = (commands[0]).replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
            command = self.bot.commands.get(commands[0])
            if command is None:
                try:
                    await self.bot.send_message(destination, embed = discord.Embed(title = "Error \U0000274e", description =  self.bot.command_not_found.format(name), colour =0x90181e))
                except discord.Forbidden:
                    await self.bot.send_message(destination, self.bot.command_not_found.format(name))
                return

            for key in commands[1:]:
                try:
                    key = mention_pattern.sub(repl, key)
                    command = command.commands.get(key)
                    if command is None:
                        try:
                            await self.bot.send_message(destination, embed = discord.Embed(title = "Error \U0000274e", description =  self.bot.command_not_found.format(key), colour =0x90181e))
                        except discord.Forbidden:
                            await self.bot.send_message(destination, self.bot.command_not_found.format(key))
                        return
                except AttributeError:
                    try:
                        await self.bot.send_message(destination, embed = discord.Embed(title = "Error \U0000274e", description =  self.bot.command_has_no_subcommands.format(command, key), colour =0x90181e))
                    except discord.Forbidden:
                        await self.bot.send_message(destination, self.bot.command_has_no_subcommands.format(command, key))
                    return

            pages = self.bot.formatter.format_help_for(ctx, command)

        if self.bot.pm_help is None:
            characters = sum(map(lambda l: len(l), pages))
            # modify destination based on length of pages.
            if characters > 1000:
                destination = ctx.message.author
        else:
            pass
        #consistency check. we don't want a blank help command do we
        if my.permissions_in(channel).embed_links:
            #now we have the help builder with everything defined
            #all we need to check now is if the page is 1 or not 
            #so our embed builder can recognize it with ease
            if len(pages) == 1:
                #it is either a command or a cog since we are recieving a page from the formatter
                # now to start the procedure
                info = "".join(e for e in pages)
                info = info.replace("`","")
                colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
                colour = int(colour, 16)
                e = discord.Embed()
                e.set_author(name = "Command Help", icon_url = my.avatar_url)
                if len(commands) != 0 and commands[0] in self.bot.cogs:
                    e.title = "Category Help | {}".format(commands[0])
                elif len(commands) != 0 and commands[0] in self.bot.commands:
                    e.title = "Command Help | {0}{1}".format(ctx.prefix, commands[0])
                e.colour = colour
                e.description = info
                e.timestamp = ctx.message.timestamp
                e.set_footer(text = "{} Help Command".format(my.name))
                await self.bot.send_message(destination, embed = e)
            else:
                #this is where all the hecked up stuff happens
                #since this is a dm, we will send a selfmade description
                page_no = 1
                colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
                colour = int(colour, 16)
                for page in pages:
                    desc = "".join(e for e in page)
                    desc = desc.replace("`","")
                    clr = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
                    a = discord.Embed()
                    a.title = "Bot Commands"
                    a.set_author(name = my.name, icon_url= my.avatar_url)
                    a.timestamp = ctx.message.timestamp
                    a.description = desc
                    a.colour = 0x90181e
                    a.set_footer(text = "Page: {0} of {1}".format(page_no, len(pages)))
                    await self.bot.send_message(destination, embed = a)
                    page_no += 1
        else:
            for page in pages:
                await self.bot.send_message(destination, page)

def setup(bot):
    bot.remove_command('help')
    n = helpc(bot)
    bot.add_cog(n)
