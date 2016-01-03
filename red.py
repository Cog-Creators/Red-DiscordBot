# -*- coding: utf-8 -*-

################################
######## Red - Discord bot #####
################################
#		 made by Twentysix
#
#

import discord
import logging
import time
import datetime
import requests
import traceback
import re
import youtube_dl
import os
import asyncio
from os import path
from random import choice, randint, shuffle

import dataIO #IO settings, proverbs, etc
import economy #Credits
import youtubeparser

from sys import modules

settings = dataIO.fileIO("settings.json", "load")

help = """**Commands list:**
!flip - Flip a coin
!rps [rock or paper o scissors] - Play rock paper scissors
!proverb
!choose option1 or option2 or option3 (...) - Random choice
!8 [question] - Ask 8 ball
!sw - Start/stop the stopwatch
!trivia start - Start a trivia session
!trivia stop - Stop a trivia session
!twitch [stream] - Check if stream is online
!roll [number] - Random number between 0 and [number]
!gif [text] - GIF search
!addcom [command] [text] - Add a custom command
!editcom [command] [text] - Edit a custom command
!delcom [command] - Delete a custom command

!audio help - Audio related commands
!economy - Economy explanation, if available
"""

youtube_dl_options = {
	'format': 'bestaudio/best',
	'extractaudio': True,
	'audioformat': "mp3",
	'outtmpl': '%(id)s',
	'noplaylist': True,
	'nocheckcertificate': True,
	'ignoreerrors': True,
	'quiet': True,
	'no_warnings': True}

audio_help = """
**General audio help commands:**
!next or !skip - Next song
!prev - Previous song
!pause - Pause song
!resume - Resume song
!repeat or !replay - Replay current song
!title or !song - Current song's title + link
!youtube [link] - Play a youtube video in a voice channel
!sing - Make Red sing
!stop - Stop any voice channel activity

**Playlist commands:**
!play [playlist_name] - Play chosen playlist
!playlists - Playlist's list
!shuffle - Mix music list
!addplaylist [name] [link] - Add a youtube playlist. Link format example: https://www.youtube.com/playlist?list=PLe8jmEHFkvsaDOOWcREvkgFoj6MD0pXXX
!delplaylist [name] - Delete a youtube playlist. Limited to author and admins.
!getplaylist - Receive the current playlist through DM. This also works with favorites.

**Favorites:**
!addfavorite - Add song to your favorites
!delfavorite - Remove song from your favorites
!playfavorites - Play your favorites

**You can submit your own playlist by doing the following:**
1) Make a txt file. Name must be only letters, numbers and underscores. It will be your playlist's name, so choose wisely.
2) One youtube link each line.
3) Send me the txt. If any line is incorrect I will reject it.
4) Listen to it with !play [playlist_name]!
"""

client = discord.Client()

if not discord.opus.is_loaded():
	discord.opus.load_opus('libopus-0.dll')

