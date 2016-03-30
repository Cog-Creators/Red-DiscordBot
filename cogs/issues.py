import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os

class Issues:
	"""Resolves basic issues"""

	def __init__(self, bot):
		self.bot = bot
		self.issues_list = fileIO("data/issues/list.json", "load")

	@commands.command(pass_context = True)
	async def issue(self, ctx):
		"""Resolves basic issues with Red"""

		await self.bot.say("Before filing any issues, answer some basic questions, please")

		for i, issue in enumerate(self.issues_list):
			await self.bot.say(str(i+1) + ") " +issue["q"] + " (yes/no)")
			answer = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
			if answer is None:
				await self.bot.say("Ok, exiting helpfull mode, deal with it youself")
			elif answer.content.lower().strip() == "yes":
				if not "y" in issue:
					continue
				else:
					await self.bot.say(issue["y"])
					break
			elif answer.content.lower().strip() == "no":
				if not "n" in issue:
					continue
				else:
					await self.bot.say(issue["n"])
					break
			else:
				await self.bot.say("Ok, exiting helpfull mode, deal with it youself")

def check_folders():
	if not os.path.exists("data/issues"):
		print("Creating data/issues folder...")
		os.makedirs("data/issues")

def check_files():
	f = "data/issues/list.json"
	if not fileIO(f, "check"):
		print("Creating empty list.json...")
		fileIO(f, "save", [])

def setup(bot):
	check_folders()
	check_files()
	bot.add_cog(Issues(bot))