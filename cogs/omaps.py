from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
# Sys.
from operator import itemgetter, attrgetter
import discord
from discord.ext import commands
#from copy import deepcopy
import aiohttp
import asyncio
import json
import os
import http.client


DIR_DATA = "data/omaps"
POINTER = DIR_DATA+"/pointer.png"
MAP = DIR_DATA+"/map.png"

class OpenStreetMaps:
    """The openstreetmap.org cog"""

    def __init__(self,bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=False)
    async def prevmap(self, ctx):
        """Resend the last openstreetmap.org result"""
        user = ctx.message.author
        channel = ctx.message.channel
        if not fileIO(MAP, "check"):
            await self.bot.say("` No previous map available.`")
        else:
            await self.bot.send_file(channel, MAP)

    @commands.command(pass_context=True, no_pm=False)
    async def maps(self, ctx, zoom, *country):
        """Search at openstreetmap.org\n
        zoom: upclose, street, city, country, world
        Type: 'none' to skip"""
        user = ctx.message.author
        channel = ctx.message.channel
        country = "+".join(country)

        longitude = 0.0
        latitude = 0.0
        adressNum = 1
        limitResult  = 0    

        #Set tile zoom
        if zoom == 'upclose':
            zoomMap = 18  
        elif zoom == 'street':
            zoomMap = 16
        elif zoom == 'city':
            zoomMap = 11
        elif zoom == 'country':
            zoomMap = 8
        elif zoom == 'world':
            zoomMap = 2   
        else:
            zoomMap = 16

        #Get input data
        search = country
        await self.bot.say("` What city?`")
        response = await self.bot.wait_for_message(author=ctx.message.author)
        response = response.content.lower().strip().replace(" ", "+")
        if response == "none":
            pass
        else:
            search = search+","+response
        #http://wiki.openstreetmap.org/wiki/Nominatim
        await self.bot.say("` Enter your search term for the given location (building, company, address...)`")
        response = await self.bot.wait_for_message(author=ctx.message.author)
        response = response.content.lower().strip().replace(" ", "+")
        if response == "none":
            pass
        else:        
            search = search+","+response
        #print (search)

        #Get xml result from openstreetmap.org
        try:
            domain = "nominatim.openstreetmap.org"
            search = "/search?q={}&format=xml&polygon=1&addressdetails=1".format(search)
            #print(domain+search)
            conn = http.client.HTTPConnection(domain)
            conn.request("GET", search)
            r1 = conn.getresponse()
            data = r1.read()
            conn.close()
        except Exception as e:
            await self.bot.say("` Error getting GPS data.`")
            print("Error getting GPS data.")
            print(e)
            return  
        try:
            display_name = "-"
            soup = BeautifulSoup(data, 'html.parser')
            links = soup.findAll('place', lon=True)        
            results = len(links)
            if results == 0:
                await self.bot.say("`No results, try to rephrase`")  
                return
            #print("results:\n"+str(results))
            #print("display_name:\n"+display_name)
            #print("longitude/latitude:\n"+str(longitude)+","+str(latitude))
        except Exception as e:
            await self.bot.say("`Something went wrong while parsing xml data...`")
            print('parse XML failed')
            print(e)
            return
        await self.bot.send_typing(channel)
        if results > 1:
            list = "```erlang\nResults\n-\n"
            index = 0
            for link in links:
                index += 1
                list = list + "(" +str(index) + "): "+ link["display_name"] + "\n"
            list = list +"```` Enter result number...`"
            await self.bot.say(list)
            response = await self.bot.wait_for_message(author=ctx.message.author)
            input = response.content.lower().strip()
            #Set values for geotiler
            input = int(input)-1
            place_id = (links[input]["place_id"])
            display_name = (links[input]["display_name"])
            longitude = (links[input]['lon'])
            latitude = (links[input]['lat'])
        else:
            #Set values for geotiler        
            place_id = (links[0]["place_id"])
            display_name = (links[0]["display_name"])
            longitude = (links[0]['lon'])
            latitude = (links[0]['lat'])

        await self.bot.say("`Give me a moment to draw the lines...`")
        await self.bot.send_typing(channel)
        #print([latitude, longitude, zoomMap])

        map = geotiler.Map(center=(float(longitude), float(latitude)), zoom=zoomMap, size=(720, 720))
        map.extent
        image = await geotiler.render_map_async(map)
        image.save(MAP)
        await self.bot.send_typing(channel)
        #Add pointer and text.
        savedMap = Image(filename=MAP)
        pointer = Image(filename=POINTER)
        for o in COMPOSITE_OPERATORS:
            w = savedMap.clone()
            r = pointer.clone()
        with Drawing() as draw:
            draw.composite(operator='atop', left=311, top=311, width=90, height=90, image=r)
            draw(w)
            #Text
            draw.fill_color = Color("#7289DA")
            draw.stroke_color = Color("#5370D7")
            draw.stroke_width = 0.2
            draw.font_style = 'oblique'
            draw.font_size = 32
            splitDisplayName = display_name.split(',')
            #Object name/number
            draw.text(x=20, y=35, body=splitDisplayName[0])
            draw(w)
            del splitDisplayName[0]
            #Print location info on map.
            line0 = ""
            line1 = ""
            draw.font_size = 18
            for i in splitDisplayName:
                if len(str(line0)) > 30:
                    line1 = line1 + i + ","
                else:
                    line0 = line0 + i  + ","
            #line 0
            if len(str(line0)) > 2:            
                draw.text(x=15, y=60, body=line0)
                draw(w)
            #line 1
            if len(str(line1)) > 2:
                draw.text(x=15, y=80, body=line1)
                draw(w)
            w.save(filename=MAP)
        await self.bot.send_file(channel, MAP)
 
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Set-up
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating {} folder...".format(DIR_DATA))
        os.makedirs(DIR_DATA)

def check_files():

    f = POINTER
    if not fileIO(f, "check"):
        print("pointer.png is missing!")  

class ModuleNotFound(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message        

def setup(bot):
    global geotiler
    global Color, Drawing, display, Image, Color, Image, COMPOSITE_OPERATORS
    global BeautifulSoup
    
    check_folders()
    check_files()
    try:
        import geotiler
    except:
        raise ModuleNotFound("geotiler is not installed. Do 'pip3 install geotiler --upgrade' to use this cog.")
    try:
        from bs4 import BeautifulSoup
    except:
        raise ModuleNotFound("BeautifulSoup is not installed. Do 'pip3 install BeautifulSoup --upgrade' to use this cog.")        
    try: 
        from wand.image import Image, COMPOSITE_OPERATORS
        from wand.drawing import Drawing
        from wand.display import display
        from wand.image import Image
        from wand.color import Color
    except:
        raise ModuleNotFound("Wand is not installed. Do 'pip3 install Wand --upgrade' and make sure you have ImageMagick installed http://docs.wand-py.org/en/0.4.2/guide/install.html")    
    bot.add_cog(OpenStreetMaps(bot))