@client.async_event
async def on_message(message):

	await gameSwitcher.changeGame()

	if message.channel.is_private and message.attachments != []:
		await transferPlaylist(message)

	if not message.channel.is_private and message.author.id != client.user.id:
		if settings["FILTER"] and not isMemberAdmin(message):
			if await checkFilter(message) or await checkRegex(message):
				return False #exits without checking for commands
		if message.channel.id in shush_list and message.content == "!talk":
			await talk(message)

		if  message.channel.id not in shush_list:
			if message.content.lower() == settings["NAME"].lower() + "?":
				await client.send_message(message.channel, "`" + choice(greetings) + "`")
			elif message.content == settings["NAME"].upper():
				await client.send_message(message.channel, "`" + choice(greetings_caps) + "`")
			elif message.content == "!flip":
				await client.send_message(message.channel, "`" + settings["NAME"] + " flips a coin and... " + choice(["HEADS!`", "TAILS!`"]))
			elif message.content.startswith("!rps"):
				await rpsgame(message)
			elif message.content == "!proverb":
				await client.send_message(message.channel, "`" + choice(proverbs) + "`")
			elif message.content == "!help":
				await client.send_message(message.author, help)
				await client.send_message(message.channel, "{} `Check your DMs for the command list.`".format(message.author.mention))
			elif message.content.startswith('!choose'):
				await randomchoice(message)
			elif message.content.startswith('!8 ') and message.content.endswith("?") and len(message.content) > 5:
				await client.send_message(message.channel, "{}: ".format(message.author.mention) + "`" + choice(ball) + "`")
			elif message.content.startswith('!roll'):
				await roll(message)
			elif message.content.startswith('!addcom'):
				await addcom(message)
			elif message.content.startswith('!editcom'):
				await editcom(message)
			elif message.content.startswith('!delcom'):
				await delcom(message)
			elif message.content.startswith('!sw'):
				await stopwatch(message)
			elif message.content.startswith('!id'):
				await client.send_message(message.channel, "{} `Your id is {}`".format(message.author.mention, message.author.id))
			elif message.content.startswith('!twitch'):
				await twitchCheck(message)
			elif message.content.startswith('!image'):
				#image(message)
				pass
			elif message.content.startswith('!gif'):
				await gif(message)
			elif message.content.startswith('!uptime'):
				await uptime(message)
			elif message.content == "!sing":
				await playPlaylist(message, sing=True)
			elif message.content.startswith('!youtube'):
				await playVideo(message)
			################## music #######################
			elif message.content.startswith('!play '):
				await playPlaylist(message)
			elif message.content == "!stop":
				await leaveVoice()
			elif message.content == "!playlist" or message.content == "!playlists":
				await listPlaylists(message)
				await client.send_message(message.channel, "{} `Check your DMs for the playlists list.`".format(message.author.mention))
			elif message.content == "!skip" or message.content == "!next":
				if currentPlaylist: currentPlaylist.nextSong(currentPlaylist.getNextSong())
			elif message.content == "!prev" or message.content == "!previous":
				if currentPlaylist: currentPlaylist.nextSong(currentPlaylist.getPreviousSong())
			elif message.content == "!repeat" or message.content == "!replay":
				if currentPlaylist: currentPlaylist.nextSong(currentPlaylist.current)
			elif message.content == "!pause":
				if currentPlaylist: currentPlaylist.pause()
			elif message.content == "!resume":
				if currentPlaylist: currentPlaylist.resume()
			elif message.content == "!shuffle":
				if currentPlaylist: currentPlaylist.shuffle()
			elif message.content == "!song" or message.content == "!title" :
				if currentPlaylist: await getSongTitle(message)
			elif message.content == "!audio help":
				await client.send_message(message.author, audio_help)
				await client.send_message(message.channel, "{} `Check your DMs for the audio help.`".format(message.author.mention))
			elif message.content.startswith("!addplaylist"):
				await addPlaylist(message)
			elif message.content.startswith("!delplaylist"):
				await delPlaylist(message)
			elif message.content == "!addfavorite":
				await addToFavorites(message)
			elif message.content == "!delfavorite":
				await removeFromFavorites(message)
			elif message.content == "!playfavorites":
				await playFavorites(message)
			elif message.content == "!getplaylist":
				await sendPlaylist(message)
			################################################
			elif message.content == "!trivia start":
				if checkAuth("Trivia", message, settings):
					if not getTriviabyChannel(message.channel):
						#th = threading.Thread(target=controlTrivia, args=[message, True])
						#th.start()
						#await controlTrivia(message, True)
						await client.send_message(message.channel, "`Trivia is currently out of service. Sorry.`")
					else:
						await client.send_message(message.channel, "`A trivia session is already ongoing in this channel.`")
				else:
					await client.send_message(message.channel, "`Trivia is currently admin-only.`")
			elif message.content == "!trivia stop":
				if checkAuth("Trivia", message, settings):
					await controlTrivia(message, False)
				else:
					await client.send_message(message.channel, "`Trivia is currently admin-only.`")
			elif message.content == "!trivia":
				pass
			######## Admin commands #######################
			elif message.content.startswith('!addwords'):
				await addBadWords(message)
			elif message.content.startswith('!removewords'):
				await removeBadWords(message)
			elif message.content.startswith('!addregex ') and len(message.content) > 11:
				await addRegex(message)
			elif message.content.startswith('!removeregex ') and len(message.content) > 14:
				await removeRegex(message)
			elif message.content == "!shutdown":
				await shutdown(message)
			elif message.content.startswith('!join'):
				await join(message)
			elif message.content == "!leaveserver":
				await leave(message)
			elif message.content == "!shush":
				await shush(message)	
			elif message.content == "!talk": #prevents !talk custom command
				pass
			elif message.content == "!reload":
				reloadSettings(message)
			elif message.content.startswith("!name"):
				await changeName(message)
			elif message.content.startswith("!cleanup"):
				await cleanup(message)	
			###################################
			elif getTriviabyChannel(message.channel): #check if trivia is ongoing in the channel
				trvsession = getTriviabyChannel(message.channel)
				await trvsession.checkAnswer(message)
			elif "economy" in modules:
				await economy.checkCommands(message)

			if message.content.startswith('!') and len(message.content) > 2 and settings["CUSTOMCOMMANDS"]:
				await customCommand(message)

@client.async_event
async def on_ready():
	logger.info(settings["NAME"] + " is online. (" + client.user.id + ")")
	await gameSwitcher.changeGame(now=True)
	if client.user.name != settings["NAME"]:
		name = "." + settings["NAME"] + "()"
		await client.edit_profile(settings["PASSWORD"], username=name)
#	cns = threading.Thread(target=console, args=[])
#	cns.start() # console, WIP

@client.async_event
def on_message_delete(message):
	# WIP. Need to check for permissions
	#await client.send_message(message.channel, "{} `I have deleted your message.`".format(message.author.mention))
	pass

@client.async_event
async def on_message_edit(before, message):
	if message.author.id != client.user.id and settings["FILTER"] and not isMemberAdmin(message) and not message.channel.is_private:
		await checkFilter(message)
		await checkRegex(message)

def loggerSetup():
	#api wrapper
	logger = logging.getLogger('discord')
	logger.setLevel(logging.WARNING)
	handler = logging.FileHandler(filename='wrapper.log', encoding='utf-8', mode='a')
	handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
	logger.addHandler(handler)
	#Red
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.DEBUG)
	handler = logging.StreamHandler()
	handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
	logger.addHandler(handler)
	file_handler = logging.FileHandler(filename="red.log", mode='a')
	file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt="[%d/%m/%Y %H:%M]")
	file_handler.setFormatter(file_formatter)
	logger.addHandler(file_handler)
	return logger

