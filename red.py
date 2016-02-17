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
import aiohttp
import traceback
import re
import youtube_dl
import os
import asyncio
import glob
from os import path
from random import choice, randint, shuffle

import dataIO #IO settings, proverbs, etc
import economy #Credits
import youtubeparser

from sys import modules

#settings = {"PREFIX" : "!"} #prevents boot error

def loadHelp():
	global help, audio_help, meme_help, admin_help, trivia_help

	help = """**Commands list:**
	{0}flip - Flip a coin
	{0}rps [rock or paper o scissors] - Play rock paper scissors
	{0}proverb
	{0}choose option1 or option2 or option3 (...) - Random choice
	{0}8 [question] - Ask 8 ball
	{0}sw - Start/stop the stopwatch
	{0}avatar [name or mention] - Shows user's avatar
	{0}trivia start - Start a trivia session
	{0}trivia stop - Stop a trivia session
	{0}twitch [stream] - Check if stream is online
	{0}twitchalert [stream] - Whenever the stream is online the bot will send an alert in the channel (admin only)
	{0}stoptwitchalert [stream] - Stop sending alerts about the specified stream in the channel (admin only)
	{0}roll [number] - Random number between 0 and [number]
	{0}gif [text] - GIF search
	{0}imdb - Retrieves a movie's information from IMDB using its title
	{0}urban [text] - Search definitions in the urban dictionary
	{0}meme [ID;Text1;Text2] - Create a meme
	{0}imdb [search terms] - Search on IMDB
	{0}customcommands - Custom commands' list
	{0}addcom [command] [text] - Add a custom command
	{0}editcom [command] [text] - Edit a custom command
	{0}delcom [command] - Delete a custom command

	{0}meme help - Memes help
	{0}audio help - Audio related commands
	{0}economy - Economy explanation, if available
	{0}trivia - Trivia commands and lists
	""".format(settings["PREFIX"])

	audio_help = """
	**General audio help commands:**
	{0}next or {0}skip - Next song
	{0}prev - Previous song
	{0}pause - Pause song
	{0}resume - Resume song
	{0}repeat or {0}replay - Replay current song
	{0}title or {0}song - Current song's title + link
	{0}youtube [link] - Play a youtube video in a voice channel
	{0}sing - Make Red sing
	{0}stop - Stop any voice channel activity
	{0}volume [0-1] - Sets the volume
	{0}downloadmode - Disables/enables download mode (admin only)

	**Playlist commands:**
	{0}play [playlist_name] - Play chosen playlist
	{0}playlists - Playlists' list
	{0}shuffle - Mix music list
	{0}addplaylist [name] [link] - Add a youtube playlist. Link format example: https://www.youtube.com/playlist?list=PLe8jmEHFkvsaDOOWcREvkgFoj6MD0pXXX
	{0}delplaylist [name] - Delete a youtube playlist. Limited to author and admins.
	{0}getplaylist - Receive the current playlist through DM. This also works with favorites.

	**Local commands:**
	{0}local [playlist_name] - Play chosen local playlist
	{0}locallist or {0}local or {0}locals - Local playlists' list

	**Favorites:**
	{0}addfavorite - Add song to your favorites
	{0}delfavorite - Remove song from your favorites
	{0}playfavorites - Play your favorites

	**You can submit your own playlist by doing the following:**
	1) Make a txt file. Name must be only letters, numbers and underscores. It will be your playlist's name, so choose wisely.
	2) One youtube link each line.
	3) Send me the txt. If any line is incorrect I will reject it.
	4) Listen to it with {0}play [playlist_name]!
	""".format(settings["PREFIX"])

	meme_help = """
	Usage example:
	One-Does-Not-Simply 	Template ID: 61579
	{0}meme 61579;Test;Test

	Memes list:
	ID		Name
	61579	One Does Not Simply
	438680	Batman Slapping Robin	
	61532	The Most Interesting Man In The World
	101470	Ancient Aliens
	61520	Futurama Fry
	347390	X, X Everywhere
	5496396	Leonardo Dicaprio Cheers
	61539	First World Problems
	61546	Brace Yourselves X is Coming	
	16464531	But Thats None Of My Business
	61582	Creepy Condescending Wonka
	61585	Bad Luck Brian	
	563423	That Would Be Great
	61544	Success Kid	
	405658	Grumpy Cat	
	101288	Third World Skeptical Kid
	8072285	Doge
	100947	Matrix Morpheus
	1509839	Captain Picard Facepalm
	61533	X All The Y
	1035805	Boardroom Meeting Suggestion
	245898	Picard Wtf
	21735	The Rock Driving	
	259680	Am I The Only One Around Here
	14230520	Black Girl Wat
	40945639	Dr Evil Laser
	235589	Evil Toddler
	61580	Too Damn High
	61516	Philosoraptor
	6235864	Finding Neverland
	9440985	Face You Make Robert Downey Jr	
	101287	Third World Success Kid
	100955	Confession Bear	
	444501	The lie detector determined that was a lie. The fact that you X determined that was a lie. Maury Povich.
	97984	Disaster Girl	
	442575	Aint Nobody Got Time For That	
	109765	Ill Just Wait Here
	124212	Say That Again I Dare You
	28251713	Oprah You Get A	
	61556	Grandma Finds The Internet	
	101440	10 Guy
	101711	Skeptical Baby	
	101716	Yo Dawg Heard You	
	101511	Dont You Squidward

	For more memes: `https://imgflip.com/memetemplates`
	Choose a meme, click on "Blank Template" then add the ID
	""".format(settings["PREFIX"])

	admin_help = """
	**Admin commands:**
	{0}addwords [word1 word2 (...)] [phrase/with/many/words] - Add words to message filter
	{0}removewords [word1 word2 (...)] [phrase/with/many/words] - Remove words from message filter
	{0}addregex [regex] - Add regular expression to message filter
	{0}removeregex [regex] - Remove regular expression from message filter
	{0}shutdown - Shutdown the bot
	{0}join [invite] - Join another server
	{0}leaveserver - Leave server
	{0}shush - Ignore the current channel
	{0}talk - Stop ignoring the current channel
	{0}reload - Reload most files. Useful in case of manual edits
	{0}name [name] - Change the bot's name
	{0}cleanup [number] - Delete the last [number] messages
	{0}cleanup [name/mention] [number] - Delete the last [number] of messages by [name]
	{0}blacklist [name/mention] - Add user to Red's blacklist
	{0}forgive [name/mention] - Removes user from Red's blacklist
	{0}setting [setting] [value] - Modify setting
	""".format(settings["PREFIX"])

	trivia_help = """
	**Trivia commands:**
	{0}trivia - Trivia questions lists and help
	{0}trivia [name] - Starts trivia session with specified list
	{0}trivia random - Starts trivia session with random list
	{0}trivia stop - Stop trivia session
	""".format(settings["PREFIX"])

youtube_dl_options = {
	'format': 'bestaudio/best',
	'extractaudio': True,
	'audioformat': "mp3",
	'outtmpl': '%(id)s',
	'noplaylist': True,
	'nocheckcertificate': True,
	'ignoreerrors': True,
	'quiet': True,
	'no_warnings': True,
	'outtmpl': "cache/%(id)s"}

client = discord.Client()

if not discord.opus.is_loaded():
	discord.opus.load_opus('libopus-0.dll')

