import discord
from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import box
from cogs.utils import checks
from __main__ import send_cmd_help
import logging
import os
try:
    import tabulate
except:
    tabulate = None


log = logging.getLogger("marvin.karma")


class Karma:
    """Keep track of user scores through @mention ++/--

    Example: ++ @\u200BWill (or @\u200BWill ++)"""

    def __init__(self, bot):
        self.bot = bot
        self.scores = fileIO("data/karma/scores.json", "load")
        self.settings = fileIO("data/karma/settings.json", 'load')

    def _process_scores(self, member, score_to_add):
        member_id = member.id
        if member_id in self.scores:
            if "score" in self.scores.get(member_id, {}):
                self.scores[member_id]["score"] += score_to_add
            else:
                self.scores[member_id]["score"] = score_to_add
        else:
            self.scores[member_id] = {}
            self.scores[member_id]["score"] = score_to_add

    def _add_reason(self, member_id, reason):
        if reason.lstrip() == "":
            return
        if member_id in self.scores:
            if "reasons" in self.scores.get(member_id, {}):
                old_reasons = self.scores[member_id].get("reasons", [])
                new_reasons = [reason] + old_reasons[:4]
                self.scores[member_id]["reasons"] = new_reasons
            else:
                self.scores[member_id]["reasons"] = [reason]
        else:
            self.scores[member_id] = {}
            self.scores[member_id]["reasons"] = [reason]

    def _fmt_reasons(self, reasons):
        if len(reasons) == 0:
            return None
        ret = "```Latest Reasons:\n"
        for num, reason in enumerate(reasons):
            ret += "\t" + str(num + 1) + ") " + str(reason) + "\n"
        return ret + "```"

    @commands.command(pass_context=True)
    async def karma(self, ctx):
        """Checks a user's karma, requires @ mention

           Example: !karma @MARViN"""
        if len(ctx.message.mentions) != 1:
            await send_cmd_help(ctx)
            return
        member = ctx.message.mentions[0]
        if self.scores.get(member.id, 0) != 0:
            member_dict = self.scores[member.id]
            await self.bot.say(member.name + " has " +
                               str(member_dict["score"]) + " points!")
            reasons = self._fmt_reasons(member_dict.get("reasons", []))
            if reasons:
                await self.bot.send_message(ctx.message.author, reasons)
        else:
            await self.bot.say(member.name + " has no karma!")

    @commands.command(pass_context=True)
    async def karmaboard(self, ctx):
        """Karma leaderboard"""
        server = ctx.message.server
        member_ids = [m.id for m in server.members]
        karma_server_members = [key for key in self.scores.keys()
                                if key in member_ids]
        log.debug("Karma server members:\n\t{}".format(
            karma_server_members))
        names = list(map(lambda mid: discord.utils.get(server.members, id=mid),
                         karma_server_members))
        log.debug("Names:\n\t{}".format(names))
        scores = list(map(lambda mid: self.scores[mid]["score"],
                          karma_server_members))
        log.debug("Scores:\n\t{}".format(scores))
        headers = ["User", "Karma"]
        body = sorted(zip(names, scores), key=lambda tup: tup[1],
                      reverse=True)[:10]
        table = tabulate.tabulate(body, headers, tablefmt="psql")
        await self.bot.say(box(table))

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def karmaset(self, ctx):
        """Manage karma settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @karmaset.command(pass_context=True, name="respond")
    async def _karmaset_respond(self, ctx):
        """Toggles if bot will respond when points get added/removed"""
        if self.settings['RESPOND_ON_POINT']:
            await self.bot.say("Responses disabled.")
        else:
            await self.bot.say('Responses enabled.')
        self.settings['RESPOND_ON_POINT'] = \
            not self.settings['RESPOND_ON_POINT']
        fileIO('data/karma/settings.json', 'save', self.settings)

    async def check_for_score(self, message):
        user = message.author
        content = message.content
        mentions = message.mentions
        if message.author.id == self.bot.user.id:
            return
        splitted = content.split(" ")
        if len(splitted) > 1:
            if "++" == splitted[0] or "--" == splitted[0]:
                first_word = "".join(splitted[:2])
            elif "++" == splitted[1] or "--" == splitted[1]:
                first_word = "".join(splitted[:2])
            else:
                first_word = splitted[0]
        else:
            first_word = splitted[0]
        reason = content[len(first_word) + 1:]
        for member in mentions:
            if member.id in first_word.lower():
                if "++" in first_word.lower() or "--" in first_word.lower():
                    if member == user:
                        await self.bot.send_message(message.channel,
                                                    "You can't modify your own"
                                                    " rep, jackass.")
                        return
                if "++" in first_word.lower():
                    self._process_scores(member, 1)
                    self._add_reason(member.id, reason)
                elif "--" in first_word.lower():
                    self._process_scores(member, -1)
                    self._add_reason(member.id, reason)
                else:
                    return

                if self.settings['RESPOND_ON_POINT']:
                    msg = "{} now has {} points.".format(
                        member.name, self.scores[member.id]["score"])
                    await self.bot.send_message(message.channel, msg)
                fileIO("data/karma/scores.json", "save", self.scores)
                return


def check_folder():
    if not os.path.exists("data/karma"):
        print("Creating data/karma folder...")
        os.makedirs("data/karma")


def check_file():
    scores = {}
    settings = {"RESPOND_ON_POINT": True}

    f = "data/karma/scores.json"
    if not fileIO(f, "check"):
        print("Creating default karma's scores.json...")
        fileIO(f, "save", scores)

    f = "data/karma/settings.json"
    if not fileIO(f, "check"):
        print("Creating default karma's scores.json...")
        fileIO(f, "save", settings)


def setup(bot):
    if tabulate is None:
        raise RuntimeError("Run `pip install tabulate` to use Karma.")
    check_folder()
    check_file()
    n = Karma(bot)
    bot.add_listener(n.check_for_score, "on_message")
    bot.add_cog(n)
