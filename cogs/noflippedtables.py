import discord
from discord.ext import commands
from random import uniform as randfloat
import asyncio
import os
from .utils.dataIO import fileIO
import re
from __main__ import send_cmd_help

class Untableflip:
	"""For the table sympathizers"""

	def __init__(self, bot):
		self.bot = bot
		self.settings = fileIO("data/noflippedtables/settings.json", "load")
		self.flippedTables = {}

	@commands.group(pass_context=True)
	async def tableset(self, ctx):
		"""Got some nice settings for my UNflipped tables"""
		if ctx.invoked_subcommand is None:
			await send_cmd_help(ctx)
			msg = "```"
			for k, v in self.settings.items():
				msg += str(k) + ": " + str(v) + "\n"
			msg = "```"
			await self.bot.say(msg)

	@tableset.command(name="flipall")
	async def flipall(self):
		"""Enables/disables right all unflipped tables in a message"""
		self.settings["ALL_TABLES"] = not self.settings["ALL_TABLES"]
		if self.settings["ALL_TABLES"]:
			await self.bot.say("All tables will now be unflipped.")
		else:
			await self.bot.say("Now only one table unflipped per message.")
		fileIO("data/noflippedtables/settings.json", "save", self.settings)

	@tableset.command(name="flipbot")
	async def flipbot(self):
		"""Enables/disables allowing bot to flip tables"""
		self.settings["BOT_EXEMPT"] = not self.settings["BOT_EXEMPT"]
		if self.settings["BOT_EXEMPT"]:
			await self.bot.say("Bot is now allowed to leave its own tables flipped")
		else:
			await self.bot.say("Bot must now unflip tables that itself flips")
		fileIO("data/noflippedtables/settings.json", "save", self.settings)

	#so much fluff just for this OpieOP
	async def scrutinize_messages(self, message):
		channel = message.channel
		if channel.id not in self.flippedTables:
			 self.flippedTables[channel.id] = {}
		#┬─┬ ┬┬ ┻┻ ┻━┻ ┬───┬ ┻━┻ will leave 3 tables left flipped
		#count flipped tables
		for m in re.finditer('┻━*┻|┬─*┬', message.content):
			t = m.group()
			if '┻' in t and not (message.author.id == self.bot.user.id and self.settings["BOT_EXEMPT"]):
				if t in self.flippedTables[channel.id]:
					self.flippedTables[channel.id][t] += 1
				else:
					self.flippedTables[channel.id][t] = 1
					if not self.settings["ALL_TABLES"]:
						break
			else:
				f = t.replace('┬','┻').replace('─','━')
				if f in self.flippedTables[channel.id]:
					if self.flippedTables[channel.id][f] <= 0:
						del self.flippedTables[channel.id][f]
					else:
						self.flippedTables[channel.id][f] -= 1
		#wait random time. some tables may be unflipped by now.	
		await asyncio.sleep(randfloat(0,1.5))
		tables = ""

		deleteTables = []
		#unflip tables in self.flippedTables[channel.id]
		for t, n in self.flippedTables[channel.id].items():
			unflipped = t.replace('┻','┬').replace('━','─') + " ノ( ゜-゜ノ)" + "\n"
			for i in range(0,n):
				tables += unflipped
				#in case being processed in parallel
				self.flippedTables[channel.id][t] -= 1
			deleteTables.append(t)
		for t in deleteTables:
			del self.flippedTables[channel.id][t]
		if tables != "":
			await self.bot.send_message(channel, tables)

def check_folders():
	if not os.path.exists("data/noflippedtables"):
		print("Creating data/noflippedtables folder...")
		os.makedirs("data/noflippedtables")


def check_files():
	settings = {"ALL_TABLES" : True, "BOT_EXEMPT" : False}
	f = "data/noflippedtables/settings.json"
	if not fileIO(f, "check"):
		print("Creating settings.json...")
		fileIO(f, "save", settings)

def setup(bot):
	check_folders()
	check_files()
	n = Untableflip(bot)
	bot.add_listener(n.scrutinize_messages, "on_message")
	bot.add_cog(n)
