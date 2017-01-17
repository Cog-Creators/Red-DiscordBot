from discord.ext import commands
from .utils.dataIO import dataIO, fileIO
from .utils import checks
from __main__ import user_allowed
import os
import re

class Cmds:
  
    """Lists tree of command types that users can use"""
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(pass_context=True, no_pm=True)
    async def cmds(self, ctx, group: str):
        """Lists the groups of commands, or the commands in each group with an argument \nUse argument all for list of groups\nIf you'd like all the commands sent to you via PM, use the command '!pmcommands'"""
        user = ctx.message.author
        msg = ""
        arg = group
        if arg == "all" :
            msg = "HELP COMMANDS:\n  -Admin\n  -Mod\n  -Games\n  -Streams\n  -Casino\n  -Economy\n  -Utilities\n  -Fun\n  -Other"
        elif arg == "admin" :
            msg = "-Addrole\n-Adminset\n-Announce\n-Partycrash\n-Removerole\n-Say\n-Selfrole\n-Serverlock\n-Sudo"
        elif arg == "mod" :
            msg = "-Ban\n-Blacklist\n-Cleanup\n-Editrole\n-Filter\n-Ignore\n-Kick\n-Modset\n-Mute\n-Names\n-Reason\n-Rename\n-Softban\n-Unignore\n-Unmute\n-Whitelist"
        elif arg == "games" :
            msg = "-Games\n-"
        elif arg == "streams" :
            msg = "Dummy message"
        elif arg == "economy" :
            msg = "Dummy message"
        elif arg == "casino" :
            msg = "Dummy message"
        elif arg == "utilities" :
            msg = "Dummy message"
        elif arg == "fun" :
            msg = ("-8\n-Ascii\n-Brocode\n-Chuck\n-Duel\n  \u2022duel\n  \u2022duels\n  \u2022protect\n  \u2022protected\n  \u2022unprotect\n-Four in a row:\n  \u20224row\n  \u2022listtokens\n  \u2022mytoken\n  \u2022setmytoken\n
                  ")
        elif arg == "other" :
            msg = "Dummy message"
        else :
            msg = "Invalid Group"
        await self.bot.say(user.mention + "\n" + msg)
        
    

def check_folders():
    folders = ("data", "data/help/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)
            
def check_files():
    """Moves the file from cogs to the data directory. Important -> Also changes the name to help.json"""

    if not os.path.isfile("data/help/help.json"):
        if os.path.isfile("cogs/put_in_cogs_folder.json"):
            print("moving default help.json...")
            os.rename("cogs/put_in_cogs_folder.json", "data/help/help.json")
        else:
            print("creating default help.json...")
            fileIO("data/help/help.json", "save", " ")
            
def setup(bot):
    bot.add_cog(Cmds(bot))