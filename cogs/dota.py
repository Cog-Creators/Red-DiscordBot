import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os
import time
import aiohttp
import asyncio
from copy import deepcopy
import random
try: # check if BeautifulSoup4 is installed
	from bs4 import BeautifulSoup
	soupAvailable = True
except:
	soupAvailable = False

try: #check if Dota2py is installed
	from dota2py import api
	dotaAvailable = True
except:
	dotaAvailable = False

key = os.environ.get("DOTA2_API_KEY")

class Dota:
	"""Dota 2 Red Cog"""

	def __init__(self, bot):
		self.bot = bot
		self.herodata = fileIO("data/dota/herodata.json", "load")
		self.herokeys = list(self.herodata.keys())
		self.heronames = {}
		self.heronames_i = {}

		for i, item in enumerate(self.herokeys):
			self.heronames[self.herodata[item]["displayname"]] = item
			self.heronames_i[item] = self.herodata[item]["displayname"]

	@commands.group(pass_context=True)
	async def dota(self, ctx):
		"""Returns various data for dota players"""
		if ctx.invoked_subcommand is None:
			await self.bot.say("Type help dota for info.")

	@dota.command(name = 'online', pass_context = True)
	async def online(self, ctx):
		"""Returns current amount of players"""

		await self.bot.send_typing(ctx.message.channel)

		url = "http://steamcharts.com/app/570" #build the web adress
		async with aiohttp.get(url) as response:
			soupObject = BeautifulSoup(await response.text(), "html.parser") 
		try:
			online = soupObject.find(class_='num').get_text() 
		except:
			await self.bot.say("Couldn't load amount of players. No one is playing this game anymore or there's an error.")

		await self.bot.say(online + ' players are playing this game at the moment')

	@dota.command(name = 'heroquest')
	async def heroquest(self):
		"""Starts a hero trivia"""

		await self.bot.say(self.heronames_i[self.herokeys[random.randrange(0,len(self.herokeys))]]) 

	@dota.command(name = 'hero', pass_context = True)
	async def hero(self, ctx, hero, cat):
		"""Shows some info about <hero>
		Bio if <cat> = info
		Abilities list if <cat> = skills"""

		herojson = self.herodata[self.heronames[hero.title()]]
		image = "http://cdn.dota2.com/apps/dota2/images/heroes/" + self.heronames[hero.title()].replace("npc_dota_hero_","") + "_full.png"
		if herojson["attackrange"] == 128:
			herotype = "Melee"
		else:
			herotype = "Ranged"

		message = "";
		message += image + "\n"
		message += "**"  + hero.title() + "** (" + herotype + ")\n"

		if cat == "info":
			bio = herojson["bio"]
			bio = bio[:bio.find(".")]
			role = herojson["role"].replace(",",", ")
			message += "*" + role + "*\n"
			message += "Bio:\n`" + bio + "`\n"

			await self.bot.say(message)

		elif cat == "skills":
			message += "Abilities:\n"
			await self.bot.say(message)
			for i, ability in enumerate(herojson["abilities"]):
				if ability["displayname"] == "Empty" or ability["displayname"] == "Attribute Bonus":
					continue
				else: 
					message = "*" + ability["displayname"] + "*\n"
					message += "`" + ability["description"] + "`\n"
					message += "Damage:\n"
					for j, damage in enumerate(ability["damage"]):
						message += " [lvl" + str(j+1) +"]: " + str(damage) + ""
					message += "\nCooldown:\n"
					for j, cooldown in enumerate(ability["cooldown"]):
						message += " [lvl" + str(j+1) +"]: " + str(cooldown) + ""
					message += "\nManacost:\n"
					for j, manacost in enumerate(ability["manacost"]):
						message += " [lvl" + str(j+1) +"]: " + str(manacost) + ""

					await self.bot.say(message)

	@dota.command(name="recent", pass_context = True)
	async def recent(self, ctx, player):
		"""Gets the link to player's latest match"""

		account_id = int(api.get_steam_id(player)["response"]["steamid"])

		try:
			# Get the data from Dota API
			matches = api.get_match_history(account_id=account_id)["result"]["matches"]
			match = api.get_match_details(matches[0]["match_id"])
			heroes = api.get_heroes()
			dotaServes = True
		except:
			# Well... if anything fails...
			dotaServes = False
			print('Dota servers SO BROKEN!')
		
		if dotaServes:
			# Create a proper heroes list
			heroes = heroes["result"]["heroes"]
			def build_dict(seq, key):
				return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))
			heroes = build_dict(heroes, "id")

			# Reassign match info for ease of use
			match = match["result"]

			# Construct message
			message = "Showing the most recent match for **" + player + "** (match id: **" + str(match["match_id"]) + "**)\n"
			if "radiant_win" in match:
				message += "**RADIANT WON**"
			else:
				message += "**DIRE WON**"

			m, s = divmod(match["duration"], 60)
			h, m = divmod(m, 60)

			message += " [" + "%d:%02d:%02d" % (h, m, s) + "]\n"

			# Create a list of played heroes
			played_heroes = []
			for player in enumerate(match["players"]):
				played_heroes.append(heroes[player[1]["hero_id"]]["localized_name"])

			# Form Radiant team
			message += "Radiant team:\n"
			message += ', '.join(played_heroes[:5])

			# Form Dire team
			message += "\nDire team:\n"
			message += ', '.join(played_heroes[5:])

			message += "\nDotabuff match link: http://www.dotabuff.com/matches/" + str(match["match_id"])
			await self.bot.say(message)
		else:
			await self.bot.say('Oops.. Something is wrong with Dota2 servers, try again later!')


def check_folders():
	if not os.path.exists("data/dota"):
		print("Creating data/dota folder...")
		os.makedirs("data/dota")

def check_files():
	f = "data/dota/herodata.json"
	if not fileIO(f, "check"):
		print("Creating empty herodata.json...")
		fileIO(f, "save", [])

def setup(bot):
	check_folders()
	check_files()
	if dotaAvailable is False:
		raise RuntimeError("You don't have dota2py installed, run\n```pip3 install dota2py```And try again")
		return
	if not key:
		raise RuntimeError("Please set the DOTA2_API_KEY environment variable")
		return
	api.set_api_key(key)
	bot.add_cog(Dota(bot))
