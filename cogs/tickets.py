from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils import checks
from __main__ import send_cmd_help
import os


class Tickets:
    def __init__(self, bot):
        self.bot = bot
        self.tickets = fileIO("data/tickets/tickets.json", "load")
        self.settings = fileIO("data/tickets/settings.json", "load")

    @property
    def ticket_limit(self):
        num = self.settings.get("TICKETS_PER_USER", -1)
        if num == -1:
            self.ticket_limit = 0
            num = 0
        return num

    @ticket_limit.setter
    def ticket_limit(self, num):
        self.settings["TICKETS_PER_USER"] = num
        fileIO("data/tickets/settings.json", "save", self.settings)

    @property
    def keep_on_read(self):
        ret = self.settings.get("KEEP_ON_READ")
        if ret is None:
            self.keep_on_read = False
            ret = False
        return ret

    @keep_on_read.setter
    def keep_on_read(self, value):
        self.settings["KEEP_ON_READ"] = bool(value)
        fileIO("data/tickets/settings.json", "save", self.settings)

    @property
    def reply_to_user(self):
        ret = self.settings.get("REPLY_TO_USER")
        if ret is None:
            ret = False
            self.reply_to_user = ret
        return ret

    @reply_to_user.setter
    def reply_to_user(self, val):
        self.settings["REPLY_TO_USER"] = val
        fileIO("data/tickets/settings.json", "save", self.settings)

    def _get_ticket(self):
        if len(self.tickets) > 0:
            ticket = self.tickets[0]
            for idnum in ticket:
                ret = ticket[idnum].get(
                    "name", "no_name") + ": " + \
                    ticket[idnum].get("message", "no_message")
            if not self.keep_on_read:
                self.tickets = self.tickets[1:]
                fileIO("data/tickets/tickets.json", "save", self.tickets)
            return ret
        else:
            return "No more tickets!"

    def _get_number_tickets(self, author):
        idnum = author.id
        num = len([x for ticket in self.tickets for x in ticket if x == idnum])
        return num

    def _add_ticket(self, author, message):
        self.tickets.append(
            {author.id: {"name": author.name, "message": message}})
        fileIO("data/tickets/tickets.json", "save", self.tickets)

    @commands.command(aliases=["nt"], pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def nextticket(self, ctx):
        """Gets the next ticket"""
        if self.reply_to_user:
            reply = ctx.message.author
        else:
            reply = ctx.message.channel
        await self.bot.send_message(reply, self._get_ticket())

    @commands.command(pass_context=True)
    async def ticket(self, ctx, *, message):
        """Adds ticket.

           Example: !ticket The quick brown fox? -> adds ticket"""
        if self.ticket_limit != 0 and \
                self._get_number_tickets(ctx.message.author) >= \
                self.ticket_limit:
            await self.bot.say("{}, you've reached the ticket limit!".format(
                ctx.message.author.mention))
            return
        self._add_ticket(ctx.message.author, message)
        await self.bot.say("{}, ticket added.".format(
            ctx.message.author.mention))

    @commands.command(aliases=['ct'])
    @checks.mod_or_permissions(manage_messages=True)
    async def cleartickets(self):
        """Clears all tickets"""
        self.tickets = []
        fileIO("data/tickets/tickets.json", "save", self.tickets)
        await self.bot.say("Tickets cleared.")

    @commands.command(aliases=["dt"], pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def deleteticket(self, ctx, num: int=1):
        """Deletes any number of tickets, default = 1"""
        if num < 0:
            await send_cmd_help(ctx)
            return
        if num > len(self.tickets):
            num = len(self.tickets)
            self.tickets = []
        else:
            self.tickets = self.tickets[num:]
        fileIO("data/tickets/tickets.json", "save", self.tickets)
        await self.bot.say("{} tickets deleted.\n{} tickets remaining.".format(
            num, len(self.tickets)))

    @commands.group(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def ticketset(self, ctx):
        """Ticket cog settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "```"
            await self.bot.say(msg)

    @ticketset.command(name="limit", pass_context=True)
    async def tickets_per_user(self, ctx, num: int):
        """Limits the number of tickets a user can have 0 = infinite."""
        if num < 0:
            await send_cmd_help(ctx)
            return
        self.settings["TICKETS_PER_USER"] = num
        fileIO("data/tickets/settings.json", "save", self.settings)
        await self.bot.say("Tickets per user set to {}".format(num))

    @ticketset.command(name="keep", pass_context=True)
    async def _keep_on_read(self, ctx, val: bool):
        """Determines whether the ticket is kept after it has been read.
         - True/False"""
        self.keep_on_read = val
        await self.bot.say("Keep on read set to {}".format(val))

    @ticketset.command(name="pm")
    async def reply_to(self, boolvar: bool):
        """Determines whether !nextticket replies in a pm or not
         - True/False"""
        if boolvar:
            self.reply_to_user = True
        else:
            self.reply_to_user = False
        await self.bot.say("PM set to {}".format(boolvar))


def check_folder():
    if not os.path.exists("data/tickets"):
        print("Creating data/tickets folder...")
        os.makedirs("data/tickets")


def check_file():
    tickets = []
    settings = {"TICKETS_PER_USER": 1,
                "REPLY_TO_USER": False, "KEEP_ON_READ": False}

    f = "data/tickets/tickets.json"
    if not fileIO(f, "check"):
        print("Creating default tickets's tickets.json...")
        fileIO(f, "save", tickets)

    f = "data/tickets/settings.json"
    if not fileIO(f, "check"):
        print("Creating default tickets's settings.json...")
        fileIO(f, "save", settings)


def setup(bot):
    check_folder()
    check_file()
    n = Tickets(bot)
    bot.add_cog(n)
