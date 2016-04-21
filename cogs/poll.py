import discord
from discord.ext import commands
from .utils.dataIO import fileIO
import os

class Poll:
	"""Le poll cog. Does conflict with Red's default poll."""
	def __init__(self, bot):
		self.bot = bot
		self.poll_data = 'data/poll/poll.json'

	@commands.group(pass_context=True, no_pm=True)
	async def poll(self, context):
		"""poll <start|stop|current> Do you like fruit?;Yes;No;Maybe;Perhaps (..)"""
		pass

	@commands.command(pass_context=True)
	async def vote(self, context, vote : str):
		"""vote <option>"""
		settings = fileIO(self.poll_data, "load")
		user_id = context.message.author.id
		user_name = context.message.author.name
		channel = context.message.channel.id
		message = 'Nah'
		if channel in settings:
			if not user_id in settings[channel]['VOTERS']:
				if vote.upper() in settings[channel]['OPTIONS']:
					settings[channel]['OPTIONS'][vote.upper()] += 1
					settings[channel]['VOTERS'] = user_id
					fileIO(self.poll_data, "save", settings)
					message = '{0} just voted *{1}*!'.format(user_name, vote)
			else:
				message = 'You\'ve already voted!'
		else:
			message = 'No poll active'
		await self.bot.say(message)

	@poll.command(pass_context=True, no_pm=True)
	async def start(self, context, *arguments : str):
		"""poll start <question>;option;option;option (...)"""
		settings = fileIO(self.poll_data, "load")
		channel = context.message.channel.id
		starter = context.message.author.name
		if not channel in settings:
			poll = " ".join(arguments).split(';')
			question = poll[0]
			settings[channel] = {}
			settings[channel]['STARTER'] = starter
			settings[channel]['VOTERS'] = []
			settings[channel]['QUESTION'] = question
			settings[channel]['OPTIONS'] = {}
			for option in poll[1:]:
				settings[channel]['OPTIONS'][option.upper()] = 0			
			message = '{0} started a poll with the question *{1}*'.format(starter, question)
			fileIO(self.poll_data, "save", settings)
		await self.bot.say(message)

	@poll.command(pass_context=True, no_pm=True)
	async def current(self, context):
		"""Shows current poll results."""
		settings = fileIO(self.poll_data, "load")
		channel = context.message.channel.id
		starter = context.message.author.name
		if channel in settings:
			question = settings[channel]['QUESTION']
			options = ''
			for option in settings[channel]['OPTIONS']:
				options+='{0} {1}\n'.format(option.capitalize().ljust(4), settings[channel]['OPTIONS'][option])
			message = '```Current statistics of {0}\n\n{1}```'.format(question, options)
		else:
			message = 'There\'s no poll active in this channel.'
		await self.bot.say(message)

	@poll.command(pass_context=True, no_pm=True)
	async def stop(self, context):
		"""Stops the poll. Only for the poll starter."""
		settings = fileIO(self.poll_data, "load")
		channel = context.message.channel.id
		starter = context.message.author.name
		if channel in settings:
			if settings[channel]['STARTER'] == starter:
				question = settings[channel]['QUESTION']
				options = ''
				for option in settings[channel]['OPTIONS']:
					options+='{0} {1}\n'.format(option.capitalize().ljust(4), settings[channel]['OPTIONS'][option])
				message = '```Results of {0}\n\n{1}```'.format(question, options)
				del settings[channel]
				fileIO(self.poll_data, "save", settings)
			else:
				message = 'You didn\'t start the poll.'
		else:
			message = 'There\'s no poll active in this channel.'
		await self.bot.say(message)
   

def check_folder():
    if not os.path.exists("data/poll"):
        print("Creating data/poll folder...")
        os.makedirs("data/poll")

def check_file():
    poll = {}
    f = "data/poll/poll.json"
    if not fileIO(f, "check"):
        print("Creating default poll.json...")
        fileIO(f, "save", poll)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Poll(bot))