class Trivia():
	def __init__(self, message):
		self.channel = message.channel
		self.stop = False
		self.currentQ = ""
		self.currentA = ""
		self.scorelist = {}
		self.Atimestamp = 99 #var initialization
		self.answered = False
		self.noAnswers = ["`No one got it. Disappointing.`", "`Oook... Next one...`", "`Maybe next time I'll tell you the solution.`",
		"`*sighs*`", "`I have no words. Next one...`", "`Come on, that one was easy.`", "`That was one of the easiest ones.`",
		"`I knew the answer.`", "`Is the game almost over? I have places to be.`", "`I'm on the verge of tears...`", "`:'(`", "`Really? No one?`", "`Crazy.`",
		"`I expected nothing and I'm still disappointed.`", "`*facepalm*`"]
		logger.info("Trivia started in channel " + self.channel.id)

	async def game(self):
		global trivia_sessions
		while not self.stop:
			self.answered = False
			self.currentQ, self.currentA = self.getTriviaQuestion() # [question, answer]
			logger.debug(self.currentA)
			await client.send_message(self.channel, "`" + self.currentQ + "`")
			time.sleep(settings["TRIVIADELAY"])
			await self.checkScore()
			if time.perf_counter() - self.Atimestamp  < 3: 
				time.sleep(2) # waits for 2 seconds if the answer was given very recently
			if not self.answered and not self.stop:
				await client.send_message(self.channel, choice(self.noAnswers))
#				client.send_typing(self.channel) #doesn't work for some reason
				time.sleep(3)
		trivia_sessions.remove(self)

	async def checkAnswer(self, message):
		if self.currentA.lower() == message.content.lower() and not self.answered:
			if message.author.name in self.scorelist:
				self.scorelist[message.author.name] += 1
			else:
				self.scorelist[message.author.name] = 1
			await client.send_message(self.channel, "{} `Correct answer! +1 point! ({} points)`".format(message.author.mention, str(self.scorelist[message.author.name])))
			self.Atimestamp = time.perf_counter()
			self.answered = True

	async def checkScore(self):
		for k, v in self.scorelist.items():
			if self.scorelist[k] == settings["TRIVIAMAXSCORE"]:
				await client.send_message(self.channel, "`Congratulations {}! You win!`".format(k))
				self.sendTable()
				self.stop = True

	async def sendTable(self):
		self.scorelist = sorted(self.scorelist.items(), reverse=True, key=lambda x: x[1]) # orders score from lower to higher
		t = "```Scores: \n"
		for score in self.scorelist:
			t += score[0] # name
			t += "\t"
			t += str(score[1]) # score
			t += "\n"
		t += "```"
		await client.send_message(self.channel, t)

	async def stopp(self):
		self.stop = True
		await client.send_message(self.channel, "`Trivia stopped!`")
		logger.info("Trivia stopped in channel " + self.channel.id)

	def getTriviaQuestion(self):
		q = choice(list(trivia_questions.keys()))
		return q, trivia_questions[q] # question, answer

class botPlays():
	def __init__(self):
		self.games = dataIO.fileIO("games.json", "load")
		self.lastChanged = int(time.perf_counter())
		self.delay = 300

	async def changeGame(self, now=False):
		if abs(self.lastChanged - int(time.perf_counter())) >= self.delay or now:
			self.lastChanged = int(time.perf_counter())
			await client.change_status(discord.Game(name=choice(self.games)))

class Playlist():
	def __init__(self, filename=None, singleSong=False): #a playlist with a single song is just there to make !addfavorite work with !youtube command
		self.filename = filename
		self.current = 0
		self.stop = False
		self.lastAction = 999
		if not singleSong:
			if filename["type"] == "playlist":
				self.playlist = dataIO.fileIO("playlists/" + filename["filename"] + ".txt", "load")["playlist"]
			elif filename["type"] == "favorites":
				self.playlist = dataIO.fileIO("favorites/" + filename["filename"] + ".txt", "load")
			else:
				raise("Invalid playlist call.")
			self.nextSong(0)

	def nextSong(self, nextTrack, lastError=False):
		global musicPlayer
		if not self.passedTime() < 1 and not self.stop: #direct control
			if musicPlayer: musicPlayer.stop()
			self.lastAction = int(time.perf_counter())
			try:
				musicPlayer = client.voice.create_ytdl_player(self.playlist[nextTrack], options=youtube_dl_options)
				musicPlayer.start()
			except:
				print("Something went wrong with track " + self.playlist[self.current])
				if not lastError: #prevents error loop
					self.lastAction = 999
				self.nextSong(self.getNextSong(), lastError=True)

	async def songSwitcher(self):
		while not self.stop:
			if musicPlayer.is_done() and not self.stop:
				self.nextSong(self.getNextSong())
			await asyncio.sleep(0.5)

	def passedTime(self):
		return abs(self.lastAction - int(time.perf_counter()))

	def getPreviousSong(self):
		try:
			song = self.playlist[self.current-1]
			self.current -= 1
			return self.current
		except: #if the current song was the first song, returns the last in the playlist
			song = self.playlist[len(self.current)-1]
			self.current -= 1
			return self.current

	def getNextSong(self):
		try:
			song = self.playlist[self.current+1]
			self.current += 1
			return self.current
		except: #if the current song was the last song, returns the first in the playlist
			song = self.playlist[0]
			self.current = 0
			return self.current

	def pause(self):
		if musicPlayer.is_playing() and not self.stop:
			musicPlayer.pause()

	def resume(self):
		if not self.stop:
			musicPlayer.resume()

	def shuffle(self):
		if not self.stop:
			shuffle(self.playlist)