@client.async_event
async def on_message(message):
	global trivia_sessions

	p = settings["PREFIX"]

	await gameSwitcher.changeGame()

	if message.author.id in blacklisted_users and not isMemberAdmin(message):
		return False

	if message.channel.is_private and message.attachments != []:
		await transferPlaylist(message)

	if not message.channel.is_private and message.author.id != client.user.id:
		if settings["FILTER"] and not isMemberAdmin(message):
			if await checkFilter(message) or await checkRegex(message):
				return False #exits without checking for commands
		if message.channel.id in shush_list and message.content == p + "talk":
			await talk(message)

		if  message.channel.id not in shush_list:
			if message.content == client.user.name.upper() or message.content == client.user.name.upper() + "?":
				await client.send_message(message.channel, "`" + choice(greetings_caps) + "`")
			elif message.content.lower() == client.user.name.lower() + "?":
				await client.send_message(message.channel, "`" + choice(greetings) + "`")
			elif message.content == client.user.mention + " ?" or message.content == client.user.mention + "?":
				await client.send_message(message.channel, "`" + choice(greetings) + "`")
			elif message.content == p + "flip":
				await client.send_message(message.channel, "*flips a coin and... " + choice(["HEADS!*", "TAILS!*"]))
			elif message.content.startswith(p + "rps"):
				await rpsgame(message)
			elif message.content == p + "proverb":
				await client.send_message(message.channel, "`" + choice(proverbs) + "`")
			elif message.content == p + "help":
				await client.send_message(message.author, help)
				await client.send_message(message.channel, "{} `Check your DMs for the command list.`".format(message.author.mention))
			elif message.content.startswith(p + 'choose'):
				await randomchoice(message)
			elif message.content.startswith(p + '8 ') and message.content.endswith("?") and len(message.content) > 5:
				await client.send_message(message.channel, "{}: ".format(message.author.mention) + "`" + choice(ball) + "`")
			elif message.content.startswith(p + 'roll'):
				await roll(message)
			elif message.content.startswith(p + 'addcom'):
				await addcom(message)
			elif message.content.startswith(p + 'editcom'):
				await editcom(message)
			elif message.content.startswith(p + 'delcom'):
				await delcom(message)
			elif message.content == p + "customcommands":
				await listCustomCommands(message)
			elif message.content.startswith(p + 'sw'):
				await stopwatch(message)
			elif message.content.startswith(p + 'id'):
				await client.send_message(message.channel, "{} `Your id is {}`".format(message.author.mention, message.author.id))
			elif message.content.startswith(p + 'twitchalert'):
				await addTwitchAlert(message)
			elif message.content.startswith(p + 'stoptwitchalert'):
				await removeTwitchAlert(message)
			elif message.content.startswith(p + 'twitch'):
				await twitchCheck(message)
			elif message.content.startswith(p + 'image'):
				#image(message)
				pass
			elif message.content.startswith(p + 'gif'):
				await gif(message)
			elif message.content.startswith(p + 'imdb'):
				await imdb(message)
			elif message.content.startswith(p + 'urban'):
				await urban(message)
			elif message.content.startswith(p + 'uptime'):
				await uptime(message)
			elif message.content.startswith(p + 'avatar'):
				await avatar(message)
			elif message.content == p + 'meme help' or message.content == p + 'memes':
				await client.send_message(message.author, meme_help)
				await client.send_message(message.channel, "{} `Check your DMs for " + p +"meme help.`".format(message.author.mention))
			elif message.content.startswith (p + 'meme'):
				await memes(message)
			elif message.content.startswith (p + 'lmgtfy'):
				await lmgtfy(message)
			################## music #######################
			elif message.content == p + "sing":
				await playPlaylist(message, sing=True)
			elif message.content.startswith(p + 'youtube'):
				await playVideo(message)
			elif message.content.startswith(p + 'play '):
				await playPlaylist(message)
			elif message.content.startswith(p + 'local '):
				await playLocal(message)
			elif message.content == p + "local" or message.content == p + "locallist" or message.content == p + "locals":
				await listLocal(message)
				await client.send_message(message.channel, "{} `Check your DMs for the local playlists list.`".format(message.author.mention))
			elif message.content == p + "stop":
				await leaveVoice()
			elif message.content == p + "playlist" or message.content == p + "playlists":
				await listPlaylists(message)
				await client.send_message(message.channel, "{} `Check your DMs for the playlists list.`".format(message.author.mention))
			elif message.content == p + "skip" or message.content == p + "next":
				if currentPlaylist: currentPlaylist.nextSong(currentPlaylist.getNextSong())
			elif message.content == p + "prev" or message.content == p + "previous":
				if currentPlaylist: currentPlaylist.nextSong(currentPlaylist.getPreviousSong())
			elif message.content == p + "repeat" or message.content == p + "replay":
				if currentPlaylist: currentPlaylist.nextSong(currentPlaylist.current)
			elif message.content == p + "pause":
				if currentPlaylist: currentPlaylist.pause()
			elif message.content == p + "resume":
				if currentPlaylist: currentPlaylist.resume()
			elif message.content == p + "shuffle":
				if currentPlaylist: currentPlaylist.shuffle()
			elif message.content == p + "song" or message.content == p + "title" :
				if currentPlaylist: await getSongTitle(message)
			elif message.content == p + "audio help":
				await client.send_message(message.author, audio_help)
				await client.send_message(message.channel, "{} `Check your DMs for the audio help.`".format(message.author.mention))
			elif message.content.startswith(p + "addplaylist"):
				await addPlaylist(message)
			elif message.content.startswith(p + "delplaylist"):
				await delPlaylist(message)
			elif message.content == p + "addfavorite":
				await addToFavorites(message)
			elif message.content == p + "delfavorite":
				await removeFromFavorites(message)
			elif message.content == p + "playfavorites":
				await playFavorites(message)
			elif message.content == p + "getplaylist":
				await sendPlaylist(message)
			elif message.content.startswith(p + "volume"):
				await setVolume(message)
			elif message.content == p + "downloadmode":
				await downloadMode(message)
			elif message.content == p + "endpoll":
				await endPoll(message)
			elif message.content.startswith(p + "poll"):
				await startPoll(message)
			################################################
			elif message.content == p + "trivia":
				await triviaList(message)
			elif message.content.startswith(p + "trivia"):
				if checkAuth("Trivia", message, settings):
					if message.content == p + "trivia stop":
						if getTriviabyChannel(message.channel):
							await getTriviabyChannel(message.channel).endGame()
							await client.send_message(message.channel, "`Trivia stopped.`")
						else:
							await client.send_message(message.channel, "`There's no trivia session ongoing in this channel.`")
					elif not getTriviabyChannel(message.channel):
						t = Trivia(message)
						trivia_sessions.append(t)
						await t.loadQuestions(message.content)
					else:
						await client.send_message(message.channel, "`A trivia session is already ongoing in this channel.`")
				else:
					await client.send_message(message.channel, "`Trivia is currently admin-only.`")
			######## Admin commands #######################
			elif message.content.startswith(p + 'addwords'):
				await addBadWords(message)
			elif message.content.startswith(p + 'removewords'):
				await removeBadWords(message)
			elif message.content.startswith(p + 'addregex ') and len(message.content) > 11:
				await addRegex(message)
			elif message.content.startswith(p + 'removeregex ') and len(message.content) > 14:
				await removeRegex(message)
			elif message.content == p + "shutdown":
				await shutdown(message)
			elif message.content.startswith(p + 'join'):
				await join(message)
			elif message.content == p + "leaveserver":
				await leave(message)
			elif message.content == p + "shush":
				await shush(message)	
			elif message.content == p + "talk": #prevents !talk custom command
				pass
			elif message.content == p + "reload":
				await reloadSettings(message)
			elif message.content.startswith(p + "name"):
				await changeName(message)
			elif message.content.startswith(p + "cleanup"):
				await cleanup(message)	
			elif message.content == p + "admin help":
				if isMemberAdmin(message):
					await client.send_message(message.author, admin_help)
				else:
					await client.send_message(message.channel, "`Admin status required.`")
			elif message.content.startswith(p + "debug"):
				await debug(message)
			elif message.content.startswith(p + "exec"):
				await execFunc(message)
			elif message.content.startswith(p + "blacklist"):
				await blacklist(message, "add")
			elif message.content.startswith(p + "forgive"):
				await blacklist(message, "remove")
			elif message.content.startswith(p + "setting"):
				await modifySettings(message)
			###################################
			elif getTriviabyChannel(message.channel): #check if trivia is ongoing in the channel
				trvsession = getTriviabyChannel(message.channel)
				await trvsession.checkAnswer(message)
			elif "economy" in modules:
				await economy.checkCommands(message)

			if getPollByChannel(message):
				getPollByChannel(message).checkAnswer(message)

			if message.content.startswith(p) and len(message.content) > 2 and settings["CUSTOMCOMMANDS"]:
				await customCommand(message)

