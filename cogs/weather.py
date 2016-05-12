import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import os
from .utils.dataIO import fileIO


class weather:
	"""Search for weather in given location."""

	def __init__(self, bot):
		self.bot = bot
		self.settings = fileIO("data/weather/settings.json", "load")
		
	@commands.command(no_pm=True, pass_context=False)
	async def temp(self, location):
		"""Get the current weather.
		\nMake sure to get your own API key and put it into data/weather/settings.json\nYou can get an API key from: www.wunderground.com/weather/api/"""
		url = "http://api.wunderground.com/api/" + self.settings['api_key'] + "/geolookup/conditions/q/" + str(location) + ".json"
		async with aiohttp.get(url) as r:
			data = await r.json()

		if "current_observation" in data:
			tempc = data["current_observation"].get("temp_c", "No temperature found.")
			tempf = data["current_observation"].get("temp_f", "No temperature found.")
			weather = data["current_observation"].get("weather", "No weather found.")
			loc = data["location"].get("city", "no city found")
			state = data["location"].get("state", "no city found")
			await self.bot.say("Current weather in " + str(loc) + ", " + str(state) + " is: " + str(weather) + " with a temperature of " + str(tempc) +" °C (" + str(tempf) + " °F).")
		else:
			await self.bot.say("Use the format: City,Country(or State/Province instead of Country) or Zip Code/Postal Code /// Any spaces in the location and the command will fail (EX: New York,NY will not work. Use a zip/postal code instead. EX: 10001)")
	
	@commands.command(no_pm=True, pass_context=False)
	async def forecast(self, location):
		"""Get a forecast link for the location.
		\nMake sure to get your own API key and put it into data/weather/settings.json\nYou can get an API key from: www.wunderground.com/weather/api/"""
		url = "http://api.wunderground.com/api/" + self.settings['api_key'] + "/geolookup/conditions/q/" + str(location) + ".json"
		async with aiohttp.get(url) as r:
			data = await r.json()
		
		if "current_observation" in data:
			fore = data["current_observation"].get("forecast_url", "No forecast found.")
			loc = data["location"].get("city", "no city found")
			state = data["location"].get("state", "no city found")
			await self.bot.say("Current forecast for " + str(loc) + ", " + str(state) + " is: " + str(fore) + ".")
		else:
			await self.bot.say("Use the format: City,Country(or State/Province instead of Country) or Zip Code/Postal Code /// Any spaces in the location and the command will fail (EX: New York,NY will not work. Use a zip/postal code instead. EX: 10001)")
	
	@commands.command(no_pm=True, pass_context=False)
	async def nextday(self, location):
		"""Get the weather for tomorrow.
		\nMake sure to get your own API key and put it into data/weather/settings.json\nYou can get an API key from: www.wunderground.com/weather/api/"""
		url = "http://api.wunderground.com/api/" + self.settings['api_key'] + "/geolookup/forecast/q/" + str(location) + ".json"
		async with aiohttp.get(url) as r:
			data = await r.json()

		if "location" in data:
			loc = data["location"].get("city", "no city found")
			state = data["location"].get("state", "no state found")
			tomorrow = data["forecast"]["txt_forecast"]["forecastday"]

			for period in tomorrow:
					if period["period"] == 2:
						metric = period.get("fcttext_metric", "No metric found")
						day = period.get("title", "No day found")
						await self.bot.say("The weather for " + str(loc) + ", " + str(state) + " on " + str(day) + " is: " + str(metric))
		else:
			await self.bot.say("Use the format: City,Country(or State/Province instead of Country) or Zip Code/Postal Code /// Any spaces in the location and the command will fail (EX: New York,NY will not work. Use a zip/postal code instead. EX: 10001)")
	
	@commands.command(no_pm=True, pass_context=False)
	async def nextnight(self, location):
		"""Get the weather for tomorrow night.
		\nMake sure to get your own API key and put it into data/weather/settings.json\nYou can get an API key from: www.wunderground.com/weather/api/"""
		url = "http://api.wunderground.com/api/" + self.settings['api_key'] + "/geolookup/forecast/q/" + str(location) + ".json"
		async with aiohttp.get(url) as r:
			data = await r.json()

		if "location" in data:
			loc = data["location"].get("city", "no city found")
			state = data["location"].get("state", "no state found")
			tomorrow = data["forecast"]["txt_forecast"]["forecastday"]

			for period in tomorrow:
					if period["period"] == 3:
						metric = period.get("fcttext_metric", "No metric found")
						day = period.get("title", "No day found")
						await self.bot.say("The weather for " + str(loc) + ", " + str(state) + " on " + str(day) + " is: " + str(metric))
		else:
			await self.bot.say("Use the format: City,Country(or State/Province instead of Country) or Zip Code/Postal Code /// Any spaces in the location and the command will fail (EX: New York,NY will not work. Use a zip/postal code instead. EX: 10001)")
	
def check_folders():
	if not os.path.exists("data/weather"):
		print("Creating data/weather folder...")
		os.makedirs("data/weather")

def check_files():
	settings = {"api_key": "Get your API key from: www.wunderground.com/weather/api/"}
	
	f = "data/weather/settings.json"
	if not fileIO(f, "check"):
		print("Creating settings.json")
		print("You must obtain an API key as noted in the newly created 'settings.json' file")
		fileIO(f, "save", settings)

def setup(bot):
	check_folders()
	check_files()
	n = weather(bot)
	bot.add_cog(n)
