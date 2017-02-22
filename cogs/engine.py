import discord
from discord.ext import commands


class Engine:
	"""leavin you in the dust!"""
	def __init__(self,bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def vroom(self, ctx):
		"""You don't need no instruction manual to be free!!"""
		await self.bot.say("VROOM VROOM!")

def setup(bot):
	n = Engine(bot)
	bot.add_cog(n)