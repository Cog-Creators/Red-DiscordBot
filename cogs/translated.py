from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
# Sys.
import discord
from discord.ext import commands
from operator import itemgetter, attrgetter
#from copy import deepcopy
import random
import os
import sys
import time
#import logging
import aiohttp

__author__ = "Controller Network"
__version__ = "0.0.1"

#ToDo:

#bot output replacement. except translation commands in help output or alias commands to translated lang
#Channel language
#submit corrected sys translations to translated.net(requires translated.net account).
#...


EMAIL = "less_limitations@when_valid_mail.set" #EMAIL = "less_limitations@when_valid_mail.set"
DIR_DATA = "data/translated"
CACHE = DIR_DATA+"/cache.json"
CH_LANG = DIR_DATA+"/chlang.json"
SETTINGS = DIR_DATA+"/settings.json"

class Translated:
    """Translate text with use of translated.net API. 
    Machine Translation provided by Google, Microsoft, Worldlingo or MyMemory customized engine.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.DEL_MSG = False # Enables/Disables input replacement.
        self.NO_ERR = False # Disables notification of permission denied 403
        self.settings = fileIO(SETTINGS, "load")
        self.cache = fileIO(CACHE, "load")
        # These should be supported by translated.net (RFC3066)
        self.ISO_LANG = [["Abkhazian", "AB"], ["Afar", "AA"], ["Afrikaans", "AF"], ["Albanian", "SQ"], ["Amharic", "AM"], ["Arabic", "AR"], ["Armenian", "HY"], ["Assamese", "AS"], ["Aymara", "AY"], 
                                ["Azerbaijani", "AZ"], ["Bashkir", "BA"], ["Basque", "EU"], ["Bengali, Bangla", "BN"], ["Bhutani", "DZ"], ["Bihari", "BH"], ["Bislama", "BI"], ["Breton", "BR"], ["Bulgarian", "BG"], 
                                ["Burmese", "MY"], ["Byelorussian", "BE"], ["Cambodian", "KM"], ["Catalan", "CA"], ["Chinese", "ZH"], ["Corsican", "CO"], ["Croatian", "HR"], ["Czech", "CS"], ["Danish", "DA"], 
                                ["Dutch", "NL"], ["English, American", "EN"], ["Esperanto", "EO"], ["Estonian", "ET"], ["Faeroese", "FO"], ["Fiji", "FJ"], ["Finnish", "FI"], ["French", "FR"], ["Frisian", "FY"], 
                                ["Gaelic (Scots Gaelic)", "GD"], ["Galician", "GL"], ["Georgian", "KA"], ["German", "DE"], ["Greek", "EL"], ["Greenlandic", "KL"], ["Guarani", "GN"], ["Gujarati", "GU"], 
                                ["Hausa", "HA"], ["Hebrew", "IW"], ["Hindi", "HI"], ["Hungarian", "HU"], ["Icelandic", "IS"], ["Indonesian", "IN"], ["Interlingua", "IA"], ["Interlingue", "IE"], ["Inupiak", "IK"], 
                                ["Irish", "GA"], ["Italian", "IT"], ["Japanese", "JA"], ["Javanese", "JW"], ["Kannada", "KN"], ["Kashmiri", "KS"], ["Kazakh", "KK"], ["Kinyarwanda", "RW"], ["Kirghiz", "KY"], 
                                ["Kirundi", "RN"], ["Korean", "KO"], ["Kurdish", "KU"], ["Laothian", "LO"], ["Latin", "LA"], ["Latvian, Lettish", "LV"], ["Lingala", "LN"], ["Lithuanian", "LT"], ["Macedonian", "MK"],
                                ["Malagasy", "MG"], ["Malay", "MS"], ["Malayalam", "ML"], ["Maltese", "MT"], ["Maori", "MI"], ["Marathi", "MR"], ["Moldavian", "MO"], ["Mongolian", "MN"], ["Nauru", "NA"], 
                                ["Nepali", "NE"], ["Norwegian", "NO"], ["Occitan", "OC"], ["Oriya", "OR"], ["Oromo, Afan", "OM"], ["Pashto, Pushto", "PS"], ["Persian", "FA"], ["Polish", "PL"], ["Portuguese", "PT"],
                                ["Punjabi", "PA"], ["Quechua", "QU"], ["Rhaeto-Romance", "RM"], ["Romanian", "RO"], ["Russian", "RU"], ["Samoan", "SM"], ["Sangro", "SG"], ["Sanskrit", "SA"], ["Serbian", "SR"], 
                                ["Serbo-Croatian", "SH"], ["Sesotho", "ST"], ["Setswana", "TN"], ["Shona", "SN"], ["Sindhi", "SD"], ["Singhalese", "SI"], ["Siswati", "SS"], ["Slovak", "SK"], ["Slovenian", "SL"], 
                                ["Somali", "SO"], ["Spanish", "ES"], ["Sudanese", "SU"], ["Swahili", "SW"], ["Swedish", "SV"], ["Tagalog", "TL"], ["Tajik", "TG"], ["Tamil", "TA"], ["Tatar", "TT"], ["Tegulu", "TE"], 
                                ["Thai", "TH"], ["Tibetan", "BO"], ["Tigrinya", "TI"], ["Tonga", "TO"], ["Tsonga", "TS"], ["Turkish", "TR"], ["Turkmen", "TK"], ["Twi", "TW"], ["Ukrainian", "UK"], ["Urdu", "UR"], 
                                ["Uzbek", "UZ"], ["Vietnamese", "VI"], ["Volapuk", "VO"], ["Welsh", "CY"], ["Wolof", "WO"], ["Xhosa", "XH"], ["Yiddish", "JI"], ["Yoruba", "YO"], ["Zulu", "ZU"]]
 
    @commands.command(pass_context=True, no_pm=False)
    async def translate(self, ctx, languageFrom, languageTo,  *text):
        """Translate text with use of translated.net \n *[lang1 lang2] + [Text to translate]"""
        author = ctx.message.author 
        #channel = ctx.channel.id
        
        if text == ():
            await send_cmd_help(ctx)
            return
            
        text = " ".join(text) 
        result = await self.translate_text(languageFrom, languageTo, text)
         
        if result == "not a valid language pair":
            await self.bot.say("{} `Error Translating, wrong language format, check DM`".format(author.mention))
            lenLang = len(self.ISO_LANG)
            done = 0
            msg = ""
            while (done < lenLang-1):
                w=done+4
                while (w > done):
                    msg = msg + "{} = {}, ".format(self.ISO_LANG[done][0], self.ISO_LANG[done][1])
                    done += 1
                msg = msg + "\n"    
                if len(msg) > 1500:
                    msg = "\n```ISO language abbreviations:\n\n{}\n```".format(msg)
                    await self.bot.send_message(ctx.message.author, msg)
                    msg = ""
                done += 1
        elif result == "get error":
            await self.bot.say("{} `Error Translating`".format(author.mention))      
        elif result != "":            
            await self.bot.say("**» {}({}) **{}".format(author, languageTo.lower(), result))
                
    #@commands.command(pass_context=True, no_pm=True, hidden=True)    
    async def systranslate(self, languageFrom, languageTo, text, cachResult=True):
        #channel = ctx.channel.id
        #print(channel)
        #print(languageFrom)
        #print(languageTo)
        #print(text)

        languageFrom = languageFrom.upper() 
        languageTo = languageTo.upper()
        print(languageFrom)
        print(languageTo)
        
        if text == "":
            return
        cached = None
        if languageFrom == languageTo:
            return text
        
        langPair =  languageFrom+languageTo
        if not langPair in self.cache:
            self.cache[langPair] = {}
        if langPair in self.cache:
            if text in self.cache[langPair]:
                cached = True
                print("cached")                
                return self.cache[langPair][text]
            else:
                cached = False
                print("Not cached")
        result = "Error"
        
        print("\nSYSTRANSLATE")
        result = await self.translate_text(languageFrom, languageTo, text)
        #result = result.decode('utf8')
        replaceThis = [["** ", "**"], [" **", "**"], ["* ", "*"], [" *", "*"], ["~~ ", "~~"], [" ~~", "~~"], ["__ ", "__"], [" __", "__"], ["``` ", "```"], [" ```", "```"], ["` ", "`"], [" `", "`"], ["&#39;", "'"]]
        replacedResult = result
        for r in range(0, len(replaceThis)):
            replacedResult = replacedResult.replace(replaceThis[r][0], replaceThis[r][1])

        if cachResult and not cached:
            self.cache[langPair][text] = (replacedResult)
        fileIO(CACHE, "save", self.cache)
        return replacedResult
        
    async def translate_text(self, languageFrom, languageTo, text):
        if text == ():
            return "empty"
        else:
            text = {"q":text}
            #print(text["q"])
           
            import urllib.parse as up            
            text = up.urlencode(text)
            #print(text)
            languageFrom = languageFrom.upper()
            languageTo = languageTo.upper()
                
            validPair = False   
            if self.check_language(self.ISO_LANG, languageFrom) and self.check_language(self.ISO_LANG, languageTo):
                validPair = True
            if not validPair:
                return "not a valid language pair"
            else: 
                translated = ""
                try:
                    search = ("http://api.mymemory.translated.net/get?{}&langpair={}|{}&de={}".format(text, languageFrom, languageTo, EMAIL))
                    #print(search)
                    async with aiohttp.get(search) as r:
                        result = await r.json()
                        #print("\nRESULT\n")
                        #print(result)
                        translated = result["matches"][0]["translation"]         
                except Exception as e:
                    #print("get Err")
                    print(e)
                    return "get error"                  
                    translated = ""
                    
                if translated != "":
                    if self.DEL_MSG:
                        try:
                            await self.bot.delete_message(ctx.message)
                        except Exception as e:
                            print("get")
                            if not self.NO_ERR:
                                print("Translated: Missing permissions (403) @ {}({}).{}({})".format(ctx.message.server, ctx.message.server.id, ctx.message.channel, ctx.message.channel.id))
                    return translated
                else:
                    return False

    @commands.group(pass_context=True)
    async def settr(self, ctx):
        """Magic OP commands for translated"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            
    @settr.command(pass_context=True, name="cl", hidden=True)
    async def _set_cl(self, ctx, languageTo):
        """Set channel language"""    
        await self.bot.say("placehlolder set channel language") 
    
    @settr.command(pass_context=True, name="update")
    async def _update(self, ctx, languageTo): 
        """Update a system translation."""
        languageTo = languageTo.upper()
        langPair =  "EN"+languageTo
        textFrom = ""
        textTo = ""
        
        if not langPair in self.cache:
            await self.bot.say("langpar: {} does not exist, create? (y/n)".format(langPair))
            response = await self.bot.wait_for_message(author=ctx.message.author)
            response = response.content.lower().strip()
            if response == "y":
                self.cache[langPair] = {}     
                fileIO(CACHE, "save", self.cache)
            else:
                await self.bot.say("Failed translation update.")
                return
        
        await self.bot.say("Please enter the static system value. (== to cancel).")
        response = await self.bot.wait_for_message(author=ctx.message.author)
        response = response.content.strip()
        if response == "==":
            await self.bot.say("Cancled translation update.")
            return
        elif response != "":
            textFrom = response
        else:
            await self.bot.say("Failed translation update.")            
            return
            
        await self.bot.say("Please enter the static system value (translated) (== to cancel).")
        response = await self.bot.wait_for_message(author=ctx.message.author)
        response = response.content.strip()
        if response == "==":
            await self.bot.say("cancled translation update.")
            return
        elif response != "":
            textTo = response
        else:
            await self.bot.say("Failed translation update.")            
            return
        
        fromTo = textFrom+" : "+textTo
        await self.bot.say("Please confirm the new static system translation value. (y/n).".format(fromTo))
        response = await self.bot.wait_for_message(author=ctx.message.author)
        response = response.content.lower().strip()
        if response == "y":
            self.cache[langPair][textFrom] = (textTo)
            fileIO(CACHE, "save", self.cache)
            await self.bot.say("Done.")             
            return
        elif response != "":
            textTo= response
        else:
            await self.bot.say("Failed translation update.")
            return
                    
    def check_language(self, langAvailable, langCheck):
        availLang = len(langAvailable)
        for m in range(availLang):
            if langAvailable[m][1] == langCheck:
                return True
        return False
        
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Set-up
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating {} folder...".format(DIR_DATA))
        os.makedirs(DIR_DATA)

def check_files():

    settings = {"CHANNELS": {}}

    f = SETTINGS
    if not fileIO(f, "check"):
        print("Creating default translated settings.json...")
        fileIO(f, "save", settings)  

    cache = {}

    f = CACHE
    if not fileIO(f, "check"):
        print("Creating translated cache.json...")
        fileIO(f, "save", cache)          
        
def setup(bot):
    check_folders()
    check_files()    
    bot.add_cog(Translated(bot))

