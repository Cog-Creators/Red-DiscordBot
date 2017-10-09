from redbot.core.bot import ExitCodes
from redbot.core.data_manager import config_file
import subprocess
import sys
import json


def update_red():
    pass


def run_red(autorestart=False):

    if interpreter is None:  # This should never happen, but what if
        raise RuntimeError("Couldn't find Python's interpreter")
    
    with open(config_file, "r") as fin:
        instances = json.loads(fin.read())
    

def instance_menu(instances):
    if not instances:
        raise RuntimeError(
            "No instances configured! Configure an instance with "
            "redbot-setup and retry!"
        )
    counter = 1
    print("Red instance menu\n")
    print("Please select one of the following:\n\n")
    namenummap = {}
    for name in list(instances.keys()):
        print("{}. {}\n".format(counter, name))
        namenummap[str(counter)] = name
        counter += 1
    selection = input("Enter your selection: ")
    try:
        selection = int(selection)
    except ValueError:
        print("Invalid input! Try again.")
        return instance_menu(instances)
    else:
        if selection not in list(range(1, counter)):
            print("Invalid selection! Please try again")
            return instance_menu(instances)
        else:
            return namenummap[str(counter)]