@client.async_event
async def on_ready():
	logger.info("I'm online " + "(" + client.user.id + ")")
	print("THIS VERSION IS OBSOLETE AND NO LONGER BEING SUPPORTED.")
	print("USE THE CURRENT ONE: https://github.com/Twentysix26/Red-DiscordBot/")
	await gameSwitcher.changeGame(now=True)
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
		self.gaveAnswer = ["I know this one! {}!", "Easy: {}.", "Oh really? It's {} of course."]
		self.currentQ = None # {"QUESTION" : "String", "ANSWERS" : []}
		self.questionList = ""
		self.channel = message.channel
		logger.info("Trivia started in channel " + self.channel.id)
		self.scoreList = {}
		self.status = None
		self.timer = None
		self.count = 0

	async def loadQuestions(self, msg):
		msg = msg.split(" ")
		if len(msg) == 2:
			_, qlist = msg
			if qlist == "random":
				chosenList = choice(glob.glob("trivia/*.txt"))
				self.questionList = self.loadList(chosenList)
				self.status = "new question"
				self.timeout = time.perf_counter()
				if self.questionList: await self.newQuestion()
			else:
				if os.path.isfile("trivia/" + qlist + ".txt"):
					self.questionList = self.loadList("trivia/" + qlist + ".txt")
					self.status = "new question"
					self.timeout = time.perf_counter()
					if self.questionList: await self.newQuestion()
				else:
					await client.send_message(self.channel, "`There is no list with that name.`")
					await self.stopTrivia()
		else:
			await client.send_message(self.channel, "`" + settings["PREFIX"] + "trivia [list name]`")

	async def stopTrivia(self):
		global trivia_sessions
		self.status = "stop"
		trivia_sessions.remove(self)
		logger.info("Trivia stopped in channel " + self.channel.id)

	async def endGame(self):
		global trivia_sessions
		self.status = "stop"
		if self.scoreList:
			await self.sendTable()
		trivia_sessions.remove(self)
		logger.info("Trivia stopped in channel " + self.channel.id)


	def loadList(self, qlist):
		with open(qlist, "r", encoding="utf-8") as f:
			qlist = f.readlines()
		parsedList = []
		for line in qlist:
			if "`" in line and len(line) > 4:
				line = line.replace("\n", "")
				line = line.split("`")
				question = line[0]
				answers = []
				for l in line[1:]:
					answers.append(l.lower())
				if len(line) >= 2:
					line = {"QUESTION" : question, "ANSWERS": answers} #string, list
					parsedList.append(line)
		if parsedList != []:
			return parsedList
		else:
			self.stopTrivia()
			return None

	async def newQuestion(self):
		for score in self.scoreList.values():
			if score == settings["TRIVIA_MAX_SCORE"]:
				await self.endGame()
				return True
		if self.questionList == []:
			await self.endGame()
			return True
		self.currentQ = choice(self.questionList)
		self.questionList.remove(self.currentQ)
		self.status = "waiting for answer"
		self.count += 1
		self.timer = int(time.perf_counter())
		await client.send_message(self.channel, "**Question number {}!**\n\n{}".format(str(self.count), self.currentQ["QUESTION"]))
		while self.status != "correct answer" and abs(self.timer - int(time.perf_counter())) <= settings["TRIVIA_DELAY"]:
			if abs(self.timeout - int(time.perf_counter())) >= settings["TRIVIA_TIMEOUT"]:
				await client.send_message(self.channel, "Guys...? Well, I guess I'll stop then.")
				await self.stopTrivia()
				return True
			await asyncio.sleep(1) #Waiting for an answer or for the time limit
		if self.status == "correct answer":
			self.status = "new question"
			await asyncio.sleep(3)
			if not self.status == "stop":
				await self.newQuestion()
		elif self.status == "stop":
			return True
		else:
			msg = choice(self.gaveAnswer).format(self.currentQ["ANSWERS"][0])
			if settings["TRIVIA_BOT_PLAYS"]:
				msg += " **+1** for me!"
				self.addPoint(client.user.name)
			self.currentQ["ANSWERS"] = []
			await client.send_message(self.channel, msg)
			await client.send_typing(self.channel)
			await asyncio.sleep(3)
			if not self.status == "stop":
				await self.newQuestion()
		
	async def sendTable(self):
		self.scoreList = sorted(self.scoreList.items(), reverse=True, key=lambda x: x[1]) # orders score from lower to higher
		t = "```Scores: \n\n"
		for score in self.scoreList:
			t += score[0] # name
			t += "\t"
			t += str(score[1]) # score
			t += "\n"
		t += "```"
		await client.send_message(self.channel, t)

	async def checkAnswer(self, message):
		self.timeout = time.perf_counter()
		for answer in self.currentQ["ANSWERS"]:
			if answer in message.content.lower():
				self.currentQ["ANSWERS"] = []
				self.status = "correct answer"
				self.addPoint(message.author.name)
				await client.send_message(self.channel, "You got it {}! **+1** to you!".format(message.author.name))
				await client.send_typing(self.channel)
				return True

	def addPoint(self, user):
		if user in self.scoreList:
			self.scoreList[user] += 1
		else:
			self.scoreList[user] = 1

	def getTriviaQuestion(self):
		q = choice(list(trivia_questions.keys()))
		return q, trivia_questions[q] # question, answer

class botPlays():
	def __init__(self):
		self.games = dataIO.fileIO("json/games.json", "load")
		self.lastChanged = int(time.perf_counter())
		self.delay = 300

	async def changeGame(self, now=False):
		if abs(self.lastChanged - int(time.perf_counter())) >= self.delay or now:
			self.lastChanged = int(time.perf_counter())
			await client.change_status(discord.Game(name=choice(self.games)))

