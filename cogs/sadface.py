import discord
from discord.ext import commands
import os
import aiohttp

class Sadface:
    """D:"""

    def __init__(self,bot):
        self.bot = bot
        self.url = "https://cdn.betterttv.net/emote/55028cd2135896936880fdd7/1x"
        self.sadLoaded = os.path.exists('data/sadface/sadface.png')
        self.image = "data/sadface/sadface.png"

    async def check_sad(self, message):
        if "D:" in message.content.split():
            if not self.sadLoaded:
                try:
                    async with aiohttp.get(self.url) as r:
                        image = await r.content.read()
                    with open('data/sadface/sadface.png','wb') as f:
                        f.write(image)
                    self.sadLoaded = os.path.exists('data/sadface/sadface.png')
                    await self.bot.send_file(message.channel,self.image)
                except Exception as e:
                    print(e)
                    print("Sadface error D: I couldn't download the file, so we're gonna use the url instead")
                    await self.bot.send_message(message.channel,self.url)
            else:
                await self.bot.send_file(message.channel,self.image)

def check_folders():
    if not os.path.exists("data/sadface"):
        print("Creating data/sadface folder...")
        os.makedirs("data/sadface")

def setup(bot):
    check_folders()
    n = Sadface(bot)
    bot.add_listener(n.check_sad, "on_message")
    bot.add_cog(n)