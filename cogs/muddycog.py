import discord
from discord.ext import commands

class Muddycog:
	"""The MuddyCog, it looks like a Butterfree."""

	def __init__(self, bot):
		self.bot = bot

		
		
	@commands.command(hidden=True)
	async def defcom(self):
		"""Default command!"""

		#Your code will go here
		await self.bot.say("[](/scootasquint) Hey!!")

def setup(bot):
	bot.add_cog(Muddycog(bot))
