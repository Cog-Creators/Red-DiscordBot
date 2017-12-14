from copy import deepcopy
from datetime import datetime, timedelta
import imghdr
import os
import os.path
import shutil
import time

import aiohttp
try:
    from dateutil.relativedelta import relativedelta
    dateutil_available = True
except:
    dateutil_available = False
import discord
from discord.ext import commands

from .utils.dataIO import dataIO
from .utils import checks, chat_formatting as cf


default_settings = {
    "submissions": {},
    "next_id": 1
}


class ReviewEmoji:

    """Allows for submission and review of custom emojis."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_base = "data/reviewemoji"
        self.submissions_path = "data/reviewemoji/submissions.json"
        self.submissions = dataIO.load_json(self.submissions_path)

    def _round_time(self, dt: datetime, round_to: int=60) -> datetime:
        seconds = (dt - dt.min).seconds
        rounding = (seconds + (round_to / 2)) // round_to * round_to
        return dt + timedelta(0, rounding - seconds, -dt.microsecond)

    def _make_readable_delta(self, sub_time: float) -> str:
        sub_dt = self._round_time(datetime.fromtimestamp(sub_time))
        now_dt = self._round_time(datetime.fromtimestamp(time.time()))

        delta = relativedelta(now_dt, sub_dt)
        attrs = ['years', 'months', 'days', 'hours', 'minutes']
        return ", ".join(['%d %s' % (getattr(delta, attr),
                                     (getattr(delta, attr) != 1 and
                                      attr or attr[:-1]))
                          for attr in attrs if (getattr(delta, attr) or
                                                attr == attrs[-1])])
        + " ago"

    def _get_num_waiting_subs(self, server_id: int) -> int:
        return len([sub for sub in
                    list(self.submissions[server_id]["submissions"].values())
                    if sub["status"] == "waiting"])

    async def _send_update_pm(self, server: discord.Server, subid: str):
        sub = self.submissions[server.id]["submissions"][subid]

        user = server.get_member(sub["submitter"])

        if sub["status"] == "rejected":
            await self.bot.send_message(
                user,
                "Your emoji submission `{}` in {} has been rejected by {}.\n"
                "Here is the reason they gave:{}"
                "As a reminder, here is what your rejected emoji looks like:"
                .format(sub["name"], server.name,
                        server.get_member(
                    sub["rejector"]).mention,
                    cf.box(sub["reject_reason"])))
            await self.bot.send_file(user, sub["image"])
            await self.bot.send_message(
                user,
                "You may fix the problems with your emoji and resubmit it,"
                " or contact the rejector with any questions.")
        elif sub["status"] == "approved":
            await self.bot.send_message(
                user,
                "Your emoji submission `{}` in {} has been approved by {}."
                .format(sub["name"], server.name,
                        server.get_member(sub["approver"]).mention))

    async def _approve_emoji(self, ctx: commands.Context, subid: str):
        sub = self.submissions[ctx.message.server.id]["submissions"][subid]

        with open(sub["image"], "rb") as img:
            await self.bot.create_custom_emoji(
                ctx.message.server, name=sub["name"], image=img.read())

        sub["status"] = "approved"
        sub["approver"] = ctx.message.author.id
        sub["approve_time"] = time.time()

        dataIO.save_json(self.submissions_path, self.submissions)

        await self._send_update_pm(ctx.message.server, subid)

    async def _reject_emoji(self, ctx: commands.Context, subid: str,
                            reason: str):

        sub = self.submissions[ctx.message.server.id]["submissions"][subid]
        sub["status"] = "rejected"
        sub["rejector"] = ctx.message.author.id
        sub["reject_time"] = time.time()
        sub["reject_reason"] = reason

        dataIO.save_json(self.submissions_path, self.submissions)

        await self._send_update_pm(ctx.message.server, subid)

    @commands.command(pass_context=True, no_pm=True, name="submitemoji")
    async def _submitemoji(self, ctx: commands.Context, name: str,
                           image_url: str=None):
        """Submits a new emoji for review.

        Should include either an image as a Discord attachment,
        or a direct link to the image.
        """

        await self.bot.type()

        server = ctx.message.server
        if server.id not in self.submissions:
            self.submissions[server.id] = deepcopy(default_settings)
            dataIO.save_json(self.submissions_path, self.submissions)

        if len(name) < 2:
            await self.bot.reply(
                cf.error("Name must be at least 2 characters long."))
            return

        if name in [e.name for e in server.emojis]:
            await self.bot.reply(cf.error("That name is already taken."))
            return

        attach = ctx.message.attachments
        if len(attach) > 1 or (attach and image_url):
            await self.bot.reply(cf.error("Please only provide one file."))
            return

        url = ""
        if attach:
            url = attach[0]["url"]
        elif image_url:
            url = image_url
        else:
            await self.bot.reply(cf.error(
                "You must provide either a Discord attachment"
                " or a direct link to an image."))
            return

        if len(server.emojis) == 50:
            await self.bot.reply(cf.warning(
                "The server already has the maximum number of emojis allowed."
                " Some must be deleted before more submissions can be made."))
            return

        if len(server.emojis) + self._get_num_waiting_subs(server.id) == 50:
            await self.bot.reply(cf.warning(
                "The emoji submission queue is full. A moderator must review"
                " some submissions before more may be made."))
            return

        new_emoji_id = str(self.submissions[server.id]["next_id"])
        self.submissions[server.id]["next_id"] += 1
        dataIO.save_json(self.submissions_path, self.submissions)

        path = "{}/{}".format(self.data_base, server.id)
        if not os.path.exists(path):
            os.makedirs(path)

        path += "/" + new_emoji_id
        os.makedirs(path)

        path += "/" + os.path.basename(url)

        async with aiohttp.get(url) as new_emoji_file:
            f = open(path, "wb")
            f.write(await new_emoji_file.read())
            f.close

        if imghdr.what(path) not in ["png", "jpeg", "jpg"]:
            await self.bot.reply(
                cf.error("Only JPG and PNG images are supported."))
            shutil.rmtree(
                "{}/{}/{}".format(self.data_base, server.id, new_emoji_id))
            return

        self.submissions[server.id]["submissions"][new_emoji_id] = {
            "id": new_emoji_id,
            "status": "waiting",
            "submitter": ctx.message.author.id,
            "name": name,
            "image": path,
            "submit_time": time.time(),
            "approver": None,
            "approve_time": None,
            "rejector": None,
            "reject_time": None,
            "reject_reason": None
        }
        dataIO.save_json(self.submissions_path, self.submissions)

        await self.bot.reply(cf.info(
            "Submission successful, ID {}."
            " You can check its status with `{}checkemoji {}`."
            .format(new_emoji_id, ctx.prefix, new_emoji_id)))

    @commands.command(pass_context=True, no_pm=True, name="checkemoji")
    async def _checkemoji(self, ctx: commands.Context,
                          submission_id: str):
        """Check the status of a submitted emoji."""

        await self.bot.type()

        server = ctx.message.server

        if submission_id not in self.submissions[server.id]["submissions"]:
            await self.bot.reply(cf.error(
                "Submission with ID {} not found.".format(submission_id)))
            return

        sub = self.submissions[server.id]["submissions"][submission_id]
        status = ""
        extra = ""
        if sub["status"] == "waiting":
            status = "Awaiting review."
        elif sub["status"] == "approved":
            status = "Approved."
            extra = "\nApproved by: {}\nApproved: {}".format(
                server.get_member(sub["approver"]).display_name,
                sub["approve_time"])
        elif sub["status"] == "rejected":
            status = "Rejected."
            extra = "\nRejected by: {}\nRejected: {}\n"
            "Rejection reason: {}".format(
                server.get_member(sub["rejector"]).display_name,
                sub["reject_time"], sub["reject_reason"])

        await self.bot.reply(cf.box(
            "Submission ID: {}\nSubmitted by: {}\nSubmitted: {}\n"
            "Proposed name: {}\nStatus: {}{}".format(
                submission_id, server.get_member(
                    sub["submitter"]).display_name,
                self._make_readable_delta(sub["submit_time"]),
                sub["name"], status, extra)))

    @commands.command(pass_context=True, no_pm=True, name="reviewemoji")
    @checks.admin_or_permissions(manage_emojis=True)
    async def _reviewemoji(self, ctx: commands.Context):
        """Review emoji submissions."""

        server = ctx.message.server
        if server.id not in self.submissions:
            self.submissions[server.id] = deepcopy(default_settings)
            dataIO.save_json(self.submissions_path, self.submissions)

        if self._get_num_waiting_subs(server.id) == 0:
            await self.bot.reply("There are no submissions awaiting review.")
            return

        approved = 0
        rejected = 0
        skipped = 0

        for subid, sub in self.submissions[server.id]["submissions"].items():
            if sub["status"] == "waiting":
                await self.bot.say(cf.box(
                    "Submission ID: {}\nSubmitted by: {}\nSubmitted: {}\n"
                    "Proposed name: {}\nPreview:"
                    .format(subid,
                            server.get_member(sub["submitter"]).display_name,
                            self._make_readable_delta(sub["submit_time"]),
                            sub["name"])))
                await self.bot.upload(sub["image"])
                await self.bot.reply(cf.question(
                    "What is your decision for this emoji? You may say"
                    " \"approve\" to add it, \"reject <reason>\" to refuse it,"
                    " or \"skip\" to postpone judgment. You may also say"
                    " \"exit\" to exit the review process."))

                decision = None
                while not decision:
                    r = await self.bot.wait_for_message(
                        timeout=15, channel=ctx.message.channel,
                        author=ctx.message.author)
                    if r is None:
                        continue
                    resp = r.content.strip().lower().split()
                    if resp[0] not in ("approve", "reject", "skip", "exit"):
                        await self.bot.reply(cf.warning(
                            "Please say either \"approve\","
                            " \"reject <reason>\", or \"skip\"."))
                    elif resp[0] == "reject" and len(resp) == 1:
                        await self.bot.reply(cf.warning(
                            "If you reject an emoji,"
                            " you must provide a reason."))
                    else:
                        decision = resp

                if decision[0] == "approve":
                    try:
                        await self._approve_emoji(ctx, subid)
                    except discord.HTTPException as e:
                        await self.bot.reply(
                            cf.error("An error occurred while creating"
                                     " the new emoji: {}".format(cf.box(e))))
                        continue
                    await self.bot.reply(
                        cf.info("Submission {} approved and added. Preview:"
                                " :{}:".format(subid, sub["name"])))
                    approved += 1
                elif decision[0] == "reject":
                    reason = " ".join(decision[1:])
                    await self._reject_emoji(ctx, subid, reason)
                    await self.bot.reply(
                        cf.info("Submission {} rejected.").format(subid))
                    rejected += 1
                elif decision[0] == "skip":
                    await self.bot.reply(
                        cf.info("Submission {} skipped.".format(subid)))
                    skipped += 1
                elif decision[0] == "exit" or decision is None:
                    break

        more = self._get_num_waiting_subs(server.id)
        await self.bot.reply(cf.info(
            "Exiting review process.\n"
            "This session: {} approved, {} rejected, {} skipped.\n"
            "There {} now {} emoji{} awaiting review."
            .format(approved, rejected, skipped,
                    ("is" if more == 1 else "are"), more,
                    ("" if more == 1 else "s"))))


def check_folders():
    if not os.path.exists("data/reviewemoji"):
        print("Creating data/reviewemoji directory...")
        os.makedirs("data/reviewemoji")


def check_files():
    f = "data/reviewemoji/submissions.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/reviewemoji/submissions.json...")
        dataIO.save_json(f, {})


def setup(bot: commands.Bot):
    check_folders()
    check_files()

    if dateutil_available:
        bot.add_cog(ReviewEmoji(bot))
    else:
        raise RuntimeError("You need to install `python-dateutil`: `pip install python-dateutil`.")
