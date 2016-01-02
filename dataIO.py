import json
import logging

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