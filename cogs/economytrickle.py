import discord
from discord.ext import commands
from random import randint
import datetime
import time
import os
import asyncio
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help


class Economytrickle:
	"""Economy Trickle

	Gives Economy.py currency to active members every so often. 
	The more people active, the more currency to go around!
	This cog is dependant on Economy.py; Future updates to Economy.py may break this cog.
	"""

	def __init__(self,bot):
		self.bot = bot
		self.settings = fileIO("data/economytrickle/settings.json", "load")
		self.activeUsers = {}
		self.currentUser = {}
		self.tricklePot = {}
		self.previousDrip = {}
		self.defaultSettings = {"TRICKLE_BOT" : False, "NEW_ACTIVE_BONUS" : 1, "ACTIVE_BONUS_DEFLATE" : 1, "PAYOUT_INTERVAL" : 2, "CHANCE_TO_PAYOUT" : 50, "PAYOUT_PER_ACTIVE" : 1, "ACTIVE_TIMEOUT" : 10}
	

	@commands.group(pass_context=True)
	@checks.mod_or_permissions(manage_server=True)
	async def trickleset(self, ctx):
		"""Changes economy trickle settings
		Trickle amount: 
			(# active users - 1) x multiplier + bonus pot
		Every active user gets the trickle amount. It is not distributed between active users.
		"""
		if ctx.invoked_subcommand is None:
			await send_cmd_help(ctx)
			sid = ctx.message.server.id
			msg = "```"
			for k, v in self.settings[sid].items():
				msg += str(k) + ": " + str(v) + "\n"
			msg += "```"
			await self.bot.say(msg)

	@trickleset.command(name="bot", pass_context=True)
	async def tricklebot(self, ctx):
		"""Enables/disables trickling economy to the bot"""
		sid = ctx.message.server.id
		econ = self.bot.get_cog('Economy')
		botuser = self.bot.user
		if botuser.id in econ.bank:
			self.settings[sid]["TRICKLE_BOT"] = not self.settings[sid]["TRICKLE_BOT"]
			if self.settings[sid]["TRICKLE_BOT"]:
				await self.bot.say("I will now get currency trickled to me.")
			else:
				await self.bot.say("I will stop getting currency trickled to me.")
			fileIO("data/economytrickle/settings.json", "save", self.settings)
		else:
			await self.bot.say("I do not have an account registered with the `Economy cog`. If you want currency to trickle to me too, please use the `registerbot` command to open an account for me, then try again.")

	@trickleset.command(name="timeout", pass_context=True)
	async def timeout(self, ctx, minutes : float):
		"""Sets the amount of time a user is considered active after sending a message
		"""
		sid = ctx.message.server.id
		if minutes <= 0:
			await self.bot.say("Timeout interval must be more than 0")
			return
		self.settings[sid]["ACTIVE_TIMEOUT"] = minutes
		await self.bot.say("Active user timeout is now: " + str(self.settings[sid]["ACTIVE_TIMEOUT"]))
		fileIO("data/economytrickle/settings.json", "save", self.settings)

	@trickleset.command(name="interval", pass_context=True)
	async def interval(self, ctx, minutes : float):
		"""Sets the interval that must pass between each trickle
		"""
		sid = ctx.message.server.id
		if minutes <= 0:
			await self.bot.say("```Warning: With an interval this low, a trickle will occur after every message```")
		self.settings[sid]["PAYOUT_INTERVAL"] = minutes
		await self.bot.say("Payout interval is now: " + str(self.settings[sid]["PAYOUT_INTERVAL"]))
		fileIO("data/economytrickle/settings.json", "save", self.settings)

	@trickleset.command(name="multiplier", pass_context=True)
	async def multiplier(self, ctx, amt : float):
		"""Sets the amount added to the trickle amount per active user.
		"""
		sid = ctx.message.server.id
		if amt < 0:
			await self.bot.say("```Warning: A negative multiplier would be taking away currency the more active users you have. This will discourage conversations.```")
		self.settings[sid]["PAYOUT_PER_ACTIVE"] = amt
		await self.bot.say("Base payout per active user is now: " + str(self.settings[sid]["PAYOUT_PER_ACTIVE"]))
		fileIO("data/economytrickle/settings.json", "save", self.settings)

	@trickleset.command(name="bonus", pass_context=True)
	async def activebonus(self, ctx, amt : int):
		"""Sets the bonus amount per new active user.

		When there is a new active user, this amount will be added to the bonus pot
		"""
		sid = ctx.message.server.id
		if amt < 0:
			await self.bot.say("```Warning: Bonus amount should be positive unless you want to discourage conversations```")
		self.settings[sid]["NEW_ACTIVE_BONUS"] = amt
		await self.bot.say("Bonus per new active user is now: " + str(self.settings[sid]["NEW_ACTIVE_BONUS"]))
		fileIO("data/economytrickle/settings.json", "save", self.settings)

	@trickleset.command(name="leak", pass_context=True)
	async def bonusdeflate(self, ctx, amt : int):
		"""Sets the bonus pot leak amount.

		Whenever a trickle occurs (successful or not), this amount is taken out of the bonus pot
		"""
		sid = ctx.message.server.id
		if amt < 0:
			await self.bot.say("```Warning: The bonus pot does not reset each trickle. With a negative leak, the bonus pot will grow each time a trickle occurs.```")
		self.settings[sid]["ACTIVE_BONUS_DEFLATE"] = amt
		await self.bot.say("Bonus pot leak is now: " + str(self.settings[sid]["ACTIVE_BONUS_DEFLATE"]))
		fileIO("data/economytrickle/settings.json", "save", self.settings)

	@trickleset.command(name="chance", pass_context=True)
	async def succeedchance(self, ctx, percentage : int):
		"""Sets percentage chance that the trickle will be successful [0-100]
		"""
		sid = ctx.message.server.id
		if percentage < 0 or percentage > 100:
			await self.bot.say("Percentage chance must be between 0 and 100")
			return
		if percentage == 0:
			await self.bot.say("```Warning: This will stop all trickling. You might as well just unload cogs.economytrickle```")
		self.settings[sid]["CHANCE_TO_PAYOUT"] = percentage
		await self.bot.say("Successful trickle chance is now: " + str(self.settings[sid]["CHANCE_TO_PAYOUT"]))
		fileIO("data/economytrickle/settings.json", "save", self.settings)
 
 	#if Economy.py updates, this may break
	@commands.command(pass_context=True)
	@checks.is_owner()
	async def registerbot(self, ctx, agree : str):
		"""registers the bot into Economy.py bank. 

		WARNING: Edits Economy.py's bank.json file.
		If Economy.py is updated in the future with a different format for bank.json, the data in bank.json (everyone's balances) may be lost.

		This command will try to save a backup in data/economytrickle/bank-backup.json in case that happens.
		If you understand this and still want to register your bot in the bank, type
		registerbot "I have read and understand. Just give my bot money!"

		"""
		if agree.lower() == "i have read and understand. just give my bot money!":
			econ = self.bot.get_cog('Economy')
			bank = econ.bank
			botuser = self.bot.user
			if botuser.id not in bank:
				fileIO("data/economytrickle/bank-backup.json", "save", bank)
				bank[botuser.id] = {"name" : botuser.name, "balance" : 100}
				fileIO("data/economy/bank.json", "save", bank)
				await self.bot.say("Account opened for {}. Current balance: {}".format(botuser.mention, str(bank[botuser.id]["balance"])))
			else:
				await self.bot.say("{} already has an account at the Twentysix bank.".format(botuser.mention))
		else:
			await send_cmd_help(ctx)


	async def trickle(self, message):
		"""trickle pb to active users"""
		if message.server == None:
			return
		#if different person speaking
		sid = message.server.id
		if self.settings.get(sid,None) == None:
			self.settings[sid] = self.defaultSettings
			fileIO("data/economytrickle/settings.json", "save", self.settings)
		if (self.settings[sid]["TRICKLE_BOT"] or message.author.id != self.bot.user.id) and self.currentUser.get(message.server.id,None) != message.author.id:
			#print("----Trickle----")
			# add user or update timestamp and make him current user
			self.currentUser[sid] = message.author.id
			now = datetime.datetime.now()
			#new active user bonus
			#if server has a list yet
			if sid in self.activeUsers.keys():
				if self.currentUser[sid] not in self.activeUsers.get(sid,None).keys():
					#might be redundant
					# if self.tricklePot.get(sid,None) == None:
					# 	self.tricklePot[sid] = 0
					#don't wanna add to the pot for bot
					if message.author.id != self.bot.user.id:
						self.tricklePot[sid] += self.settings[sid]["NEW_ACTIVE_BONUS"]
			else:
				self.activeUsers[sid] = {}
				self.tricklePot[sid] = 0
			#timestamp is UTC time, not my time
			self.activeUsers[sid][self.currentUser[sid]] = now

			if sid not in self.previousDrip.keys():
				self.previousDrip[sid] = now
			elif self.previousDrip[sid] < (now - datetime.timedelta(minutes=self.settings[sid]["PAYOUT_INTERVAL"])):
				self.previousDrip[sid] = now
				#stuffs
				#amount to give it dependant on how many people are active
				#half the time don't give anything
				trickleAmt = 0
				if randint(1,100) <= self.settings[sid]["CHANCE_TO_PAYOUT"]:
					numActive = len(self.activeUsers[sid])
					#don't want bot to add to payout
					if self.bot.user.id in self.activeUsers[sid]:
						numActive -= 1
					trickleAmt = int((numActive - 1)*self.settings[sid]["PAYOUT_PER_ACTIVE"] + self.tricklePot[sid])
				#debug
				debug = message.server.name + " - trickle: " + str(trickleAmt) + " > "
				expireTime = now - datetime.timedelta(minutes=self.settings[sid]["ACTIVE_TIMEOUT"])
				
				econ = None
				econ = self.bot.get_cog('Economy')
				if econ == None:
					print("--- Error: Was not able to load Economy cog into Economytrickle. ---")
				#all active users
				#print(message.author.id + " " + message.author.name)
				templist = []
				for u in self.activeUsers[sid].keys():
					#print(str(now) + " | " + str(self.activeUsers[u]) + " " + str(expireTime) + str(self.activeUsers[u] > expireTime))
					if self.activeUsers[sid][u] < expireTime:
						templist.append(u)
					elif econ.account_check(u):
						econ.add_money(u, trickleAmt)
						#debug
						debug += message.server._members[u].name + ", "
				#debug
				if len(templist) != 0:
					debug += "\n--- expired - removing | "
				for u in templist:
					del self.activeUsers[sid][u]
					debug += message.server._members[u].name + ", "
				debug += "\n" + str(len(self.activeUsers[sid])) +" ausers left in server---"
				print(debug)
				#new active user bonus reduce
				if self.tricklePot[sid] > 0:
					self.tricklePot[sid] -= self.settings[sid]["ACTIVE_BONUS_DEFLATE"]
					if self.tricklePot[sid] < 0:
						self.tricklePot[sid] = 0


def check_folders():
	if not os.path.exists("data/economytrickle"):
		print("Creating data/economytrickle folder...")
		os.makedirs("data/economytrickle")

def check_files():
	serverSettings = {}

	f = "data/economytrickle/settings.json"
	if not fileIO(f, "check"):
		print("Creating empty economytrickle's settings.json...")
		fileIO(f, "save", serverSettings)	


#unload cog if economy isn't loaded

def setup(bot):
	check_folders()
	check_files()
	n = Economytrickle(bot)
	bot.add_listener(n.trickle, "on_message")
	bot.add_cog(n)
