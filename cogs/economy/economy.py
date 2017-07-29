import calendar
import logging
import random
from collections import defaultdict, deque
from enum import Enum

import discord
from discord.ext import commands

from core import checks, Config, bank
from core.utils.chat_formatting import pagify, box
from core.bot import Red

logger = logging.getLogger("red.economy")

NUM_ENC = "\N{COMBINING ENCLOSING KEYCAP}"


class SMReel(Enum):
    cherries = "\N{CHERRIES}"
    cookie = "\N{COOKIE}"
    two = "\N{DIGIT TWO}" + NUM_ENC
    flc = "\N{FOUR LEAF CLOVER}"
    cyclone = "\N{CYCLONE}"
    sunflower = "\N{SUNFLOWER}"
    six = "\N{DIGIT SIX}" + NUM_ENC
    mushroom = "\N{MUSHROOM}"
    heart = "\N{HEAVY BLACK HEART}"
    snowflake = "\N{SNOWFLAKE}"


PAYOUTS = {
    (SMReel.two, SMReel.two, SMReel.six): {
        "payout": lambda x: x * 2500 + x,
        "phrase": "JACKPOT! 226! Your bid has been multiplied * 2500!"
    },
    (SMReel.flc, SMReel.flc, SMReel.flc): {
        "payout": lambda x: x + 1000,
        "phrase": "4LC! +1000!"
    },
    (SMReel.cherries, SMReel.cherries, SMReel.cherries): {
        "payout": lambda x: x + 800,
        "phrase": "Three cherries! +800!"
    },
    (SMReel.two, SMReel.six): {
        "payout": lambda x: x * 4 + x,
        "phrase": "2 6! Your bid has been multiplied * 4!"
    },
    (SMReel.cherries, SMReel.cherries): {
        "payout": lambda x: x * 3 + x,
        "phrase": "Two cherries! Your bid has been multiplied * 3!"
    },
    "3 symbols": {
        "payout": lambda x: x + 500,
        "phrase": "Three symbols! +500!"
    },
    "2 symbols": {
        "payout": lambda x: x * 2 + x,
        "phrase": "Two consecutive symbols! Your bid has been multiplied * 2!"
    },
}

SLOT_PAYOUTS_MSG = ("Slot machine payouts:\n"
                    "{two.value} {two.value} {six.value} Bet * 2500\n"
                    "{flc.value} {flc.value} {flc.value} +1000\n"
                    "{cherries.value} {cherries.value} {cherries.value} +800\n"
                    "{two.value} {six.value} Bet * 4\n"
                    "{cherries.value} {cherries.value} Bet * 3\n\n"
                    "Three symbols: +500\n"
                    "Two symbols: Bet * 2".format(**SMReel.__dict__))


class SetParser:
    def __init__(self, argument):
        allowed = ("+", "-")
        self.sum = int(argument)
        if argument and argument[0] in allowed:
            if self.sum < 0:
                self.operation = "withdraw"
            elif self.sum > 0:
                self.operation = "deposit"
            else:
                raise RuntimeError
            self.sum = abs(self.sum)
        elif argument.isdigit():
            self.operation = "set"
        else:
            raise RuntimeError


class Economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    default_guild_settings = {
        "PAYDAY_TIME": 300,
        "PAYDAY_CREDITS": 120,
        "SLOT_MIN": 5,
        "SLOT_MAX": 100,
        "SLOT_TIME": 0,
        "REGISTER_CREDITS": 0
    }

    default_member_settings = {
        "next_payday": 0,
        "last_slot": 0
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.file_path = "data/economy/settings.json"
        self.config = Config.get_conf(self, 1256844281)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_member(**self.default_member_settings)
        self.slot_register = defaultdict(dict)

    @commands.group(name="bank")
    async def _bank(self, ctx: commands.Context):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_bank.command()
    async def balance(self, ctx: commands.Context, user: discord.Member = None):
        """Shows balance of user.

        Defaults to yours."""
        if user is None:
            user = ctx.author

        bal = bank.get_balance(user)
        currency = bank.get_currency_name(ctx.guild)

        await ctx.send("{}'s balance is {} {}".format(
            user.display_name, bal, currency))

    @_bank.command()
    async def transfer(self, ctx: commands.Context, to: discord.Member, amount: int):
        """Transfer currency to other users"""
        from_ = ctx.author
        currency = bank.get_currency_name(ctx.guild)

        try:
            await bank.transfer_credits(from_, to, amount)
        except ValueError as e:
            await ctx.send(str(e))

        await ctx.send("{} transferred {} {} to {}".format(
            from_.display_name, amount, currency, to.display_name
        ))

    @_bank.command(name="set")
    @checks.admin_or_permissions(manage_guild=True)
    async def _set(self, ctx: commands.Context, to: discord.Member, creds: SetParser):
        """Sets balance of user's bank account. See help for more operations

        Passing positive and negative values will add/remove currency instead

        Examples:
            bank set @Twentysix 26 - Sets balance to 26
            bank set @Twentysix +2 - Increases balance by 2
            bank set @Twentysix -6 - Decreases balance by 6"""
        author = ctx.author
        currency = bank.get_currency_name(ctx.guild)

        if creds.operation == "deposit":
            await bank.deposit_credits(to, creds.sum)
            await ctx.send("{} added {} {} to {}'s account.".format(
                author.display_name, creds.sum, currency, to.display_name
            ))
        elif creds.operation == "withdraw":
            await bank.withdraw_credits(to, creds.sum)
            await ctx.send("{} removed {} {} from {}'s account.".format(
                author.display_name, creds.sum, currency, to.display_name
            ))
        else:
            await bank.set_balance(to, creds.sum)
            await ctx.send("{} set {}'s account to {} {}.".format(
                author.display_name, to.display_name, creds.sum, currency
            ))

    @_bank.command()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def reset(self, ctx, confirmation: bool = False):
        """Deletes all guild's bank accounts"""
        if confirmation is False:
            await ctx.send("This will delete all bank accounts on "
                           "this guild.\nIf you're sure, type "
                           "{}bank reset yes".format(ctx.prefix))
        else:
            success = await bank.wipe_bank(ctx.guild)
            if success:
                await ctx.send("All bank accounts of this guild have been "
                               "deleted.")

    @commands.command()
    async def payday(self, ctx: commands.Context):
        """Get some free currency"""
        author = ctx.author
        guild = ctx.guild
        next_payday = self.config.member(author).next_payday()
        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())
        credits_name = bank.get_currency_name(ctx.guild)

        if cur_time >= next_payday:
            await bank.deposit_credits(author, self.config.guild(guild).PAYDAY_CREDITS())
            next_payday = cur_time + self.config.guild(guild).PAYDAY_TIME()
            await self.config.member(author).next_payday.set(next_payday)
            await ctx.send(
                "{} Here, take some {}. Enjoy! (+{}"
                " {}!)".format(
                    author.mention, credits_name,
                    str(self.config.guild(guild).PAYDAY_CREDITS()),
                    credits_name))
        else:
            dtime = self.display_time(next_payday - cur_time)
            await ctx.send(
                "{} Too soon. For your next payday you have to"
                " wait {}.".format(author.mention, dtime))

    @commands.command()
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context, top: int = 10):
        """Prints out the leaderboard

        Defaults to top 10"""
        # Originally coded by Airenkun - edited by irdumb, rewritten by Palm__ for v3
        guild = ctx.guild
        if top < 1:
            top = 10
        if bank.is_global():
            bank_sorted = sorted(bank.get_global_accounts(ctx.author),
                                 key=lambda x: x.balance, reverse=True)
        else:
            bank_sorted = sorted(bank.get_guild_accounts(guild),
                                 key=lambda x: x.balance, reverse=True)
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1
        for acc in topten:
            dname = str(acc.name)
            if len(dname) >= 23 - len(str(acc.balance)):
                dname = dname[:(23 - len(str(acc.balance))) - 3]
                dname += "... "
            highscore += str(place).ljust(len(str(top)) + 1)
            highscore += dname.ljust(23 - len(str(acc.balance)))
            highscore += str(acc.balance) + "\n"
            place += 1
        if highscore != "":
            for page in pagify(highscore, shorten_by=12):
                await ctx.send(box(page, lang="py"))
        else:
            await ctx.send("There are no accounts in the bank.")

    @commands.command()
    @commands.guild_only()
    async def payouts(self, ctx: commands.Context):
        """Shows slot machine payouts"""
        await ctx.author.send(SLOT_PAYOUTS_MSG)

    @commands.command()
    @commands.guild_only()
    async def slot(self, ctx: commands.Context, bid: int):
        """Play the slot machine"""
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        valid_bid = self.config.guild(guild).SLOT_MIN() <= bid <= self.config.guild(guild).SLOT_MAX()
        slot_time = self.config.guild(guild).SLOT_TIME()
        last_slot = self.config.member(author).last_slot()
        now = calendar.timegm(ctx.message.created_at.utctimetuple())

        if (now - last_slot) < slot_time:
            await ctx.send("You're on cooldown, try again in a bit.")
            return
        if not valid_bid:
            await ctx.send("That's an invalid bid amount, sorry :/")
            return
        if not bank.can_spend(author, bid):
            await ctx.send("You ain't got enough money, friend.")
            return
        await self.config.member(author).last_slot.set(now)
        await self.slot_machine(author, channel, bid)

    async def slot_machine(self, author, channel, bid):
        default_reel = deque(SMReel)
        reels = []
        for i in range(3):
            default_reel.rotate(random.randint(-999, 999))  # weeeeee
            new_reel = deque(default_reel, maxlen=3)  # we need only 3 symbols
            reels.append(new_reel)  # for each reel
        rows = ((reels[0][0], reels[1][0], reels[2][0]),
                (reels[0][1], reels[1][1], reels[2][1]),
                (reels[0][2], reels[1][2], reels[2][2]))

        slot = "~~\n~~"  # Mobile friendly
        for i, row in enumerate(rows):  # Let's build the slot to show
            sign = "  "
            if i == 1:
                sign = ">"
            slot += "{}{} {} {}\n".format(sign, *[c.value for c in row])

        payout = PAYOUTS.get(rows[1])
        if not payout:
            # Checks for two-consecutive-symbols special rewards
            payout = PAYOUTS.get((rows[1][0], rows[1][1]),
                                 PAYOUTS.get((rows[1][1], rows[1][2])))
        if not payout:
            # Still nothing. Let's check for 3 generic same symbols
            # or 2 consecutive symbols
            has_three = rows[1][0] == rows[1][1] == rows[1][2]
            has_two = (rows[1][0] == rows[1][1]) or (rows[1][1] == rows[1][2])
            if has_three:
                payout = PAYOUTS["3 symbols"]
            elif has_two:
                payout = PAYOUTS["2 symbols"]

        if payout:
            then = bank.get_balance(author)
            pay = payout["payout"](bid)
            now = then - bid + pay
            await bank.set_balance(author, now)
            await channel.send("{}\n{} {}\n\nYour bid: {}\n{} → {}!"
                               "".format(slot, author.mention,
                                         payout["phrase"], bid, then, now))
        else:
            then = bank.get_balance(author)
            await bank.withdraw_credits(author, bid)
            now = then - bid
            await channel.send("{}\n{} Nothing!\nYour bid: {}\n{} → {}!"
                               "".format(slot, author.mention, bid, then, now))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def economyset(self, ctx: commands.Context):
        """Changes economy module settings"""
        guild = ctx.guild
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @economyset.command()
    async def slotmin(self, ctx: commands.Context, bid: int):
        """Minimum slot machine bid"""
        guild = ctx.guild
        await self.config.guild(guild).SLOT_MIN.set(bid)
        credits_name = bank.get_currency_name(guild)
        await ctx.send("Minimum bid is now {} {}.".format(bid, credits_name))

    @economyset.command()
    async def slotmax(self, ctx: commands.Context, bid: int):
        """Maximum slot machine bid"""
        guild = ctx.guild
        credits_name = bank.get_currency_name(guild)
        await self.config.guild(guild).SLOT_MAX.set(bid)
        await ctx.send("Maximum bid is now {} {}.".format(bid, credits_name))

    @economyset.command()
    async def slottime(self, ctx: commands.Context, seconds: int):
        """Seconds between each slots use"""
        guild = ctx.guild
        await self.config.guild(guild).SLOT_TIME.set(seconds)
        await ctx.send("Cooldown is now {} seconds.".format(seconds))

    @economyset.command()
    async def paydaytime(self, ctx: commands.Context, seconds: int):
        """Seconds between each payday"""
        guild = ctx.guild
        await self.config.guild(guild).PAYDAY_TIME.set(seconds)
        await ctx.send("Value modified. At least {} seconds must pass "
                       "between each payday.".format(seconds))

    @economyset.command()
    async def paydayamount(self, ctx: commands.Context, creds: int):
        """Amount earned each payday"""
        guild = ctx.guild
        credits_name = bank.get_currency_name(guild)
        if creds <= 0:
            await ctx.send("Har har so funny.")
            return
        await self.config.guild(guild).PAYDAY_CREDITS.set(creds)
        await ctx.send("Every payday will now give {} {}."
                       "".format(creds, credits_name))

    @economyset.command()
    async def registeramount(self, ctx: commands.Context, creds: int):
        """Amount given on registering an account"""
        guild = ctx.guild
        if creds < 0:
            creds = 0
        credits_name = bank.get_currency_name(guild)
        await bank.set_default_balance(creds, guild)
        await ctx.send("Registering an account will now give {} {}."
                       "".format(creds, credits_name))

    # What would I ever do without stackoverflow?
    def display_time(self, seconds, granularity=2):
        intervals = (  # Source: http://stackoverflow.com/a/24542445
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),  # 60 * 60 * 24
            ('hours', 3600),  # 60 * 60
            ('minutes', 60),
            ('seconds', 1),
        )

        result = []

        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