async def addcom(message):
	if checkAuth("ModifyCommands", message, settings):
		msg = message.content.split()	
		if len(msg) > 2:
			msg = message.content[8:] # removes !addcom
			newcmd = msg[:msg.find(" ")] # extracts custom command
			customtext = msg[msg.find(" ") + 1:] # extracts [text]
			if len(newcmd) > 1 and newcmd.find(" ") == -1:
				if not message.channel.server.id in commands:
					commands[message.channel.server.id] = {}
				cmdlist = commands[message.channel.server.id]
				if newcmd not in cmdlist:
					cmdlist[newcmd] = customtext
					commands[message.channel.server.id] = cmdlist
					dataIO.fileIO("commands.json", "save", commands)
					logger.info("Saved commands database.")
					await client.send_message(message.channel, "`Custom command successfully added.`")
				else:
					await client.send_message(message.channel, "`This command already exists. Use !editcom [command] [text]`")

		else:
			await client.send_message(message.channel, "`!addcom [command] [text]`")
	else:
		await client.send_message(message.channel, "`You don't have permissions to edit custom commands.`")

async def editcom(message):
	if checkAuth("ModifyCommands", message, settings):
		msg = message.content.split()	
		if len(msg) > 2:
			msg = message.content[9:] # removes !editcom
			cmd = msg[:msg.find(" ")] # extracts custom command
			customtext = msg[msg.find(" ") + 1:] # extracts [text]
			if message.channel.server.id in commands:
				cmdlist = commands[message.channel.server.id]
				if cmd in cmdlist:
					cmdlist[cmd] = customtext
					commands[message.channel.server.id] = cmdlist
					dataIO.fileIO("commands.json", "save", commands)
					logger.info("Saved commands database.")
					await client.send_message(message.channel, "`Custom command successfully edited.`")
				else:
					await client.send_message(message.channel, "`That command doesn't exist. Use !addcom [command] [text]`")
			else:
				await client.send_message(message.channel, "`There are no custom commands in this server. Use !addcom [command] [text]`")

		else:
			await client.send_message(message.channel, "`!editcom [command] [text]`")
	else:
		await client.send_message(message.channel, "`You don't have permissions to edit custom commands.`")

async def delcom(message):
	if checkAuth("ModifyCommands", message, settings):
		msg = message.content.split()	
		if len(msg) == 2:
			if message.channel.server.id in commands:
				cmdlist = commands[message.channel.server.id]
				if msg[1] in cmdlist:
					cmdlist.pop(msg[1], None)
					commands[message.channel.server.id] = cmdlist
					dataIO.fileIO("commands.json", "save", commands)
					logger.info("Saved commands database.")
					await client.send_message(message.channel, "`Custom command successfully deleted.`")
				else:
					await client.send_message(message.channel, "`That command doesn't exist.`")
			else:
				await client.send_message(message.channel, "`There are no custom commands in this server. Use !addcom [command] [text]`")

		else:
			await client.send_message(message.channel, "`!delcom [command]`")
	else:
		await client.send_message(message.channel, "`You don't have permissions to edit custom commands.`")

def checkAuth(cmd, message, settings): #checks if those settings are on. If they are, it checks if the user is a owner
	if cmd == "ModifyCommands":
		if settings["EDIT_CC_ADMIN_ONLY"]:
			if isMemberAdmin(message):
				return True
			else:
				return False
		else:
			return True
	elif cmd == "Trivia":
		if settings["TRIVIA_ADMIN_ONLY"]:
			if isMemberAdmin(message):
				return True
			else:
				return False
		else:
			return True
	else:
		print("Invalid call to checkAuth")
		return False


async def rpsgame(message):
	rps = {"rock" : ":moyai:",
		   "paper": ":page_facing_up:",
		   "scissors":":scissors:"
	}
	msg = message.content.lower().split(" ")
	if len(msg) == 2:
		_, userchoice = msg
		if userchoice in rps.keys():
			botchoice = choice(list(rps.keys()))
			msgs = {
				"win": " You win {}!".format(message.author.mention),
				"square": " We're square {}!".format(message.author.mention),
				"lose": " You lose {}!".format(message.author.mention)
			}
			if userchoice == botchoice:
				await client.send_message(message.channel, rps[botchoice] + msgs["square"])
			elif userchoice == "rock" and botchoice == "paper":
				await client.send_message(message.channel, rps[botchoice] + msgs["lose"])
			elif userchoice == "rock" and botchoice == "scissors":
				await client.send_message(message.channel, rps[botchoice] + msgs["win"])
			elif userchoice == "paper" and botchoice == "rock":
				await client.send_message(message.channel, rps[botchoice] + msgs["win"])
			elif userchoice == "paper" and botchoice == "scissors":
				await client.send_message(message.channel, rps[botchoice] + msgs["lose"])
			elif userchoice == "scissors" and botchoice == "rock":
				await client.send_message(message.channel, rps[botchoice] + msgs["lose"])
			elif userchoice == "scissors" and botchoice == "paper":
				await client.send_message(message.channel, rps[botchoice] + msgs["win"])
		else:
			await client.send_message(message.channel, "`!rps [rock or paper or scissors]`")
	else:
		await client.send_message(message.channel, "`!rps [rock or paper or scissors]`")

async def randomchoice(message):
	frasi = ["Mmm... I think I'll choose ", "I choose ", "I prefer ", "This one is best: ", "This: "]
	msg = message.content[8:] # removes !choose
	msg = message.content.split(" or ")
	if len(msg) == 1:
		await client.send_message(message.channel, "`!choose option1 or option2 or option3 (...)`")
	elif len(msg) >= 2:
		msg.pop(0)
		await client.send_message(message.channel, "`" + choice(frasi) + choice(msg) + "`")
	else:
		await client.send_message(message.channel, "`The options must be at least two.`")

