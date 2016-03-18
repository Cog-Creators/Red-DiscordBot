import discord
from discord.ext import commands
import asyncio
import threading
import queue
import os
from random import choice as rndchoice
from random import shuffle
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
import glob
import re
import aiohttp
import json
import time

try:
    import youtube_dl
except:
    youtube_dl = None

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except OSError: # Incorrect bitness
    opus = False
except: # Missing opus
    opus = None
else:
    opus = True

youtube_dl_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'outtmpl': '%(id)s',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'default_search': 'auto',
    'no_warnings': True,
    'outtmpl': "data/audio/cache/%(id)s",
    'default_search' : 'auto'}

class Audio:
    """Music streaming."""

    def __init__(self, bot):
        self.bot = bot
        self.music_player = EmptyPlayer()
        self.settings = fileIO("data/audio/settings.json", "load")
        self.queue_mode = False
        self.queue = []
        self.q = queue.Queue()
        self.playlist = []
        self.titles = []
        self.search_results = []
        self.current = -1 #current track index in self.playlist
        self.downloader = {"DONE" : False, "TITLE" : False, "ID" : False, "URL" : False, "DURATION" : False, "DOWNLOADING" : False}
        self.skip_votes = []
        self.cleanup_timer = int(time.perf_counter())
        self.past_titles = [] # This is to prevent the audio module from setting the status to None if a status other than a track's title gets set

        self.sing =  ["https://www.youtube.com/watch?v=zGTkAVsrfg8", "https://www.youtube.com/watch?v=cGMWL8cOeAU",
                     "https://www.youtube.com/watch?v=vFrjMq4aL-g", "https://www.youtube.com/watch?v=WROI5WYBU_A",
                     "https://www.youtube.com/watch?v=41tIUr_ex3g", "https://www.youtube.com/watch?v=f9O2Rjn1azc"]

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *link : str):
        """Plays videos (links/search terms)
        """
        if self.downloader["DOWNLOADING"]:
            await self.bot.say("I'm already downloading a track.")
            return
        msg = ctx.message
        if await self.check_voice(msg.author, msg):
            if link != ():
                link = " ".join(link)
                if "http" not in link and "www." not in link:
                    link = "[SEARCH:]" + link
                else:
                    if not self.is_playlist_valid([link]):
                        await self.bot.say("Invalid link.")
                        return
                if await self.is_alone_or_admin(msg):
                    self.queue = []
                    self.current = -1
                    self.playlist = []
                    self.titles = []
                    self.queue.append(link)
                    result = await self.get_song_metadata(link)
                    self.titles.append(result["title"])
                    self.music_player.paused = False
                    if self.music_player.is_playing(): self.music_player.stop()
                    await self.bot.say("Playing requested link...")
                else:
                    self.playlist = []
                    self.current = -1
                    if not self.queue: await self.bot.say("The link has been put into queue.")
                    self.queue.append(link)
                    result = await self.get_song_metadata(link)
                    self.titles.append(result["title"])
            else:
                await self.bot.say("You need to add a link or search terms.")

    @commands.command(aliases=["title"])
    async def song(self):
        """Shows song title
        """
        if self.downloader["TITLE"] and "localtracks" not in self.downloader["TITLE"]:
            url = ""
            if self.downloader["URL"]: url = 'Link : "' + self.downloader["URL"] + '"'
            await self.bot.say(self.downloader["TITLE"] + "\n" + url)
        else:
            await self.bot.say("No title available.")

    @commands.command(name="playlist", pass_context=True, no_pm=True)
    async def _playlist(self, ctx, name : str): #some checks here
        """Plays saved playlist
        """
        await self.start_playlist(ctx, name, random=False)

    @commands.command(pass_context=True, no_pm=True)
    async def mix(self, ctx, name : str): #some checks here
        """Plays saved playlist (shuffled)
        """
        await self.start_playlist(ctx, name, random=True)

    async def start_playlist(self, ctx, name, random=None):
        if self.downloader["DOWNLOADING"]:
            await self.bot.say("I'm already downloading a track.")
            return
        msg = ctx.message
        name += ".txt"
        if await self.check_voice(msg.author, msg):
            if os.path.isfile("data/audio/playlists/" + name):
                self.queue = []
                self.titles = fileIO("data/audio/playlists/" + name, "load")["titles"]
                self.current = -1
                self.playlist = fileIO("data/audio/playlists/" + name, "load")["playlist"]
                if random:                
                    pl = self.playlist
                    ttl = self.titles
                    combo = list(zip(pl, ttl))
                    shuffle(combo)
                    self.playlist, self.titles = zip(*combo)
                    
                self.music_player.paused = False
                if self.music_player.is_playing(): self.music_player.stop()
            else:
                await self.bot.say("There's no playlist with that name.")

    @commands.command(pass_context=True, aliases=["next"], no_pm=True)
    async def skip(self, ctx):
        """Skips song
        """
        msg = ctx.message
        if self.music_player.is_playing():
            if await self.is_alone_or_admin(msg):
                self.music_player.paused = False
                if self.music_player.is_playing(): self.music_player.stop()
            else:
                await self.vote_skip(msg)

    async def vote_skip(self, msg):
        v_channel = msg.server.me.voice_channel
        if msg.author.voice_channel.id == v_channel.id:
            if msg.author.id in self.skip_votes:
                await self.bot.say("You already voted.")
                return
            self.skip_votes.append(msg.author.id)
            if msg.server.me.id not in self.skip_votes: self.skip_votes.append(msg.server.me.id)
            current_users = []
            for m in v_channel.voice_members:
                current_users.append(m.id)

            clean_skip_votes = [] #Removes votes of people no longer in the channel
            for m_id in self.skip_votes:
                if m_id in current_users:
                    clean_skip_votes.append(m_id)
            self.skip_votes = clean_skip_votes

            votes_needed = int((len(current_users)-1) / 2)

            if len(self.skip_votes)-1 >= votes_needed:
                self.music_player.paused = False
                if self.music_player.is_playing(): self.music_player.stop()
                self.skip_votes = []
                return
            await self.bot.say("You voted to skip. Votes: [{0}/{1}]".format(str(len(self.skip_votes)-1), str(votes_needed)))
    
    @commands.command(pass_context=True, no_pm=True)
    async def local(self, ctx, name : str):
        """Plays a local playlist

        For bot's owner:
        https://github.com/Twentysix26/Red-DiscordBot/wiki/Audio-module"""
        help_link = "https://github.com/Twentysix26/Red-DiscordBot/wiki/Audio-module"
        if self.downloader["DOWNLOADING"]:
            await self.bot.say("I'm already downloading a track.")
            return
        msg = ctx.message
        localplaylists = self.get_local_playlists()
        self.titles = []
        if localplaylists and ("data/audio/localtracks/" not in name and "\\" not in name):
            if name in localplaylists:
                files = []
                if glob.glob("data/audio/localtracks/" + name + "/*.mp3"):
                    files.extend(glob.glob("data/audio/localtracks/" + name + "/*.mp3"))
                if glob.glob("data/audio/localtracks/" + name + "/*.flac"):
                    files.extend(glob.glob("data/audio/localtracks/" + name + "/*.flac"))
                if await self.is_alone_or_admin(msg):
                    if await self.check_voice(msg.author, ctx.message):
                        for file in files:
                            f = file.split("\\")
                            self.titles.append(f[1][:-4])
                        self.queue = []
                        self.current = -1
                        self.playlist = files
                        self.music_player.paused = False
                        if self.music_player.is_playing(): self.music_player.stop()
                else:
                    await self.bot.say("I'm in queue mode. Controls are disabled if you're in a room with multiple people.")
            else:
                await self.bot.say("There is no local playlist with that name.")
        else:
            await self.bot.say(message.channel, "There are no valid playlists in the localtracks folder.\nIf you're the owner, see {}".format(help_link))

    @commands.command(pass_context=True, no_pm=True)
    async def loop(self, ctx):
        """Loops single song
        """
        msg = ctx.message
        if self.music_player.is_playing():
            if await self.is_alone_or_admin(msg):
                self.current = -1
                if self.downloader["URL"]:
                    self.playlist = [self.downloader["URL"]]
                else: # local
                    self.playlist = [self.downloader["ID"]]
                await self.bot.say("I will play this song on repeat.")
            else:
                await self.bot.say("I'm in queue mode. Controls are disabled if you're in a room with multiple people.")

    @commands.command(pass_context=True, no_pm=True)
    async def shuffle(self, ctx):
        """Shuffle playlist
        """
        msg = ctx.message
        if self.music_player.is_playing():
            if await self.is_alone_or_admin(msg):
                if self.playlist:
                    pl = self.playlist
                    ttl = self.titles
                    combo = list(zip(pl, ttl))
                    shuffle(combo)
                    self.playlist, self.titles = zip(*combo)
                    await self.bot.say("The order of this playlist has been mixed")
            else:
                await self.bot.say("I'm in queue mode. Controls are disabled if you're in a room with multiple people.")

    @commands.command(pass_context=True, aliases=["previous"], no_pm=True) #TODO, PLAYLISTS
    async def prev(self, ctx):
        """Previous song
        """
        msg = ctx.message
        if self.music_player.is_playing() and self.playlist:
            if await self.is_alone_or_admin(msg):
                self.current -= 2
                if self.current == -1:
                    self.current = len(self.playlist) -3
                elif self.current == -2:
                    self.current = len(self.playlist) -2
                self.music_player.paused = False
                if self.music_player.is_playing(): self.music_player.stop()



    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops audio activity
        """
        msg = ctx.message
        if self.music_player.is_playing():
            if await self.is_alone_or_admin(msg):
                await self.close_audio()
            else:
                await self.bot.say("You can't stop music when there are other people in the channel! Vote to skip instead.")
        else:
            await self.close_audio()

    async def close_audio(self):
        self.queue = []
        self.playlist = []
        self.current = -1
        if self.music_player.is_playing(): self.music_player.stop()
        await asyncio.sleep(1)
        if self.bot.voice: await self.bot.voice.disconnect()

    @commands.command(name="queue", pass_context=True, no_pm=True) #check that author is in the same channel as the bot
    async def _queue(self, ctx, *link : str):
        """Add links or search terms to queue

        Shows queue list if no links are provided.
        """
        if link == ():
            pages = await self.queue_titles()
            await self.bot.say("Tracks in queue: \n\n")
            for page in pages:
                await self.bot.say(page)
                await asyncio.sleep(1)
            await self.bot.say("\n\nType queue <link> to add a link or search terms to the queue.")
        elif await self.check_voice(ctx.message.author, ctx.message):
            if not self.playlist:
                link = " ".join(link)
                if "http" not in link or "." not in link:
                    link = "[SEARCH:]" + link
                else:
                    if not self.is_playlist_valid([link]):
                        await self.bot.say("Invalid link.")
                        return
                self.queue.append(link)
                msg = ctx.message
                result = await self.get_song_metadata(link)
                self.titles.append(result["title"])
                try: # In case of invalid SOUNDCLOUD ID
                    if result["title"] != []:
                        await self.bot.say("{} has been put into the queue by {}.".format(result["title"], msg.author))
                    else:
                        await self.bot.say("The song has been put into the queue by {}, however it may error.".format(msg.author))
                except:
                    await self.bot.say("A song has been put into the queue by {}.".format(msg.author))

            else:
                await self.bot.say("I'm already playing a playlist.")
        else:
            await self.bot.say("That link is now allowed.")

    async def is_alone_or_admin(self, message): #Direct control. fix everything
        author = message.author
        server = message.server
        if not self.settings["QUEUE_MODE"]:
            return True
        elif author.id == bot_settings.owner:
            return True
        elif discord.utils.get(author.roles, name=bot_settings.get_server_admin(server)) is not None:
            return True
        elif discord.utils.get(author.roles, name=bot_settings.get_server_mod(server)) is not None:
            return True
        elif len(author.voice_channel.voice_members) in (1, 2):
            return True
        else:
            return False

    @commands.command(name="sing", pass_context=True, no_pm=True)
    async def _sing(self, ctx):
        """Makes Red sing"""
        if self.downloader["DOWNLOADING"]:
            await self.bot.say("I'm already downloading a track.")
            return
        msg = ctx.message
        if await self.check_voice(msg.author, msg):
            if not self.music_player.is_playing():
                    self.queue = []
                    await self.play_video(rndchoice(self.sing))
            else:
                if await self.is_alone_or_admin(msg):
                    self.queue = []
                    await self.play_video(rndchoice(self.sing))
                else:
                    await self.bot.say("I'm already playing music for someone else at the moment.")

    @commands.command()
    async def pause(self):
        """Pauses the current song"""
        if self.music_player.is_playing():
            self.music_player.paused = True
            self.music_player.pause()
            await self.bot.say("Song paused.")
            
    @commands.command()
    async def resume(self):
        """Resumes paused song."""
        if not self.music_player.is_playing():
            self.music_player.paused = False
            self.music_player.resume()
            await self.bot.say("Resuming song.")

    @commands.group(name="list", pass_context=True)
    async def _list(self, ctx):
        """Lists playlists"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_list.command(name="playlist", pass_context=True)
    async def list_playlist(self, ctx):
        msg = "Available playlists: \n\n```"
        files = os.listdir("data/audio/playlists/")
        if files:
            for i, f in enumerate(files):
                if f.endswith(".txt"):
                    if i % 4 == 0 and i != 0:
                        msg = msg + f.replace(".txt", "") + "\n"
                    else:
                        msg = msg + f.replace(".txt", "") + "\t"
            msg += "```"
            await self.bot.send_message(ctx.message.author, msg)
        else:
            await self.bot.say("There are no playlists.")

    @_list.command(name="local", pass_context=True)
    async def list_local(self, ctx):
        msg = "Available local playlists: \n\n```"
        dirs = self.get_local_playlists()
        if dirs:
            for i, d in enumerate(dirs):
                if i % 4 == 0 and i != 0:
                    msg = msg + d + "\n"
                else:
                    msg = msg + d + "\t"
            msg += "```"
            await self.bot.send_message(ctx.message.author, msg)
        else:
            await self.bot.say("There are no local playlists.")

    async def local_songs_change_status(self):
        current_song = self.downloader["TITLE"]
        if "data/audio/localtracks" in current_song:
            f = current_song.split("\\")
            current_song = f[1][:-4]
            await self.bot.change_status(discord.Game(name=current_song))
        return current_song
    
    @_list.command(name="queue", pass_context=True)
    async def list_queue(self, ctx):
        pages = await self.queue_titles()
        await self.bot.say("Tracks in queue: \n\n")
        for page in pages:
            await self.bot.say(page)
            await asyncio.sleep(1)
    
    async def queue_titles(self):
        message = ""
        pages = []
        current_song = await self.local_songs_change_status()
        message += ("Current Song: "+current_song+"\n\n")
        for i,t in enumerate(self.titles):
            message += str(i+1)+". "+t+"\n"
            if len(message)>1500:
                pages.append(message)
                message = ""
        pages.append(message)
        return pages

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def audioset(self, ctx):
        """Changes audio module settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "```"
            await self.bot.say(msg)

    @audioset.command(name="queue")
    async def queueset(self):
        """Enables/disables forced queue"""
        self.settings["QUEUE_MODE"] = not self.settings["QUEUE_MODE"]
        if self.settings["QUEUE_MODE"]:
            await self.bot.say("Queue mode is now on.")
        else:
            await self.bot.say("Queue mode is now off.")
        fileIO("data/audio/settings.json", "save", self.settings)

    @audioset.command(name="status")
    async def songstatus(self):
        """Enables/disables songs' titles as status"""
        self.settings["TITLE_STATUS"] = not self.settings["TITLE_STATUS"]
        if self.settings["TITLE_STATUS"]:
            await self.bot.say("Songs' titles will show up as status.")
        else:
            await self.bot.say("Songs' titles will no longer show up as status.")
        fileIO("data/audio/settings.json", "save", self.settings)

    @audioset.command()
    async def maxlength(self, length : int):
        """Maximum track length (seconds) for requested links"""
        self.settings["MAX_LENGTH"] = length
        await self.bot.say("Maximum length is now " + str(length) + " seconds.")
        fileIO("data/audio/settings.json", "save", self.settings)

    @audioset.command()
    async def volume(self, level : float):
        """Sets the volume (0-1)"""
        if level >= 0 and level <= 1:
            self.settings["VOLUME"] = level
            await self.bot.say("Volume is now set at " + str(level) + ". It will take effect after the current track.")
            fileIO("data/audio/settings.json", "save", self.settings)
        else:
            await self.bot.say("Volume must be between 0 and 1. Example: 0.40")

    @audioset.command()
    @checks.is_owner()
    async def maxcache(self, size : int):
        """Sets the maximum audio cache size (megabytes)

        If set to 0, auto cleanup is disabled."""
        self.settings["MAX_CACHE"] = size
        fileIO("data/audio/settings.json", "save", self.settings)
        if not size:
            await self.bot.say("Auto audio cache cleanup disabled.")
        else:
            await self.bot.say("Maximum audio cache size has been set to " + str(size) + "MB.")

    @audioset.command()
    @checks.is_owner()
    async def soundcloud(self, ID : str=None):
        """Sets the SoundCloud Client ID
        """
        self.settings["SOUNDCLOUD_CLIENT_ID"] = ID
        fileIO("data/audio/settings.json", "save", self.settings)
        if not ID:
            await self.bot.say("SoundCloud API intergration has been disabled")
        else:
            await self.bot.say("SoundCloud Client ID has been set")

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def cache(self, ctx):
        """Audio cache management"""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Current audio cache size: " + str(self.cache_size()) + "MB" )

    @cache.command(name="empty")
    async def cache_delete(self):
        """Empties audio cache"""
        self.empty_cache()
        await self.bot.say("Cache emptied.")

    def empty_cache(self):
        files = os.listdir("data/audio/cache")
        for f in files:
            try:
                os.unlink("data/audio/cache/" + f)
            except PermissionError: # In case it tries to delete the file that it's currently playing
                pass

    def cache_size(self):
        total = [os.path.getsize("data/audio/cache/" + f) for f in os.listdir("data/audio/cache")]
        size = 0
        for f in total:
            size += f
        return int(size / (1024*1024.0))

    async def play_video(self, link):
        self.downloader = {"DONE" : False, "TITLE" : False, "ID" : False, "URL": False, "DURATION" : False, "DOWNLOADING" : False}
        if "https://" in link or "http://" in link or "[SEARCH:]" in link:
            path = "data/audio/cache/"
            t = threading.Thread(target=self.get_video, args=(link,self,))
            t.start()
        else: #local
            path = ""
            self.downloader = {"DONE" : True, "TITLE" : link, "ID" : link, "URL": False, "DURATION" : False, "DOWNLOADING" : False}
            await self.local_songs_change_status()
        while not self.downloader["DONE"]:
            await asyncio.sleep(1)
        if self.downloader["ID"]:
            try:
                if self.music_player.is_playing(): self.music_player.stop()
                self.music_player = self.bot.voice.create_ffmpeg_player(path + self.downloader["ID"], options='''-filter:a "volume={}"'''.format(self.settings["VOLUME"]))
                self.music_player.paused = False
                self.music_player.start()
                if path != "" and self.settings["TITLE_STATUS"]:
                    self.past_titles.append(self.downloader["TITLE"])
                    await self.bot.change_status(discord.Game(name=self.downloader["TITLE"]))
            except discord.errors.ClientException:
                print("Error: I can't play music without ffmpeg. Install it.")
                self.downloader = {"DONE" : False, "TITLE" : False, "ID" : False, "URL": False, "DURATION" : False, "DOWNLOADING" : False}
                self.queue = []
                self.playlist = []
                self.titles = []
            except Exception as e:
                print(e)
        else:
            pass


    async def check_voice(self, author, message):
        if self.bot.is_voice_connected():
            v_channel = self.bot.voice.channel
            if author.voice_channel == v_channel:
                return True
            elif len(v_channel.voice_members) == 1:
                if author.voice_channel:
                    if author.voice_channel.permissions_for(message.server.me).connect:
                        wait = await self.close_audio()
                        await self.bot.join_voice_channel(author.voice_channel)
                        return True
                    else:
                        await self.bot.say("I need permissions to join that voice channel.")
                        return False
                else:
                    await self.bot.say("You need to be in a voice channel.")
                    return False
            else:
                if not self.playlist and not self.queue:
                    return True
                else:
                    await self.bot.say("I'm already playing music for other people.")
                    return False
        elif author.voice_channel:
            if author.voice_channel.permissions_for(message.server.me).connect:
                await self.bot.join_voice_channel(author.voice_channel)
                return True
            else:
                await self.bot.say("I need permissions to join that voice channel.")
                return False
        else:
            await self.bot.say("You need to be in a voice channel.")
            return False

    async def changeLink(self, new_link):
        self.skip_votes = []
        await self.play_video(new_link)

    async def queue_manager(self):
        while "Audio" in self.bot.cogs:
            if not self.music_player.paused and not self.music_player.is_playing():
                if self.queue:
                    await self.changeLink(self.queue.pop(0))
                elif self.playlist:
                    if not self.current == len(self.playlist)-1:
                        self.current += 1
                    else:
                        self.current = 0
                    await self.changeLink(self.playlist[self.current])
            await asyncio.sleep(1)

    def get_video(self, url, audio):
        try:
            self.downloader["DOWNLOADING"] = True
            yt = youtube_dl.YoutubeDL(youtube_dl_options)
            if "[SEARCH:]" not in url:
                v = yt.extract_info(url, download=False, process=False)
            else:
                url = url.replace("[SEARCH:]", "")
                url = "https://youtube.com/watch?v=" + yt.extract_info(url, download=False, process=False)["entries"][0]["id"]
                v = yt.extract_info(url, download=False, process=False)
            if v["duration"] > self.settings["MAX_LENGTH"]: raise MaximumLength("Track exceeded maximum length. See help audioset maxlength")
            if not os.path.isfile("data/audio/cache/" + v["id"]):
                v = yt.extract_info(url, download=True)
            audio.downloader = {"DONE" : True, "TITLE" : v["title"], "ID" : v["id"], "URL" : url, "DURATION" : v["duration"], "DOWNLOADING" : False} #Errors out here if invalid link
        except Exception as e:
            print(e) # TODO
            audio.downloader = {"DONE" : True, "TITLE" : False, "ID" : False, "URL" : False, "DOWNLOADING" : False}

    async def incoming_messages(self, msg):
        if msg.author.id != self.bot.user.id:

            if self.settings["MAX_CACHE"] != 0:
                if abs(self.cleanup_timer - int(time.perf_counter())) >= 900: # checks cache's size every 15 minutes
                    self.cleanup_timer = int(time.perf_counter())
                    if self.cache_size() >= self.settings["MAX_CACHE"]:
                        self.empty_cache()
                        print("Cache emptied.")

            if msg.channel.is_private and msg.attachments != []:
                await self.transfer_playlist(msg)
        if not msg.channel.is_private:
            if not self.playlist and not self.queue and not self.music_player.is_playing() and str(msg.server.me.game) in self.past_titles:
                self.past_titles = []
                await self.bot.change_status(None)

    def get_local_playlists(self):
        dirs = []
        files = os.listdir("data/audio/localtracks/")
        for f in files:
            if os.path.isdir("data/audio/localtracks/" + f) and " " not in f:
                if glob.glob("data/audio/localtracks/" + f + "/*.mp3") != []:
                    dirs.append(f)
                elif glob.glob("data/audio/localtracks/" + f + "/*.flac") != []:
                    dirs.append(f)
        if dirs != []:
            return dirs
        else:
            return False

    async def search_yt(self, yt, s_count, search_for):
        name = 'ytsearch'
        search_format = '%s%s:%s' % (name, s_count, search_for)
        entries = (yt.extract_info(search_format, download=False, process=False))['entries']
        for i in entries:
            self.search_results.append(await self.bot.say("https://www.youtube.com/watch?v="+i['url']))

    async def get_sc_metadata(self, api_url):
        url = "{0}.json?client_id={1}".format(api_url, self.settings["SOUNDCLOUD_CLIENT_ID"])
        result = await self.get_json(url)
        return result

    async def search_sc(self, yt, s_count, search_for):
        name = 'scsearch'
        search_format = '%s%s:%s' % (name, s_count, search_for)
        entries = (yt.extract_info(search_format, download=False, process=False))['entries']
        for i in entries:
            result = await self.get_sc_metadata(i['url'])
            self.search_results.append(await self.bot.say(result['permalink_url']))
    
    @commands.command(pass_context=True, no_pm=True)
    async def search(self, ctx, where : str, length : int , *query : str):
        """Searches for tracks from youtube/soundcloud Ex. yt 1 gmod"""
        
        self.search_results = [ctx.message]
        yt = youtube_dl.YoutubeDL(youtube_dl_options)
        if 'yt' in where or 'youtube' in where:
            await self.search_yt(yt, length, query)
        elif 'sc' in where or 'soundcloud' in where:
            if self.settings["SOUNDCLOUD_CLIENT_ID"] is None:
                await self.bot.say("Soundcloud ID is required for SC Search.")
            else:
                await self.search_sc(yt, length, query)

    @commands.command(aliases=["delsrc"],pass_context=True, no_pm=True)
    async def deletesearch(self, ctx):
        """Deletes all recent search results"""
        
        if self.search_results == []:
            self.bot.delete_message(ctx.message)
            return       
        self.search_results.append(ctx.message)
        self.search_results.reverse()
        try:
            for result in self.search_results:             
                await self.bot.delete_message(result)
            self.search_results = []
        except discord.errors.Forbidden:
            await self.bot.say("I need permissions to delete search results in this channel.")

    @commands.command(pass_context=True, no_pm=True)
    async def addplaylist(self, ctx, name : str, link : str): #CHANGE COMMAND NAME
        """Adds tracks from youtube / soundcloud playlist link"""
        temp_list = self.titles
        self.titles = []
        if self.is_playlist_name_valid(name) and len(name) < 25:
            if fileIO("playlists/" + name + ".txt", "check"):
                await self.bot.say("`A playlist with that name already exists.`")
                return False
            if "youtube" in link.lower():
                links = await self.parse_yt_playlist(link)
            elif "soundcloud" in link.lower():
                links = await self.parse_sc_playlist(link)
            if links:
                data = { "author"  : ctx.message.author.id,
                         "playlist": links,
                         "titles"  : self.titles,
                         "link"    : link}
                fileIO("data/audio/playlists/" + name + ".txt", "save", data)
                self.titles = temp_list
                await self.bot.say("Playlist added. Name: {}, songs: {}".format(name, str(len(links))))
            else:
                await self.bot.say("Something went wrong. Either the link was incorrect or I was unable to retrieve the page.")
        else:
            await self.bot.say("Something is wrong with the playlist's link or its filename. Remember, the name must be with only numbers, letters and underscores.")

    @commands.command(pass_context=True, no_pm=True)
    async def delplaylist(self, ctx, name : str):
        """Deletes playlist

        Limited to owner, admins and author of the playlist."""
        file_path = "data/audio/playlists/" + name + ".txt"
        author = ctx.message.author
        if fileIO(file_path, "check"):
            playlist_author_id = fileIO(file_path, "load")["author"]
            check = await self.admin_or_owner(ctx.message)
            if check or author.id == playlist_author_id:
                os.remove(file_path)
                await self.bot.say("Playlist {} has been removed.".format(name))
            else:
                await self.bot.say("Only owner, admins and the author of the playlist can delete it.")
        else:
            await self.bot.say("There's no playlist with that name.")

    async def admin_or_owner(self, message):
        if message.author.id == bot_settings.owner:
            return True
        elif discord.utils.get(message.author.roles, name=bot_settings.get_server_admin(message.server)) is not None:
            return True
        else:
            return False

    async def transfer_playlist(self, message):
        msg = message.attachments[0]
        if msg["filename"].endswith(".txt"):
            if not fileIO("data/audio/playlists/" + msg["filename"], "check"): #returns false if file already exists
                r = await aiohttp.get(msg["url"])
                r = await r.text()
                data = r.replace("\r", "")
                data = data.split()
                if self.is_playlist_valid(data) and self.is_playlist_name_valid(msg["filename"].replace(".txt", "")):
                    data = { "author" : message.author.id,
                             "playlist": data,
                             "titles"  : self.titles,
                             "link"    : False}
                    fileIO("data/audio/playlists/" + msg["filename"], "save", data)
                    await self.bot.send_message(message.channel, "Playlist added. Name: {}".format(msg["filename"].replace(".txt", "")))
                else:
                    await self.bot.send_message(message.channel, "Something is wrong with the playlist or its filename.") # Add formatting info
            else:
                await self.bot.send_message(message.channel, "A playlist with that name already exists. Change the filename and resubmit it.")

    def is_playlist_valid(self, data):
        data = [y for y in data if y != ""] # removes all empty elements
        data = [y for y in data if y != "\n"]
        pattern = "|".join(fileIO("data/audio/accepted_links.json", "load"))
        for link in data:
            rr = re.search(pattern, link, re.I | re.U)
            if rr == None:
                return False
        return True

    def is_playlist_link_valid(self, link):
        pattern = "^https:\/\/www.youtube.com\/playlist\?list=(.[^:/]*)"
        rr = re.search(pattern, link, re.I | re.U)
        if not rr == None:
            return rr.group(1)
        else:
            return False

    def is_playlist_name_valid(self, name):
        for l in name:
            if l.isdigit() or l.isalpha() or l == "_":
                pass
            else:
                return False
        return True

    def worker(self):
        while True:
            item = self.q.get()
            yt = youtube_dl.YoutubeDL(youtube_dl_options)
            if item is None:
                break
            self.titles[item[1]]=yt.extract_info(item[0], download=False, process=False)['title']
            self.q.task_done()
    
    async def get_titles_yt(self, entries):
    
        for i in entries:
            self.titles.append(i['title'])
            
    async def parse_yt_playlist(self, url):
        try:
            if not "www.youtube.com/playlist?list=" in url:   
                url = url.split("&")
                url = "https://www.youtube.com/playlist?" + [x for x in url if "list=" in x][0]
            playlist = []
            yt = youtube_dl.YoutubeDL(youtube_dl_options)
            entries = list(yt.extract_info(url, download=False, process=False)["entries"])
            await self.get_titles_yt(entries)
            for entry in entries:
                playlist.append("https://www.youtube.com/watch?v=" + entry["id"])           
            return playlist
        except:
            return False

    async def get_titles_sc(self, entries, link):                
        if (self.settings["SOUNDCLOUD_CLIENT_ID"] is None):
            threads = []      
            urls = []       
            for i in entries:
                urls.append(i['url'])
            length = len(urls)
            self.titles = [None]*length
            for i in range(0,length):
                t = threading.Thread(target=self.worker)
                t.start()
                threads.append(t)
                
            for counter in range(0,length):
                self.q.put([urls[counter],counter])
            
            # block until all tasks are done
            self.q.join()

            # stop workers
            for i in range(0,length):
                self.q.put(None)
            for t in threads:
                t.join()
        else:
            semi_url = 'http://api.soundcloud.com/resolve.json?url={0}&client_id={1}'
            url = semi_url.format(link,self.settings["SOUNDCLOUD_CLIENT_ID"])
            entries = await(self.get_json(url))
            for i in (entries['tracks']):
                self.titles.append(i['title'])
            
    async def parse_sc_playlist(self, link):
        try:
            playlist = []
            yt = youtube_dl.YoutubeDL(youtube_dl_options)
            entries = list(yt.extract_info(link, download=False, process=False)["entries"])
            await self.get_titles_sc(entries,link)
            for i in entries:
                playlist.append(i['url'][:4] + 's' + i['url'][4:])
            return playlist
        except:
            return False

    async def get_json(self, url):
        """
        Returns the JSON from an URL.
        Expects the url to be valid and return a JSON object.
        """
        async with aiohttp.get(url) as r:
            result = await r.json()
        return result

    async def get_song_metadata(self, song_url):
        """
        Returns JSON object containing metadata about the song.
        Expects song_url to be valid url and in acepted_list
        """

        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube|youtu|youtube-nocookie)\.(com|be)/'
            '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
        soundcloud_regex = "^(https:\\/\\/soundcloud\\.com\\/.*)"
        is_youtube_link = re.match(youtube_regex, song_url)
        is_soundcloud_link = re.match(soundcloud_regex, song_url)

        if is_youtube_link:
            url = "http://www.youtube.com/oembed?url={0}&format=json".format(song_url)
            result = await self.get_json(url)
        elif is_soundcloud_link and (self.settings["SOUNDCLOUD_CLIENT_ID"] is not None):
            url = "http://api.soundcloud.com/resolve.json?url={0}&client_id={1}".format(song_url, self.settings["SOUNDCLOUD_CLIENT_ID"])
            result = await self.get_json(url)
        else:
            result = {"title": "A song "}
        return result

