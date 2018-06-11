import logging
import asyncio
from typing import Union
from datetime import timedelta
from copy import copy
import contextlib
import discord

from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.antispam import AntiSpam
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.tunnel import Tunnel


_ = Translator("Reports", __file__)

log = logging.getLogger("red.reports")


@cog_i18n(_)
class Reports:

    default_guild_settings = {"output_channel": None, "active": False, "next_ticket": 1}

    default_report = {"report": {}}

    # This can be made configureable later if it
    # becomes an issue.
    # Intervals should be a list of tuples in the form
    # (period: timedelta, max_frequency: int)
    # see redbot/core/utils/antispam.py for more details

    intervals = [
        (timedelta(seconds=5), 1),
        (timedelta(minutes=5), 3),
        (timedelta(hours=1), 10),
        (timedelta(days=1), 24),
    ]

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 78631113035100160, force_registration=True)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_custom("REPORT", **self.default_report)
        self.antispam = {}
        self.user_cache = []
        self.tunnel_store = {}
        # (guild, ticket#):
        #   {'tun': Tunnel, 'msgs': List[int]}

    @property
    def tunnels(self):
        return [x["tun"] for x in self.tunnel_store.values()]

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="reportset", autohelp=True)
    async def reportset(self, ctx: commands.Context):
        """
        Settings for the report system
        """
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @reportset.command(name="output")
    async def setoutput(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where reports will show up"""
        await self.config.guild(ctx.guild).output_channel.set(channel.id)
        await ctx.send(_("The report channel has been set."))

    @checks.admin_or_permissions(manage_guild=True)
    @reportset.command(name="toggle")
    async def report_toggle(self, ctx: commands.Context):
        """Enables or Disables reporting for the server"""

        active = await self.config.guild(ctx.guild).active()
        active = not active
        await self.config.guild(ctx.guild).active.set(active)
        if active:
            await ctx.send(_("Reporting is now enabled"))
        else:
            await ctx.send(_("Reporting is now disabled."))

    async def internal_filter(self, m: discord.Member, mod=False, perms=None):
        ret = False
        if mod:
            guild = m.guild
            admin_role = discord.utils.get(
                guild.roles, id=await self.bot.db.guild(guild).admin_role()
            )
            mod_role = discord.utils.get(guild.roles, id=await self.bot.db.guild(guild).mod_role())
            ret |= any(r in m.roles for r in (mod_role, admin_role))
        if perms:
            ret |= m.guild_permissions >= perms
        # The following line is for consistency with how perms are handled
        # in Red, though I'm not sure it makse sense to use here.
        ret |= await self.bot.is_owner(m)
        return ret

    async def discover_guild(
        self,
        author: discord.User,
        *,
        mod: bool = False,
        permissions: Union[discord.Permissions, dict] = None,
        prompt: str = ""
    ):
        """
        discovers which of shared guilds between the bot
        and provided user based on conditions (mod or permissions is an or)

        prompt is for providing a user prompt for selection
        """
        shared_guilds = []
        if permissions is None:
            perms = discord.Permissions()
        elif isinstance(permissions, discord.Permissions):
            perms = permissions
        else:
            perms = discord.Permissions(**permissions)

        for guild in self.bot.guilds:
            x = guild.get_member(author.id)
            if x is not None:
                if await self.internal_filter(x, mod, perms):
                    shared_guilds.append(guild)
        if len(shared_guilds) == 0:
            raise ValueError("No Qualifying Shared Guilds")
        if len(shared_guilds) == 1:
            return shared_guilds[0]
        output = ""
        guilds = sorted(shared_guilds, key=lambda g: g.name)
        for i, guild in enumerate(guilds, 1):
            output += "{}: {}\n".format(i, guild.name)
        output += "\n{}".format(prompt)

        for page in pagify(output, delims=["\n"]):
            dm = await author.send(box(page))

        def pred(m):
            return m.author == author and m.channel == dm.channel

        try:
            message = await self.bot.wait_for("message", check=pred, timeout=45)
        except asyncio.TimeoutError:
            await author.send(_("You took too long to select. Try again later."))
            return None

        try:
            message = int(message.content.strip())
            guild = guilds[message - 1]
        except (ValueError, IndexError):
            await author.send(_("That wasn't a valid choice."))
            return None
        else:
            return guild

    async def send_report(self, msg: discord.Message, guild: discord.Guild):

        author = guild.get_member(msg.author.id)
        report = msg.clean_content

        channel_id = await self.config.guild(guild).output_channel()
        channel = guild.get_channel(channel_id)
        if channel is None:
            return None

        files = await Tunnel.files_from_attatch(msg)

        ticket_number = await self.config.guild(guild).next_ticket()
        await self.config.guild(guild).next_ticket.set(ticket_number + 1)

        if await self.bot.embed_requested(channel, author):
            em = discord.Embed(description=report)
            em.set_author(
                name=_("Report from {0.display_name}").format(author), icon_url=author.avatar_url
            )
            em.set_footer(text=_("Report #{}").format(ticket_number))
            send_content = None
        else:
            em = None
            send_content = _("Report from {author.mention} (Ticket #{number})").format(
                author=author, number=ticket_number
            )
            send_content += "\n" + report

        try:
            await Tunnel.message_forwarder(
                destination=channel, content=send_content, embed=em, files=files
            )
        except (discord.Forbidden, discord.HTTPException):
            return None

        await self.config.custom("REPORT", guild.id, ticket_number).report.set(
            {"user_id": author.id, "report": report}
        )
        return ticket_number

    @commands.group(name="report", invoke_without_command=True)
    async def report(self, ctx: commands.Context, *, _report: str = ""):
        """
        Use [p]report <text> to send a report
		or alternatively [p]report for DM reporting
        """
        author = ctx.author
        guild = ctx.guild
        if guild is None:
            guild = await self.discover_guild(
                author, prompt=_("Select a server to make a report in by number.")
            )
        if guild is None:
            return
        g_active = await self.config.guild(guild).active()
        if not g_active:
            return await author.send(_("Reporting has not been enabled for this server"))
        if guild.id not in self.antispam:
            self.antispam[guild.id] = {}
        if author.id not in self.antispam[guild.id]:
            self.antispam[guild.id][author.id] = AntiSpam(self.intervals)
        if self.antispam[guild.id][author.id].spammy:
            return await author.send(
                _(
                    "You've sent too many reports recently. "
                    "Please contact a server admin if this is important matter, or please wait and try again "
                    "later."
                )
            )
        if author.id in self.user_cache:
            return await author.send(
                _(
                    "Please finish making your prior report before trying to make an additional one!"
                )
            )
        self.user_cache.append(author.id)

        if _report:
            _m = copy(ctx.message)
            _m.content = _report
            _m.content = _m.clean_content
            val = await self.send_report(_m, guild)
        else:
            try:
                dm = await author.send(
                    _(
                        "Please respond to this message with your Report."
                        "\nYour report should be a single message"
                    )
                )
            except discord.Forbidden:
                return await ctx.send(_("This requires DMs enabled."))

            def pred(m):
                return m.author == author and m.channel == dm.channel

            try:
                message = await self.bot.wait_for("message", check=pred, timeout=180)
            except asyncio.TimeoutError:
                return await author.send(_("You took too long. Try again later."))
            else:
                val = await self.send_report(message, guild)

        with contextlib.suppress(discord.Forbidden, discord.HTTPException):
            if val is None:
                await author.send(
                    _("There was an error sending your report, please contact a server admin.")
                )
            else:
                await author.send(_("Your report was submitted. (Ticket #{})").format(val))
                self.antispam[guild.id][author.id].stamp()

    @report.after_invoke
    async def report_cleanup(self, ctx: commands.Context):
        """
        The logic is cleaner this way
        """
        if ctx.author.id in self.user_cache:
            self.user_cache.remove(ctx.author.id)
        if ctx.guild and ctx.invoked_subcommand is None:
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass

    async def on_raw_reaction_add(self, payload):
        """
        oh dear....
        """
        if not str(payload.emoji) == "\N{NEGATIVE SQUARED CROSS MARK}":
            return

        _id = payload.message_id
        t = next(filter(lambda x: _id in x[1]["msgs"], self.tunnel_store.items()), None)

        if t is None:
            return
        tun = t[1]["tun"]
        if payload.user_id in [x.id for x in tun.members]:
            await tun.react_close(
                uid=payload.user_id, message=_("{closer} has closed the correspondence")
            )
            self.tunnel_store.pop(t[0], None)

    async def on_message(self, message: discord.Message):
        for k, v in self.tunnel_store.items():
            topic = _("Re: ticket# {1} in {0.name}").format(*k)
            # Tunnels won't forward unintended messages, this is safe
            msgs = await v["tun"].communicate(message=message, topic=topic)
            if msgs:
                self.tunnel_store[k]["msgs"] = msgs

    @checks.mod_or_permissions(manage_members=True)
    @report.command(name="interact")
    async def response(self, ctx, ticket_number: int):
        """
        opens a message tunnel between things you say in this channel
        and the ticket opener's direct messages

        tunnels do not persist across bot restarts
        """

        # note, mod_or_permissions is an implicit guild_only
        guild = ctx.guild
        rec = await self.config.custom("REPORT", guild.id, ticket_number).report()

        try:
            user = guild.get_member(rec.get("user_id"))
        except KeyError:
            return await ctx.send(_("That ticket doesn't seem to exist"))

        if user is None:
            return await ctx.send(_("That user isn't here anymore."))

        tun = Tunnel(recipient=user, origin=ctx.channel, sender=ctx.author)

        if tun is None:
            return await ctx.send(
                _(
                    "Either you or the user you are trying to reach already "
                    "has an open communication."
                )
            )

        big_topic = _(
            "{who} opened a 2-way communication."
            "about ticket number {ticketnum}. Anything you say or upload here "
            "(8MB file size limitation on uploads) "
            "will be forwarded to them until the communication is closed.\n"
            "You can close a communication at any point "
            "by reacting with the X to the last message recieved. "
            "\nAny message succesfully forwarded will be marked with a check."
            "\nTunnels are not persistent across bot restarts."
        )
        topic = big_topic.format(
            ticketnum=ticket_number, who=_("A moderator in `{guild.name}` has").format(guild=guild)
        )
        try:
            m = await tun.communicate(message=ctx.message, topic=topic, skip_message_content=True)
        except discord.Forbidden:
            await ctx.send(_("That user has DMs disabled."))
        else:
            self.tunnel_store[(guild, ticket_number)] = {"tun": tun, "msgs": m}
            await ctx.send(big_topic.format(who=_("You have"), ticketnum=ticket_number))
