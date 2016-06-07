import discord
from discord.ext import commands

class Dogcog:
	"""The DogCog, it makes woofing noises."""

	def __init__(self, bot):
		self.bot = bot

		
		
	@commands.command(hidden=True)
	async def dogcom(self):
		"""Default command!"""

		#Your code will go here
		await self.bot.say("[](/scootasquint) Hey!!")
		
	@commands.command()
	@checks.serverowner_or_permissions(administrator=True)
	async def print(self, *, message : str):
		"""Prints message"""
		await self.bot.say(message)

def setup(bot):
	bot.add_cog(Dogcog(bot))
