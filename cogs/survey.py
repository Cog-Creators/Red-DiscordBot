import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import zip_longest
import os
from typing import Any, Dict, List

try:
    from dateutil import parser as dp
    dateutil_available = True
except:
    dateutil_available = False
import discord
from discord.ext import commands
try:
    import pytz
    pytz_available = True
except:
    pytz_available = False
try:
    from tabulate import tabulate
    tabulate_available = True
except:
    tabulate_available = False

from .utils.dataIO import dataIO
from .utils import checks, chat_formatting as cf


Option = Dict[str, Any]
Options = Dict[str, Option]


class PastDeadlineError(Exception):
    pass


class Survey:

    """Runs surveys for a specific role of people via DM,
    and prints real-time results to a given text channel.

    Supports changing responses, answer option quotas,
    and reminders based on initial answer.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.surveys_path = "data/survey/surveys.json"
        self.surveys = dataIO.load_json(self.surveys_path)
        self.tasks = defaultdict(list)

        self.bot.loop.create_task(self._resume_running_surveys())

    async def _resume_running_surveys(self):
        await self.bot.wait_until_ready()

        closed = self.surveys["closed"]

        for server_id in self.surveys:
            if server_id not in ["closed", "next_id"]:
                server = self.bot.get_server(server_id)
                for survey_id in self.surveys[server_id]:
                    if survey_id not in closed:
                        self._setup_reprompts(server_id, survey_id)
                        self._schedule_close(
                            server_id, survey_id, self._get_timeout(
                                self._deadline_string_to_datetime(
                                    self.surveys[server_id][survey_id]
                                    ["deadline"], adjust=False)))
                        await self._update_answers_message(
                            server_id, survey_id)
                        for uid in self.surveys[server_id][survey_id]["asked"]:
                            user = server.get_member(uid)
                            new_task = self.bot.loop.create_task(
                                self._send_message_and_wait_for_message(
                                    server_id, survey_id, user,
                                    send_question=False))
                            self.tasks[survey_id].append(new_task)

    def _member_has_role(self, member: discord.Member, role: discord.Role):
        return role in member.roles

    def _get_users_with_role(self, server: discord.Server,
                             role: discord.Role) -> List[discord.User]:
        roled = []
        for member in server.members:
            if (not member.bot) and self._member_has_role(member, role):
                roled.append(member)
        return roled

    def _deadline_string_to_datetime(self, deadline: str,
                                     adjust: bool=True) -> datetime:
        dl = dp.parse(deadline, tzinfos=tzd)
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=pytz.utc)

        to = self._get_timeout(dl)

        if adjust and -86400 < to < 0:
            dl += timedelta(days=1)
        elif to < -86400:
            raise PastDeadlineError()

        return dl

    def _get_timeout(self, deadline: datetime) -> int:
        return (deadline - datetime.utcnow().replace(
            tzinfo=pytz.utc)).total_seconds()

    def _mark_as_closed(self, survey_id: str):
        if not self.surveys["closed"]:
            self.surveys["closed"] = []

        closed = self.surveys["closed"]

        if survey_id not in closed:
            closed.append(survey_id)

        dataIO.save_json(self.surveys_path, self.surveys)

    async def _parse_options(self, options: str) -> Options:
        opts_list = None if options == "*" else [
            r.lower().strip() for r in options.split(";")]

        opts = {}
        if opts_list:
            opt_names = [o[0] for o in [op.split(":") for op in opts_list]]
            for opt in opts_list:
                opt_s = opt.split(":")
                if len(opt_s) == 1:
                    opts[opt_s[0]] = {
                        "limit": None, "reprompt": None, "link": None}
                elif len(opt_s) > 1:
                    if opt_s[1] == "":
                        opts[opt_s[0]] = {"limit": None}
                    else:
                        try:
                            int(opt_s[1])
                        except ValueError:
                            await self.bot.reply(cf.error(
                                "A limit you provided was not a number."))
                            return "return"
                        opts[opt_s[0]] = {"limit": opt_s[1]}

                if len(opt_s) > 2:
                    if opt_s[2] == "":
                        opts[opt_s[0]]["reprompt"] = None
                    else:
                        try:
                            int(opt_s[2])
                        except ValueError:
                            await self.bot.reply(cf.error(
                                "A reprompt value you provided was"
                                " not a number."))
                            return "return"
                        opts[opt_s[0]]["reprompt"] = int(opt_s[2]) * 60
                else:
                    opts[opt_s[0]]["reprompt"] = None

                if len(opt_s) == 4:
                    if opts[opt_s[0]]["reprompt"] is None:
                        await self.bot.reply(cf.error(
                            "You cannot link an option without giving a"
                            " reprompt value. Please try again."))
                        return "return"
                    if opt_s[3] == "":
                        opts[opt_s[0]]["link"] = None
                    else:
                        if opt_s[3] not in opt_names:
                            await self.bot.reply(cf.error(
                                "A link that you gave is not the name of"
                                " an option. Please try again."))
                            return "return"
                        opts[opt_s[0]]["link"] = opt_s[3]
                else:
                    opts[opt_s[0]]["link"] = None

        else:
            opts = None

        return opts

    def _save_deadline(self, server_id: str, survey_id: str, deadline: str):
        self.surveys[server_id][survey_id]["deadline"] = deadline
        dataIO.save_json(self.surveys_path, self.surveys)

    def _save_channel(self, server_id: str, survey_id: str, channel_id: str):
        self.surveys[server_id][survey_id]["channel"] = channel_id
        dataIO.save_json(self.surveys_path, self.surveys)

    def _save_question(self, server_id: str, survey_id: str, question: str):
        self.surveys[server_id][survey_id]["question"] = question
        dataIO.save_json(self.surveys_path, self.surveys)

    def _save_options(self, server_id: str, survey_id: str, options: Options):
        self.surveys[server_id][survey_id]["options"] = options
        self.surveys[server_id][survey_id]["answers"] = {}
        dataIO.save_json(self.surveys_path, self.surveys)

        if options != "any":
            for opt in options:
                self.surveys[server_id][survey_id]["answers"][opt] = []
                dataIO.save_json(self.surveys_path, self.surveys)

    def _save_asked(self, server_id: str, survey_id: str,
                    users: List[discord.User]):
        asked = [u.id for u in users]
        self.surveys[server_id][survey_id]["asked"] = asked
        dataIO.save_json(self.surveys_path, self.surveys)

    def _save_prefix(self, server_id: str, survey_id: str, prefix: str):
        self.surveys[server_id][survey_id]["prefix"] = prefix
        dataIO.save_json(self.surveys_path, self.surveys)

    def _save_answer(self, server_id: str, survey_id: str, user: discord.User,
                     answer: str, change: bool) -> bool:
        answers = self.surveys[server_id][survey_id]["answers"]
        asked = self.surveys[server_id][survey_id]["asked"]
        options = self.surveys[server_id][survey_id]["options"]

        if change:
            for a in answers.values():
                if user.id in a:
                    a.remove(user.id)

        if options != "any":
            limit = options[answer]["limit"]

        if answer not in answers:
            answers[answer] = []

        if answer in options and limit and len(answers[answer]) >= int(limit):
            return False

        answers[answer].append(user.id)
        if user.id in asked:
            asked.remove(user.id)
        dataIO.save_json(self.surveys_path, self.surveys)
        return True

    def _setup_reprompts(self, server_id: str, survey_id: str):
        options = self.surveys[server_id][survey_id]["options"]
        if options == "any":
            return

        timeout = self._get_timeout(self._deadline_string_to_datetime(
            self.surveys[server_id][survey_id]["deadline"]))

        for optname, settings in options.items():
            if settings["reprompt"]:
                new_handle = None
                if settings["link"]:
                    new_handle = self.bot.loop.call_later(
                        timeout - settings["reprompt"], self._check_reprompt,
                        server_id, survey_id, optname, settings["link"])
                else:
                    new_handle = self.bot.loop.call_later(
                        timeout - settings["reprompt"], self._check_reprompt,
                        server_id, survey_id, optname)
                self.tasks[survey_id].append(new_handle)

    def _check_reprompt(self, server_id: str, survey_id: str, option_name: str,
                        link_name: str=None):
        answers = self.surveys[server_id][survey_id]["answers"]
        options = self.surveys[server_id][survey_id]["options"]

        if (link_name and
                len(answers[link_name]) == int(options[link_name]["limit"])):
            return

        for uid in answers[option_name]:
            user = self.bot.get_server(server_id).get_member(uid)
            new_task = self.bot.loop.create_task(
                self._send_message_and_wait_for_message(
                    server_id, survey_id, user, change=True,
                    rp_opt=option_name))
            self.tasks[survey_id].append(new_task)

    async def _update_answers_message(self, server_id: str, survey_id: str):
        question = self.surveys[server_id][survey_id]["question"]
        channel_id = self.surveys[server_id][survey_id]["channel"]
        channel = self.bot.get_channel(channel_id)
        table = self._make_answer_table(server_id, survey_id)
        waiting = self._make_waiting_list(server_id, survey_id)

        if "messages" not in self.surveys[server_id][survey_id]:
            self.surveys[server_id][survey_id]["messages"] = {}

        if "results" not in self.surveys[server_id][survey_id]["messages"]:
            res_message = await self.bot.send_message(
                channel,
                "{} (ID {})\n{}"
                .format(cf.bold(question), survey_id, cf.box(table)))
            self.surveys[server_id][survey_id][
                "messages"]["results"] = res_message.id

            if waiting:
                wait_message = await self.bot.send_message(
                    channel,
                    "{}\n{}".format("Awaiting answers from:", cf.box(waiting)))
                self.surveys[server_id][survey_id][
                    "messages"]["waiting"] = wait_message.id

            dataIO.save_json(self.surveys_path, self.surveys)
        else:
            res_message = await self.bot.edit_message(
                await self.bot.get_message(
                    channel,
                    self.surveys[server_id][survey_id]["messages"]["results"]),
                "{} (ID {})\n{}"
                .format(cf.bold(question), survey_id, cf.box(table)))
            self.surveys[server_id][survey_id][
                "messages"]["results"] = res_message.id
            if waiting:
                wait_message = await self.bot.edit_message(
                    await self.bot.get_message(
                        channel,
                        self.surveys[server_id][survey_id]["messages"]
                        ["waiting"]),
                    "{}\n{}"
                    .format("Waiting on answers from:", cf.box(waiting)))
                self.surveys[server_id][survey_id][
                    "messages"]["waiting"] = wait_message.id
            elif (self.surveys[server_id][survey_id]["messages"]["waiting"]
                  is not None):
                await self.bot.delete_message(
                    await self.bot.get_message(
                        channel,
                        self.surveys[server_id][survey_id]["messages"]
                        ["waiting"]))
                self.surveys[server_id][survey_id][
                    "messages"]["waiting"] = None

            dataIO.save_json(self.surveys_path, self.surveys)

    def _make_answer_table(self, server_id: str, survey_id: str) -> str:
        server = self.bot.get_server(server_id)
        answers = sorted(self.surveys[server_id][survey_id]["answers"].items())
        rows = list(zip_longest(
            *[[server.get_member(y).display_name for y in x[1]
               if server.get_member(y) is not None] for x in answers]))
        headers = [x[0] for x in answers]
        return tabulate(rows, headers, tablefmt="orgtbl")

    def _make_waiting_list(self, server_id: str, survey_id: str) -> str:
        server = self.bot.get_server(server_id)
        return ", ".join(sorted(
            [server.get_member(m).display_name
             for m in self.surveys[server_id][survey_id]["asked"]
             if server.get_member(m) is not None]))

    def _get_server_id_from_survey_id(self, survey_id):
        for server_id, survey_ids in [
                (ser, sur) for (ser, sur) in self.surveys.items()
                if ser not in ["next_id", "closed"]]:
            if survey_id in survey_ids:
                return server_id
        return None

    def _schedule_close(self, server_id: str, survey_id: str, delay: int):
        new_handle = self.bot.loop.call_later(
            delay, self._mark_as_closed, survey_id)
        self.tasks[survey_id].append(new_handle)

    async def _send_message_and_wait_for_message(self, server_id: str,
                                                 survey_id: str,
                                                 user: discord.User,
                                                 change: bool=False,
                                                 rp_opt: str=None,
                                                 send_question: bool=True):
        try:
            prefix = self.surveys[server_id][survey_id]["prefix"]
            question = self.surveys[server_id][survey_id]["question"]
            deadline_hr = self.surveys[server_id][survey_id]["deadline"]
            deadline = self._deadline_string_to_datetime(deadline_hr)
            options = self.surveys[server_id][survey_id]["options"]
            options_hr = "any" if options == "any" else "/".join(
                options.keys())
            achannel_id = self.surveys[server_id][survey_id]["channel"]
            achannel = self.bot.get_channel(achannel_id)

            if rp_opt:
                options_hr = options_hr.replace(
                    rp_opt, cf.strikethrough(rp_opt))

            rp_mes = "(You previously answered {}, but are being asked again."
            " You may not answer the same as last time, but if you do not wish"
            " to change your answer, you may ignore this message.)".format(
                cf.bold(rp_opt) if rp_opt else "")

            premsg = "A new survey has been posted! (ID {})\n".format(
                survey_id)
            if change or rp_opt:
                premsg = ""

            if send_question:
                await self.bot.send_message(user, premsg + cf.question(
                    "{} *[deadline {}]*\n(options: {}){}".format(
                        cf.bold(question), deadline_hr, options_hr,
                        ("\n"+rp_mes) if rp_opt else "")))

            channel = await self.bot.start_private_message(user)

            answer = None
            while not answer:
                r = (await self.bot.wait_for_message(channel=channel,
                                                     timeout=self._get_timeout(
                                                         deadline),
                                                     author=user))
                if r is None:
                    break
                r = r.content.lower().strip()
                if rp_opt and r == rp_opt:
                    await self.bot.send_message(
                        user,
                        cf.warning(
                            "You are be asked again, and may not choose the"
                            " same answer as last time.\nPlease choose one of"
                            " the other available options: ({})".format(
                                options_hr)))
                elif options == "any" or r in options:
                    answer = r
                else:
                    await self.bot.send_message(
                        user,
                        cf.warning(
                            "Please choose one of the available options: ({})"
                            .format(cf.bold(options_hr))))

            if not answer:
                await self.bot.send_message(
                    user,
                    cf.info("Survey {} is now closed.".format(survey_id)))
            else:
                if not self._save_answer(
                        server_id, survey_id, user, answer, change):
                    await self.bot.send_message(
                        user,
                        cf.warning(
                            "That answer has reached its limit. Answer could"
                            " not be {}. To try again, use `{}changeanswer {}`"
                            " in this DM.".format(
                                "changed" if change else "recorded",
                                prefix, survey_id)))
                    return
                await self._update_answers_message(server_id, survey_id)
                await self.bot.send_message(
                    user,
                    cf.info(
                        "Answer {}. If you want to change it, use"
                        " `{}changeanswer {}` in this DM.\nYou can see all the"
                        " answers in {}.".format(
                            "changed" if change else "recorded",
                            prefix, survey_id, achannel.mention)))
        except asyncio.CancelledError:
            await self.bot.send_message(
                user,
                cf.info("Survey {} has been closed.".format(survey_id)))
        except discord.Forbidden:
            return

    @commands.command(pass_context=True, no_pm=True, name="startsurvey")
    @checks.admin_or_permissions(administrator=True)
    async def _startsurvey(self, ctx: commands.Context,
                           role: discord.Role, channel: discord.Channel,
                           question: str, options: str, *, deadline: str):
        """Starts a new survey.
        Role is the Discord server role to notify. Should be the @<role>.
        Channel is the channel in which to post results. Should be #<channel>
        Question is the survey question.
        Options should be a semicolon-separated list of options, or * to allow any option.
        Each option is of the format <name>:<limit>:<reprompt>:<link>, where everything but <name> is optional, i.e. the simplest form is <opt1>;<opt2>;...
            <name> is the name of the option.
            <limit> is the maximum number of answers that are this option.
            <reprompt> is the time, in minutes, before the deadline to reprompt those who answered with this option.
            <link> is the name of a different option. If set, reprompt will only happen if the given option has not hit its limit of responses. Requires that <reprompt> is set.
        Deadline should be of a sane time format, date optional, but timezone abbreviation is strongly recommended (otherwise UTC is assumed).

        For example: [p]startsurvey everyone channel_name "Question here. Which should be enclosed in double quotes because it includes SPACES" "Yes;No;Options enclosed with double quotes too, if contain SPACES" 2016/12/25 12:00
        """

        server = ctx.message.server

        if server.id not in self.surveys:
            self.surveys[server.id] = {}
            dataIO.save_json(self.surveys_path, self.surveys)

        try:
            dl = self._deadline_string_to_datetime(deadline)
            deadline_better = dl.strftime("%m/%d/%Y %I:%S%p %Z")
        except ValueError:
            await self.bot.reply(cf.error(
                "Your deadline format could not be understood."
                " Please try again."))
            return
        except PastDeadlineError:
            await self.bot.reply(cf.error(
                "Your deadline is in the past."))
            return

        opts = await self._parse_options(options)
        if opts == "return":
            return

        new_survey_id = str(self.surveys["next_id"])
        self.surveys["next_id"] += 1
        dataIO.save_json(self.surveys_path, self.surveys)

        self.surveys[server.id][new_survey_id] = {}
        dataIO.save_json(self.surveys_path, self.surveys)

        self._save_prefix(server.id, new_survey_id, ctx.prefix)
        self._save_deadline(server.id, new_survey_id, deadline_better)
        self._save_channel(server.id, new_survey_id, channel.id)
        self._save_question(server.id, new_survey_id, question)
        self._save_options(server.id, new_survey_id, opts if opts else "any")

        self._setup_reprompts(server.id, new_survey_id)

        self._schedule_close(server.id, new_survey_id, self._get_timeout(dl))

        users_with_role = self._get_users_with_role(server, role)
        self._save_asked(server.id, new_survey_id, users_with_role)

        try:
            await self._update_answers_message(server.id, new_survey_id)
        except discord.Forbidden:
            await self.bot.reply(
                "I do not have permission to talk in {}.".format(
                    channel.mention))
            return

        for user in users_with_role:
            new_task = self.bot.loop.create_task(
                self._send_message_and_wait_for_message(server.id,
                                                        new_survey_id, user))
            self.tasks[new_survey_id].append(new_task)

        await self.bot.reply(cf.info("Survey started. You can close it with"
                                     " `{}closesurvey {}`.".format(
                                         ctx.prefix, new_survey_id)))

    @commands.command(pass_context=True, no_pm=True, name="closesurvey")
    @checks.admin_or_permissions(administrator=True)
    async def _closesurvey(self, ctx: commands.Context,
                           survey_id: str):
        """Cancels the given survey."""

        server = ctx.message.server
        surver = self._get_server_id_from_survey_id(survey_id)

        if not surver or server.id != surver:
            await self.bot.reply(cf.error("Survey with ID {} not found."
                                          .format(survey_id)))
            return

        if survey_id in self.surveys["closed"]:
            await self.bot.reply(cf.warning(
                "Survey with ID {} is already closed.".format(survey_id)))
            return

        if survey_id in self.tasks:
            for t in self.tasks[survey_id]:
                t.cancel()
            del self.tasks[survey_id]

        self._mark_as_closed(survey_id)

        await self.bot.reply(cf.info("Survey with ID {} closed."
                                     .format(survey_id)))

    @commands.command(pass_context=True, no_pm=False, name="changeanswer")
    async def _changeanswer(self, ctx: commands.Context,
                            survey_id: str):
        """Changes the calling user's response for the given survey."""
        user = ctx.message.author
        server_id = self._get_server_id_from_survey_id(survey_id)

        if survey_id in self.surveys["closed"]:
            await self.bot.send_message(user,
                                        cf.error("That survey is closed."))
            return

        if not server_id:
            await self.bot.send_message(user, cf.error(
                "Survey with ID {} not found.".format(survey_id)))
            return

        new_task = self.bot.loop.create_task(
            self._send_message_and_wait_for_message(server_id,
                                                    survey_id, user,
                                                    change=True))
        self.tasks[survey_id].append(new_task)


