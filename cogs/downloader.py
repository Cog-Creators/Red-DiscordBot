from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils import checks
from cogs.utils.chat_formatting import box
from __main__ import send_cmd_help, set_cog
import os
from subprocess import call, Popen
import shutil
import asyncio


class Downloader:
    """Cog downloader/installer."""

    def __init__(self, bot):
        self.bot = bot
        self.path = "data/downloader/"
        # {name:{url,cog1:{installed},cog1:{installed}}}
        self.repos = fileIO("data/downloader/repos.json", "load")
        self.update_repos()

    def save_repos(self):
        fileIO("data/downloader/repos.json", "save", self.repos)

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def cog(self, ctx):
        """Additional cogs management"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @cog.group(pass_context=True)
    async def repo(self, ctx):
        """Repo management commands"""
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)
            return

    @repo.command(name="add", pass_context=True)
    async def _repo_add(self, ctx, repo_name: str, repo_url: str):
        """Adds repo to available repo lists

        Warning: Adding 3RD Party Repositories is at your own
        Risk."""
        await self.bot.say("Type 'I agree' to confirm "
                           "adding a 3rd party repo. This has the possibility"
                           " of being harmful. You will not receive help "
                           "in Red - Discord Bot #support for any cogs "
                           "installed from this repo. If you do require "
                           "support you should contact the owner of this "
                           "repo.\n\nAgain, ANY repo you add is at YOUR"
                           " discretion and the creator of Red has "
                           "ABSOLUTELY ZERO responsibility to help if "
                           "something goes wrong.")
        answer = await self.bot.wait_for_message(timeout=15,
                                                 author=ctx.message.author)
        if answer is None:
            await self.bot.say('Not adding repo.')
            return
        elif "i agree" not in answer.content.lower():
            await self.bot.say('Not adding repo.')
            return
        self.repos[repo_name] = {}
        self.repos[repo_name]['url'] = repo_url
        self.update_repo(repo_name)
        self.populate_list(repo_name)
        self.save_repos()
        await self.bot.say("Repo '{}' added.".format(repo_name))

    @repo.command(name="remove")
    async def _repo_del(self, repo_name: str):
        """Removes repo from repo list. COGS ARE NOT REMOVED."""
        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        del self.repos[repo_name]
        self.save_repos()
        await self.bot.say("Repo '{}' removed.".format(repo_name))

    @cog.command(name="list")
    async def _send_list(self, repo_name=None):
        """Lists installable cogs"""
        retlist = []
        if repo_name and repo_name in self.repos:
            msg = "Available cogs:\n"
            for cog in sorted(self.repos[repo_name].keys()):
                if 'url' == cog:
                    continue
                data = self.get_info_data(repo_name, cog)
                if data:
                    retlist.append([cog, data['NAME']])
                else:
                    retlist.append([cog, ''])
        else:
            msg = "Available repos:\n"
            retlist = sorted([[k, ''] for k in self.repos])

        col_width = max(len(row[0]) for row in retlist) + 2
        for row in retlist:
            msg += "\t" + "".join(word.ljust(col_width) for word in row) + "\n"
        await self.bot.say(box(msg))  # Need to deal with over 2000 characters

    @cog.command()
    async def info(self, repo_name: str, cog: str):
        """Shows info about the specified cog"""
        cogs = self.list_cogs(repo_name)
        if cog in cogs:
            data = self.get_info_data(repo_name, cog)
            if data:
                msg = "{} by {}\n\n".format(cog, data["AUTHOR"])
                msg += data["NAME"] + "\n\n" + data["DESCRIPTION"]
                await self.bot.say(box(msg))
            else:
                await self.bot.say("The specified cog has no info file.")
        else:
            await self.bot.say("That cog doesn't exist."
                               " Use cog list to see the full list.")

    @cog.command(hidden=True)
    async def search(self, *terms: str):
        """Search installable cogs"""
        pass  # TO DO

    @cog.command(pass_context=True)
    async def update(self, ctx):
        """Updates cogs"""
        self.update_repos()
        await self.bot.say("Downloading updated cogs. Wait 10 seconds...")
        # TO DO: Wait for the result instead, without being blocking.
        await asyncio.sleep(10)
        installed_user_cogs = [(repo, cog) for repo in self.repos
                               for cog in self.repos[repo]
                               if cog != 'url' and
                               self.repos[repo][cog]['INSTALLED'] is True]
        for cog in installed_user_cogs:
            await self.install(*cog)
        await self.bot.say("Cogs updated. Reload all installed cogs? (yes/no)")
        answer = await self.bot.wait_for_message(timeout=15,
                                                 author=ctx.message.author)
        if answer is None:
            await self.bot.say("Ok then, you can reload cogs with"
                               " `{}reload <cog_name>`".format(ctx.prefix))
        elif answer.content.lower().strip() == "yes":
            for (repo, cog) in installed_user_cogs:
                self.bot.unload_extension("cogs." + cog)
                self.bot.load_extension("cogs." + cog)
            await self.bot.say("Done.")
        else:
            await self.bot.say("Ok then, you can reload cogs with"
                               " `{}reload <cog_name>`".format(ctx.prefix))

    @cog.command(name="install", pass_context=True)
    async def _install(self, ctx, repo_name: str, cog: str):
        """Installs specified cog"""
        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        if cog not in self.repos[repo_name]:
            await self.bot.say("That cog isn't available from that repo.")
            return
        install_cog = await self.install(repo_name, cog)
        if install_cog:
            await self.bot.say("Installation completed. Load it now? (yes/no)")
            answer = await self.bot.wait_for_message(timeout=15,
                                                     author=ctx.message.author)
            if answer is None:
                await self.bot.say("Ok then, you can load it with"
                                   " `{}load {}`".format(ctx.prefix, cog))
            elif answer.content.lower().strip() == "yes":
                set_cog("cogs." + cog, True)
                self.bot.unload_extension("cogs." + cog)
                self.bot.load_extension("cogs." + cog)
                await self.bot.say("Done.")
            else:
                await self.bot.say("Ok then, you can load it with"
                                   " `{}load {}`".format(ctx.prefix, cog))
        elif install_cog is False:
            await self.bot.say("Invalid cog. Installation aborted.")
        else:
            await self.bot.say("That cog doesn't exist. Use cog list to see"
                               " the full list.")

    async def install(self, repo_name, cog):
        if cog.endswith('.py'):
            cog = cog[:-3]

        path = self.repos[repo_name][cog]['file']
        cog_folder_path = self.repos[repo_name][cog]['folder']
        cog_data_path = os.path.join(cog_folder_path, 'data')

        to_path = os.path.join("cogs/", cog+".py")

        print("Copying {}...".format(cog))
        shutil.copy(path, to_path)

        if os.path.exists(cog_data_path):
            print("Copying {}'s data folder...".format(cog))
            if os.path.exists(os.path.join('data/', cog)):
                shutil.rmtree(os.path.join('data/', cog))
            shutil.copytree(cog_data_path, os.path.join('data/', cog))
        self.repos[repo_name][cog]['INSTALLED'] = True
        self.save_repos()
        return True

    def get_info_data(self, repo_name, cog):
        cogs = self.list_cogs(repo_name)
        if cog in cogs:
            info_file = os.path.join(cogs[cog].get('folder'), "info.json")
            if os.path.isfile(info_file):
                try:
                    data = fileIO(info_file, "load")
                except:
                    return None
                return data
        return None

    def list_cogs(self, repo_name):
        valid_cogs = {}

        repo_path = os.path.join(self.path, repo_name)
        folders = [f for f in os.listdir(repo_path)
                   if os.path.isdir(os.path.join(repo_path, f))]
        legacy_path = os.path.join(repo_path, "cogs")
        legacy_folders = []
        if os.path.exists(legacy_path):
            for f in os.listdir(legacy_path):
                if os.path.isdir(os.path.join(legacy_path, f)):
                    legacy_folders.append(os.path.join("cogs", f))

        folders = folders + legacy_folders

        for f in folders:
            cog_folder_path = os.path.join(self.path, repo_name, f)
            cog_folder = os.path.basename(cog_folder_path)
            for cog in os.listdir(cog_folder_path):
                cog_path = os.path.join(cog_folder_path, cog)
                if os.path.isfile(cog_path) and cog_folder == cog[:-3]:
                    valid_cogs[cog[:-3]] = {'folder': cog_folder_path,
                                            'file': cog_path}
        return valid_cogs

    def get_dir_name(self, url):
        splitted = url.split("/")
        git_name = splitted[-1]
        return git_name[:-4]

    def populate_list(self, name):
        valid_cogs = self.list_cogs(name)
        for cog in valid_cogs:
            if cog not in self.repos[name]:
                self.repos[name][cog] = valid_cogs.get(cog, {})
                self.repos[name][cog]['INSTALLED'] = False
            else:
                self.repos[name][cog].update(valid_cogs[cog])

    def update_repos(self):
        for name in self.repos:
            self.update_repo(name)
            self.populate_list(name)
        self.save_repos()

    def update_repo(self, name):
        if name not in self.repos:
            return
        if not os.path.exists("data/downloader/" + name):
            print("Downloading cogs repo...")
            url = self.repos[name]['url']
            # It's blocking but it shouldn't matter
            call(["git", "clone", url, "data/downloader/" + name])
        else:
            Popen(["git", "-C", "data/downloader/" + name, "pull", "-q"])


def check_folders():
    if not os.path.exists("data/downloader"):
        print('Making repo downloads folder...')
        os.mkdir('data/downloader')


def check_files():
    repos = \
        {'community': {'url': "https://github.com/Twentysix26/Red-Cogs.git"}}

    f = "data/downloader/repos.json"
    if not fileIO(f, "check"):
        print("Creating default data/downloader/repos.json")
        fileIO(f, "save", repos)

def setup(bot):
    check_folders()
    check_files()
    n = Downloader(bot)
    bot.add_cog(n)