class EmptyPlayer(): #dummy player
    def __init__(self):
        self.paused = False

    def stop(self):
        pass

    def is_playing(self):
        return False

class MaximumLength(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message

def check_folders():
    folders = ("data/audio", "data/audio/cache", "data/audio/playlists", "data/audio/localtracks")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_files():

    default = {"VOLUME" : 0.5, "MAX_LENGTH" : 3700, "QUEUE_MODE" : True, "MAX_CACHE" : 0, "SOUNDCLOUD_CLIENT_ID": None, "TITLE_STATUS" : True}
    settings_path = "data/audio/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default audio settings.json...")
        fileIO(settings_path, "save", default)
    else: #consistency check
        current = fileIO(settings_path, "load")
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print("Adding " + str(key) + " field to audio settings.json")
            fileIO(settings_path, "save", current)


    allowed = ["^(https:\/\/www\\.youtube\\.com\/watch\\?v=...........*)", "^(https:\/\/youtu.be\/...........*)",
              "^(https:\/\/youtube\\.com\/watch\\?v=...........*)", "^(https:\/\/soundcloud\\.com\/.*)"]

    if not os.path.isfile("data/audio/accepted_links.json"):
        print("Creating accepted_links.json...")
        fileIO("data/audio/accepted_links.json", "save", allowed)

def setup(bot):
    check_folders()
    check_files()
    if youtube_dl is None:
        raise RuntimeError("You need to run `pip3 install youtube_dl`")
        return
    if opus is False:
        raise RuntimeError("Your opus library's bitness must match your python installation's bitness. They both must be either 32bit or 64bit.")
        return
    elif opus is None:
        raise RuntimeError("You need to install ffmpeg and opus. See \"https://github.com/Twentysix26/Red-DiscordBot/wiki/Requirements\"")
        return
    loop = asyncio.get_event_loop()
    n = Audio(bot)
    loop.create_task(n.queue_manager())
    bot.add_listener(n.incoming_messages, "on_message")
    bot.add_cog(n)