class Playlist():
	def __init__(self, filename=None): #a playlist with a single song is just there to make !addfavorite work with !youtube command
		self.filename = filename
		self.current = 0
		self.stop = False
		self.lastAction = 999
		self.currentTitle = ""
		self.type = filename["type"]
		if filename["type"] == "playlist":
			self.playlist = dataIO.fileIO("playlists/" + filename["filename"] + ".txt", "load")["playlist"]
		elif filename["type"] == "favorites":
			self.playlist = dataIO.fileIO("favorites/" + filename["filename"] + ".txt", "load")
		elif filename["type"] == "local":
			self.playlist = filename["filename"]
		elif filename["type"] == "singleSong":
			self.playlist = [filename["filename"]]
			self.playSingleSong(self.playlist[0])
		else:
			raise("Invalid playlist call.")
		if filename["type"] != "singleSong":
			self.nextSong(0)

	def nextSong(self, nextTrack, lastError=False):
		global musicPlayer
		if not self.passedTime() < 1 and not self.stop: #direct control
			if musicPlayer: musicPlayer.stop()
			self.lastAction = int(time.perf_counter())
			try:
				if isPlaylistValid([self.playlist[nextTrack]]): #Checks if it's a valid youtube link
					if settings["DOWNLOADMODE"]:
						path = self.getVideo(self.playlist[nextTrack])
						try:
							logger.info("Starting track...")
							musicPlayer = client.voice.create_ffmpeg_player("cache/" + path, options='''-filter:a "volume={}"'''.format(settings["VOLUME"]))
							musicPlayer.start()
						except:
							logger.warning("Something went wrong with track " + self.playlist[self.current])
							if not lastError: #prevents error loop
								self.lastAction = 999
							self.nextSong(self.getNextSong(), lastError=True)
					else: #Stream mode. Buggy.
						musicPlayer = client.voice.create_ytdl_player(self.playlist[nextTrack], options=youtube_dl_options)
						musicPlayer.start()
				else: # must be a local playlist then
					musicPlayer = client.voice.create_ffmpeg_player(self.playlist[nextTrack], options='''-filter:a "volume={}"'''.format(settings["VOLUME"]))
					musicPlayer.start()
			except Exception as e:
				logger.warning("Something went wrong with track " + self.playlist[self.current])
				if not lastError: #prevents error loop
					self.lastAction = 999
				self.nextSong(self.getNextSong(), lastError=True)

	def getVideo(self, url):
		try:
			yt = youtube_dl.YoutubeDL(youtube_dl_options)
			v = yt.extract_info(url, download=False)
			if not os.path.isfile("cache/" + v["id"]):
				logger.info("Track not in cache, downloading...")
				v = yt.extract_info(url, download=True)
			self.currentTitle = v["title"]
			return v["id"]
		except Exception as e:
			logger.error(e)
			return False

	def playSingleSong(self, url):
		global musicPlayer
		if settings["DOWNLOADMODE"]:
			v = self.getVideo(url)
			if musicPlayer:
				if musicPlayer.is_playing():
					musicPlayer.stop()
			if v:
				musicPlayer = client.voice.create_ffmpeg_player("cache/" + v, options='''-filter:a "volume={}"'''.format(settings["VOLUME"]))
				musicPlayer.start()
		else:
			if musicPlayer:
				if musicPlayer.is_playing():
					musicPlayer.stop()
			musicPlayer = client.voice.create_ytdl_player(self.playlist[0], options=youtube_dl_options)
			musicPlayer.start()

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

class Poll():
	def __init__(self, message):
		self.channel = message.channel
		self.author = message.author.id
		msg = message.content[6:]
		msg = msg.split(";")
		if len(msg) < 2: # Needs at least one question and 2 choices
			self.valid = False
			return None 
		else:
			self.valid = True
		self.already_voted = []
		self.question = msg[0]
		msg.remove(self.question)
		self.answers = {}
		i = 1
		for answer in msg: # {id : {answer, votes}}
			self.answers[i] = {"ANSWER" : answer, "VOTES" : 0}
			i += 1

	async def start(self):
		msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
		for id, data in self.answers.items():
			msg += "{}. *{}*\n".format(id, data["ANSWER"])
		msg += "\nType the number to vote!"
		await client.send_message(self.channel, msg)
		await asyncio.sleep(settings["POLL_DURATION"])
		if self.valid:
			await self.endPoll()

	async def endPoll(self):
		global poll_sessions
		self.valid = False
		msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
		for data in self.answers.values():
			msg += "*{}* - {} votes\n".format(data["ANSWER"], str(data["VOTES"]))
		await client.send_message(self.channel, msg)
		poll_sessions.remove(self)

	def checkAnswer(self, message):
		try:
			i = int(message.content)
			if i in self.answers.keys():
				if message.author.id not in self.already_voted:
					data = self.answers[i]
					data["VOTES"] += 1
					self.answers[i] = data
					self.already_voted.append(message.author.id)
		except ValueError:
			pass

async def startPoll(message):
	global poll_sessions
	if not getPollByChannel(message):
		p = Poll(message)
		if p.valid: 
			poll_sessions.append(p)
			await p.start()
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "poll question;option1;option2 (...)`")
	else:
		await client.send_message(message.channel, "`A poll is already ongoing in this channel.`")

async def endPoll(message):
	global poll_sessions
	if getPollByChannel(message):
		p = getPollByChannel(message)
		if p.author == message.author.id or isMemberAdmin(message):
			await getPollByChannel(message).endPoll()
		else:
			await client.send_message(message.channel, "`Only admins and the author can stop the poll.`")
	else:
		await client.send_message(message.channel, "`There's no poll ongoing in this channel.`")


def getPollByChannel(message):
	for poll in poll_sessions:
		if poll.channel == message.channel:
			return poll
	return False

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
					dataIO.fileIO("json/commands.json", "save", commands)
					logger.info("Saved commands database.")
					await client.send_message(message.channel, "`Custom command successfully added.`")
				else:
					await client.send_message(message.channel, "`This command already exists. Use " + settings["PREFIX"] + "editcom [command] [text]`")

		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "addcom [command] [text]`")
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
					dataIO.fileIO("json/commands.json", "save", commands)
					logger.info("Saved commands database.")
					await client.send_message(message.channel, "`Custom command successfully edited.`")
				else:
					await client.send_message(message.channel, "`That command doesn't exist. Use " + settings["PREFIX"] + "addcom [command] [text]`")
			else:
				await client.send_message(message.channel, "`There are no custom commands in this server. Use " + settings["PREFIX"] + "addcom [command] [text]`")

		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "editcom [command] [text]`")
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
					dataIO.fileIO("json/commands.json", "save", commands)
					logger.info("Saved commands database.")
					await client.send_message(message.channel, "`Custom command successfully deleted.`")
				else:
					await client.send_message(message.channel, "`That command doesn't exist.`")
			else:
				await client.send_message(message.channel, "`There are no custom commands in this server. Use " + settings["PREFIX"] + "addcom [command] [text]`")

		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "delcom [command]`")
	else:
		await client.send_message(message.channel, "`You don't have permissions to edit custom commands.`")

async def listCustomCommands(message):
	msg = "Custom commands: \n\n```"
	if message.channel.server.id in commands:
		cmds = commands[message.channel.server.id].keys()
		if cmds:
			for i, d in enumerate(cmds):
				if i % 4 == 0 and i != 0:
					msg = msg + d + "\n"
				else:
					msg = msg + d + "\t"
			msg += "```"
			await client.send_message(message.author, msg)
		else:
			await client.send_message(message.author, "There are no custom commands.")
	else:
		await client.send_message(message.author, "There are no custom commands.")

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
		logger.error("Invalid call to checkAuth")
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
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "rps [rock or paper or scissors]`")
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "rps [rock or paper or scissors]`")

