from random import randint, choice
import time

import dataIO

bank = dataIO.fileIO("economy.json", "load")
client = None
#words = dataIO.loadWords()
#anagram_sessions_timestamps = {}
anagram_sessions = []
payday_register = {}
PAYDAY_TIME = 300 # seconds between each payday
PAYDAY_CREDITS = 120 # credits received

slot_help = """ Slot machine payouts:
:two: :two: :six: Bet * 5000
:four_leaf_clover: :four_leaf_clover: :four_leaf_clover: +1000
:cherries: :cherries: :cherries: +800
:two: :six: Bet * 4
:cherries: :cherries: Bet * 3

Three symbols: +500
Two symbols: Bet * 2

You need an account to play. !register one.
Bet range: 5 - 100
"""

economy_exp = """ **Economy. Get rich and have fun with imaginary currency!**

!register - Register an account at the Twentysix bank
!balance - Check your balance
!slot help - Slot machine explanation
!slot [bid] - Play the slot machine
!payday - Type it every {} seconds to receive some credits.
""".format(str(PAYDAY_TIME))
#!payday - Get some cash every 10 minutes

def initialize(c):
	global client
	client = c

async def checkCommands(message):
	cmd = message.content
	user = message.author
	if cmd == "!balance":
		if accountCheck(user.id):
			await client.send_message(message.channel, "{} `Your balance is: {}`".format(user.mention, str(checkBalance(user.id))))
		else:
			await client.send_message(message.channel, "{} `You don't have an account at the Twentysix bank. Type !register to open one.`".format(user.mention, str(checkBalance(user.id))))
	elif cmd == "!register":
		await registerAccount(user, message)
	elif cmd == "!slot help":
		await client.send_message(message.author, slot_help)
		await client.send_message(message.channel, "{} `Check your DMs for the slot machine explanation.`".format(message.author.mention))
	elif cmd.startswith("!slot"):
		await slotMachineCheck(message)
	elif cmd == "!economy":
		await client.send_message(message.author, economy_exp)
		await client.send_message(message.channel, "{} `Check your DMs for the economy explanation.`".format(message.author.mention))
	elif cmd == "!challenge":
		#isChallengeOngoing(message)
		pass
	elif cmd == "!payday":
		await payday(message)

async def registerAccount(user, message):
	if user.id not in bank:
		bank[user.id] = {"name" : user.name, "balance" : 100}
		dataIO.fileIO("economy.json", "save", bank)
		await client.send_message(message.channel, "{} `Account opened. Current balance: {}`".format(user.mention, str(checkBalance(user.id))))
	else:
		await client.send_message(message.channel, "{} `You already have an account at the Twentysix bank.`".format(user.mention))

def accountCheck(id):
	if id in bank:
		return True
	else:
		return False

def checkBalance(id):
	if accountCheck(id):
		return bank[id]["balance"]
	else:
		return False

def withdrawMoney(id, amount):
	if accountCheck(id):
		if bank[id]["balance"] >= int(amount):
			bank[id]["balance"] = bank[id]["balance"] - int(amount)
			dataIO.fileIO("economy.json", "save", bank)
		else:
			return False
	else:
		return False

def addMoney(id, amount):
	if accountCheck(id):
		bank[id]["balance"] = bank[id]["balance"] + int(amount)
		dataIO.fileIO("economy.json", "save", bank)
	else:
		return False

def enoughMoney(id, amount):
	if accountCheck(id):
		if bank[id]["balance"] >= int(amount):
			return True
		else:
			return False
	else:
		return False

async def isChallengeOngoing(message): #Work in progress
	global anagram_sessions, anagram_sessions_timestamps
	id = message.channel.id
	for session in anagram_sessions:
		if time.perf_counter() - session.started >= 600:
			if session.done:
				anagram_sessions.remove(session)
				anagram_sessions.append(Anagram(message))
				return True
			else:
				await client.send_message(message.channel, "{} `A challenge is already ongoing.`".format(message.author.mention))
				return True
		else:
			await client.send_message(message.channel, "{} `You have to wait 10 minutes before each challenge.`".format(message.author.mention))
			return True
	anagram_sessions.append(Anagram(message))

async def payday(message):
	id = message.author.id
	if accountCheck(id):
		if id in payday_register:
			if abs(payday_register[id] - int(time.perf_counter()))  >= PAYDAY_TIME: 
				addMoney(id, PAYDAY_CREDITS)
				payday_register[id] = int(time.perf_counter())
				await client.send_message(message.channel, "{} `Here, take some credits. Enjoy! (+{} credits!)`".format(message.author.mention, str(PAYDAY_CREDITS)))
			else:
				await client.send_message(message.channel, "{} `Too soon. You have to wait {} seconds between each payday.`".format(message.author.mention, str(PAYDAY_TIME)))
		else:
			payday_register[id] = int(time.perf_counter())
			addMoney(id, PAYDAY_CREDITS)
			await client.send_message(message.channel, "{} `Here, take some credits. Enjoy! (+{} credits!)`".format(message.author.mention, str(PAYDAY_CREDITS)))
	else:
		await client.send_message(message.channel, "{} `You need an account to receive credits. (!economy)`".format(message.author.mention))