async def stopwatch(message):
	global stopwatches
	if message.author.id in stopwatches:
		tmp = abs(stopwatches[message.author.id] - int(time.perf_counter()))
		tmp = str(datetime.timedelta(seconds=tmp))
		await client.send_message(message.channel, "`Stopwatch stopped! Time: " + str(tmp) + " `")
		stopwatches.pop(message.author.id, None)
	else:
		stopwatches[message.author.id] = int(time.perf_counter())
		await client.send_message(message.channel, "`Stopwatch started! Use !sw to stop it.`")

async def image(message): # API's dead.
	msg = message.content.split()
	if len(msg) > 1:
		if len(msg[1]) > 1 and len([msg[1]]) < 20:
			try:
				msg.remove(msg[0])
				msg = "+".join(msg)
				search = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=" + msg + "&start=0"
				result = requests.get(search).json()
				url = result["responseData"]["results"][0]["url"]
				await client.send_message(message.channel, url)
			except:
				await client.send_message(message.channel, "Error.")
		else:
			await client.send_message(message.channel, "Invalid search.")
	else:
		await client.send_message(message.channel, "!image [text]")

async def gif(message):
	msg = message.content.split()
	if len(msg) > 1:
		if len(msg[1]) > 1 and len([msg[1]]) < 20:
			try:
				msg.remove(msg[0])
				msg = "+".join(msg)
				search = "http://api.giphy.com/v1/gifs/search?q=" + msg + "&api_key=dc6zaTOxFJmzC"
				result = requests.get(search).json()
				if result["data"] != []:		
					url = result["data"][0]["url"]
					await client.send_message(message.channel, url)
				else:
					await client.send_message(message.channel, "Your search terms gave no results.")
			except:
				await client.send_message(message.channel, "Error.")
		else:
			await client.send_message(message.channel, "Invalid search.")
	else:
		await client.send_message(message.channel, "!gif [text]")

async def controlTrivia(message, b):
	global trivia_sessions
	if b: #new trivia
		tmp = Trivia(message)
		trivia_sessions.append(tmp)
		await client.send_message(message.channel, "`Trivia started! First question...`")
		time.sleep(3)
		await tmp.game()
	else:
		await stopTriviabyChannel(message.channel)

async def stopTriviabyChannel(channel):
	global trivia_sessions
	for t in trivia_sessions:
		if t.channel == channel:
			await t.stopp()

def getTriviabyChannel(channel):
	for t in trivia_sessions:
		if t.channel == channel:
			return t
	return False

async def roll(message):
	msg = message.content.split()
	if len(msg) == 2:
		if msg[1].isdigit():
			msg[1] = int(msg[1])
			if msg[1] < 99999 and msg[1] > 1:
				await client.send_message(message.channel, "{} :game_die: `{}` :game_die:".format(message.author.mention, str(randint(1, msg[1]))))
			else:
				await client.send_message(message.channel, "{} `A number between 1 and 99999, maybe? :)`".format(message.author.mention))
		else:
			await client.send_message(message.channel, "`!roll [number]`")
	else:
		await client.send_message(message.channel, "`!roll [number]`")

async def checkFilter(message): #WIP
	msg = message.content.lower()
	if message.server.id in badwords:
		for word in badwords[message.server.id]:
			if msg.find(word.lower()) != -1:
				if canDeleteMessages(message):
					await client.delete_message(message)
					logger.info("Message eliminated.")
					return True
				else:
					logger.info("Couldn't delete message. I need permissions.")
					return False
	return False

async def checkRegex(message): #WIP
	msg = message.content #.lower()?
	if message.server.id in badwords_regex:
		for pattern in badwords_regex[message.server.id]:
			rr = re.search(pattern, msg, re.I | re.U)
			if rr != None:
				if canDeleteMessages(message):
					await client.delete_message(message)
					logger.info("Message eliminated. Regex: " + pattern)
					return True
				else:
					logger.info("Couldn't delete message. I need permissions.")
					return False
	return False

async def twitchCheck(message):
	msg = message.content.split()
	if len(msg) == 2:
		try:
			url =  "https://api.twitch.tv/kraken/streams/" + msg[1]
			data = requests.get(url).json()
			if "error" in data:
				await client.send_message(message.channel, "{} `There is no streamer named {}`".format(message.author.mention, msg[1]))
			elif "stream" in data:
				if data["stream"] != None:
					await client.send_message(message.channel, "{} `{} is online!` {}".format(message.author.mention, msg[1], "http://www.twitch.tv/" + msg[1]))
				else:
					await client.send_message(message.channel, "{} `{} is offline.`".format(message.author.mention, msg[1]))
			else:
				await client.send_message(message.channel, "{} `There is no streamer named {}`".format(message.author.mention, msg[1]))
		except:
			await client.send_message(message.channel, "{} `Error.`".format(message.author.mention))
	else:
		await client.send_message(message.channel, "{} `!twitch [stream]`".format(message.author.mention))

async def uptime(message):
	up = abs(uptime_timer - int(time.perf_counter()))
	up = str(datetime.timedelta(seconds=up))
	await client.send_message(message.channel, "`Uptime: {}`".format(up))

async def checkVoice(message):
	if not client.is_voice_connected():
		if message.author.voice_channel:
			await client.join_voice_channel(message.author.voice_channel)
		else:
			await client.send_message(message.channel, "{} `You need to join a voice channel first.`".format(message.author.mention))
			return False
	return True

