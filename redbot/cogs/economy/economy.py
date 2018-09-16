import calendar
import logging
import random
from collections import defaultdict, deque
from enum import Enum

import discord

from redbot.cogs.bank import check_global_setting_guildowner, check_global_setting_admin
from redbot.core import Config, bank, commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from redbot.core.bot import Red

_ = Translator("Economy", __file__)

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
        "phrase": _("JACKPOT! 226! Your bid has been multiplied * 2500!"),
    },
    (SMReel.flc, SMReel.flc, SMReel.flc): {
        "payout": lambda x: x + 1000,
        "phrase": _("4LC! +1000!"),
    },
    (SMReel.cherries, SMReel.cherries, SMReel.cherries): {
        "payout": lambda x: x + 800,
        "phrase": _("Three cherries! +800!"),
    },
    (SMReel.two, SMReel.six): {
        "payout": lambda x: x * 4 + x,
        "phrase": _("2 6! Your bid has been multiplied * 4!"),
    },
    (SMReel.cherries, SMReel.cherries): {
        "payout": lambda x: x * 3 + x,
        "phrase": _("Two cherries! Your bid has been multiplied * 3!"),
    },
    "3 symbols": {"payout": lambda x: x + 500, "phrase": _("Three symbols! +500!")},
    "2 symbols": {
        "payout": lambda x: x * 2 + x,
        "phrase": _("Two consecutive symbols! Your bid has been multiplied * 2!"),
    },
}

SLOT_PAYOUTS_MSG = _(
    "Slot machine payouts:\n"
    "{two.value} {two.value} {six.value} Bet * 2500\n"
    "{flc.value} {flc.value} {flc.value} +1000\n"
    "{cherries.value} {cherries.value} {cherries.value} +800\n"
    "{two.value} {six.value} Bet * 4\n"
    "{cherries.value} {cherries.value} Bet * 3\n\n"
    "Three symbols: +500\n"
    "Two symbols: Bet * 2"
).format(**SMReel.__dict__)


def guild_only_check():
    async def pred(ctx: commands.Context):
        if await bank.is_global():
            return True
        elif not await bank.is_global() and ctx.guild is not None:
            return True
        else:
            return False

    return commands.check(pred)


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