###############SLOT##############

async def slotMachineCheck(message):
	msg = message.content.split()
	if len(msg) == 2:
		if msg[1].isdigit():
			bid = int(msg[1])
			if enoughMoney(message.author.id, bid):
				if bid > 4 and bid < 101:
					await slotMachine(message, bid)
				else:
					await client.send_message(message.channel, "{} `Bid must be between 5 and 100.`".format(message.author.mention))
			else:
				await client.send_message(message.channel, "{} `You need an account with enough funds to play the slot machine. (!economy)`".format(message.author.mention))
		else:
			await client.send_message(message.channel, "{} `!slot [bid]`".format(message.author.mention))
	else:
		await client.send_message(message.channel, "{} `!slot [bid]`".format(message.author.mention))

async def slotMachine(message, bid):
	reel_pattern = [":cherries:", ":cookie:", ":two:", ":four_leaf_clover:", ":cyclone:", ":sunflower:", ":six:", ":mushroom:", ":heart:", ":snowflake:"]
	padding_before = [":mushroom:", ":heart:", ":snowflake:"] # padding prevents index errors
	padding_after = [":cherries:", ":cookie:", ":two:"]
	reel = padding_before + reel_pattern + padding_after
	reels = []
	for i in range(0, 3):
		n = randint(3,12)
		reels.append([reel[n - 1], reel[n], reel[n + 1]])
	line = [reels[0][1], reels[1][1], reels[2][1]]

	display_reels = "  " + reels[0][0] + " " + reels[1][0] + " " + reels[2][0] + "\n"
	display_reels += ">" + reels[0][1] + " " + reels[1][1] + " " + reels[2][1] + "\n"
	display_reels += "  " + reels[0][2] + " " + reels[1][2] + " " + reels[2][2] + "\n"

	if line[0] == ":two:" and line[1] == ":two:" and line[2] == ":six:":
		bid = bid * 5000
		await client.send_message(message.channel, "{}{} `226! Your bet is multiplied * 5000! {}!` ".format(display_reels, message.author.mention, str(bid)))
	elif line[0] == ":four_leaf_clover:" and line[1] == ":four_leaf_clover:" and line[2] == ":four_leaf_clover:":
		bid += 1000
		await client.send_message(message.channel, "{}{} `Three FLC! +1000!` ".format(display_reels, message.author.mention))
	elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
		bid += 800
		await client.send_message(message.channel, "{}{} `Three cherries! +800!` ".format(display_reels, message.author.mention))
	elif line[0] == line[1] == line[2]:
		bid += 500
		await client.send_message(message.channel, "{}{} `Three symbols! +500!` ".format(display_reels, message.author.mention))
	elif line[0] == ":two:" and line[1] == ":six:" or line[1] == ":two:" and line[2] == ":six:":
		bid = bid * 4
		await client.send_message(message.channel, "{}{} `26! Your bet is multiplied * 4! {}!` ".format(display_reels, message.author.mention, str(bid)))
	elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:":
		bid = bid * 3
		await client.send_message(message.channel, "{}{} `Two cherries! Your bet is multiplied * 3! {}!` ".format(display_reels, message.author.mention, str(bid)))
	elif line[0] == line[1] or line[1] == line[2]:
		bid = bid * 2
		await client.send_message(message.channel, "{}{} `Two symbols! Your bet is multiplied * 2! {}!` ".format(display_reels, message.author.mention, str(bid)))
#	elif line[0] == ":cherries:" or line[1] == ":cherries:" or line[2] == ":cherries:":
#		await client.send_message(message.channel, "{}{} `Cherries! Your bet is safe!` ".format(display_reels, message.author.mention))
	else:
		await client.send_message(message.channel, "{}{} `Nothing! Lost bet.` ".format(display_reels, message.author.mention))
		withdrawMoney(message.author.id, bid)
		return True
	addMoney(message.author.id, bid)

#######################################

############### ANAGRAM ###############
#			Work in progress

class Anagram():
	def __init__(self, message):
		self.channel = message.channel
		self.word = choice(words).lower()
		self.anagram = list(self.word)
		shuffle(self.anagram)
		self.anagram = "".join(self.anagram)
		self.started = int(time.perf_counter())
		self.MAX_TIME = 60
		self.done = False

	def checkWord(self, message):
		if time.perf_counter() - self.Atimestamp  <= self.MAX_TIME: 
			msg = message.content.lower()
			if msg.find(self.word) != -1:
				pass
		else:
			self.gameOver()

	async def gameOver(self):
		self.done = True
		try:
			await client.send_message(self.channel, "`Anagram session over! No one guessed the word!`")
		except:
			pass

######################################