async def randomchoice(message):
	sentences = ["Mmm... I think I'll choose ", "I choose ", "I prefer ", "This one is best: ", "This: "]
	msg = message.content[8:] # removes !choose
	msg = msg.split(" or ")
	if len(msg) == 1:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "choose option1 or option2 or option3 (...)`")
	elif len(msg) >= 2:
		await client.send_message(message.channel, "`" + choice(sentences) + choice(msg) + "`")
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
		await client.send_message(message.channel, "`Stopwatch started! Use " + settings["PREFIX"] + "sw to stop it.`")

"""
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
"""

async def imdb(message): # Method added by BananaWaffles.
	msg = message.content.split()
	if apis["MYAPIFILMS_TOKEN"] == "TOKENHERE":
		await client.send_message(message.channel, "`This command wasn't configured properly. If you're the owner, edit json/apis.json`")
		return False
	if len(msg) > 1:
			if len(msg[1]) > 1 and len([msg[1]]) < 20:
					try:
						msg.remove(msg[0])
						msg = "+".join(msg)
						search = "http://api.myapifilms.com/imdb/title?format=json&title=" + msg + "&token=" + apis["MYAPIFILMS_TOKEN"]
						async with aiohttp.get(search) as r:
							result = await r.json()
							title = result['data']['movies'][0]['title']
							year = result['data']['movies'][0]['year']
							rating = result['data']['movies'][0]['rating']
							url = result['data']['movies'][0]['urlIMDB']
							msg = "Title: " + title + " | Released on: " + year + " | IMDB Rating: " + rating + ".\n" + url
							await client.send_message(message.channel, msg)
					except:
						await client.send_message(message.channel, "`Error.`")
			else:
				await client.send_message(message.channel, "`Invalid search.`")
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "imdb [text]`")

async def memes(message):
	msg = message.content[6:]
	msg = msg.split(";")
	if apis["IMGFLIP_USERNAME"] == "USERNAMEHERE" or apis["IMGFLIP_PASSWORD"] == "PASSWORDHERE":
		await client.send_message(message.channel, "`This command wasn't configured properly. If you're the owner, edit json/apis.json`")
		return False
	if len(msg) == 3:
		if len(msg[0]) > 1 and len([msg[1]]) < 20 and len([msg[2]]) < 20:
			try:
				search = "https://api.imgflip.com/caption_image?template_id=" + msg[0] + "&username=" + apis["IMGFLIP_USERNAME"] + "&password=" + apis["IMGFLIP_PASSWORD"] + "&text0=" + msg[1] + "&text1=" + msg[2]
				async with aiohttp.get(search) as r:
					result = await r.json()
				if result["data"] != []:		
					url = result["data"]["url"]
					await client.send_message(message.channel, url)
			except:
				error = result["error_message"]
				await client.send_message(message.channel, error)
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "meme id;text1;text2   |  " + settings["PREFIX"] + "meme help for full list`")
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "meme id;text1;text2   |  " + settings["PREFIX"] + "meme help for full list`")

async def urban(message):
	msg = message.content.split()
	if len(msg) > 1:
		if len(msg[1]) > 1 and len([msg[1]]) < 20:
			try:
				msg.remove(msg[0])
				msg = "+".join(msg)
				search = "http://api.urbandictionary.com/v0/define?term=" + msg
				async with aiohttp.get(search) as r:
					result = await r.json()
				if result["list"] != []:
					definition = result['list'][0]['definition']
					example = result['list'][0]['example']
					await client.send_message(message.channel, "Definition: " + definition + "\n\n" + "Example: " + example )
				else:
					await client.send_message(message.channel, "`Your search terms gave no results.`")
			except:
				await client.send_message(message.channel, "`Error.`")
		else:
			await client.send_message(message.channel, "`Invalid search.`")
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "urban [text]`")

async def gif(message):
	msg = message.content.split()
	if len(msg) > 1:
		if len(msg[1]) > 1 and len([msg[1]]) < 20:
			try:
				msg.remove(msg[0])
				msg = "+".join(msg)
				search = "http://api.giphy.com/v1/gifs/search?q=" + msg + "&api_key=dc6zaTOxFJmzC"
				async with aiohttp.get(search) as r:
					result = await r.json()
				if result["data"] != []:		
					url = result["data"][0]["url"]
					await client.send_message(message.channel, url)
				else:
					await client.send_message(message.channel, "`Your search terms gave no results.`")
			except:
				await client.send_message(message.channel, "`Error.`")
		else:
			await client.send_message(message.channel, "`Invalid search.`")
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "gif [text]`")

async def avatar(message):
	if message.mentions:
		m = message.mentions[0]
		await client.send_message(message.channel, "{}'s avatar: {}".format(m.name, m.avatar_url))
	else:
		if len(message.content.split(" ")) >= 2:
			name = message.content[8:]
			member = discord.utils.get(message.server.members, name=name)
			if member != None:
				await client.send_message(message.channel, "{}'s avatar: {}".format(member.name, member.avatar_url))
			else:
				await client.send_message(message.channel, "`User not found.`")
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "avatar [name or mention]`")

async def lmgtfy(message):
	msg = message.content.split()
	if len(msg) >= 2:
		msg = "+".join(msg[1:])
		await client.send_message(message.channel, "http://lmgtfy.com/?q=" + msg)
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "lmgtfy [search terms]`")

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
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "roll [number]`")
	else:
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "roll [number]`")

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
			async with aiohttp.get(url) as r:
				data = await r.json()
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
		await client.send_message(message.channel, "{} `".format(message.author.mention) + settings["PREFIX"] + "twitch [name]`")

async def triviaList(message):
	await client.send_message(message.author, trivia_help)
	msg = "**Available trivia lists:** \n\n```"
	lists = os.listdir("trivia/")
	if lists:
		clean_list = []
		for txt in lists:
			if txt.endswith(".txt") and " " not in txt:
				txt = txt.replace(".txt", "")
				clean_list.append(txt)
		if clean_list:
			for i, d in enumerate(clean_list):
				if i % 4 == 0 and i != 0:
					msg = msg + d + "\n"
				else:
					msg = msg + d + "\t"
			msg += "```"
			await client.send_message(message.author, msg)
		else:
			await client.send_message(message.author, "There are no trivia lists available.")
	else:
		await client.send_message(message.author, "There are no trivia lists available.")

async def uptime(message):
	up = abs(uptime_timer - int(time.perf_counter()))
	up = str(datetime.timedelta(seconds=up))
	await client.send_message(message.channel, "`Uptime: {}`".format(up))

async def checkVoice(message):
	if not client.is_voice_connected():
		if message.author.voice_channel:
			if message.author.voice_channel.permissions_for(message.server.me).connect:
				await client.join_voice_channel(message.author.voice_channel)
			else:
				await client.send_message(message.channel, "{} `I need permissions to join that channel.`".format(message.author.mention))
				return False
		else:
			await client.send_message(message.channel, "{} `You need to join a voice channel first.`".format(message.author.mention))
			return False
	return True

async def playVideo(message):
	global musicPlayer, currentPlaylist
	toDelete = None
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
		if settings["DOWNLOADMODE"]:
			toDelete = await client.send_message(message.channel, "`I'm in download mode. It might take a bit for me to start. I'll delete this message as soon as I'm ready.`".format(id, message.author.name))
		data = {"filename" : 'https://www.youtube.com/watch?v=' + id, "type" : "singleSong"}
		currentPlaylist = Playlist(data)
		if canDeleteMessages(message):
			await client.send_message(message.channel, "`Playing youtube video {} requested by {}`".format(await youtubeparser.getTitle(currentPlaylist.playlist[currentPlaylist.current]), message.author.name))
			await client.delete_message(message)
		if toDelete:
			await client.delete_message(toDelete)
