import sys
import warnings
import discord
from colorama import init

init()
# Let's do all the dumb version checking in one place.

if discord.version_info.major < 1:
    print(
        "You are not running the rewritten version of discord.py.\n\n"
        "In order to use Red v3 you MUST be running d.py version"
        " >= 1.0.0."
    )
    sys.exit(1)

# Filter fuzzywuzzy slow sequence matcher warning
warnings.filterwarnings("ignore", module=r"fuzzywuzzy.*")
