import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from .utils.chat_formatting import box
from __main__ import send_cmd_help, set_cog
import os
from subprocess import call, Popen
from distutils.dir_util import copy_tree
import shutil
import asyncio

class Downloader:
    """Cog downloader/installer."""

    def __init__(self, bot):
        self.bot = bot
        self.path = "data/downloader/cogs/"

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def cog(self, ctx):
        """Additional cogs management"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @cog.command(name="list")
    async def _send_list(self):
        """Lists installable cogs"""
        index = await self.make_index()
        msg = "Available cogs:\n\n"
        for cog in index.keys():
            if not index[cog]["DISABLED"]:
                msg += cog + "\t" + index[cog]["NAME"] + "\n"
        await self.bot.say(box(msg)) # Need to deal with over 2000 characters

    @cog.command()
    async def info(self, cog : str):
        """Shows info about the specified cog"""
        cogs = self.list_cogs()
        info_file = self.path + cog + "/info.json"
        if cog in cogs:
            if os.path.isfile(info_file):
                data = fileIO(info_file, "load")
                msg = "{} by {}\n\n".format(cog, data["AUTHOR"])
                msg += data["NAME"] + "\n\n" + data["DESCRIPTION"]
                await self.bot.say(box(msg))
            else:
                await self.bot.say("The specified cog has no info file.")
        else:
            await self.bot.say("That cog doesn't exist. Use cog list to see the full list.")

    @cog.command(hidden=True)
    async def search(self, *terms : str):
        """Search installable cogs"""
        pass #TO DO

    @cog.command(pass_context=True)
    async def update(self, ctx):
        """Updates cogs"""
        self.update_repo()
        await self.bot.say("Downloading updated cogs. Wait 10 seconds...")
        await asyncio.sleep(10) # TO DO: Wait for the result instead, without being blocking.
        downloadable_cogs = self.list_cogs()
        all_cogs = [f.replace(".py", "") for f in os.listdir("cogs/") if f.endswith(".py")]
        installed_user_cogs = [f for f in all_cogs if f in downloadable_cogs]
        for cog in installed_user_cogs:
            result = await self.install(cog)
        await self.bot.say("Cogs updated. Reload all installed cogs? (yes/no)")
        answer = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
        if answer is None:
            await self.bot.say("Ok then, you can reload cogs with `{}reload <cog_name>`".format(ctx.prefix))
        elif answer.content.lower().strip() in ["yes", "y"]:
            for cog in installed_user_cogs:
                self.bot.unload_extension("cogs." + cog)
                self.bot.load_extension("cogs." + cog)
            await self.bot.say("Done.")
        else:
            await self.bot.say("Ok then, you can reload cogs with `{}reload <cog_name>`".format(ctx.prefix))

    @cog.command(name="install", pass_context=True)
    async def _install(self, ctx, cog : str):
        """Installs specified cog"""
        install_cog = await self.install(cog)
        if install_cog:
            await self.bot.say("Installation completed. Load it now? (yes/no)")
            answer = await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
            if answer is None:
                await self.bot.say("Ok then, you can load it with `{}load {}`".format(ctx.prefix, cog))
            elif answer.content.lower().strip() in ["yes", "y"]:
                set_cog("cogs." + cog, True)
                self.bot.unload_extension("cogs." + cog)
                self.bot.load_extension("cogs." + cog)
                await self.bot.say("Done.")
            else:
                await self.bot.say("Ok then, you can load it with `{}load {}`".format(ctx.prefix, cog))
        elif install_cog == False:
            await self.bot.say("Invalid cog. Installation aborted.")
        else:
            await self.bot.say("That cog doesn't exist. Use cog list to see the full list.")

    async def make_index(self):
        cogs = self.list_cogs()
        index = {}
        if not cogs:
            await self.bot.say("There are no cogs available for installation.")
            return
        for cog in cogs:
            if os.path.isfile(self.path + cog + "/info.json"):
                info = fileIO(self.path + cog + "/info.json", "load")
                index[cog] = info
        # Sort by alphabetic order?
        return index

    async def install(self, cog):
        cogs = self.list_cogs()
        cog = cog.lower()
        if not cog in cogs:
            return None
        files = [f for f in os.listdir(self.path + cog) if os.path.isfile(self.path + cog + "/" + f)] # Listing all files (not dirs) in the cog directory
        cog_file = [f for f in files if f.endswith(".py")] #Verifying the presence of a single py file
        if len(cog_file) != 1:
            return False
        cog_file = cog_file[0]
        print("Copying {}...".format(cog_file))
        shutil.copy(self.path + cog + "/" + cog_file, "cogs/")
        cog_data_path = self.path + cog + "/data"
        if os.path.exists(cog_data_path):
            print("Copying {}'s data folder...".format(cog))
            copy_tree(cog_data_path, "data/" + cog)
        return True

    def list_cogs(self):
        dirs = [d for d in os.listdir(self.path) if os.path.exists(self.path + d)]
        return dirs

    def update_repo(self):
            if not os.path.exists("data/downloader"):
                print("Downloading cogs repo...")
                call(["git", "clone", "https://github.com/Twentysix26/Red-Cogs.git", "data/downloader"]) # It's blocking but it shouldn't matter
            else:
                Popen(["git", "-C", "data/downloader", "pull", "-q"])

def setup(bot):
    n = Downloader(bot)
    n.update_repo()
    bot.add_cog(n)