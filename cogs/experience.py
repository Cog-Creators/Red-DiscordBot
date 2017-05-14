import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os
import json
import re

class Experience:
    """Keeps track of user experience."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/red/settings.json", "load")

    def is_int(self, s):
	    try: 
	        int(s)
	        return True
	    except ValueError:
	        return False

    async def add_xp(self, message):
        #if not message.author.bot:
            prefixes = self.settings['PREFIXES']
            content = message.content
            valid = True
            for prefix in prefixes:
                if prefix in content[0:5]:
                    valid = False
            if valid:
                file = 'data/experience/experience.json'
                experience = fileIO(file, "load")
                server = message.server.id
                author_mention = message.author.mention
                author = message.author.name
                if not server in experience:
                    experience[server] = {}
                else:
                    if not author_mention in experience[server]:
                        parse = re.sub(r"http\S+", "", message.content)
                        experience[server][author_mention] = {}
                        experience[server][author_mention]['USERNAME'] = author
                        experience[server][author_mention]['TOTAL_XP'] = int(len(parse))
                        experience[server][author_mention]['IGNORE'] = False
                    else:
                        if not experience[server][author_mention]['IGNORE']:
                            experience[server][author_mention]['USERNAME'] = author
                            experience[server][author_mention]['TOTAL_XP'] += int(len(message.content))
                fileIO(file, "save", experience)

    @commands.command(name="xp", aliases=["shamelist", "score"], pass_context=True)
    async def xp(self, context, *userid : str):
        """The user experience list"""
        file = 'data/experience/experience.json'
        experience = fileIO(file, "load")
        server = context.message.server.id
        experience = experience[server]
        if userid:
        	if userid[0] in experience:
        		message = '`{0} has {1} XP.`'.format(experience[userid[0]]['USERNAME'], experience[userid[0]]['TOTAL_XP'])
        	else:
        		message = '`\'{0}\' is not in my database.`'.format(userid[0])
        else:
	        xp = sorted(experience, key=lambda x: (experience[x]['TOTAL_XP']), reverse=True)
	        message = '```The XP highscores of {0}.\n\n'.format(context.message.server.name)
	        i = 1
	        for userid in xp:
	        	message+='{0} {1} {2}\n'.format(str(i).ljust(3), str(experience[userid]['TOTAL_XP']).ljust(9), experience[userid]['USERNAME'])
	        	i+=1
	        	if i > 15:
	        		break
	        message+='```'
        await self.bot.say(message)

    @commands.command(name="xpset", pass_context=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def xpset(self, context, *arguments : str):
    	file = 'data/experience/experience.json'
    	experience = fileIO(file, "load")
    	server = context.message.server.id
    	if arguments:
    		if arguments[0] in experience[server]:
    			if arguments[1]:
	    			if self.is_int(arguments[1]):
	    				experience[server][arguments[0]]['TOTAL_XP'] = int(arguments[1])
	    				fileIO(file, "save", experience)
	    			else:
	    				message = '`Value must be an integer.`'
	    		else:
	    			message = '`Value must be an integer.`'
    		else:
    			message = '`Who?`'
    	else:
    		message = '`Request help for more information.`'
    	await self.bot.say(message)

    @commands.command(name="xpignore", pass_context=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def xpignore(self, context, *arguments : str):
        file = 'data/experience/experience.json'
        experience = fileIO(file, "load")
        server = context.message.server.id
        if arguments:
            if arguments[0] in experience[server]:
                if arguments[1].upper() == 'TRUE':
                    experience[server][arguments[0]]['IGNORE'] = True
                    fileIO(file, "save", experience)
                    message = 'Ignoring {0}'.format(arguments[0])
                    
                elif arguments[1].upper() == 'FALSE':
                    experience[server][arguments[0]]['IGNORE'] = False
                    fileIO(file, "save", experience)
                    message = 'Listening to {0}'.format(arguments[0])
                else:
                    message = '`Value must be either True or False.`'
            else:
                message = '`Who?`'
        else:
            message = '`Request help for more information.`'
        await self.bot.say(message)


def check_folder():
    if not os.path.exists("data/experience"):
        print("Creating data/experience folder...")
        os.makedirs("data/experience")

def check_file():
    experience = {}
    f = "data/experience/experience.json"
    if not fileIO(f, "check"):
        print("Creating default experience.json...")
        fileIO(f, "save", experience)

def setup(bot):
	check_folder()
	check_file()
	n = Experience(bot)
	bot.add_listener(n.add_xp, "on_message")
	bot.add_cog(n)