"""
Red-DiscordBot built in Supervisor
Coded by CCubed (AKA Rory in DAPI)
"""
import os
import subprocess
import sys
import urllib.request
from functools import partial
from html.parser import HTMLParser
from zipfile import *


IS_X8664 = sys.maxsize > 2**32


def check_for_git():
    """
    Does git exist? let's find out.
    :return: True or False
    """
    try:
        subprocess.check_output(['git', '--version'])
        return True
    except Exception as e:
        return False

if __name__ == "__main__":
    # Check for Git
    if not check_for_git():
        print("Please install GIT to properly use this supervisor.")
        sys.exit(0)

    # Try to pull
    print("We're going to update your instance of redbot now.")
    if subprocess.run(['git', 'pull']).returncode:
        print("Error updating Redbot. Please investigate.")
        sys.exit(0)
    else:
        print("Redbot has been updated.")

    # Well, let's start her up
    print("Redbot starting.")
    if os.name == 'nt':
        redbot = partial(subprocess.Popen, [sys.executable, 'red.py'],
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.STDOUT,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                         )
    else:
        redbot = partial(subprocess.Popen, [sys.executable, 'red.py'],
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.STDOUT,
                         preexec_fn=os.setpgrp,
                         )
    while True:
        if redbot().wait() == 0:
            break
    print("Redbot shutting down.")
    sys.exit(0)
