# LOLspeak translator library
# Created by Stephen Newey
#
# Python stuff, copyright (c)2008 Stephen Newey
# Inspired by Dave Dribin's Ruby library lolspeak (http://www.dribin.org/dave/lolspeak/)
# tranzlator.yml dictionary by Dave Dribin
#
# python code licensed under the Mozilla Public License v1.1.
# http://www.mozilla.org/MPL/MPL-1.1.html
#
# downloaded from: https://code.google.com/archive/p/pylolz/

# Credit for idea/implementation: Will(@tekulvw) / Nikki(@cookiezeater) / Mash(@Canule) / irdumb(@irdumbs)

import asyncio

from discord.ext import commands
from .utils.dataIO import fileIO
import logging
import re
import os


log = logging.getLogger(__name__)
request_logging_format = '{method} {response.url} has returned {response.status}'
request_success_log = '{response.url} with {json} received {data}'


default_settings = {"SERVER": {"DEFAULT": False}}


class Lolz:
    """translates all text the bot speaks to lolcat"""

    # regex's edited from lolz
    def __init__(self, bot):
        self.bot = bot

        self.easy_regex = [
            (re.compile("(.*)ed$"), 'd'),
            (re.compile("(.*)ing$"), 'in'),
            (re.compile("(.*)ss$"), 's'),
            (re.compile("(.*)er$"), 'r'),
        ]

        # more complicated search/replace operations
        self.regex = {
            'apostrophy': re.compile('(?P<prefix>.*)(?P<suffix>[\']\w*)'),
            'tion': re.compile("(.*)tion(s?)$"),
            'stoz': re.compile("^([\w]+)s$"),
            'ous': re.compile("ous$"),
            'link': re.compile("https?://..")  # not the same as discord's
        }

        self.cached = {}
        self.settings = fileIO("data/lolz/settings.json", "load")
        self.tranzlashun = fileIO("data/lolz/tranzlashun.json", "load")

        # object independant send_message. do not overwrite
        # self.old_send = commands.Bot.send_message
        # self.old_send = self.bot.send_message

    @commands.command(pass_context=True, no_pm=True)
    async def lolz(self, ctx):
        """Toggle lolspeak for this server"""
        server = ctx.message.server
        if server.id not in self.settings["SERVER"]:
            self.settings["SERVER"][
                server.id] = default_settings["SERVER"]["DEFAULT"]
        self.settings["SERVER"][
            server.id] = not self.settings["SERVER"][server.id]
        if self.settings["SERVER"][server.id]:
            await self.bot.say("I will now lolz sentences.")
        else:
            await self.bot.say("I won't lolz sentences anymore.")
        fileIO("data/lolz/settings.json", "save", self.settings)

    # This is bad. If you're reading this, you're probably trying to find out how it does what it does.
    # Please head to Red's #testing/#coding channels and ask for help from the contributors listed above
    # We do not recommend doing this. If multiple cogs start doing this, things will be very messy and very buggy
    # We do not have a standard/protocol yet on how to communicate these changes between cogs. 
    # We will be very leery of doing so, as this is a BAD programming practice.
    # Again, speak to the contributors if you have questions. More notably, Will(@tekulvw)
    def send_lolz(self, old_send):
        async def predicate(destination, content, *args, **kwargs):
            channel_id = await self.bot._resolve_destination(destination)
            channel = self.bot.get_channel(channel_id)
            content = str(content)
            if not channel.is_private:
                # what about group friend things. might need to fix later. just
                # check if None now..
                server = channel.server
                # we aren't in PM or future group PM i hope
                if server is not None:
                    # if setting exists and is on
                    if self.settings["SERVER"].get(server.id, False):
                        # if not a link
                        if not re.findall(self.regex['link'], content):
                            content = self.translate_sentence(content).upper()
            # msg = await old_send(self.bot, destination, content, *args,
            # **kwargs)
            msg = await old_send(destination, content, *args, **kwargs)
            return msg

        predicate.old = old_send

        return predicate

    # add randomization from Nikki's link. see todo

    # code edited from lolz
    def translate_word(self, word):
        # don't LOLZ links
        # if re.findall(self.regex['link'], word):
        #     return word

        # lower case lolz pleaz, ph is pronounces f!
        word = word.lower()

        # easiest first, look in dictionary
        if word in self.tranzlashun:
            return self.tranzlashun[word]

        # fastest, check the cache...
        if word in self.cached:
            return self.cached[word]

        word = word.replace('ph', 'f')

        # not found, perhaps a possesive apostrophy or the like?
        if self.regex['apostrophy'].search(word):
            result = self.regex['apostrophy'].search(word).groupdict()
            if result['prefix'] in self.tranzlashun:
                self.cached[word] = '%s%s' % (
                    self.tranzlashun[result['prefix']], result['suffix'])
                return self.cached[word]

        # no matches? try heuristics unless we've been told otherwise
        # if self.heuristics is True:
        for regex, replace in self.easy_regex:
            match = regex.search(word)
            if match:
                self.cached[word] = match.group(1) + replace
                return self.cached[word]
        tion = self.regex['tion'].search(word)
        if tion:
            self.cached[word] = tion.group(1) + 'shun' + tion.group(2)
            return self.cached[word]
        stoz = self.regex['stoz'].search(word)
        if stoz and not self.regex['ous'].search(word):
            self.cached[word] = stoz.group(1) + 'z'
            return self.cached[word]

        # no matches, leave it alone!
        self.cached[word] = word
        return word

    # code edited from lolz
    def translate_sentence(self, sentence):
        new_sentence = ''
        # reminder to self...
        # ([\w]*) - match 0 or more a-zA-Z0-9_ group
        # ([\W]*) - match 0 or more non-(see above) group
        for word, space in re.findall("([\w]*)([\W]*)", sentence):
            word = self.translate_word(word)
            # if word != '':
            new_sentence += word + space
        return new_sentence

    async def lolz_oh_crap_revert(self):
        await asyncio.sleep(6)  # be safe lolz
        while "Lolz" in self.bot.cogs:
            # this checks if overwritten by same process(adding an old), undefined behavior if some other cog overwrites the same way.
            if not hasattr(self.bot.send_message, 'old'):
                print(
                    '[WARNING:] -- Overwriting bot.send_message with '
                    'send_lolz. If bot.send_message is not reloaded,')
                print(
                    '[WARNING:] -- in the event of a crash of the lolz cog, '
                    'you may not be able revert to bot.send_message without a '
                    'restart/reloading lolz')
                self.bot.send_message = self.send_lolz(self.bot.send_message)
            await asyncio.sleep(1)
        # revert any changes done with this method. we should check instead for only lolz override
        if hasattr(self.bot.send_message, 'old'):
            print('[CLEANUP:] -- Trying to reload old self.bot.send_message')
            self.bot.send_message = self.bot.send_message.old
            print(
                '[CLEANUP:] -- Done. Reloading should have been successful '
                'unless the lolz cog crashed without cleaning up')
            print(
                '[CLEANUP:] -- If that is the case, the bot may need to be '
                'restarted')


def check_folders():
    if not os.path.exists("data/lolz"):
        print("Creating lolz folder...")
        os.makedirs("data/lolz")


def check_files(bot):
    settings_path = "data/lolz/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default lolz settings.json...")
        fileIO(settings_path, "save", default_settings)


def setup(bot):
    check_folders()
    check_files(bot)
    n = Lolz(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.lolz_oh_crap_revert())
