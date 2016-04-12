import discord
from discord.ext import commands
import random
try: #check if wikia is installed
	import wikia
	wikiaAvailable = True
except:
	wikiaAvailable = False

class Bdwiki:
	"""Fetching stuff"""

	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context = True)
	async def bdwiki(self, ctx, search):
		"""Gets info from Black Desert wikia"""

		def is_number(s):
			try:
				int(s)
				return True
			except ValueError:
				return False

		result = wikia.search("Blackdesert", search)
		await self.bot.say("Found in wikia:\n")
		for item in enumerate(result):
			await self.bot.say(str(item[0]) + ") " + item[1] + '\n')
		await self.bot.say("Choose required topic by typing it's number")

		answer = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
		if is_number(answer.content.strip()):
			data = wikia.page("Blackdesert", result[int(answer.content.strip())])
			await self.bot.say(data.title + '\n' + data.content + '\n' + data.url)
		else:
			await self.bot.say("Incorrect response, search again")

def setup(bot):
	if wikiaAvailable is False:
		raise RuntimeError("You don't have wikia installed, run\n```pip3 install wikia```And try again")
		return
	bot.add_cog(Bdwiki(bot))