#		currentPlaylist.playlist = ['https://www.youtube.com/watch?v=' + id]
#		musicPlayer = client.voice.create_ytdl_player('https://www.youtube.com/watch?v=' + id, options=youtube_dl_options)
#		musicPlayer.start()
		#!addfavorite compatibility stuff

async def playPlaylist(message, sing=False):
	global musicPlayer, currentPlaylist
	p = settings["PREFIX"]
	msg = message.content
	toDelete = None
	if not sing:
		if msg != p + "play" or msg != "play ":
			if await checkVoice(message):
				msg = message.content[6:]
				if dataIO.fileIO("playlists/" + msg + ".txt", "check"):
					stopMusic()
					data = {"filename" : msg, "type" : "playlist"}
					if settings["DOWNLOADMODE"]:
						toDelete = await client.send_message(message.channel, "`I'm in download mode. It might take a bit for me to start and switch between tracks. I'll delete this message as soon as the current playlist stops.`".format(id, message.author.name))
					currentPlaylist = Playlist(data)
					await asyncio.sleep(2)
					await currentPlaylist.songSwitcher()
					if toDelete:
						await client.delete_message(toDelete)
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
			data = {"filename" : song, "type" : "singleSong"}
			if settings["DOWNLOADMODE"]:
				toDelete = await client.send_message(message.channel, "`I'm in download mode. It might take a bit for me to start. I'll delete this message as soon as I'm ready.`".format(id, message.author.name))
			currentPlaylist = Playlist(data)
#			currentPlaylist.playlist = [song]
#			musicPlayer = client.voice.create_ytdl_player(song, options=youtube_dl_options)
#			musicPlayer.start()
			if toDelete:
				await client.delete_message(toDelete)
			await client.send_message(message.channel, choice(msg))


async def playLocal(message):
	global currentPlaylist
	p = settings["PREFIX"]
	msg = message.content.split(" ")
	if await checkVoice(message):
		if len(msg) == 2:
			localplaylists = getLocalPlaylists()
			if localplaylists and ("/" not in msg[1] and "\\" not in msg[1]):
				if msg[1] in localplaylists:
					files = []
					if glob.glob("localtracks/" + msg[1] + "/*.mp3"):
						files.extend(glob.glob("localtracks/" + msg[1] + "/*.mp3"))
					if glob.glob("localtracks/" + msg[1] + "/*.flac"):
						files.extend(glob.glob("localtracks/" + msg[1] + "/*.flac"))
					stopMusic()
					data = {"filename" : files, "type" : "local"}
					currentPlaylist = Playlist(data)
					await asyncio.sleep(2)
					await currentPlaylist.songSwitcher()
				else:
					await client.send_message(message.channel, "`There is no local playlist called {}. " + p + "local or " + p + "locallist to receive the list.`".format(msg[1]))
			else:
				await client.send_message(message.channel, "`There are no valid playlists in the localtracks folder.`")
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "local [playlist]`")

def getLocalPlaylists():
	dirs = []
	files = os.listdir("localtracks/")
	for f in files:
		if os.path.isdir("localtracks/" + f) and " " not in f:
			if glob.glob("localtracks/" + f + "/*.mp3") != []:
				dirs.append(f)
			elif glob.glob("localtracks/" + f + "/*.flac") != []:
				dirs.append(f)
	if dirs != []:
		return dirs
	else:
		return False

async def leaveVoice():
	if client.is_voice_connected():
		stopMusic()
		await client.voice.disconnect()
		
async def listPlaylists(message):
	msg = "Available playlists: \n\n```"
	files = os.listdir("playlists/")
	if files:
		for i, f in enumerate(files):
			if f.endswith(".txt"):
				if i % 4 == 0 and i != 0:
					msg = msg + f.replace(".txt", "") + "\n"
				else:
					msg = msg + f.replace(".txt", "") + "\t"
		msg += "```"
		await client.send_message(message.author, msg)
	else:
		await client.send_message(message.author, "There are no playlists.")

async def listLocal(message):
	msg = "Available local playlists: \n\n```"
	dirs = getLocalPlaylists()
	if dirs:
		for i, d in enumerate(dirs):
			if i % 4 == 0 and i != 0:
				msg = msg + d + "\n"
			else:
				msg = msg + d + "\t"
		msg += "```"
		await client.send_message(message.author, msg)
	else:
		await client.send_message(message.author, "There are no local playlists.")


def stopMusic():
	global musicPlayer, currentPlaylist
	if currentPlaylist != None:
		currentPlaylist.stop = True
	if musicPlayer != None:
		musicPlayer.stop()

async def transferPlaylist(message):
	msg = message.attachments[0]
	if msg["filename"].endswith(".txt"):
		if not dataIO.fileIO("playlists/" + msg["filename"], "check"): #returns false if file already exists
			r = await aiohttp.get(msg["url"])
			r = await r.text()
			data = r.replace("\r", "")
			data = data.split()
			if isPlaylistValid(data) and isPlaylistNameValid(msg["filename"].replace(".txt", "")):
				data = { "author" : message.author.id,
						 "playlist": data}
				dataIO.fileIO("playlists/" + msg["filename"], "save", data)
				await client.send_message(message.channel, "`Playlist added. Name: {}`".format(msg["filename"].replace(".txt", "")))
			else:
				await client.send_message(message.channel, "`Something is wrong with the playlist or its filename. Type " + settings["PREFIX"] + "audio help to read how to format it properly.`")
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
			links = await youtubeparser.parsePlaylist(link)
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
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "addplaylist [name] [link]`")

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
		await client.send_message(message.channel, "`" + settings["PREFIX"] + "delplaylist [name]`")

async def getSongTitle(message):
	title = await youtubeparser.getTitle(currentPlaylist.playlist[currentPlaylist.current])
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
			await client.send_message(message.channel, "{} `You don't have any favorites yet. Start adding them with " + settings["PREFIX"] + "addfavorite`".format(message.author.mention))
	else:
		await client.send_message(message.channel, "{} `No song is being played`".format(message.author.mention))

async def playFavorites(message):
	global musicPlayer, currentPlaylist
	if await checkVoice(message):
		if dataIO.fileIO("favorites/" + message.author.id + ".txt", "check"):
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
			if len(msg) >= 1900:
				msg += "```"
				await client.send_message(message.author, msg)
				msg = "```"
		if msg != "```":
			msg += "```"
			await client.send_message(message.author, msg)

async def setVolume(message):
	global settings
	p = settings["PREFIX"]
	msg = message.content
	if len(msg.split(" ")) == 2:
		msg = msg.split(" ")
		try:
			vol = float(msg[1])
			if vol >= 0 and vol <= 1:
				settings["VOLUME"] = vol
				await(client.send_message(message.channel, "`Volume set. Next track will have the desired volume.`"))
				dataIO.fileIO("json/settings.json", "save", settings)
			else:
				await(client.send_message(message.channel, "`Volume must be between 0 and 1. Example: " + p + "volume 0.50`"))
		except:
			await(client.send_message(message.channel, "`Volume must be between 0 and 1. Example: " + p + "volume 0.15`"))
	else:
		await(client.send_message(message.channel, "`Volume must be between 0 and 1. Example: " + p + "volume 0.15`"))