def check_folders():
    if not os.path.exists("data/survey"):
        print("Creating data/survey directory...")
        os.makedirs("data/survey")


def check_files():
    f = "data/survey/surveys.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/survey/surveys.json...")
        dataIO.save_json(f, {"next_id": 1, "closed": []})


def setup(bot: commands.Bot):
    check_folders()
    check_files()

    if dateutil_available:
        if pytz_available:
            if tabulate_available:
                bot.add_cog(Survey(bot))
            else:
                raise RuntimeError(
                    "You need to install `tabulate`: `pip install tabulate`.")
        else:
            raise RuntimeError(
                "You need to install `pytz`: `pip install pytz`.")
    else:
        raise RuntimeError(
            "You need to install `python-dateutil`:"
            " `pip install python-dateutil`.")

tz_str = """-12 Y
-11 X NUT SST
-10 W CKT HAST HST TAHT TKT
-9 V AKST GAMT GIT HADT HNY
-8 U AKDT CIST HAY HNP PST PT
-7 T HAP HNR MST PDT
-6 S CST EAST GALT HAR HNC MDT
-5 R CDT COT EASST ECT EST ET HAC HNE PET
-4 Q AST BOT CLT COST EDT FKT GYT HAE HNA PYT
-3 P ADT ART BRT CLST FKST GFT HAA PMST PYST SRT UYT WGT
-2 O BRST FNT PMDT UYST WGST
-1 N AZOT CVT EGT
0 Z EGST GMT UTC WET WT
1 A CET DFT WAT WEDT WEST
2 B CAT CEDT CEST EET SAST WAST
3 C EAT EEDT EEST IDT MSK
4 D AMT AZT GET GST KUYT MSD MUT RET SAMT SCT
5 E AMST AQTT AZST HMT MAWT MVT PKT TFT TJT TMT UZT YEKT
6 F ALMT BIOT BTT IOT KGT NOVT OMST YEKST
7 G CXT DAVT HOVT ICT KRAT NOVST OMSST THA WIB
8 H ACT AWST BDT BNT CAST HKT IRKT KRAST MYT PHT SGT ULAT WITA WST
9 I AWDT IRKST JST KST PWT TLT WDT WIT YAKT
10 K AEST ChST PGT VLAT YAKST YAPT
11 L AEDT LHDT MAGT NCT PONT SBT VLAST VUT
12 M ANAST ANAT FJT GILT MAGST MHT NZST PETST PETT TVT WFT
13 FJST NZDT
11.5 NFT
10.5 ACDT LHST
9.5 ACST
6.5 CCT MMT
5.75 NPT
5.5 SLT
4.5 AFT IRDT
3.5 IRST
-2.5 HAT NDT
-3.5 HNT NST NT
-4.5 HLV VET
-9.5 MART MIT"""

tzd = {}
for tz_descr in map(str.split, tz_str.split('\n')):
    tz_offset = int(float(tz_descr[0]) * 3600)
    for tz_code in tz_descr[1:]:
        tzd[tz_code] = tz_offset
