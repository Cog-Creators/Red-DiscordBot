import json
import logging
import os
import glob

default_settings = ('{"TRIVIA_ADMIN_ONLY": false, "EDIT_CC_ADMIN_ONLY": false, "PASSWORD": "PASSWORDHERE", "FILTER": true, "CUSTOMCOMMANDS": true, ' +
					'"TRIVIA_MAX_SCORE": 10, "TRIVIA_DELAY": 15, "LOGGING": true, "EMAIL": "EMAILHERE", "ADMINROLE": "Transistor", "DOWNLOADMODE" : true, ' +
					'"VOLUME": 0.20, "TRIVIA_BOT_PLAYS" : false, "TRIVIA_TIMEOUT" : 120, "DEBUG_ID" : "IgnoreThis", "POLL_DURATION" : 60, "PREFIX" : "!"}')
					
default_apis = ('{"IMGFLIP_USERNAME": "USERNAMEHERE", "IMGFLIP_PASSWORD": "PASSWORDHERE", "MYAPIFILMS_TOKEN" : "TOKENHERE"}')

logger = logging.getLogger("__main__")


def fileIO(filename, IO, data=None):
	if IO == "save" and data != None:
		with open(filename, encoding='utf-8', mode="w") as f:
			f.write(json.dumps(data))
	elif IO == "load" and data == None:
		with open(filename, encoding='utf-8', mode="r") as f:
			return json.loads(f.read())
	elif IO == "check" and data == None:
		try:
			with open(filename, encoding='utf-8', mode="r") as f:
				return True
		except:
			return False
	else:
		logger.info("Invalid fileIO call")

def loadProverbs():
	with open("proverbs.txt", encoding='utf-8', mode="r") as f:
		data = f.readlines()
	return data

def loadAndCheckSettings():
	to_delete = []
	try:
		current_settings = fileIO("json/settings.json", "load")
		default = json.loads(default_settings)
		if current_settings.keys() != default.keys():
			logger.warning("Something wrong detected with settings.json. Starting check...")
			for field in default:
				if field not in current_settings:
					logger.info("Adding " + field + " field.")
					current_settings[field] = default[field]
			for field in current_settings:
				if field not in default:
					logger.info("Removing " + field + " field.")
					to_delete.append(field)
			for field in to_delete:
				del current_settings[field]
			logger.warning("Your settings.json was deprecated (missing or useless fields detected). I fixed it. " +
						   "If the file was missing any field I've added it and put default values. You might want to check it.")
		fileIO("json/settings.json", "save", current_settings)
		return current_settings
	except IOError:
		fileIO("json/settings.json", "save", json.loads(default_settings))
		logger.error("Your settings.json is missing. I've created a new one. Edit it with your settings and restart me.")
		exit(1)
	except:
		logger.error("Your settings.json seems to be invalid. Check it. If you're unable to fix it delete it and I'll create a new one the next start.")
		exit(1)

def migration():
	if not os.path.exists("json/"):
		os.makedirs("json")
		logger.info("Creating json folder...")

	if not os.path.exists("cache/"): #Stores youtube audio for DOWNLOADMODE
		os.makedirs("cache")

	if not os.path.exists("trivia/"):
		os.makedirs("trivia")
	
	files = glob.glob("*.json")
	if files != []:
		logger.info("Moving your json files into the json folder...")
		for f in files:
			logger.info("Moving {}...".format(f))
			os.rename(f, "json/" + f)

def createEmptyFiles():
	files = {"twitch.json": [], "commands.json": {}, "economy.json" : {}, "filter.json" : {}, "regex_filter.json" : {}, "shushlist.json" : [], "blacklist.json" : []}
	games = ["Multi Theft Auto", "her Turn()", "Tomb Raider II", "some music.", "NEO Scavenger", "Python", "World Domination", "with your heart."]
	files["games.json"] = games
	for f, data in files.items() :
		if not os.path.isfile("json/" + f):
			logger.info("Missing {}. Creating it...".format(f))
			fileIO("json/" + f, "save", data)
	if not os.path.isfile("json/settings.json"):
		logger.info("Missing settings.json. Creating it...\n")
		fileIO("json/settings.json", "save", json.loads(default_settings))
		print("You have to configure your settings. If you'd like to do it manually, close this window.\nOtherwise type your bot's account email. DO NOT use your own account for the bot, make a new one.\n\nEmail:")
		email = input(">")
		print("Now enter the password.")
		password = input(">")
		print("Admin role? Leave empty for default (Transistor)")
		admin_role = input(">")
		if admin_role == "": 
			admin_role = "Transistor"
		print("Command prefix? Leave empty for default, '!'. Maximum 1 character.")
		prefix = input(">")
		if len(prefix) != 1 or prefix == " ":
			print("Invalid prefix. Setting prefix as '!'...")
			prefix = "!"
		new_settings = json.loads(default_settings)
		new_settings["EMAIL"] = email
		new_settings["PASSWORD"] = password
		new_settings["ADMINROLE"] = admin_role
		new_settings["PREFIX"] = prefix
		fileIO("json/settings.json", "save", new_settings )
		logger.info("Settings have been saved.")

	if not os.path.isfile("json/apis.json"):
		logger.info("Missing apis.json. Creating it...\n")
		fileIO("json/apis.json", "save", json.loads(default_apis))
		print("\nIt's now time to configure optional services\nIf you're not interested, leave empty and keep pressing enter.\nMemes feature: create an account on https://imgflip.com/.\nimgflip username:")
		imgflip_username = input(">")
		print("Now enter the imgflip password.")
		imgflip_password = input(">")
		if imgflip_username == "": imgflip_username = "USERNAMEHERE"
		if imgflip_password == "": imgflip_password = "PASSWORDHERE"
		print("\n!imdb configuration. Get your token here http://www.myapifilms.com/token.do\nOr just press enter if you're not interested.")
		imdb_token = input(">")
		if imdb_token == "": imdb_token = "TOKENHERE"
		new_settings = json.loads(default_apis)
		new_settings["IMGFLIP_USERNAME"] = imgflip_username
		new_settings["IMGFLIP_PASSWORD"] = imgflip_password
		new_settings["MYAPIFILMS_TOKEN"] = imdb_token
		fileIO("json/apis.json", "save", new_settings )
		logger.info("API Settings have been saved.\n")
