import sys
import warnings
import discord
import colorama

MIN_PYTHON_VERSION = (3, 7, 0)

if sys.version_info < MIN_PYTHON_VERSION:
    print(
        f"Python {'.'.join(map(str, MIN_PYTHON_VERSION))} is required to run Red, but you have "
        f"{sys.version}! Please update Python."
    )
    sys.exit(1)

if discord.version_info.major < 1:
    print(
        "You are not running the rewritten version of discord.py.\n\n"
        "In order to use Red V3 you MUST be running d.py version "
        "1.0.0 or greater."
    )
    sys.exit(1)


colorama.init()

# Filter fuzzywuzzy slow sequence matcher warning
warnings.filterwarnings("ignore", module=r"fuzzywuzzy.*")
# Prevent discord PyNaCl missing warning
discord.voice_client.VoiceClient.warn_nacl = False
