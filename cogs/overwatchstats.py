import discord
import asyncio
import json
import argparse
import urllib.request
import requests
import aiohttp

class OverWatchStats:
    """Overwatch Stats"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def on_message(message):
        author = message.author
    if message.content.startswith('!ow'):
        try:
            null, stat, mode, battletag = map(str, message.content.split())
            battlenet = battletag
            battletag = battletag.replace("#","-")
            if stat == 'heroes':
                stat = 'heroes'
            elif mode == 'qp':
                mode = 'general'
            elif mode == 'comp':
                mode = 'competitive'
            elif stat != 'stats':
                await self.bot.say("Hey {0}, you entered the mode wrong!".format(author))

            with aiohttp.ClientSession() as session:
                async with session.get('https://owapi.net/api/v2/u/'+ battletag + '/' + stat  + '/' + mode) as r:
                    resp = await r.json()
                    if 'error' in resp:
                        await self.bot.say("{0},  I tried looking for {1}'s Overwatch statistics in {2} as you requested, but couldn't find anything 🐯".format(message.author, battlenet, mode))
                    else:
                        print_status('DATA','')
                        print(resp)
                        stats = ''
                        for k1,v1 in resp.items():
                            if isinstance(v1, dict) and (k1 != '_request' and k1 != 'game_stats'):
                                stats = stats +"\n\n" + str(k1.replace("_"," ").title()) + ":\n"
                                for key, value in v1.items():
                                    if key != 'avatar':
                                        stats = (stats + "\n" + str(key.replace("_"," ").title()) + ': ' + str(value))
                                        if(key == 'win_rate'):
                                            stats = stats + "%"
                        await self.bot.say("```Overwatch {0} stats for {1}:".format(mode.title(),battlenet) + stats + "```" )
                        print_status('GOOD',str('Command ' + message.content + ' completed'))
        except ValueError as e:
            await self.bot.say("Hey, @{0}, you used the !ow command wrong. Did you enter the wrong name, or forget a mode?\nTry using !help to see what you forgot.".format(message.author))
        except Exception as e:
            await self.bot.say("Looks like @evanextreme messed up somehow. Tell him you got a {}".format(type(e).__name__, e.args))
            print_status('FAIL',str("An exception of type {0} occured. Arguments:\n{1!r}".format(type(e).__name__, e.args)))

def setup(bot):
    bot.add_cog(OverWatchStats(bot))