@cog_i18n(_)
class Economy(commands.Cog):
    """Economy

    Get rich and have fun with imaginary currency!"""

    default_guild_settings = {
        "PAYDAY_TIME": 300,
        "PAYDAY_CREDITS": 120,
        "SLOT_MIN": 5,
        "SLOT_MAX": 100,
        "SLOT_TIME": 0,
        "REGISTER_CREDITS": 0,
    }

    default_global_settings = default_guild_settings

    default_member_settings = {"next_payday": 0, "last_slot": 0}

    default_role_settings = {"PAYDAY_CREDITS": 0}

    default_user_settings = default_member_settings

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.file_path = "data/economy/settings.json"
        self.config = Config.get_conf(self, 1256844281)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_global(**self.default_global_settings)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.config.register_role(**self.default_role_settings)
        self.slot_register = defaultdict(dict)

    @guild_only_check()
    @commands.group(name="bank")
    async def _bank(self, ctx: commands.Context):
        """Bank operations"""
        pass

    @_bank.command()
    async def balance(self, ctx: commands.Context, user: discord.Member = None):
        """Shows balance of user.

        Defaults to yours."""
        if user is None:
            user = ctx.author

        bal = await bank.get_balance(user)
        currency = await bank.get_currency_name(ctx.guild)

        await ctx.send(_("{}'s balance is {} {}").format(user.display_name, bal, currency))

    @_bank.command()
    async def transfer(self, ctx: commands.Context, to: discord.Member, amount: int):
        """Transfer currency to other users"""
        from_ = ctx.author
        currency = await bank.get_currency_name(ctx.guild)

        try:
            await bank.transfer_credits(from_, to, amount)
        except ValueError as e:
            return await ctx.send(str(e))

        await ctx.send(
            _("{} transferred {} {} to {}").format(
                from_.display_name, amount, currency, to.display_name
            )
        )

    @_bank.command(name="set")
    @check_global_setting_admin()
    async def _set(self, ctx: commands.Context, to: discord.Member, creds: SetParser):
        """Sets balance of user's bank account. See help for more operations

        Passing positive and negative values will add/remove currency instead

        Examples:
            bank set @Twentysix 26 - Sets balance to 26
            bank set @Twentysix +2 - Increases balance by 2
            bank set @Twentysix -6 - Decreases balance by 6"""
        author = ctx.author
        currency = await bank.get_currency_name(ctx.guild)

        if creds.operation == "deposit":
            await bank.deposit_credits(to, creds.sum)
            await ctx.send(
                _("{} added {} {} to {}'s account.").format(
                    author.display_name, creds.sum, currency, to.display_name
                )
            )
        elif creds.operation == "withdraw":
            await bank.withdraw_credits(to, creds.sum)
            await ctx.send(
                _("{} removed {} {} from {}'s account.").format(
                    author.display_name, creds.sum, currency, to.display_name
                )
            )
        else:
            await bank.set_balance(to, creds.sum)
            await ctx.send(
                _("{} set {}'s account to {} {}.").format(
                    author.display_name, to.display_name, creds.sum, currency
                )
            )

    @_bank.command()
    @check_global_setting_guildowner()
    async def reset(self, ctx, confirmation: bool = False):
        """Deletes bank accounts"""
        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for {}.\nIf you're sure, type "
                    "`{}bank reset yes`"
                ).format(
                    self.bot.user.name if await bank.is_global() else "this server", ctx.prefix
                )
            )
        else:
            await bank.wipe_bank()
            await ctx.send(
                _("All bank accounts for {} have been deleted.").format(
                    self.bot.user.name if await bank.is_global() else "this server"
                )
            )

    @guild_only_check()
    @commands.command()
    async def payday(self, ctx: commands.Context):
        """Get some free currency"""
        author = ctx.author
        guild = ctx.guild

        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())
        credits_name = await bank.get_currency_name(ctx.guild)
        if await bank.is_global():  # Role payouts will not be used
            next_payday = await self.config.user(author).next_payday()
            if cur_time >= next_payday:
                await bank.deposit_credits(author, await self.config.PAYDAY_CREDITS())
                next_payday = cur_time + await self.config.PAYDAY_TIME()
                await self.config.user(author).next_payday.set(next_payday)

                pos = await bank.get_leaderboard_position(author)
                await ctx.send(
                    _(
                        "{0.mention} Here, take some {1}. Enjoy! (+{2} {1}!)\n\n"
                        "You currently have {3} {1}.\n\n"
                        "You are currently #{4} on the global leaderboard!"
                    ).format(
                        author,
                        credits_name,
                        str(await self.config.PAYDAY_CREDITS()),
                        str(await bank.get_balance(author)),
                        pos,
                    )
                )

            else:
                dtime = self.display_time(next_payday - cur_time)
                await ctx.send(
                    _("{} Too soon. For your next payday you have to wait {}.").format(
                        author.mention, dtime
                    )
                )
        else:
            next_payday = await self.config.member(author).next_payday()
            if cur_time >= next_payday:
                credit_amount = await self.config.guild(guild).PAYDAY_CREDITS()
                for role in author.roles:
                    role_credits = await self.config.role(
                        role
                    ).PAYDAY_CREDITS()  # Nice variable name
                    if role_credits > credit_amount:
                        credit_amount = role_credits
                await bank.deposit_credits(author, credit_amount)
                next_payday = cur_time + await self.config.guild(guild).PAYDAY_TIME()
                await self.config.member(author).next_payday.set(next_payday)
                pos = await bank.get_leaderboard_position(author)
                await ctx.send(
                    _(
                        "{0.mention} Here, take some {1}. Enjoy! (+{2} {1}!)\n\n"
                        "You currently have {3} {1}.\n\n"
                        "You are currently #{4} on the leaderboard!"
                    ).format(
                        author,
                        credits_name,
                        credit_amount,
                        str(await bank.get_balance(author)),
                        pos,
                    )
                )
            else:
                dtime = self.display_time(next_payday - cur_time)
                await ctx.send(
                    _("{} Too soon. For your next payday you have to wait {}.").format(
                        author.mention, dtime
                    )
                )

    @commands.command()
    @guild_only_check()
    async def leaderboard(self, ctx: commands.Context, top: int = 10, show_global: bool = False):
        """Prints out the leaderboard

        Defaults to top 10"""
        guild = ctx.guild
        author = ctx.author
        if top < 1:
            top = 10
        if (
            await bank.is_global() and show_global
        ):  # show_global is only applicable if bank is global
            guild = None
        bank_sorted = await bank.get_leaderboard(positions=top, guild=guild)
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        header = f"{f'#':4}{f'Name':36}{f'Score':2}\n"
        highscores = [
            (
                f"{f'{pos}.': <{3 if pos < 10 else 2}} {acc[1]['name']: <{35}s} "
                f"{acc[1]['balance']: >{2 if pos < 10 else 1}}\n"
            )
            if acc[0] != author.id
            else (
                f"{f'{pos}.': <{3 if pos < 10 else 2}} <<{acc[1]['name'] + '>>': <{33}s} "
                f"{acc[1]['balance']: >{2 if pos < 10 else 1}}\n"
            )
            for pos, acc in enumerate(bank_sorted, 1)
        ]
        if highscores:
            pages = [
                f"```md\n{header}{''.join(''.join(highscores[x:x + 10]))}```"
                for x in range(0, len(highscores), 10)
            ]
            await menu(ctx, pages, DEFAULT_CONTROLS)
        else:
            await ctx.send(_("There are no accounts in the bank."))

    @commands.command()
    @guild_only_check()
    async def payouts(self, ctx: commands.Context):
        """Shows slot machine payouts"""
        await ctx.author.send(SLOT_PAYOUTS_MSG)

    @commands.command()
    @guild_only_check()
    async def slot(self, ctx: commands.Context, bid: int):
        """Play the slot machine"""
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        if await bank.is_global():
            valid_bid = await self.config.SLOT_MIN() <= bid <= await self.config.SLOT_MAX()
            slot_time = await self.config.SLOT_TIME()
            last_slot = await self.config.user(author).last_slot()
        else:
            valid_bid = (
                await self.config.guild(guild).SLOT_MIN()
                <= bid
                <= await self.config.guild(guild).SLOT_MAX()
            )
            slot_time = await self.config.guild(guild).SLOT_TIME()
            last_slot = await self.config.member(author).last_slot()
        now = calendar.timegm(ctx.message.created_at.utctimetuple())

        if (now - last_slot) < slot_time:
            await ctx.send(_("You're on cooldown, try again in a bit."))
            return
        if not valid_bid:
            await ctx.send(_("That's an invalid bid amount, sorry :/"))
            return
        if not await bank.can_spend(author, bid):
            await ctx.send(_("You ain't got enough money, friend."))
            return
        if await bank.is_global():
            await self.config.user(author).last_slot.set(now)
        else:
            await self.config.member(author).last_slot.set(now)
        await self.slot_machine(author, channel, bid)

    async def slot_machine(self, author, channel, bid):
        default_reel = deque(SMReel)
        reels = []
        for i in range(3):
            default_reel.rotate(random.randint(-999, 999))  # weeeeee
            new_reel = deque(default_reel, maxlen=3)  # we need only 3 symbols
            reels.append(new_reel)  # for each reel
        rows = (
            (reels[0][0], reels[1][0], reels[2][0]),
            (reels[0][1], reels[1][1], reels[2][1]),
            (reels[0][2], reels[1][2], reels[2][2]),
        )

        slot = "~~\n~~"  # Mobile friendly
        for i, row in enumerate(rows):  # Let's build the slot to show
            sign = "  "
            if i == 1:
                sign = ">"
            slot += "{}{} {} {}\n".format(sign, *[c.value for c in row])

        payout = PAYOUTS.get(rows[1])
        if not payout:
            # Checks for two-consecutive-symbols special rewards
            payout = PAYOUTS.get((rows[1][0], rows[1][1]), PAYOUTS.get((rows[1][1], rows[1][2])))
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
            then = await bank.get_balance(author)
            pay = payout["payout"](bid)
            now = then - bid + pay
            await bank.set_balance(author, now)
            await channel.send(
                _("{}\n{} {}\n\nYour bid: {}\n{} → {}!").format(
                    slot, author.mention, payout["phrase"], bid, then, now
                )
            )
        else:
            then = await bank.get_balance(author)
            await bank.withdraw_credits(author, bid)
            now = then - bid
            await channel.send(
                _("{}\n{} Nothing!\nYour bid: {}\n{} → {}!").format(
                    slot, author.mention, bid, then, now
                )
            )

    @commands.group()
    @guild_only_check()
    @check_global_setting_admin()
    async def economyset(self, ctx: commands.Context):
        """Changes economy module settings"""
        guild = ctx.guild
        if ctx.invoked_subcommand is None:
            if await bank.is_global():
                slot_min = await self.config.SLOT_MIN()
                slot_max = await self.config.SLOT_MAX()
                slot_time = await self.config.SLOT_TIME()
                payday_time = await self.config.PAYDAY_TIME()
                payday_amount = await self.config.PAYDAY_CREDITS()
            else:
                slot_min = await self.config.guild(guild).SLOT_MIN()
                slot_max = await self.config.guild(guild).SLOT_MAX()
                slot_time = await self.config.guild(guild).SLOT_TIME()
                payday_time = await self.config.guild(guild).PAYDAY_TIME()
                payday_amount = await self.config.guild(guild).PAYDAY_CREDITS()
            register_amount = await bank.get_default_balance(guild)
            msg = box(
                _(
                    "Minimum slot bid: {}\n"
                    "Maximum slot bid: {}\n"
                    "Slot cooldown: {}\n"
                    "Payday amount: {}\n"
                    "Payday cooldown: {}\n"
                    "Amount given at account registration: {}"
                    ""
                ).format(
                    slot_min, slot_max, slot_time, payday_amount, payday_time, register_amount
                ),
                _("Current Economy settings:"),
            )
            await ctx.send(msg)

    @economyset.command()
    async def slotmin(self, ctx: commands.Context, bid: int):
        """Minimum slot machine bid"""
        if bid < 1:
            await ctx.send(_("Invalid min bid amount."))
            return
        guild = ctx.guild
        if await bank.is_global():
            await self.config.SLOT_MIN.set(bid)
        else:
            await self.config.guild(guild).SLOT_MIN.set(bid)
        credits_name = await bank.get_currency_name(guild)
        await ctx.send(_("Minimum bid is now {} {}.").format(bid, credits_name))

    @economyset.command()
    async def slotmax(self, ctx: commands.Context, bid: int):
        """Maximum slot machine bid"""
        slot_min = await self.config.SLOT_MIN()
        if bid < 1 or bid < slot_min:
            await ctx.send(_("Invalid slotmax bid amount. Must be greater than slotmin."))
            return
        guild = ctx.guild
        credits_name = await bank.get_currency_name(guild)
        if await bank.is_global():
            await self.config.SLOT_MAX.set(bid)
        else:
            await self.config.guild(guild).SLOT_MAX.set(bid)
        await ctx.send(_("Maximum bid is now {} {}.").format(bid, credits_name))

    @economyset.command()
    async def slottime(self, ctx: commands.Context, seconds: int):
        """Seconds between each slots use"""
        guild = ctx.guild
        if await bank.is_global():
            await self.config.SLOT_TIME.set(seconds)
        else:
            await self.config.guild(guild).SLOT_TIME.set(seconds)
        await ctx.send(_("Cooldown is now {} seconds.").format(seconds))

    @economyset.command()
    async def paydaytime(self, ctx: commands.Context, seconds: int):
        """Seconds between each payday"""
        guild = ctx.guild
        if await bank.is_global():
            await self.config.PAYDAY_TIME.set(seconds)
        else:
            await self.config.guild(guild).PAYDAY_TIME.set(seconds)
        await ctx.send(
            _("Value modified. At least {} seconds must pass between each payday.").format(seconds)
        )

    @economyset.command()
    async def paydayamount(self, ctx: commands.Context, creds: int):
        """Amount earned each payday"""
        guild = ctx.guild
        credits_name = await bank.get_currency_name(guild)
        if creds <= 0:
            await ctx.send(_("Har har so funny."))
            return
        if await bank.is_global():
            await self.config.PAYDAY_CREDITS.set(creds)
        else:
            await self.config.guild(guild).PAYDAY_CREDITS.set(creds)
        await ctx.send(_("Every payday will now give {} {}.").format(creds, credits_name))

    @economyset.command()
    async def rolepaydayamount(self, ctx: commands.Context, role: discord.Role, creds: int):
        """Amount earned each payday for a role"""
        guild = ctx.guild
        credits_name = await bank.get_currency_name(guild)
        if await bank.is_global():
            await ctx.send("The bank must be per-server for per-role paydays to work.")
        else:
            await self.config.role(role).PAYDAY_CREDITS.set(creds)
            await ctx.send(
                _("Every payday will now give {} {} to people with the role {}.").format(
                    creds, credits_name, role.name
                )
            )

    @economyset.command()
    async def registeramount(self, ctx: commands.Context, creds: int):
        """Amount given on registering an account"""
        guild = ctx.guild
        if creds < 0:
            creds = 0
        credits_name = await bank.get_currency_name(guild)
        await bank.set_default_balance(creds, guild)
        await ctx.send(
            _("Registering an account will now give {} {}.").format(creds, credits_name)
        )

    # What would I ever do without stackoverflow?
    def display_time(self, seconds, granularity=2):
        intervals = (  # Source: http://stackoverflow.com/a/24542445
            (_("weeks"), 604800),  # 60 * 60 * 24 * 7
            (_("days"), 86400),  # 60 * 60 * 24
            (_("hours"), 3600),  # 60 * 60
            (_("minutes"), 60),
            (_("seconds"), 1),
        )

        result = []

        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip("s")
                result.append("{} {}".format(value, name))
        return ", ".join(result[:granularity])