async def downloadMode(message):
	if isMemberAdmin(message):
		if settings["DOWNLOADMODE"]:
			settings["DOWNLOADMODE"] = False
			await(client.send_message(message.channel, "`Download mode disabled. This mode is unstable and tracks might interrupt. Also, the volume settings will not have any effect.`"))
		else:
			settings["DOWNLOADMODE"] = True
			await(client.send_message(message.channel, "`Download mode enabled.`"))
		dataIO.fileIO("json/settings.json", "save", settings)
	else:
		await(client.send_message(message.channel, "`I don't take orders from you.`"))

############## ADMIN COMMANDS ###################

async def shutdown(message):
	if isMemberAdmin(message):
		await client.send_message(message.channel, client.user.name + " shutting down... See you soon. :hand:")
		await client.logout()
		try:
			exit(1)
		except SystemExit: #clean exit
			logger.info("Shutting down as requested by " + message.author.id + "...")
			pass
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def join(message):
	if isMemberAdmin(message):
		msg = message.content.split()
		if len(msg) > 1:
			await client.accept_invite(msg[1])
		else:
			logger.warning("Join: missing parameters")
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
		dataIO.fileIO("json/shushlist.json", "save", shush_list)
		logger.info("Saved silenced channels database.")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def talk(message):
	if isMemberAdmin(message):
		if message.channel.id in shush_list:
			shush_list.remove(message.channel.id)
			dataIO.fileIO("json/shushlist.json", "save", shush_list)
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
			dataIO.fileIO("json/filter.json", "save", badwords)
			logger.info("Saved filter words.")
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "addwords [word1] [word2] [phrase/with/many/words] (...)`")
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
				dataIO.fileIO("json/filter.json", "save", badwords)
				logger.info("Saved filter words.")
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "removewords [word1] [word2] [phrase/with/many/words](...)`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def changeName(message):
	global settings
	if isMemberAdmin(message):
		msg = message.content.split()
		if len(msg) == 2:
			try:
				await client.edit_profile(settings["PASSWORD"], username=msg[1])
			except Exception as e:
				logger.error(e)
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "name [new name]`")
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
		dataIO.fileIO("json/regex_filter.json", "save", badwords_regex)
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
				dataIO.fileIO("json/regex_filter.json", "save", badwords_regex)
				logger.info("Saved regex filter database.")
			else:
				await client.send_message(message.channel, "`No match.`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def reloadSettings(message):
	if isMemberAdmin(message):
		loadDataFromFiles(True)
		await client.send_message(message.channel, "`Settings and files reloaded.`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def cleanup(message):
	errorMsg = "`" + settings["PREFIX"] + "cleanup [number] " + settings["PREFIX"] + "cleanup [name/mention] [number]`"
	if isMemberAdmin(message):
		if canDeleteMessages(message):
			try:
				async for x in client.logs_from(message.channel, limit=1):
					pass
			except TypeError:
				logger.error("Your discord.py is outdated. Update it to use cleanup.")
				return False
			msg = message.content.split()
			if len(msg) == 2:
				if msg[1].isdigit():
					n = int(msg[1])
					async for x in client.logs_from(message.channel, limit=n+1):
						await client.delete_message(x)
				else:
					await client.send_message(message.channel, errorMsg)
			elif len(msg) == 3:
				_, name, limit = msg
				try:
					limit = int(limit)
				except:
					await client.send_message(message.channel, errorMsg)
					return False
				if message.mentions:
					m = message.mentions[0]
				else:
					m = discord.utils.get(message.server.members, name=name)
				if m and limit != 0:
					checksLeft = 5
					await client.delete_message(message)
					while checksLeft != 0 and limit != 0:
						async for x in client.logs_from(message.channel, limit=100):
							if x.author == m and limit != 0:
								await client.delete_message(x)
								limit -= 1
						checksLeft -= 1
				else:
					await client.send_message(message.channel, errorMsg)

			else:
				await client.send_message(message.channel, errorMsg)
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
	return message.channel.permissions_for(message.server.me).manage_messages

async def addTwitchAlert(message):
	global twitchStreams
	added = False
	if isMemberAdmin(message):
		msg = message.content.split(" ")
		if len(msg) == 2:
			if "twitch.tv/" in msg[1]:
				await client.send_message(message.channel, "`Enter the name of the stream, not the URL.`")
				return False
			for i, stream in enumerate(twitchStreams):
				if stream["NAME"] == msg[1] and message.channel.id in stream["CHANNELS"]:
					await client.send_message(message.channel, "`I'm already monitoring that stream in this channel.`")
					return False
			for stream in twitchStreams:
				if stream["NAME"] == msg[1] and message.channel.id not in stream["CHANNELS"]: # twitchAlert is already monitoring this streamer but not in this channel
					twitchStreams[i]["CHANNELS"].append(message.channel.id)
					added = True
			if not added: # twitchAlert wasn't monitoring this streamer
				twitchStreams.append({"CHANNELS" : [message.channel.id], "NAME" : msg[1], "ALREADY_ONLINE" : False})

			dataIO.fileIO("json/twitch.json", "save", twitchStreams)
			await client.send_message(message.channel, "`I will always send an alert in this channel whenever {}'s stream is online. Use !stoptwitchalert [name] to stop it.`".format(msg[1]))
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "twitchalert [name]`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def removeTwitchAlert(message):
	global twitchStreams
	if isMemberAdmin(message):
		msg = message.content.split(" ")
		if len(msg) == 2:
			for i, stream in enumerate(twitchStreams):
				if stream["NAME"] == msg[1] and message.channel.id in stream["CHANNELS"]:
					if len(stream["CHANNELS"]) == 1:
						twitchStreams.remove(stream)
					else:
						twitchStreams[i]["CHANNELS"].remove(message.channel.id)
					dataIO.fileIO("json/twitch.json", "save", twitchStreams)
					await client.send_message(message.channel, "`I will stop sending alerts about {}'s stream in this channel.`".format(msg[1]))
					return True
			await client.send_message(message.channel, "`There's no alert for {}'s stream in this channel.`".format(msg[1]))
		else:
			await client.send_message(message.channel, "`" + settings["PREFIX"] + "stoptwitchalert [name]`")
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def blacklist(message, mode):
	global blacklisted_users
	p = settings["PREFIX"]
	if isMemberAdmin(message):
		if message.mentions:
			m = message.mentions[0]
		else:
			if len(message.content.split(" ")) >= 2:
				if message.content.startswith(p + "blacklist"):
					name = message.content[11:]
				else:
					name = message.content[9:]
				m = discord.utils.get(message.server.members, name=name)
				if m == None:
					await client.send_message(message.channel, "`User not found.`")
					return False
			else:
				return False
		if mode == "add":
			blacklisted_users.append(m.id)
			await client.send_message(message.channel, "`{} is now in blacklist.`".format(m.name))
		else:
			if m.id in blacklisted_users:
				blacklisted_users.remove(m.id)
				await client.send_message(message.channel, "`{} has been removed from blacklist.`".format(m.name))
			else:
				await client.send_message(message.channel, "`User not in blacklist.`")
				return False
		dataIO.fileIO("json/blacklist.json", "save", blacklisted_users)
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

async def modifySettings(message):
	global settings
	if isMemberAdmin(message):
		msg = message.content.split(" ")
		if len(msg) == 3:
			_, key, value = msg
			if key.lower() == "password" or key.lower() == "email" or key.lower() == "debug_id":
				await client.send_message(message.channel, "`You cannot modify EMAIL, PASSWORD or DEBUG_ID`")
				return False
			if key.lower() == "prefix" and len(value) != 1:
				await client.send_message(message.channel, "`Prefix cannot be more than one character.`")
				return False
			if key in settings.keys():
				if value.lower() == "true": value = True
				elif value.lower() == "false": value = False
				else:
					try:
						value = int(value)
					except:
						pass
				settings[key] = value
				dataIO.fileIO("json/settings.json", "save", settings)
				loadHelp()
				if "economy" in modules:
					economy.settings = settings
					economy.loadHelp()
				await client.send_message(message.channel, "`'{}' set to '{}'`".format(key, str(value)))
			else:
				await client.send_message(message.channel, "`That setting doesn't exist`")
		else:
			msg = "```"
			for k, v in settings.items():
				if k != "EMAIL" and k != "PASSWORD":
					msg += k + ": " + str(v) + "\n"
			msg += "```\n"
			msg += settings["PREFIX"] + "setting [setting] [value]"
			await client.send_message(message.channel, msg)
	else:
		await client.send_message(message.channel, "`I don't take orders from you.`")

################################################

@asyncio.coroutine
async def twitchAlert():
	global twitchStreams
	CHECK_DELAY = 10
	while True:
		if twitchStreams and client.is_logged_in:
			to_delete = []
			save = False
			consistency_check = twitchStreams
			for i, stream in enumerate(twitchStreams):
				if twitchStreams == consistency_check: #prevents buggy behavior if twitchStreams gets modified during the iteration
					try:
						url =  "https://api.twitch.tv/kraken/streams/" + stream["NAME"]
						async with aiohttp.get(url) as r:
							data = await r.json()
						if "status" in data: 
							if data["status"] == 404: #Stream doesn't exist, remove from list
								to_delete.append(stream)
						elif "stream" in data:
							if data["stream"] != None:
								if not stream["ALREADY_ONLINE"]:
									for channel in stream["CHANNELS"]:
										try:
											await client.send_message(client.get_channel(channel), "`{} is online!` {}".format(stream["NAME"], "http://www.twitch.tv/" + stream["NAME"]))
										except: #In case of missing permissions
											pass
									twitchStreams[i]["ALREADY_ONLINE"] = True
									save = True
							else:
								if stream["ALREADY_ONLINE"]:
									twitchStreams[i]["ALREADY_ONLINE"] = False
									save = True
					except Exception as e:
						logger.warning(e)

					if save: #Saves online status, in case the bot needs to be restarted it can prevent message spam
						dataIO.fileIO("json/twitch.json", "save", twitchStreams)
						save = False

					await asyncio.sleep(CHECK_DELAY)
				else:
					break

			if to_delete:
				for invalid_stream in to_delete:
					twitchStreams.remove(invalid_stream)
				dataIO.fileIO("json/twitch.json", "save", twitchStreams)
		else:
			await asyncio.sleep(5)

async def customCommand(message):
	msg = message.content[1:]
	if message.channel.server.id in commands:
		cmdlist = commands[message.channel.server.id]
		if msg in cmdlist:
			await client.send_message(message.channel, cmdlist[msg] )

async def debug(message):	# If you don't know what this is, *leave it alone*
	if message.author.id == settings["DEBUG_ID"]: # Never assign DEBUG_ID to someone other than you
		msg = message.content.split("`") # Example: !debug `message.author.id`
		if len(msg) == 3:
			_, cmd, _ = msg		
			try:
				result = str(eval(cmd))
				if settings["PASSWORD"].lower() not in result.lower() and settings["EMAIL"].lower() not in result.lower():
					await client.send_message(message.channel, "```" + result + "```")
				else:
					await client.send_message(message.author, "`Are you trying to send my credentials in chat? Because that's how you send my credentials in chat.`")
			except Exception as e:
				await client.send_message(message.channel, "```" + str(e) + "```")

async def execFunc(message): #same warning as the other function ^
	if message.author.id == settings["DEBUG_ID"]:
		msg = message.content.split("`") # Example: !exec `import this`
		if len(msg) == 3:
			_, cmd, _ = msg		
			try:
				result = exec(cmd)
				#await client.send_message(message.channel, "```" + str(result) + "```")
			except Exception as e:
				await client.send_message(message.channel, "```" + str(e) + "```")


def console():
	while True:
		try:
			exec(input(""))
		except Exception:
			traceback.print_exc()
			print("\n")

def loadDataFromFiles(loadsettings=False):
	global proverbs, commands, trivia_questions, badwords, badwords_regex, shush_list, twitchStreams, blacklisted_users, apis

	proverbs = dataIO.loadProverbs()
	logger.info("Loaded " + str(len(proverbs)) + " proverbs.")

	commands = dataIO.fileIO("json/commands.json", "load")
	logger.info("Loaded " + str(len(commands)) + " lists of custom commands.")

	badwords = dataIO.fileIO("json/filter.json", "load")
	logger.info("Loaded " + str(len(badwords)) + " lists of filtered words.")

	blacklisted_users = dataIO.fileIO("json/blacklist.json", "load")
	logger.info("Loaded " + str(len(blacklisted_users)) + " blacklisted users.")

	badwords_regex = dataIO.fileIO("json/regex_filter.json", "load")
	logger.info("Loaded " + str(len(badwords_regex)) + " regex lists.")

	shush_list = dataIO.fileIO("json/shushlist.json", "load")
	logger.info("Loaded " + str(len(shush_list)) + " silenced channels.")

	twitchStreams = dataIO.fileIO("json/twitch.json", "load")
	logger.info("Loaded " + str(len(twitchStreams)) + " streams to monitor.")
	
	apis = dataIO.fileIO("json/apis.json", "load")
	logger.info("Loaded APIs configuration.")

	if loadsettings:
		global settings
		settings = dataIO.fileIO("json/settings.json", "load")

	loadHelp()

	if "economy" in modules:
		economy.settings = settings
		economy.loadHelp()

def main():
	global ball, greetings, greetings_caps, stopwatches, trivia_sessions, message, gameSwitcher, uptime_timer, musicPlayer, currentPlaylist
	global logger, settings, poll_sessions

	logger = loggerSetup()
	dataIO.logger = logger

	dataIO.migration()
	dataIO.createEmptyFiles()

	settings = dataIO.loadAndCheckSettings()

	loadDataFromFiles()

	ball = ["As I see it, yes", "It is certain", "It is decidedly so", "Most likely", "Outlook good",
	 "Signs point to yes", "Without a doubt", "Yes", "Yes – definitely", "You may rely on it", "Reply hazy, try again",
	 "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
	 "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]

	greetings = ["Hey.", "Yes?", "Hi.", "I'm listening.", "Hello.", "I'm here."]
	greetings_caps = ["DON'T SCREAM", "WHAT", "WHAT IS IT?!", "ì_ì", "NO CAPS LOCK"]

	stopwatches = {}

	trivia_sessions = []
	poll_sessions = []

	message = ""

	gameSwitcher = botPlays()

	if "economy" in modules:
		economy.client = client
		economy.initialize()

	uptime_timer = int(time.perf_counter())

	musicPlayer = None
	currentPlaylist = None

	loop.create_task(twitchAlert())

	#client.run(settings["EMAIL"], settings["PASSWORD"])
	yield from client.login(settings["EMAIL"], settings["PASSWORD"])
	yield from client.connect()

if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	try:
		loop.run_until_complete(main())
	except discord.LoginFailure:
		logger.error("The credentials you put in settings.json are wrong. Take a look.")
	except Exception as e:
		logger.error(e)
		loop.run_until_complete(client.logout())
	finally:
		loop.close()
