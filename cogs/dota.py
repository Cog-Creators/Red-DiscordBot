import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os
import time
import aiohttp
import urllib
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

try: #check if tabulate is installed
	from tabulate import tabulate
	tabulateAvailable = True
except:
	tabulateAvailable = False

key = os.environ.get("DOTA2_API_KEY")

class Dota:
	"""Dota 2 Red Cog"""

	def __init__(self, bot):
		self.bot = bot

	@commands.group(pass_context=True)
	async def dota(self, ctx):
		"""Returns various data for dota players"""
		if ctx.invoked_subcommand is None:
			await self.bot.say("Type help dota for info.")

	@dota.command(name = 'online', pass_context = True)
	async def online(self, ctx):
		"""Returns current amount of players"""

		url = "https://steamdb.info/app/570/graphs/" #build the web adress
		async with aiohttp.get(url) as response:
			soupObject = BeautifulSoup(await response.text(), "html.parser") 
		try:
			online = soupObject.find(class_='home-stats').find('li').find('strong').get_text() 
			await self.bot.say(online + ' players are playing this game at the moment')
		except:
			await self.bot.say("Couldn't load amount of players. No one is playing this game anymore or there's an error.")

	@dota.command(name = 'hero', pass_context = True)
	async def hero(self, ctx, *, hero):
		"""Shows some info about hero"""

		await self.bot.send_typing(ctx.message.channel)

		reqHero = urllib.parse.quote(hero.lower())

		async def buildHeroInfo(payload):
			herojson = payload

			if herojson["Range"] == 128:
				herotype = "Melee"
			else:
				herotype = "Ranged"

			table = [
				[
					"HP",
					herojson["HP"],
					"%.2f" % (float(herojson["StrGain"]) * 19)
				],
				[
					"MP",
					herojson["Mana"],
					"%.2f" % (float(herojson["IntGain"]) * 19)
				],
				[
					"AGI",
					herojson["BaseAgi"],
					herojson["AgiGain"]
				],
				[
					"STR",
					herojson["BaseStr"],
					herojson["StrGain"]
				],
				[
					"INT",
					herojson["BaseInt"],
					herojson["IntGain"]
				],
				[
					"Damage",
					"53~61",
					""
				],
				[
					"Armor",
					herojson["Armor"],
					"%.2f" % (float(herojson["AgiGain"]) * 0.14)
				],
				[
					"Movespeed",
					herojson["Movespeed"],
					herojson["AgiGain"]
				]
			]

			table[1 + herojson["PrimaryStat"]][0] = "[" + table[1 + herojson["PrimaryStat"]][0] + "]"

			message = "";
			message += "**"  + hero.title() + "** (" + herotype + ")\n"
			message += "This hero's stats:\n\n"
			message += "```"
			message += tabulate(table, headers=["Stat","Value","Gain/lvl"], tablefmt="fancy_grid")
			message += "```\n"
			if (herojson["Legs"] > 0):
				message += "Also you might consider buying " + str(herojson["Legs"]) + " boots, because this hero, apparently, has " + str(herojson["Legs"]) + " legs! ;)"
			else:
				message += "Talking about boots... this hero seems to have no legs, so you might consider playing without any ;)"

			await self.bot.say(message)
		
		url =  "http://api.herostats.io/heroes/" + reqHero
		try:
			async with aiohttp.get(url) as r:
				data = await r.json()
			if "error" not in data.keys():
				await buildHeroInfo(data)
			else:
				await self.bot.say(data["error"])
		except:
			await self.bot.say('Dota API is offline')

	@dota.command(name="build", pass_context = True)
	async def build(self, ctx, *, hero):
		"""Gets most popular skillbuild for a hero"""

		await self.bot.send_typing(ctx.message.channel)

		url = "http://www.dotabuff.com/heroes/" + hero.lower().replace(" ", "-")

		#for actual requests
		async with aiohttp.get(url, headers = {"User-Agent": "Red-DiscordBot"}) as response:
			soupObject = BeautifulSoup(await response.text(), "html.parser") 

		#for local test
		#soupObject = BeautifulSoup(open("data/dota/jakiro.html", "r+").read(), "html.parser")

		build = []
		headers = ""

		try:
			skillSoup = soupObject.find(class_='skill-choices')
			for skill in enumerate(skillSoup.find_all(class_='skill')):

				#add skill name
				build.append([skill[1].find(class_='line').find(class_='icon').find('img').get('alt')])

				#generate build
				for entry in enumerate(skill[1].find(class_='line').find_all(class_='entry')):
					if "choice" in entry[1].get("class"):
						build[skill[0]].append("X")
					else:
						build[skill[0]].append(" ")

			#takes care of splitting the build into something that fits into discord window
			def getPartialTable(table, start, end):
				tables = []
				for row in enumerate(table):
					if start == 0:
						result = []
					else:
						result = [table[row[0]][0]]
					result[1:] = row[1][start:end]
					tables.append(result)
				return tables

			#dem messages
			message = "The most popular build **at the moment**, according to Dotabuff:\n\n"
			message += "```"
			headers = ["Skill/Lvl"]
			headers[len(headers):] = range(1,7)
			message += tabulate(getPartialTable(build,0,7), headers=headers, tablefmt="fancy_grid")
			message += "```\n"

			message += "```"
			headers = ["Skill/Lvl"]
			headers[len(headers):] = range(7,14)
			message += tabulate(getPartialTable(build,7,13), headers=headers, tablefmt="fancy_grid")
			message += "```\n"

			await self.bot.say(message)

			message = "```"
			headers = ["Skill/Lvl"]
			headers[len(headers):] = range(14,21)
			message += tabulate(getPartialTable(build,13,19), headers=headers, tablefmt="fancy_grid")
			message += "```\n"

			await self.bot.say(message)
		except:
			await self.bot.say("Error parsing Dotabuff, maybe try again later")

	@dota.command(name="items", pass_context = True)
	async def items(self, ctx, *, hero):
		"""Gets the most popular items for a hero"""

		await self.bot.send_typing(ctx.message.channel)

		url = "http://www.dotabuff.com/heroes/" + hero.lower().replace(" ", "-")

		#for actual requests
		async with aiohttp.get(url, headers = {"User-Agent": "Red-DiscordBot"}) as response:
			soupObject = BeautifulSoup(await response.text(), "html.parser") 

		items = soupObject.find_all("section")[3].find("tbody").find_all("tr")

		build = []
		for item in items:
			build.append(
				[
					item.find_all("td")[1].find("a").get_text(),
					item.find_all("td")[2].get_text(),
					item.find_all("td")[4].get_text()
				]
			)

		message = "The most popular items **at the moment**, according to Dotabuff:\n\n```"
		message += tabulate(build, headers=["Item", "Matches", "Winrate"], tablefmt="fancy_grid")
		message += "```"

		await self.bot.say(message)


	@dota.command(name="recent", pass_context = True)
	async def recent(self, ctx, player):
		"""Gets the link to player's latest match"""

		await self.bot.send_typing(ctx.message.channel)

		def is_number(s):
			try:
				int(s)
				return True
			except ValueError:
				return False

		if is_number(player.strip()):
			account_id = player.strip()
		else:
			account_id = api.get_steam_id(player)["response"]

			if (int(account_id["success"]) > 1):
				await self.bot.say("Player not found :(")
			else:
				account_id = account_id["steamid"]
		
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

			table = []
			# Form Radiant team
			for i in range(0,5):
				table.append([
						played_heroes[i],
						str(match["players"][i]["kills"]) + "/" + str(match["players"][i]["deaths"]) + "/" + str(match["players"][i]["assists"]),
						played_heroes[5+i],
						str(match["players"][5+i]["kills"]) + "/" + str(match["players"][5+i]["deaths"]) + "/" + str(match["players"][5+i]["assists"])
					])

			message += "\n```"
			message += tabulate(table, headers=["Radiant Team", "K/D/A", "Dire Team", "K/D/A"], tablefmt="fancy_grid")
			message += "```"

			message += "\nDotabuff match link: http://www.dotabuff.com/matches/" + str(match["match_id"])
			await self.bot.say(message)
		else:
			await self.bot.say('Oops.. Something is wrong with Dota2 servers, try again later!')

def setup(bot):
	if soupAvailable is False:
		raise RuntimeError("You don't have BeautifulSoup installed, run\n```pip3 install bs4```And try again")
		return
	if dotaAvailable is False:
		raise RuntimeError("You don't have dota2py installed, run\n```pip3 install dota2py```And try again")
		return
	if not key:
		raise RuntimeError("Please set the DOTA2_API_KEY environment variable")
		return
	if tabulateAvailable is False:
		raise RuntimeError("You don't have tabulate installed, run\n```pip3 install tabulate```And try again")
		return
	api.set_api_key(key)
	bot.add_cog(Dota(bot))
