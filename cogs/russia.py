import discord
from discord.ext import commands
import asyncio
import os
import aiohttp

class Russian:
	"""HE'S FROM RUSSIA!"""

	def __init__(self, bot):
		self.bot = bot
		self.url = 'https://s-media-cache-ak0.pinimg.com/736x/64/84/bb/6484bbae1782cc50059be379254c7e77.jpg'
		self.rusLoaded = os.path.exists('data/russian/russian.jpg')
		self.image = "data/russian/russian.jpg"

	@commands.command()
	async def russian(self):
		"""WE NEED MORE RUSSIA IN CHAT!"""

		await self.bot.say("PUTIN VODKA BALALAIKA!\n")

	async def check_russian(self, message):
		if "russia" in message.content.split():
			if not self.rusLoaded:
				try:
					async with aiohttp.get(self.url) as r:
						image = await r.content.read()
					with open('data/russian/russian.jpg','wb') as f:
						f.write(image)
					self.rusLoaded = os.path.exists('data/russian/russian.jpg')
					await self.bot.send_message(message.channel, "PUTIN VODKA BALALAIKA!")
					await self.bot.send_file(message.channel,self.image)
				except Exception as e:
					print(e)
					print("Rissan error D: Gonna drink VODKA and use url instead")
					await self.bot.send_message(message.channel,"PUTIN VODKA BALALAIKA!\n" + self.url)
			else:
				await self.bot.send_message(message.channel, "PUTIN VODKA BALALAIKA!")
				await self.bot.send_file(message.channel,self.image)

def check_folders():
	if not os.path.exists("data/russian"):
		print("Creating data/russian folder...")
		os.makedirs("data/russian")

def setup(bot):
	check_folders()
	n = Russian(bot)
	bot.add_listener(n.check_russian, "on_message")
	bot.add_cog(n)
