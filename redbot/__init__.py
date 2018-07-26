import sys
import discord
from colorama import init, Back

init()
# Let's do all the dumb version checking in one place.

if 'Cog Creators' not in discord.__author__:
    print(
        "You are not running our version of discord.py.\n\n"
        "In order to use Red v3 you MUST be using our fork."
        "\n\nYou can avoid conflicts with a python virtual environment"
    )
    sys.exit(1)