async def playVideo(message):
	global musicPlayer, currentPlaylist
	if await checkVoice(message):
		pattern = "(?:youtube\.com\/watch\?v=)(.*)|(?:youtu.be/)(.*)"
		rr = re.search(pattern, message.content, re.I | re.U)
		if rr.group(1) != None:
			id = rr.group(1)
		elif rr.group(2) != None:
			id = rr.group(2)
		else:
			await client.send_message(message.channel, "{} `Invalid link.`".format(message.author.mention))
			return False
		stopMusic()
		if canDeleteMessages(message):
			await client.send_message(message.channel, "`Playing youtube video {} requested by {}`".format(id, message.author.name))
			await client.delete_message(message)
		currentPlaylist = Playlist(singleSong=True)
		currentPlaylist.playlist = ['https://www.youtube.com/watch?v=' + id]
		musicPlayer = client.voice.create_ytdl_player('https://www.youtube.com/watch?v=' + id, options=youtube_dl_options)
		musicPlayer.start()
		#!addfavorite compatibility stuff

async def playPlaylist(message, sing=False):
	global musicPlayer, currentPlaylist
	msg = message.content
	if not sing:
		if msg != "!play" or msg != "play ":
			if await checkVoice(message):
				msg = message.content[6:]
				if dataIO.fileIO("playlists/" + msg + ".txt", "check"):
					stopMusic()
					data = {"filename" : msg, "type" : "playlist"}
					currentPlaylist = Playlist(data)
					await asyncio.sleep(2)
					await currentPlaylist.songSwitcher()
				else:
					await client.send_message(message.channel, "{} `That playlist doesn't exist.`".format(message.author.mention))
	else:
		if await checkVoice(message):
			stopMusic()
			msg = ["Sure why not? :microphone:", "*starts singing* :microphone:", "*starts humming* :notes:"]
			playlist = ["https://www.youtube.com/watch?v=zGTkAVsrfg8", "https://www.youtube.com/watch?v=cGMWL8cOeAU",
						"https://www.youtube.com/watch?v=vFrjMq4aL-g", "https://www.youtube.com/watch?v=WROI5WYBU_A",
						"https://www.youtube.com/watch?v=41tIUr_ex3g", "https://www.youtube.com/watch?v=f9O2Rjn1azc"]
			song = choice(playlist)
			currentPlaylist = Playlist(singleSong=True)
			currentPlaylist.playlist = [song]
			musicPlayer = client.voice.create_ytdl_player(song, options=youtube_dl_options)
			musicPlayer.start()
			await client.send_message(message.channel, choice(msg))


async def leaveVoice():
	if client.is_voice_connected():
		stopMusic()
		await client.voice.disconnect()
		
async def listPlaylists(message):
	msg = "Available playlists: \n\n```"
	files = os.listdir("playlists/")
	for i, f in enumerate(files):
		if f.endswith(".txt"):
			if i % 4 == 0 and i != 0:
				msg = msg + f.replace(".txt", "") + "\n"
			else:
				msg = msg + f.replace(".txt", "") + "\t"
	msg += "```"
	"""
	files = os.listdir("playlists/")
	for f in files:
		if f.endswith(".txt"):
			msg = msg + f.replace(".txt", "") + "\t"
	msg += "`"
	"""
	await client.send_message(message.author, msg)


def stopMusic():
	global musicPlayer, currentPlaylist
	if currentPlaylist != None:
		print("Stopping playlist")
		currentPlaylist.stop = True
	if musicPlayer != None:
		musicPlayer.stop()

async def transferPlaylist(message):
	msg = message.attachments[0]
	if msg["filename"].endswith(".txt"):
		if not dataIO.fileIO("playlists/" + msg["filename"], "check"): #returns false if file already exists
			r = requests.get(msg["url"])
			data = r.text.replace("\r", "")
			data = data.split()
			if isPlaylistValid(data) and isPlaylistNameValid(msg["filename"].replace(".txt", "")):
				data = { "author" : message.author.id,
						 "playlist": data}
				dataIO.fileIO("playlists/" + msg["filename"], "save", data)
				await client.send_message(message.channel, "`Playlist added. Name: {}`".format(msg["filename"].replace(".txt", "")))
			else:
				await client.send_message(message.channel, "`Something is wrong with the playlist or its filename. Type !audio help to read how to format it properly.`")
		else:
			await client.send_message(message.channel, "`A playlist with that name already exists. Change the filename and resubmit it.`")

def isPlaylistValid(data):
	data = [y for y in data if y != ""] # removes all empty elements
	data = [y for y in data if y != "\n"]
	for link in data:
		pattern = "^(https:\/\/www\.youtube\.com\/watch\?v=...........*)|^(https:\/\/youtu.be\/...........*)|^(https:\/\/youtube\.com\/watch\?v=...........*)"
		rr = re.search(pattern, link, re.I | re.U)
		if rr == None:
			return False
	return True

def isPlaylistNameValid(name):
	for l in name:
		if l.isdigit() or l.isalpha() or l == "_":
			pass
		else:
			return False
	return True

def isPlaylistLinkValid(link):
	pattern = "^https:\/\/www.youtube.com\/playlist\?list=(.[^:/]*)"
	rr = re.search(pattern, link, re.I | re.U)
	if not rr == None:
		return rr.group(1)
	else:
		return False

