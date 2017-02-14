import aiohttp
import itertools
import os
import re

from __main__ import send_cmd_help
from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO

try:
    from PIL import Image
    PIL = True
except:
    PIL = False
# if this seem hard to read/understand, remove the comments. Might make it easier


class Emote:
    """Emote was made using irdumb's sadface cog's code.

    Owner is responsible for it's handling."""

    def __init__(self, bot):
        self.bot = bot
        self.data_path = "data/emote/servers.json"
        self.servers = dataIO.load_json(self.data_path)
        self.emote = self.servers["emote"]

    # doesn't make sense to use this command in a pm, because pms aren't in servers
    # mod_or_permissions needs something in it otherwise it's mod or True which is always True

    @commands.group(pass_context=True)
    async def emotes(self, ctx):
        """Emote settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @emotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def set(self, ctx):
        """Enables/Disables emotes for this server"""
        # default off.
        server = ctx.message.server
        if server.id not in self.servers:
            self.servers[server.id] = dict({"status": False})
        else:
            self.servers[server.id]["status"] = not self.servers[server.id]["status"]
        if "emotes" not in self.servers[server.id]:
            self.servers[server.id]["emotes"] = dict()
        dataIO.save_json(self.data_path, self.servers)
        # for a toggle, settings should save here in case bot fails to send message
        if self.servers[server.id]["status"]:
            await self.bot.say('Emotes on. Please turn this off in the Red - DiscordBot server.'
                               ' This is only an example cog.')
        else:
            await self.bot.say('Emotes off.')

    @emotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def add(self, ctx, name, url):
        """Allows you to add emotes to the emote list
        [p]emotes add pan http://i.imgur.com/FFRjKBW.gifv"""
        server = ctx.message.server
        name = name.lower()
        option = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
                                '(KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}
        if server.id not in self.servers:
            # default off
            self.servers[server.id] = dict({"status": False})
            if "emotes" not in self.servers[server.id]:
                self.servers[server.id]["emotes"] = dict()
            dataIO.save_json(self.data_path, self.servers)
        if not url.endswith((".gif", ".gifv", ".png")):
            await self.bot.say("Links ending in .gif, .png, and .gifv are the only ones accepted."
                               "Please try again with a valid emote link, thanks.")
            return
        if name in self.servers[server.id]["emotes"]:
            await self.bot.say("This keyword already exists, please use another keyword.")
            return
        if url.endswith(".gifv"):
            url = url.replace(".gifv", ".gif")
        try:
            await self.bot.say("Downloading {}.".format(name))
            async with aiohttp.get(url, headers=option) as r:
                emote = await r.read()
                with open(self.emote+"{}.{}".format(name, url[-3:]), 'wb') as f:
                    f.write(emote)
                await self.bot.say("Adding {} to the list.".format(name))
                self.servers[server.id]["emotes"][name] = "{}.{}".format(name, url[-3:])
                self.servers[server.id]["emotes"]
            dataIO.save_json(self.data_path, self.servers)
            await self.bot.say("{} has been added to the list".format(name))
        except Exception as e:
            print(e)
            await self.bot.say("It seems your url is not valid,"
                               " please make sure you are not typing names with spaces as they are and then the url."
                               " If so, do [p]emotes add name_with_spaces url")

    @emotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def remove(self, ctx, name):
        """Allows you to remove emotes from the emotes list"""
        server = ctx.message.server
        name = name.lower()
        try:
            if server.id not in self.servers:
                # default off
                self.servers[server.id] = dict({"status": False})
                if "emotes" not in self.servers[server.id]:
                    self.servers[server.id]["emotes"] = dict()
                dataIO.save_json(self.data_path, self.servers)
            if name in self.servers[server.id]["emotes"]:
                os.remove(self.emote+self.servers[server.id]["emotes"][name])
                del self.servers[server.id]["emotes"][name]
            else:
                await self.bot.say("{} is not a valid name, please make sure the name of the"
                                   " emote that you want to remove actually exists."
                                   " Use [p]emotes list to verify it's there.".format(name))
                return
            dataIO.save_json(self.data_path, self.servers)
            await self.bot.say("{} has been removed from the list".format(name))
        except FileNotFoundError:
            await self.bot.say("For some unknown reason, your emote is not available in the default directory"
                               ", that is, data/emote/images. This means that it can't be removed. "
                               "But it has been successfully removed from the emotes list.")

    @emotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def edit(self, ctx, name, newname):
        """Allows you to edit the keyword that triggers the emote
         from the emotes list"""
        server = ctx.message.server
        name = name.lower()
        if server.id not in self.servers:
            # default off
            self.servers[server.id] = dict({"status": False})
            if "emotes" not in self.servers[server.id]:
                self.servers[server.id]["emotes"] = dict()
            dataIO.save_json(self.data_path, self.servers)
        if newname in self.servers[server.id]["emotes"]:
            await self.bot.say("This keyword already exists, please use another keyword.")
            return
        try:
            emotes = self.servers[server.id]["emotes"]
            if name in emotes:
                emotes[newname] = "{}.{}".format(newname, emotes[name][-3:])
                os.rename(self.emote+emotes[name],
                          self.emote+emotes[newname])
                del emotes[name]
            else:
                await self.bot.say("{} is not a valid name, please make sure the name of the"
                                   " emote that you want to edit exists"
                                   " Use [p]emotes list to verify it's there.".format(name))
                return
            dataIO.save_json(self.data_path, self.servers)
            await self.bot.say("{} in the emotes list has been renamed to {}".format(name, newname))
        except FileNotFoundError:
            await self.bot.say("For some unknown reason, your emote is not available in the default directory,"
                               " that is, data/emote/images. This means that it can't be edited."
                               " But it has been successfully edited in the emotes list.")

    @emotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def list(self, ctx, style):
        """Shows you the emotes list.
        Supported styles: [p]emotes list 10 (shows 10 emotes per page)
        and [p]emotes list a (shows all the emotes beginning with a)"""
        server = ctx.message.server
        style = style.lower()
        istyles = sorted(self.servers[server.id]["emotes"])
        if server.id not in self.servers:
            # default off
            self.servers[server.id] = dict({"status": False})
            if "emotes" not in self.servers[server.id]:
                self.servers[server.id]["emotes"] = dict()
            dataIO.save_json(self.data_path, self.servers)
        if not istyles:
            await self.bot.say("Your emotes list is empty."
                               " Please add a few emotes using the [p]emote add function.")
            return
        if style.isdigit():
            if style == "0":
                await self.bot.say("Only numbers from 1 to infinite are accepted.")
                return
            style = int(style)
            istyle = istyles
        elif style.isalpha():
            istyle = []
            for i in range(len(istyles)):
                ist = re.findall("\\b"+style+"\\w+", istyles[i])
                istyle = istyle + ist
            style = 10
        else:
            await self.bot.say("Your list style is not correct, please use one"
                               " of the accepted styles, either do [p]emotes list A or [p]emotes list 10")
            return
        s = "\n"
        count = style
        counter = len(istyle) + count
        while style <= counter:
            if style <= count:
                y = s.join(istyle[:style])
                await self.bot.say("List of available emotes:\n{}".format(y))
                if style > len(istyle):
                    return
                style += count
            elif style > count:
                style2 = style - count
                y = s.join(istyle[style2:style])
                await self.bot.say("Continuation:\n{}".format(y))
                if style > len(istyle):
                    return
                style += count
            await self.bot.say("Do you want to continue seeing the list? Yes/No")
            answer = await self.bot.wait_for_message(timeout=15,
                                                     author=ctx.message.author)
            if answer is None:
                return
            elif answer.content.lower().strip() == "yes":
                continue
            else:
                return

    @emotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def compare(self, ctx, style, alls: str=None):
        """Allows you to compare keywords to files
        or files to keywords and then make sure that
        they all coincide.
        Keywords to Files name: K2F
        Files to Keywords name: F2K
        [p]emotes compare K2F
        [p]emotes compare K2F all
        [p]emotes compare F2K all"""
        server = ctx.message.server
        style = style.lower()
        if alls is not None:
            alls = alls.lower()
        styleset = ["k2f", "f2k"]
        if server.id not in self.servers:
            # default off
            self.servers[server.id] = dict({"status": False})
            if "emotes" not in self.servers[server.id]:
                self.servers[server.id]["emotes"] = dict()
            dataIO.save_json(self.data_path, self.servers)
        if style not in styleset:
            return
        msg = "Keywords deleted due to missing files in the emotes list:\n"
        c = list()
        for entry in os.scandir(self.emote):
            c.append(entry.name)
        if style == styleset[0]:
            if alls == "all":
                servers = sorted(self.servers)
                servers.remove("emote")
                for servs in servers:
                    missing = list()
                    istyles = sorted(self.servers[servs]["emotes"])
                    for n in istyles:
                        cat = "|".join(c)
                        if not n[0].isalnum():
                            z = re.compile(r"\B"+n+r"\b")
                        else:
                            z = re.compile(r"\b"+n+r"\b")
                        if z.search(cat) is None:
                            missing.append(n)
                    if not missing:
                        await self.bot.say("All files and keywords are accounted for in " + servs)
                        if len(servers) == servers.index(servs):
                            return
                        else:
                            continue
                    for m in missing:
                        if m in self.servers[servs]["emotes"]:
                            del self.servers[servs]["emotes"][m]
                    dataIO.save_json(self.data_path, self.servers)
                    s = "\n"
                    style = 10
                    counter = len(missing) + 10
                    while style <= counter:
                        if style <= 10:
                            y = s.join(missing[:style])
                            await self.bot.say(msg + y)
                            if style >= len(missing):
                                break
                            style += 10
                        elif style > 10:
                            style2 = style - 10
                            y = s.join(missing[style2:style])
                            await self.bot.say("Continuation:\n{}".format(y))
                            if style >= len(missing):
                                break
                            style += 10
                        await self.bot.say("Do you want to continue seeing the list? Yes/No")
                        answer = await self.bot.wait_for_message(timeout=15,
                                                                 author=ctx.message.author)
                        if answer is None:
                            break
                        elif answer.content.lower().strip() == "yes":
                            continue
                        else:
                            break
            else:
                istyles = sorted(self.servers[server.id]["emotes"])
                for n in istyles:
                    cat = "|".join(c)
                    if not n[0].isalnum():
                        z = re.compile(r"\B"+n+r"\b")
                    else:
                        z = re.compile(r"\b"+n+r"\b")
                    if z.search(cat) is None:
                        missing.append(n)
                if not missing:
                    await self.bot.say("All files and keywords are accounted for")
                    return
                for m in missing:
                    if m in self.servers[server.id]["emotes"]:
                        del self.servers[server.id]["emotes"][m]
                dataIO.save_json(self.data_path, self.servers)
                s = "\n"
                style = 10
                counter = len(missing) + 10
                while style <= counter:
                    if style <= 10:
                        y = s.join(missing[:style])
                        await self.bot.say(msg + y)
                        if style >= len(missing):
                            return
                        style += 10
                    elif style > 10:
                        style2 = style - 10
                        y = s.join(missing[style2:style])
                        await self.bot.say("Continuation:\n{}".format(y))
                        if style >= len(missing):
                            return
                        style += 10
                    await self.bot.say("Do you want to continue seeing the list? Yes/No")
                    answer = await self.bot.wait_for_message(timeout=15,
                                                             author=ctx.message.author)
                    if answer is None:
                        return
                    elif answer.content.lower().strip() == "yes":
                        continue
                    else:
                        return

        elif style == styleset[1]:
            if alls == "all":
                servers = sorted(self.servers)
                servers.remove("emote")
                if not c:
                    await self.bot.say("It is impossible to verify the integrity of files and "
                                       "keywords due to missing files. Please make sure that the"
                                       " files have not been deleted.")
                    return
                for servs in servers:
                    count = 0
                    for cat in c:
                        if cat.endswith(".png"):
                            listing = cat.split('.png')
                            dog = len(listing)-1
                            del listing[dog]
                            listing.append(".png")
                        elif cat.endswith(".gif"):
                            listing = cat.split('.gif')
                            dog = len(listing)-1
                            del listing[dog]
                            listing.append(".gif")
                        if listing[0] not in self.servers[servs]["emotes"]:
                            self.servers[servs]["emotes"][listing[0]] = cat
                            count += 1
                    if count == 0:
                        await self.bot.say("All files and keywords are accounted for in " + servs)
                        if len(servers) == servers.index(servs):
                            return
                        else:
                            continue
                    dataIO.save_json(self.data_path, self.servers)
                    await self.bot.say(str(count) + " Keywords have been successfully added to the image list in "
                                       + servs)
            else:
                if not c:
                    await self.bot.say("It is impossible to verify the integrity of files and "
                                       "keywords due to missing files. Please make sure that the"
                                       " files have not been deleted.")
                    return
                count = 0
                for cat in c:
                    listing = cat.split('.')
                    if listing[0] not in self.servers[server.id]["emotes"]:
                        self.servers[server.id]["emotes"][listing[0]] = cat
                        count += 1
                if count == 0:
                    await self.bot.say("All files and keywords are accounted for")
                    return
                dataIO.save_json(self.data_path, self.servers)
                await self.bot.say(str(count) + " Keywords have been successfully added to the image list")

    async def check_emotes(self, message):
        # check if setting is on in this server
        # Let emotes happen in PMs always
        server = message.server

        # Filter unauthorized users, bots and empty messages
        if not (self.bot.user_allowed(message) and message.content):
            return

        # Don't respond to commands
        for m in self.bot.settings.get_prefixes(server):
            if message.content.startswith(m):
                return

        if server is not None:
            if server.id not in self.servers:
                # default off
                self.servers[server.id] = dict({"status": False})
                if "emotes" not in self.servers[server.id]:
                    self.servers[server.id]["emotes"] = dict()
                dataIO.save_json(self.data_path, self.servers)
            # emotes is off, so ignore
            if "status" not in self.servers[server.id]:
                self.servers[server.id] = dict({"status": False})
                if "emotes" not in self.servers[server.id]:
                    self.servers[server.id]["emotes"] = dict()
                dataIO.save_json(self.data_path, self.servers)
            if not self.servers[server.id]["status"]:
                return

        msg = message.content.lower().split()
        listed = []
        regexen = []
        for n in sorted(self.servers[server.id]["emotes"]):
            if not n[0].isalnum():
                regexen.append(re.compile(r"\B"+n+r"\b"))
            else:
                regexen.append(re.compile(r"\b"+n+r"\b"))

        for w, r in itertools.product(msg, regexen):
            match = r.search(w)
            if match:
                listed.append(self.servers[server.id]["emotes"][match.group(0)])

        pnglisted = list(filter(lambda n: not n.endswith('.gif'), listed))
        giflisted = list(filter(lambda n: n.endswith('.gif'), listed))
        if pnglisted and len(pnglisted) > 1:
            ims = self.imgprocess(pnglisted)
            await self.bot.send_file(message.channel, self.emote+ims)
        elif pnglisted:
            await self.bot.send_file(message.channel, self.emote+pnglisted[0])
        if giflisted:
            for ims in giflisted:
                await self.bot.send_file(message.channel, self.emote+ims)

    def imgprocess(self, listed):
        for i in range(len(listed)):
            listed[i] = self.emote + listed[i]
        images = [Image.open(i) for i in listed]
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths)
        max_height = max(heights)
        new_im = Image.new("RGBA", (total_width, max_height))
        x_offset = 0
        for im in images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]
        cat = "test.png"
        new_im.save("data/emote/images/" + cat)
        return cat


def check_folders():
    # create data/emote if not there
    if not os.path.exists('data/emote/images'):
        print('Creating data/emote/images folder...')
        os.mkdir('data/emote')
        os.mkdir('data/emote/images')


def check_files():
    # create server.json if not there
    # put in default values
    default = {}
    default['emote'] = 'data/emote/images/'
    if not os.path.isfile('data/emote/servers.json'):
        print('Creating default emote servers.json...')
        dataIO.save_json('data/emote/servers.json', default)


def setup(bot):
    if PIL:
        check_folders()
        check_files()
        n = Emote(bot)
        # add an on_message listener
        bot.add_listener(n.check_emotes, 'on_message')
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to run 'pip3 install Pillow'")
