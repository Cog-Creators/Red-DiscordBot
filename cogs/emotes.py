import discord
from discord.ext import commands
import aiohttp
import asyncio
from cogs.utils import checks
from cogs.utils.dataIO import fileIO
import os
import requests
from __main__ import send_cmd_help

class Emotes:
    """Twitch Emotes commands."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/emotes/settings.json","load")
        self.emote_list = []
        self.available_emotes = fileIO("data/emotes/available_emotes.json","load")
        self.emote_url = "https://api.twitch.tv/kraken/chat/emoticons"

    def save_settings(self):
        fileIO("data/emotes/settings.json","save",self.settings)

    def save_available_emotes(self):
        fileIO("data/emotes/available_emotes.json","save",self.available_emotes)

    def get_limit_per_message(self,server):
        if server is None:
            return 5
        if not self._is_enabled(server):
            return 5
        return self.settings[server.id].get("LIMIT_PER_MESSAGE",5)

    def set_limit_per_message(self,server,value):
        if server is None:
            return
        if self._is_enabled(server):
            self.settings[server.id]["LIMIT_PER_MESSAGE"] = int(value)
            self.save_settings()

    def update_emote_list(self):
        resp = requests.get(self.emote_url)
        data = resp.json().get("emoticons",{})
        #to_remove = (emote["chan_id"] for server in self.available_emotes for emote in self.available_emotes[server])
        #self.emote_list = list(filter(lambda emote: emote.get("emoticon_set",-1) not in to_remove,data))
        self.emote_list = data

    def _is_enabled(self,server):
        assert isinstance(server,discord.Server)
        if server.id not in self.settings:
            return False
        if not self.settings[server.id]["ENABLED"]:
            return False
        return True

    @commands.group(pass_context=True,no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def emoteset(self,ctx):
        """Various emote settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            #TODO server-specific settings

    @emoteset.command(name="enabled",pass_context=True)
    async def _emoteset_enabled(self,ctx,setting : bool):
        """Bool to see if emotes are enabled on this server."""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {}
        self.settings[server.id]["ENABLED"] = bool(setting)
        self.save_settings()
        if server.id not in self.available_emotes:
            self.available_emotes[server.id] = []
            self.save_available_emotes()
        if setting:
            await self.bot.reply("emotes are now enabled.")
        else:
            await self.bot.reply("emotes are now disabled.")

    @emoteset.command(name="limit",pass_context=True)
    async def _emoteset_limit(self,ctx,limit : int):
        """Emote limit per message."""
        if limit < 0: await send_cmd_help(ctx)
        self.set_limit_per_message(ctx.message.server,limit)
        await self.bot.say("Limit set to {}.".format(limit))

    def _write_image(self, chan_id, name, image_data):
        #Assume channel folder already exists
        with open('data/emotes/{}/{}'.format(chan_id,name),'wb') as f:
            f.write(image_data)

    async def _remove_all_emotes(self,server,chan_id,name=""):
        assert isinstance(server,discord.Server)
        if server.id not in self.available_emotes:
            return
        self.available_emotes[server.id] = [emote for emote in self.available_emotes[server.id] if emote["chan_id"] != chan_id or emote["name"] == name]
        self.save_available_emotes()

    async def _add_emote(self,server,chan_id):
        assert isinstance(server,discord.Server)
        if chan_id == -1:
            return
        if not os.path.exists("data/emotes/{}".format(chan_id)):
            os.makedirs("data/emotes/{}".format(chan_id))
        await self._remove_all_emotes(server,chan_id)
        for emote in self.emote_list:
            if chan_id == emote["images"][0].get("emoticon_set",-1):
                url = emote["images"][0].get("url","")
                name = emote.get("regex","")
                file_name = url.split('/')[-1]
                if url == "" or name == "":
                    continue
                if not os.path.exists('data/emotes/{}/{}'.format(chan_id,file_name)):
                    try:
                        async with aiohttp.get(url) as r:
                            image = await r.content.read()
                    except Exception as e:
                        print("Huh, I have no idea what errors aiohttp throws.")
                        print("This is one of them:")
                        print(e)
                        print(dir(e))
                        print("------")
                        return
                    self._write_image(chan_id,file_name,image)
                if server.id not in self.available_emotes:
                    self.available_emotes[server.id] = {}
                self.available_emotes[server.id].append({
                                                    "name":name,
                                                    "file_name":file_name,
                                                    "chan_id":chan_id
                                                })
        self.save_available_emotes()

    @commands.command(pass_context=True)
    async def emote(self,ctx,emote_name:str):
        """Enabled emote and all emotes from same twitch channel"""
        server = ctx.message.server
        if not self._is_enabled(server):
            await self.bot.say("Emotes are not enabled on this server.")
            return
        server_emotes = self.available_emotes[server.id]
        if emote_name in server_emotes:
            await self.bot.say("This server already has '{}'".format(emote_name))
            return
        await self.bot.say("Retrieving emotes from '{}'. Please wait a moment.".format(emote_name))
        for emote in self.emote_list:
            if emote_name == emote.get("regex",""):
                chan_id = emote["images"][0].get("emoticon_set",-1)
                if chan_id == -1:
                    await self.bot.say("Yeah, something failed, try again later?")
                    return
                await self._add_emote(server,chan_id)
                await self.bot.say("'{}' and other channel emotes added.".format(emote_name))
                return
        await self.bot.say("No such emote '{}' found.".format(emote_name))

    async def check_messages(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.is_private:
            return
        if not self._is_enabled(message.server):
            return

        valid_emotes = self.available_emotes[message.server.id]

        splitted = message.content.split(' ')

        count = 0

        for word in splitted:
            for emote in valid_emotes:
                if word == emote.get("name",""):
                    fname = 'data/emotes/{}/{}'.format(emote["chan_id"],emote["file_name"])
                    if not os.path.exists(fname):
                        await self._add_emote(chan_id)
                    await self.bot.send_file(message.channel,fname)
                    if len(splitted) == 1:
                        try:
                            await self.bot.delete_message(message)
                        except:
                            return
                    count += 1
                    if self.get_limit_per_message(message.server) != 0 and count >= self.get_limit_per_message(message.server):
                        return
                    break

def check_folders():
    if not os.path.exists("data/emotes"):
        print("Creating data/emotes folder...")
        os.makedirs("data/emotes")

def check_files():
    f = "data/emotes/settings.json"
    if not fileIO(f, "check"):
        print("Creating empty settings.json...")
        fileIO(f, "save", {})

    f = "data/emotes/available_emotes.json"
    if not fileIO(f, "check"):
        print("Creating empty available_emotes.json...")
        fileIO(f, "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Emotes(bot)
    n.update_emote_list()
    bot.add_listener(n.check_messages, "on_message")
    bot.add_cog(n)