async def addPlaylist(message):
	msg = message.content.split(" ")
	if len(msg) == 3:
		_, name, link = msg
		if isPlaylistNameValid(name) and len(name) < 25 and isPlaylistLinkValid(link):
			if dataIO.fileIO("playlists/" + name + ".txt", "check"):
				await client.send_message(message.channel, "`A playlist with that name already exists.`")
				return False
			links = youtubeparser.parsePlaylist(link)
			if links:
				data = { "author" : message.author.id,
						 "playlist": links}
				dataIO.fileIO("playlists/" + name + ".txt", "save", data)
				await client.send_message(message.channel, "`Playlist added. Name: {}`".format(name))
			else:
				await client.send_message(message.channel, "`Something went wrong. Either the link was incorrect or I was unable to retrieve the page.`")
		else:
			await client.send_message(message.channel, "`Something is wrong with the playlist's link or its filename. Remember, the name must be with only numbers, letters and underscores. Link must be this format: https://www.youtube.com/playlist?list=PLe8jmEHFkvsaDOOWcREvkgFoj6MD0pXXX`")

	else:
		await client.send_message(message.channel, "`!addplaylist [name] [link]`")

async def delPlaylist(message):
	msg = message.content.split(" ")
	if len(msg) == 2:
		_, filename = msg
		if dataIO.fileIO("playlists/" + filename + ".txt", "check"):
			authorid = dataIO.fileIO("playlists/" + filename + ".txt", "load")["author"]
			if message.author.id == authorid or isMemberAdmin(message):
				os.remove("playlists/" + filename + ".txt")
				await client.send_message(message.channel, "`Playlist {} removed.`".format(filename))
			else:
				await client.send_message(message.channel, "`Only the playlist's author and admins can do that.`")
		else:
			await client.send_message(message.channel, "`There is no playlist with that name.`")
	else:
		await client.send_message(message.channel, "`!delplaylist [name]`")

async def getSongTitle(message):
	title = youtubeparser.getTitle(currentPlaylist.playlist[currentPlaylist.current])
	if title:
		await client.send_message(message.channel, "`Current song: {}\n{}`".format(title, currentPlaylist.playlist[currentPlaylist.current]))
	else:
		await client.send_message(message.channel, "`I couldn't retrieve the current song's title.`")

async def addToFavorites(message):
	if currentPlaylist:
		if dataIO.fileIO("favorites/" + message.author.id + ".txt", "check"):
			data = dataIO.fileIO("favorites/" + message.author.id + ".txt", "load")
		else:
			data = []
		data.append(currentPlaylist.playlist[currentPlaylist.current])
		dataIO.fileIO("favorites/" + message.author.id + ".txt", "save", data)
		await client.send_message(message.channel, "{} `This song has been added to your favorites.`".format(message.author.mention))
	else:
		await client.send_message(message.channel, "{} `No song is being played`".format(message.author.mention))


async def removeFromFavorites(message):
	if currentPlaylist:
		if dataIO.fileIO("favorites/" + message.author.id + ".txt", "check"):
			data = dataIO.fileIO("favorites/" + message.author.id + ".txt", "load")
			if currentPlaylist.playlist[currentPlaylist.current] in data:
				data.remove(currentPlaylist.playlist[currentPlaylist.current])
				dataIO.fileIO("favorites/" + message.author.id + ".txt", "save", data)
				await client.send_message(message.channel, "{} `This song has been removed from your favorites.`".format(message.author.mention))
			else:
				await client.send_message(message.channel, "{} `This song isn't in your favorites.`".format(message.author.mention))
		else:
			await client.send_message(message.channel, "{} `You don't have any favorites yet. Start adding them with !addfavorite`".format(message.author.mention))
	else:
		await client.send_message(message.channel, "{} `No song is being played`".format(message.author.mention))

async def playFavorites(message):
	global musicPlayer, currentPlaylist
	if dataIO.fileIO("favorites/" + message.author.id + ".txt", "check") and await checkVoice(message):
		data = {"filename" : message.author.id, "type" : "favorites"}
		stopMusic()
		currentPlaylist = Playlist(data)
		await asyncio.sleep(2)
		await currentPlaylist.songSwitcher()
	else:
		await client.send_message(message.channel, "{} `You don't have any favorites yet. Start adding them with !addfavorite`".format(message.author.mention))

async def sendPlaylist(message):
	if currentPlaylist:
		msg = "Here's the current playlist:\n```"
		for track in currentPlaylist.playlist:
			msg += track
			msg += "\n"
		msg += "```"
		await client.send_message(message.author, msg)

############## ADMIN COMMANDS ###################

