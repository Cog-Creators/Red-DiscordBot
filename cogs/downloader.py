from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils.chat_formatting import pagify, box
from __main__ import send_cmd_help, set_cog
import os
from subprocess import run as sp_run, PIPE
import shutil
from asyncio import as_completed
from setuptools import distutils
import discord
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from time import time
from importlib.util import find_spec
from copy import deepcopy

NUM_THREADS = 4
REPO_NONEX = 0x1
REPO_CLONE = 0x2
REPO_SAME = 0x4
REPOS_LIST = "https://twentysix26.github.io/Red-Docs/red_cog_approved_repos/"

DISCLAIMER = ("You're about to add a 3rd party repository. The creator of Red"
              " and its community have no responsibility for any potential "
              "damage that the content of 3rd party repositories might cause."
              "\nBy typing 'I agree' you declare to have read and understand "
              "the above message. This message won't be shown again until the"
              " next reboot.")


class UpdateError(Exception):
    pass


class CloningError(UpdateError):
    pass


class RequirementFail(UpdateError):
    pass


class Downloader:
    """Cog downloader/installer."""

    def __init__(self, bot):
        self.bot = bot
        self.disclaimer_accepted = False
        self.path = os.path.join("data", "downloader")
        self.file_path = os.path.join(self.path, "repos.json")
        # {name:{url,cog1:{installed},cog1:{installed}}}
        self.repos = dataIO.load_json(self.file_path)
        self.executor = ThreadPoolExecutor(NUM_THREADS)
        self._do_first_run()

    def save_repos(self):
        dataIO.save_json(self.file_path, self.repos)

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
        if not self.disclaimer_accepted:
            await self.bot.say(DISCLAIMER)
            answer = await self.bot.wait_for_message(timeout=30,
                                                     author=ctx.message.author)
            if answer is None:
                await self.bot.say('Not adding repo.')
                return
            elif "i agree" not in answer.content.lower():
                await self.bot.say('Not adding repo.')
                return
            else:
                self.disclaimer_accepted = True
        self.repos[repo_name] = {}
        self.repos[repo_name]['url'] = repo_url
        try:
            self.update_repo(repo_name)
        except CloningError:
            await self.bot.say("That repository link doesn't seem to be "
                               "valid.")
            del self.repos[repo_name]
            return
        self.populate_list(repo_name)
        self.save_repos()
        data = self.get_info_data(repo_name)
        if data:
            msg = data.get("INSTALL_MSG")
            if msg:
                await self.bot.say(msg[:2000])
        await self.bot.say("Repo '{}' added.".format(repo_name))

    @repo.command(name="remove")
    async def _repo_del(self, repo_name: str):
        """Removes repo from repo list. COGS ARE NOT REMOVED."""
        def remove_readonly(func, path, excinfo):
            os.chmod(path, 0o755)
            func(path)

        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        del self.repos[repo_name]
        try:
            shutil.rmtree(os.path.join(self.path, repo_name), onerror=remove_readonly)
        except FileNotFoundError:
            pass
        self.save_repos()
        await self.bot.say("Repo '{}' removed.".format(repo_name))

    @cog.command(name="list")
    async def _send_list(self, repo_name=None):
        """Lists installable cogs

        Repositories list:
        https://twentysix26.github.io/Red-Docs/red_cog_approved_repos/"""
        retlist = []
        if repo_name and repo_name in self.repos:
            msg = "Available cogs:\n"
            for cog in sorted(self.repos[repo_name].keys()):
                if 'url' == cog:
                    continue
                data = self.get_info_data(repo_name, cog)
                if data and data.get("HIDDEN") is True:
                    continue
                if data:
                    retlist.append([cog, data.get("SHORT", "")])
                else:
                    retlist.append([cog, ''])
        else:
            if self.repos:
                msg = "Available repos:\n"
                for repo_name in sorted(self.repos.keys()):
                    data = self.get_info_data(repo_name)
                    if data:
                        retlist.append([repo_name, data.get("SHORT", "")])
                    else:
                        retlist.append([repo_name, ""])
            else:
                await self.bot.say("You haven't added a repository yet.\n"
                                   "Start now! {}".format(REPOS_LIST))
                return

        col_width = max(len(row[0]) for row in retlist) + 2
        for row in retlist:
            msg += "\t" + "".join(word.ljust(col_width) for word in row) + "\n"
        msg += "\nRepositories list: {}".format(REPOS_LIST)
        for page in pagify(msg, delims=['\n'], shorten_by=8):
            await self.bot.say(box(page))

    @cog.command()
    async def info(self, repo_name: str, cog: str=None):
        """Shows info about the specified cog"""
        if cog is not None:
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
        else:
            data = self.get_info_data(repo_name)
            if data is None:
                await self.bot.say("That repo does not exist or the"
                                   " information file is missing for that repo"
                                   ".")
                return
            name = data.get("NAME", None)
            name = repo_name if name is None else name
            author = data.get("AUTHOR", "Unknown")
            desc = data.get("DESCRIPTION", "")
            msg = ("```{} by {}```\n\n{}".format(name, author, desc))
            await self.bot.say(msg)

    @cog.command(hidden=True)
    async def search(self, *terms: str):
        """Search installable cogs"""
        pass  # TO DO

    @cog.command(pass_context=True)
    async def update(self, ctx):
        """Updates cogs"""

        tasknum = 0
        num_repos = len(self.repos)

        min_dt = 0.5
        burst_inc = 0.1/(NUM_THREADS)
        touch_n = tasknum
        touch_t = time()

        def regulate(touch_t, touch_n):
            dt = time() - touch_t
            if dt + burst_inc*(touch_n) > min_dt:
                touch_n = 0
                touch_t = time()
                return True, touch_t, touch_n
            return False, touch_t, touch_n + 1

        tasks = []
        for r in self.repos:
            task = partial(self.update_repo, r)
            task = self.bot.loop.run_in_executor(self.executor, task)
            tasks.append(task)

        base_msg = "Downloading updated cogs, please wait... "
        status = ' %d/%d repos updated' % (tasknum, num_repos)
        msg = await self.bot.say(base_msg + status)

        updated_cogs = []
        new_cogs = []
        deleted_cogs = []
        failed_cogs = []
        error_repos = {}
        installed_updated_cogs = []

        for f in as_completed(tasks):
            tasknum += 1
            try:
                name, updates, oldhash = await f
                if updates:
                    if type(updates) is dict:
                        for k, l in updates.items():
                            tl = [(name, c, oldhash) for c in l]
                            if k == 'A':
                                new_cogs.extend(tl)
                            elif k == 'D':
                                deleted_cogs.extend(tl)
                            elif k == 'M':
                                updated_cogs.extend(tl)
            except UpdateError as e:
                name, what = e.args
                error_repos[name] = what
            edit, touch_t, touch_n = regulate(touch_t, touch_n)
            if edit:
                status = ' %d/%d repos updated' % (tasknum, num_repos)
                msg = await self._robust_edit(msg, base_msg + status)
        status = 'done. '

        for t in updated_cogs:
            repo, cog, _ = t
            if self.repos[repo][cog]['INSTALLED']:
                try:
                    await self.install(repo, cog,
                                       no_install_on_reqs_fail=False)
                except RequirementFail:
                    failed_cogs.append(t)
                else:
                    installed_updated_cogs.append(t)

        for t in updated_cogs.copy():
            if t in failed_cogs:
                updated_cogs.remove(t)

        if not any(self.repos[repo][cog]['INSTALLED'] for
                   repo, cog, _ in updated_cogs):
            status += ' No updates to apply. '

        if new_cogs:
            status += '\nNew cogs: ' \
                   + ', '.join('%s/%s' % c[:2] for c in new_cogs) + '.'
        if deleted_cogs:
            status += '\nDeleted cogs: ' \
                   + ', '.join('%s/%s' % c[:2] for c in deleted_cogs) + '.'
        if updated_cogs:
            status += '\nUpdated cogs: ' \
                   + ', '.join('%s/%s' % c[:2] for c in updated_cogs) + '.'
        if failed_cogs:
            status += '\nCogs that got new requirements which have ' + \
                   'failed to install: ' + \
                   ', '.join('%s/%s' % c[:2] for c in failed_cogs) + '.'
        if error_repos:
            status += '\nThe following repos failed to update: '
            for n, what in error_repos.items():
                status += '\n%s: %s' % (n, what)

        msg = await self._robust_edit(msg, base_msg + status)

        if not installed_updated_cogs:
            return

        patchnote_lang = 'Prolog'
        shorten_by = 8 + len(patchnote_lang)
        for note in self.patch_notes_handler(installed_updated_cogs):
            if note is None:
                continue
            for page in pagify(note, delims=['\n'], shorten_by=shorten_by):
                await self.bot.say(box(page, patchnote_lang))

        await self.bot.say("Cogs updated. Reload updated cogs? (yes/no)")
        answer = await self.bot.wait_for_message(timeout=15,
                                                 author=ctx.message.author)
        if answer is None:
            await self.bot.say("Ok then, you can reload cogs with"
                               " `{}reload <cog_name>`".format(ctx.prefix))
        elif answer.content.lower().strip() == "yes":
            registry = dataIO.load_json(os.path.join("data", "red", "cogs.json"))
            update_list = []
            fail_list = []
            for repo, cog, _ in installed_updated_cogs:
                if not registry.get('cogs.' + cog, False):
                    continue
                try:
                    self.bot.unload_extension("cogs." + cog)
                    self.bot.load_extension("cogs." + cog)
                    update_list.append(cog)
                except:
                    fail_list.append(cog)
            msg = 'Done.'
            if update_list:
                msg += " The following cogs were reloaded: "\
                    + ', '.join(update_list) + "\n"
            if fail_list:
                msg += " The following cogs failed to reload: "\
                    + ', '.join(fail_list)
            await self.bot.say(msg)

        else:
            await self.bot.say("Ok then, you can reload cogs with"
                               " `{}reload <cog_name>`".format(ctx.prefix))

    def patch_notes_handler(self, repo_cog_hash_pairs):
        for repo, cog, oldhash in repo_cog_hash_pairs:
            repo_path = os.path.join('data', 'downloader', repo)
            cogfile = os.path.join(cog, cog + ".py")
            cmd = ["git", "-C", repo_path, "log", "--relative-date",
                   "--reverse", oldhash + '..', cogfile
                   ]
            try:
                log = sp_run(cmd, stdout=PIPE).stdout.decode().strip()
                yield self.format_patch(repo, cog, log)
            except:
                pass

    @cog.command(pass_context=True)
    async def uninstall(self, ctx, repo_name, cog):
        """Uninstalls a cog"""
        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        if cog not in self.repos[repo_name]:
            await self.bot.say("That cog isn't available from that repo.")
            return
        set_cog("cogs." + cog, False)
        self.repos[repo_name][cog]['INSTALLED'] = False
        self.save_repos()
        os.remove(os.path.join("cogs", cog + ".py"))
        owner = self.bot.get_cog('Owner')
        await owner.unload.callback(owner, cog_name=cog)
        await self.bot.say("Cog successfully uninstalled.")

    @cog.command(name="install", pass_context=True)
    async def _install(self, ctx, repo_name: str, cog: str):
        """Installs specified cog"""
        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        if cog not in self.repos[repo_name]:
            await self.bot.say("That cog isn't available from that repo.")
            return
        data = self.get_info_data(repo_name, cog)
        try:
            install_cog = await self.install(repo_name, cog, notify_reqs=True)
        except RequirementFail:
            await self.bot.say("That cog has requirements that I could not "
                               "install. Check the console for more "
                               "informations.")
            return
        if data is not None:
            install_msg = data.get("INSTALL_MSG", None)
            if install_msg:
                await self.bot.say(install_msg[:2000])
        if install_cog:
            await self.bot.say("Installation completed. Load it now? (yes/no)")
            answer = await self.bot.wait_for_message(timeout=15,
                                                     author=ctx.message.author)
            if answer is None:
                await self.bot.say("Ok then, you can load it with"
                                   " `{}load {}`".format(ctx.prefix, cog))
            elif answer.content.lower().strip() == "yes":
                set_cog("cogs." + cog, True)
                owner = self.bot.get_cog('Owner')
                await owner.load.callback(owner, cog_name=cog)
            else:
                await self.bot.say("Ok then, you can load it with"
                                   " `{}load {}`".format(ctx.prefix, cog))
        elif install_cog is False:
            await self.bot.say("Invalid cog. Installation aborted.")
        else:
            await self.bot.say("That cog doesn't exist. Use cog list to see"
                               " the full list.")

    async def install(self, repo_name, cog, *, notify_reqs=False,
                      no_install_on_reqs_fail=True):
        # 'no_install_on_reqs_fail' will make the cog get installed anyway
        # on requirements installation fail. This is necessary because due to
        # how 'cog update' works right now, the user would have no way to
        # reupdate the cog if the update fails, since 'cog update' only
        # updates the cogs that get a new commit.
        # This is not a great way to deal with the problem and a cog update
        # rework would probably be the best course of action.
        reqs_failed = False
        if cog.endswith('.py'):
            cog = cog[:-3]

        path = self.repos[repo_name][cog]['file']
        cog_folder_path = self.repos[repo_name][cog]['folder']
        cog_data_path = os.path.join(cog_folder_path, 'data')
        data = self.get_info_data(repo_name, cog)
        if data is not None:
            requirements = data.get("REQUIREMENTS", [])

            requirements = [r for r in requirements
                            if not self.is_lib_installed(r)]

            if requirements and notify_reqs:
                await self.bot.say("Installing cog's requirements...")

            for requirement in requirements:
                if not self.is_lib_installed(requirement):
                    success = await self.bot.pip_install(requirement)
                    if not success:
                        if no_install_on_reqs_fail:
                            raise RequirementFail()
                        else:
                            reqs_failed = True

        to_path = os.path.join("cogs", cog + ".py")

        print("Copying {}...".format(cog))
        shutil.copy(path, to_path)

        if os.path.exists(cog_data_path):
            print("Copying {}'s data folder...".format(cog))
            distutils.dir_util.copy_tree(cog_data_path,
                                         os.path.join('data', cog))
        self.repos[repo_name][cog]['INSTALLED'] = True
        self.save_repos()
        if not reqs_failed:
            return True
        else:
            raise RequirementFail()

    def get_info_data(self, repo_name, cog=None):
        if cog is not None:
            cogs = self.list_cogs(repo_name)
            if cog in cogs:
                info_file = os.path.join(cogs[cog].get('folder'), "info.json")
                if os.path.isfile(info_file):
                    try:
                        data = dataIO.load_json(info_file)
                    except:
                        return None
                    return data
        else:
            repo_info = os.path.join(self.path, repo_name, 'info.json')
            if os.path.isfile(repo_info):
                try:
                    data = dataIO.load_json(repo_info)
                    return data
                except:
                    return None
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

    def is_lib_installed(self, name):
        return bool(find_spec(name))

    def _do_first_run(self):
        save = False
        repos_copy = deepcopy(self.repos)

        # Issue 725
        for repo in repos_copy:
            for cog in repos_copy[repo]:
                cog_data = repos_copy[repo][cog]
                if isinstance(cog_data, str):  # ... url field
                    continue
                for k, v in cog_data.items():
                    if k in ("file", "folder"):
                        repos_copy[repo][cog][k] = os.path.normpath(cog_data[k])

        if self.repos != repos_copy:
            self.repos = repos_copy
            save = True

        invalid = []

        for repo in self.repos:
            broken = 'url' in self.repos[repo] and len(self.repos[repo]) == 1
            if broken:
                save = True
                try:
                    self.update_repo(repo)
                    self.populate_list(repo)
                except CloningError:
                    invalid.append(repo)
                    continue
                except Exception as e:
                    print(e) # TODO: Proper logging
                    continue

        for repo in invalid:
            del self.repos[repo]

        if save:
            self.save_repos()

    def populate_list(self, name):
        valid_cogs = self.list_cogs(name)
        new = set(valid_cogs.keys())
        old = set(self.repos[name].keys())
        for cog in new - old:
            self.repos[name][cog] = valid_cogs.get(cog, {})
            self.repos[name][cog]['INSTALLED'] = False
        for cog in new & old:
            self.repos[name][cog].update(valid_cogs[cog])
        for cog in old - new:
            if cog != 'url':
                del self.repos[name][cog]

    def update_repo(self, name):

        def run(*args, **kwargs):
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
            kwargs['env'] = env
            return sp_run(*args, **kwargs)

        try:
            dd = self.path
            if name not in self.repos:
                raise UpdateError("Repo does not exist in data, wtf")
            folder = os.path.join(dd, name)
            # Make sure we don't git reset the Red folder on accident
            if not os.path.exists(os.path.join(folder, '.git')):
                #if os.path.exists(folder):
                    #shutil.rmtree(folder)
                url = self.repos[name].get('url')
                if not url:
                    raise UpdateError("Need to clone but no URL set")
                branch = None
                if "@" in url: # Specific branch
                    url, branch = url.rsplit("@", maxsplit=1)
                if branch is None:
                    p = run(["git", "clone", url, folder])
                else:
                    p = run(["git", "clone", "-b", branch, url, folder])
                if p.returncode != 0:
                    raise CloningError()
                self.populate_list(name)
                return name, REPO_CLONE, None
            else:
                rpbcmd = ["git", "-C", folder, "rev-parse", "--abbrev-ref", "HEAD"]
                p = run(rpbcmd, stdout=PIPE)
                branch = p.stdout.decode().strip()

                rpcmd = ["git", "-C", folder, "rev-parse", branch]
                p = run(["git", "-C", folder, "reset", "--hard",
                        "origin/%s" % branch, "-q"])
                if p.returncode != 0:
                    raise UpdateError("Error resetting to origin/%s" % branch)
                p = run(rpcmd, stdout=PIPE)
                if p.returncode != 0:
                    raise UpdateError("Unable to determine old commit hash")
                oldhash = p.stdout.decode().strip()
                p = run(["git", "-C", folder, "pull", "-q", "--ff-only"])
                if p.returncode != 0:
                    raise UpdateError("Error pulling updates")
                p = run(rpcmd, stdout=PIPE)
                if p.returncode != 0:
                    raise UpdateError("Unable to determine new commit hash")
                newhash = p.stdout.decode().strip()
                if oldhash == newhash:
                    return name, REPO_SAME, None
                else:
                    self.populate_list(name)
                    self.save_repos()
                    ret = {}
                    cmd = ['git', '-C', folder, 'diff', '--no-commit-id',
                           '--name-status', oldhash, newhash]
                    p = run(cmd, stdout=PIPE)

                    if p.returncode != 0:
                        raise UpdateError("Error in git diff")

                    changed = p.stdout.strip().decode().split('\n')

                    for f in changed:
                        if not f.endswith('.py'):
                            continue

                        status, _, cogpath = f.partition('\t')
                        cogname = os.path.split(cogpath)[-1][:-3]  # strip .py
                        if status not in ret:
                            ret[status] = []
                        ret[status].append(cogname)

                    return name, ret, oldhash

        except CloningError as e:
            raise CloningError(name, *e.args) from None
        except UpdateError as e:
            raise UpdateError(name, *e.args) from None

    async def _robust_edit(self, msg, text):
        try:
            msg = await self.bot.edit_message(msg, text)
        except discord.errors.NotFound:
            msg = await self.bot.send_message(msg.channel, text)
        except:
            raise
        return msg

    @staticmethod
    def format_patch(repo, cog, log):
        header = "Patch Notes for %s/%s" % (repo, cog)
        line = "=" * len(header)
        if log:
            return '\n'.join((header, line, log))


def check_folders():
    if not os.path.exists(os.path.join("data", "downloader")):
        print('Making repo downloads folder...')
        os.mkdir(os.path.join("data", "downloader"))


def check_files():
    f = os.path.join("data", "downloader", "repos.json")
    if not dataIO.is_valid_json(f):
        print("Creating default data/downloader/repos.json")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = Downloader(bot)
    bot.add_cog(n)
