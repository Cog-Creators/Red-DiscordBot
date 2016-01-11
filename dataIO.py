import json
import logging

default_settings = ('{"TRIVIA_ADMIN_ONLY": false, "EDIT_CC_ADMIN_ONLY": false, "PASSWORD": "PASSWORDHERE", "FILTER": true, "CUSTOMCOMMANDS": true, ' +
					'"TRIVIA_MAX_SCORE": 10, "TRIVIA_DELAY": 15, "LOGGING": true, "EMAIL": "EMAILHERE", "ADMINROLE": "Transistor", "DOWNLOADMODE" : true, ' +
					'"VOLUME": 0.20, "TRIVIA_BOT_PLAYS" : false, "TRIVIA_TIMEOUT" : 120}')
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

def loadTrivia():
	w = {}
	with open("questions.txt", "r") as f:
		for line in f:
			line = line.replace("\n", "")
			line = line.split("|")
			w[line[0]] = line[1]
	return w

def loadWords():
	w = []
	with open("words.dat", "r") as f:
		for line in f:
			w += line
	return w

def loadAndCheckSettings():
	to_delete = []
	try:
		current_settings = fileIO("settings.json", "load")
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
		fileIO("settings.json", "save", current_settings)
		return current_settings
	except IOError:
		fileIO("settings.json", "save", json.loads(default_settings))
		logger.error("Your settings.json is missing. I've created a new one. Edit it with your settings and restart me.")
		exit(1)
	except:
		logger.error("Your settings.json seems to be invalid. Check it. If you're unable to fix it delete it and I'll create a new one the next start.")
		exit(1)