async def shutdown(message):
	if isMemberAdmin(message):
		await client.send_message(message.channel, "`" + settings["NAME"] + " shutting down... See you soon.` :hand:")
		await client.logout()
		exit(1)
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def join(message):
	if isMemberAdmin(message):
		msg = message.content.split()
		if len(msg) > 1:
			await client.accept_invite(msg[1])
		else:
			print("Join: missing parameters")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def leave(message):
	if isMemberAdmin(message):
		await client.send_message(message.channel, "`Bye.`")
		await client.leave_server(message.channel.server)
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def shush(message):
	global shush_list
	if isMemberAdmin(message):
		await client.send_message(message.channel, "`Ok, I'll ignore this channel.`")
		shush_list.append(message.channel.id)
		dataIO.fileIO("shushlist.json", "save", shush_list)
		logger.info("Saved silenced channels database.")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def talk(message):
	if isMemberAdmin(message):
		if message.channel.id in shush_list:
			shush_list.remove(message.channel.id)
			dataIO.fileIO("shushlist.json", "save", shush_list)
			logger.info("Saved silenced channels database.")
			await client.send_message(message.channel, "`Aaand I'm back.`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def addBadWords(message):
	global badwords
	if isMemberAdmin(message):
		msg = message.content.split()
		if len(msg) >= 2:
			del msg[0]
			if not message.server.id in badwords:
				badwords[message.server.id] = []
			for word in msg:
					if word.find("/") != -1:
						word = word.replace("/", " ")
					badwords[message.server.id].append(word)
			await client.send_message(message.channel, "`Updated banned words database.`")
			dataIO.fileIO("filter.json", "save", badwords)
			logger.info("Saved filter words.")
		else:
			await client.send_message(message.channel, "`!addwords [word1] [word2] [phrase/with/many/words] (...)`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def removeBadWords(message):
	global badwords
	if isMemberAdmin(message):
		msg = message.content.split()
		if len(msg) >= 2:
			del msg[0]
			if message.server.id in badwords:
				for w in msg:
					try:
						if w.find("/") != -1:
							w = w.replace("/", " ")
						badwords[message.server.id].remove(w)
					except:
						pass
				await client.send_message(message.channel, "`Updated banned words database.`")
				dataIO.saveFilter(badwords)
		else:
			await client.send_message(message.channel, "`!removewords [word1] [word2] [phrase/with/many/words](...)`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def changeName(message):
	global settings
	if isMemberAdmin(message):
		msg = message.content.split()
		if len(msg) == 2:
			try:
				name = "." + msg[1] + "()"
				await client.edit_profile(settings["PASSWORD"], username=name)
				settings["NAME"] = msg[1]
				dataIO.fileIO("settings.json", "save", settings)
				logger.info("Saved settings.")
			except:
				pass
		else:
			await client.send_message(message.channel, "`!name [new name]`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def addRegex(message):
	global badwords_regex
	if isMemberAdmin(message):
		msg = message.content
		msg = msg[10:]
		if not message.server.id in badwords_regex:
			badwords_regex[message.server.id] = []
		badwords_regex[message.server.id].append(msg)
		await client.send_message(message.channel, "`Updated regex filter database.`")
		dataIO.fileIO("regex_filter.json", "save", badwords_regex)
		logger.info("Saved regex filter database.")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def removeRegex(message):
	global badwords_regex
	if isMemberAdmin(message):
		msg = message.content
		msg = msg[13:]
		if message.server.id in badwords_regex:
			if msg in badwords_regex[message.server.id]:
				badwords_regex[message.server.id].remove(msg)
				await client.send_message(message.channel, "`Updated regex filter database.`")
				dataIO.saveRegex(badwords_regex)
			else:
				await client.send_message(message.channel, "`No match.`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def reloadSettings(message):
	if isMemberAdmin(message):
		loadDataFromFiles(True)
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def cleanup(message):
	if isMemberAdmin(message):
		if canDeleteMessages(message):
			msg = message.content.split()
			if len(msg) == 2:
				if msg[1].isdigit():
					n = int(msg[1])
					for x in await client.logs_from(message.channel, limit=n+1):
						await client.delete_message(x)
				else:
					await client.send_message(message.channel, "`!cleanup [number]`")
			else:
				await client.send_message(message.channel, "`!cleanup [number]`")
		else:
			await client.send_message(message.channel, "`I need permissions to delete messages.`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

def isMemberAdmin(message):
	if not message.channel.is_private:
		if discord.utils.get(message.author.roles, name=settings["ADMINROLE"]) != None:
			return True
		else:
			return False
	else:
		return False

def canDeleteMessages(message):
	return message.channel.permissions_for(message.server.me).can_manage_messages

################################################

async def customCommand(message):
	msg = message.content[1:]
	if message.channel.server.id in commands:
		cmdlist = commands[message.channel.server.id]
		if msg in cmdlist:
			await client.send_message(message.channel, cmdlist[msg] )

def console():
	while True:
		try:
			exec(input(""))
		except Exception:
			traceback.print_exc()
			print("\n")

logger = loggerSetup()

dataIO.logger = logger

def loadDataFromFiles(loadsettings=False):
	global proverbs, commands, trivia_questions, badwords, badwords_regex, shush_list

	proverbs = dataIO.loadProverbs()
	logger.info("Loaded " + str(len(proverbs)) + " proverbs.")

	commands = dataIO.fileIO("commands.json", "load")
	logger.info("Loaded " + str(len(commands)) + " lists of commands.")

#	trivia_questions = dataIO.loadTrivia()
#	logger.info("Loaded " + str(len(trivia_questions)) + " questions.")

	badwords = dataIO.fileIO("filter.json", "load")
	logger.info("Loaded " + str(len(badwords)) + " words.")

	badwords_regex = dataIO.fileIO("regex_filter.json", "load")
	logger.info("Loaded " + str(len(badwords_regex)) + " regex lists.")

	shush_list = dataIO.fileIO("shushlist.json", "load")
	logger.info("Loaded " + str(len(shush_list)) + " silenced channels.")
	
	if loadsettings:
		global settings
		settings = dataIO.fileIO("settings.json", "load")


loadDataFromFiles()

ball = ["As I see it, yes", "It is certain", "It is decidedly so", "Most likely", "Outlook good",
 "Signs point to yes", "Without a doubt", "Yes", "Yes – definitely", "You may rely on it", "Reply hazy, try again",
 "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
 "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]

greetings = ["Hey.", "Yes?", "Hi.", "I'm listening.", "Hello.", "I'm here."]
greetings_caps = ["DON'T SCREAM", "WHAT", "WHAT IS IT?!", "ì_ì", "NO CAPS LOCK"]

stopwatches = {}

trivia_sessions = []

message = ""

gameSwitcher = botPlays()

if "economy" in modules:
	economy.initialize(client)

uptime_timer = int(time.perf_counter())

musicPlayer = None
currentPlaylist = None

client.run(settings["EMAIL"], settings["PASSWORD"])