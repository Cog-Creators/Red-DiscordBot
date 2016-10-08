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


class LinkParser(HTMLParser):
    def __init__(self):
        self.static_download = None
        super().__init__()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    if 'win32-static.zip' in attr[1]:
                        self.static_download = attr[1]


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


def check_for_ffmpeg():
    """
    Does ffmpeg exist? let's find out
    :return:  True or False
    """
    try:
        subprocess.check_output(['ffmpeg', '-version'])
        return True
    except Exception as e:
        return False


if __name__ == "__main__":
    # Check for Git
    if not check_for_git():
        print("Please install GIT to properly use this supervisor.")
        sys.exit(0)

    # Check for FFMPEG
    if os.name == 'nt':
        if not check_for_ffmpeg():
            if IS_X8664:
                print("FFMPEG not found. Downloading.")
                for item in ['ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe']:
                    with urllib.request.urlopen("https://github.com/Twentysix26/Red-DiscordBot/raw/master/{}".format(item)) as data:
                        with open(item, "wb") as f:
                            f.write(data.read())
                print("FFMPEG downloaded.")
            else:
                parser = LinkParser()
                with urllib.request.urlopen("https://ffmpeg.zeranoe.com/builds/") as data:
                    parser.feed(data.read().decode('utf-8', errors='ignore'))
                if parser.static_download is not None:
                    print("FFMPEG not found, downloading.")
                    with urllib.request.urlopen(parser.static_download) as data:
                        with open("win32static.zip", "wb") as f:
                            f.write(data.read())
                    print("FFMPEG downloaded. Extracting.")
                    with ZipFile('win32static.zip', 'r') as myzip:
                        myzip.extractall()
                    os.remove("win32static.zip")
                    print("FFMPEG extracted.")
                else:
                    print("FFMPEG was not found in the path and I couldn't identify the download link automatically. Please visit https://ffmpeg.zeranoe.com/builds/ and download the 32bit Static build then extract it here.")
    else:
        if not check_for_ffmpeg():
            print("Please install FFMPEG and then run this script again.")
            sys.exit(0)

    # Try to pull
    print("We're going to update your instance of redbot now.")
    updates = subprocess.run(['git', 'pull'])
    if updates.wait() != 0:
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
