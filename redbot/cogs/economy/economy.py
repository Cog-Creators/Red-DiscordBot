import calendar
import logging
import random
from collections import defaultdict, deque, namedtuple
from enum import Enum
from math import ceil
from typing import cast, Iterable, Union, Literal

import discord

from redbot.cogs.bank import is_owner_if_bank_global
from redbot.cogs.mod.converters import RawUserIds
from redbot.core import Config, bank, commands, errors, checks
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.core.bot import Red
from redbot.core.utils.menus import SimpleHybridMenu

from .converters import positive_int
from .menus import LeaderboardSource

T_ = Translator("Economy", __file__)

logger = logging.getLogger("red.economy")

NUM_ENC = "\N{COMBINING ENCLOSING KEYCAP}"
VARIATION_SELECTOR = "\N{VARIATION SELECTOR-16}"
MOCK_MEMBER = namedtuple("Member", "id guild")


class SMReel(Enum):
    cherries = "\N{CHERRIES}"
    cookie = "\N{COOKIE}"
    two = "\N{DIGIT TWO}" + NUM_ENC
    flc = "\N{FOUR LEAF CLOVER}"
    cyclone = "\N{CYCLONE}"
    sunflower = "\N{SUNFLOWER}"
    six = "\N{DIGIT SIX}" + NUM_ENC
    mushroom = "\N{MUSHROOM}"
    heart = "\N{HEAVY BLACK HEART}" + VARIATION_SELECTOR
    snowflake = "\N{SNOWFLAKE}" + VARIATION_SELECTOR


_ = lambda s: s
PAYOUTS = {
    (SMReel.two, SMReel.two, SMReel.six): {
        "payout": lambda x: x * 50,
        "phrase": _("JACKPOT! 226! Your bid has been multiplied * 50!"),
    },
    (SMReel.flc, SMReel.flc, SMReel.flc): {
        "payout": lambda x: x * 25,
        "phrase": _("4LC! Your bid has been multiplied * 25!"),
    },
    (SMReel.cherries, SMReel.cherries, SMReel.cherries): {
        "payout": lambda x: x * 20,
        "phrase": _("Three cherries! Your bid has been multiplied * 20!"),
    },
    (SMReel.two, SMReel.six): {
        "payout": lambda x: x * 4,
        "phrase": _("2 6! Your bid has been multiplied * 4!"),
    },
    (SMReel.cherries, SMReel.cherries): {
        "payout": lambda x: x * 3,
        "phrase": _("Two cherries! Your bid has been multiplied * 3!"),
    },
    "3 symbols": {
        "payout": lambda x: x * 10,
        "phrase": _("Three symbols! Your bid has been multiplied * 10!"),
    },
    "2 symbols": {
        "payout": lambda x: x * 2,
        "phrase": _("Two consecutive symbols! Your bid has been multiplied * 2!"),
    },
}

SLOT_PAYOUTS_MSG = _(
    "Slot machine payouts:\n"
    "{two.value} {two.value} {six.value} Bet * 50\n"
    "{flc.value} {flc.value} {flc.value} Bet * 25\n"
    "{cherries.value} {cherries.value} {cherries.value} Bet * 20\n"
    "{two.value} {six.value} Bet * 4\n"
    "{cherries.value} {cherries.value} Bet * 3\n\n"
    "Three symbols: Bet * 10\n"
    "Two symbols: Bet * 2"
).format(**SMReel.__dict__)
_ = T_


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
        try:
            self.sum = int(argument)
        except ValueError:
            raise commands.BadArgument(
                _(
                    "Invalid value, the argument must be an integer,"
                    " optionally preceded with a `+` or `-` sign."
                )
            )
        if argument and argument[0] in allowed:
            if self.sum < 0:
                self.operation = "withdraw"
            elif self.sum > 0:
                self.operation = "deposit"
            else:
                raise commands.BadArgument(
                    _(
                        "Invalid value, the amount of currency to increase or decrease"
                        " must be an integer different from zero."
                    )
                )
            self.sum = abs(self.sum)
        else:
            self.operation = "set"


@cog_i18n(_)
class Economy(commands.Cog):
    """Get rich and have fun with imaginary currency!"""

    default_guild_settings = {
        "PAYDAY_TIME": 300,
        "PAYDAY_CREDITS": 120,
        "SLOT_MIN": 5,
        "SLOT_MAX": 100,
        "SLOT_TIME": 5,
        "REGISTER_CREDITS": 0,
    }

    default_global_settings = default_guild_settings

    default_member_settings = {"next_payday": 0, "last_slot": 0}

    default_role_settings = {"PAYDAY_CREDITS": 0}

    default_user_settings = default_member_settings

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 1256844281)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_global(**self.default_global_settings)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.config.register_role(**self.default_role_settings)
        self.slot_register = defaultdict(dict)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        await self.config.user_from_id(user_id).clear()

        all_members = await self.config.all_members()

        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

    @guild_only_check()
    @commands.group(name="bank")
    async def _bank(self, ctx: commands.Context):
        """Base command to manage the bank."""
        pass

    @_bank.command()
    async def balance(self, ctx: commands.Context, user: discord.Member = None):
        """Show the user's account balance.

        Example:
            - `[p]bank balance`
            - `[p]bank balance @Twentysix`

        **Arguments**

        - `<user>` The user to check the balance of. If omitted, defaults to your own balance.
        """
        if user is None:
            user = ctx.author

        bal = await bank.get_balance(user)
        currency = await bank.get_currency_name(ctx.guild)
        max_bal = await bank.get_max_balance(ctx.guild)
        if bal > max_bal:
            bal = max_bal
            await bank.set_balance(user, bal)
        await ctx.send(
            _("{user}'s balance is {num} {currency}").format(
                user=user.display_name, num=humanize_number(bal), currency=currency
            )
        )

    @_bank.command()
    async def transfer(self, ctx: commands.Context, to: discord.Member, amount: int):
        """Transfer currency to other users.

        This will come out of your balance, so make sure you have enough.

        Example:
            - `[p]bank transfer @Twentysix 500`

        **Arguments**

        - `<to>` The user to give currency to.
        - `<amount>` The amount of currency to give.
        """
        from_ = ctx.author
        currency = await bank.get_currency_name(ctx.guild)

        try:
            await bank.transfer_credits(from_, to, amount)
        except (ValueError, errors.BalanceTooHigh) as e:
            return await ctx.send(str(e))

        await ctx.send(
            _("{user} transferred {num} {currency} to {other_user}").format(
                user=from_.display_name,
                num=humanize_number(amount),
                currency=currency,
                other_user=to.display_name,
            )
        )

    @is_owner_if_bank_global()
    @checks.admin_or_permissions(manage_guild=True)
    @_bank.command(name="set")
    async def _set(self, ctx: commands.Context, to: discord.Member, creds: SetParser):
        """Set the balance of a user's bank account.

        Putting + or - signs before the amount will add/remove currency on the user's bank account instead.

        Examples:
            - `[p]bank set @Twentysix 26` - Sets balance to 26
            - `[p]bank set @Twentysix +2` - Increases balance by 2
            - `[p]bank set @Twentysix -6` - Decreases balance by 6

        **Arguments**

        - `<to>` The user to set the currency of.
        - `<creds>` The amount of currency to set their balance to.
        """
        author = ctx.author
        currency = await bank.get_currency_name(ctx.guild)

        try:
            if creds.operation == "deposit":
                await bank.deposit_credits(to, creds.sum)
                msg = _("{author} added {num} {currency} to {user}'s account.").format(
                    author=author.display_name,
                    num=humanize_number(creds.sum),
                    currency=currency,
                    user=to.display_name,
                )
            elif creds.operation == "withdraw":
                await bank.withdraw_credits(to, creds.sum)
                msg = _("{author} removed {num} {currency} from {user}'s account.").format(
                    author=author.display_name,
                    num=humanize_number(creds.sum),
                    currency=currency,
                    user=to.display_name,
                )
            else:
                await bank.set_balance(to, creds.sum)
                msg = _("{author} set {user}'s account balance to {num} {currency}.").format(
                    author=author.display_name,
                    num=humanize_number(creds.sum),
                    currency=currency,
                    user=to.display_name,
                )
        except (ValueError, errors.BalanceTooHigh) as e:
            await ctx.send(str(e))
        else:
            await ctx.send(msg)

    @is_owner_if_bank_global()
    @checks.guildowner_or_permissions(administrator=True)
    @_bank.command()
    async def reset(self, ctx, confirmation: bool = False):
        """Delete all bank accounts.

        Examples:
            - `[p]bank reset` - Did not confirm. Shows the help message.
            - `[p]bank reset yes`

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for {scope}.\nIf you're sure, type "
                    "`{prefix}bank reset yes`"
                ).format(
                    scope=self.bot.user.name if await bank.is_global() else _("this server"),
                    prefix=ctx.clean_prefix,
                )
            )
        else:
            await bank.wipe_bank(guild=ctx.guild)
            await ctx.send(
                _("All bank accounts for {scope} have been deleted.").format(
                    scope=self.bot.user.name if await bank.is_global() else _("this server")
                )
            )

    @is_owner_if_bank_global()
    @checks.admin_or_permissions(manage_guild=True)
    @_bank.group(name="prune")
    async def _prune(self, ctx):
        """Base command for pruning bank accounts."""
        pass

    @_prune.command(name="server", aliases=["guild", "local"])
    @commands.guild_only()
    @checks.guildowner()
    async def _local(self, ctx, confirmation: bool = False):
        """Prune bank accounts for users no longer in the server.

        Cannot be used with a global bank. See `[p]bank prune global`.

        Examples:
            - `[p]bank prune server` - Did not confirm. Shows the help message.
            - `[p]bank prune server yes`

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        global_bank = await bank.is_global()
        if global_bank is True:
            return await ctx.send(_("This command cannot be used with a global bank."))

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for users no longer in this server."
                    "\nIf you're sure, type "
                    "`{prefix}bank prune local yes`"
                ).format(prefix=ctx.clean_prefix)
            )
        else:
            await bank.bank_prune(self.bot, guild=ctx.guild)
            await ctx.send(
                _("Bank accounts for users no longer in this server have been deleted.")
            )

    @_prune.command(name="global")
    @checks.is_owner()
    async def _global(self, ctx, confirmation: bool = False):
        """Prune bank accounts for users who no longer share a server with the bot.

        Cannot be used without a global bank. See `[p]bank prune server`.

        Examples:
            - `[p]bank prune global` - Did not confirm. Shows the help message.
            - `[p]bank prune global yes`

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        global_bank = await bank.is_global()
        if global_bank is False:
            return await ctx.send(_("This command cannot be used with a local bank."))

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for users "
                    "who no longer share a server with the bot."
                    "\nIf you're sure, type `{prefix}bank prune global yes`"
                ).format(prefix=ctx.clean_prefix)
            )
        else:
            await bank.bank_prune(self.bot)
            await ctx.send(
                _(
                    "Bank accounts for users who "
                    "no longer share a server with the bot have been pruned."
                )
            )

    @_prune.command(usage="<user> [confirmation=False]")
    async def user(
        self, ctx, member_or_id: Union[discord.Member, RawUserIds], confirmation: bool = False
    ):
        """Delete the bank account of a specified user.

        Examples:
            - `[p]bank prune user @TwentySix` - Did not confirm. Shows the help message.
            - `[p]bank prune user @TwentySix yes`

        **Arguments**

        - `<user>` The user to delete the bank of. Takes mentions, names, and user ids.
        - `<confirmation>` This will default to false unless specified.
        """
        global_bank = await bank.is_global()
        if global_bank is False and ctx.guild is None:
            return await ctx.send(_("This command cannot be used in DMs with a local bank."))
        try:
            name = member_or_id.display_name
            uid = member_or_id.id
        except AttributeError:
            name = member_or_id
            uid = member_or_id

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete {name}'s bank account."
                    "\nIf you're sure, type "
                    "`{prefix}bank prune user {id} yes`"
                ).format(prefix=ctx.clean_prefix, id=uid, name=name)
            )
        else:
            await bank.bank_prune(self.bot, guild=ctx.guild, user_id=uid)
            await ctx.send(_("The bank account for {name} has been pruned.").format(name=name))

    @guild_only_check()
    @commands.command()
    async def payday(self, ctx: commands.Context):
        """Get some free currency.

        The amount awarded and frequency can be configured.
        """
        author = ctx.author
        guild = ctx.guild

        cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())
        credits_name = await bank.get_currency_name(ctx.guild)
        if await bank.is_global():  # Role payouts will not be used

            # Gets the latest time the user used the command successfully and adds the global payday time
            next_payday = (
                await self.config.user(author).next_payday() + await self.config.PAYDAY_TIME()
            )
            if cur_time >= next_payday:
                try:
                    await bank.deposit_credits(author, await self.config.PAYDAY_CREDITS())
                except errors.BalanceTooHigh as exc:
                    await bank.set_balance(author, exc.max_balance)
                    await ctx.send(
                        _(
                            "You've reached the maximum amount of {currency}! "
                            "Please spend some more \N{GRIMACING FACE}\n\n"
                            "You currently have {new_balance} {currency}."
                        ).format(
                            currency=credits_name, new_balance=humanize_number(exc.max_balance)
                        )
                    )
                    return
                # Sets the current time as the latest payday
                await self.config.user(author).next_payday.set(cur_time)

                pos = await bank.get_leaderboard_position(author)
                await ctx.send(
                    _(
                        "{author.mention} Here, take some {currency}. "
                        "Enjoy! (+{amount} {currency}!)\n\n"
                        "You currently have {new_balance} {currency}.\n\n"
                        "You are currently #{pos} on the global leaderboard!"
                    ).format(
                        author=author,
                        currency=credits_name,
                        amount=humanize_number(await self.config.PAYDAY_CREDITS()),
                        new_balance=humanize_number(await bank.get_balance(author)),
                        pos=humanize_number(pos) if pos else pos,
                    )
                )

            else:
                dtime = self.display_time(next_payday - cur_time)
                await ctx.send(
                    _(
                        "{author.mention} Too soon. For your next payday you have to wait {time}."
                    ).format(author=author, time=dtime)
                )
        else:

            # Gets the users latest successfully payday and adds the guilds payday time
            next_payday = (
                await self.config.member(author).next_payday()
                + await self.config.guild(guild).PAYDAY_TIME()
            )
            if cur_time >= next_payday:
                credit_amount = await self.config.guild(guild).PAYDAY_CREDITS()
                for role in author.roles:
                    role_credits = await self.config.role(
                        role
                    ).PAYDAY_CREDITS()  # Nice variable name
                    if role_credits > credit_amount:
                        credit_amount = role_credits
                try:
                    await bank.deposit_credits(author, credit_amount)
                except errors.BalanceTooHigh as exc:
                    await bank.set_balance(author, exc.max_balance)
                    await ctx.send(
                        _(
                            "You've reached the maximum amount of {currency}! "
                            "Please spend some more \N{GRIMACING FACE}\n\n"
                            "You currently have {new_balance} {currency}."
                        ).format(
                            currency=credits_name, new_balance=humanize_number(exc.max_balance)
                        )
                    )
                    return

                # Sets the latest payday time to the current time
                next_payday = cur_time

                await self.config.member(author).next_payday.set(next_payday)
                pos = await bank.get_leaderboard_position(author)
                await ctx.send(
                    _(
                        "{author.mention} Here, take some {currency}. "
                        "Enjoy! (+{amount} {currency}!)\n\n"
                        "You currently have {new_balance} {currency}.\n\n"
                        "You are currently #{pos} on the global leaderboard!"
                    ).format(
                        author=author,
                        currency=credits_name,
                        amount=humanize_number(credit_amount),
                        new_balance=humanize_number(await bank.get_balance(author)),
                        pos=humanize_number(pos) if pos else pos,
                    )
                )
            else:
                dtime = self.display_time(next_payday - cur_time)
                await ctx.send(
                    _(
                        "{author.mention} Too soon. For your next payday you have to wait {time}."
                    ).format(author=author, time=dtime)
                )

    @commands.command()
    @guild_only_check()
    async def leaderboard(self, ctx: commands.Context, top: int = 10, show_global: bool = False):
        """Print the leaderboard.

        Defaults to top 10.

        Examples:
            - `[p]leaderboard`
            - `[p]leaderboard 50` - Shows the top 50 instead of top 10.
            - `[p]leaderboard 100 yes` - Shows the top 100 from all servers.

        **Arguments**

        - `<top>` How many positions on the leaderboard to show. Defaults to 10 if omitted.
        - `<show_global>` Whether to include results from all servers. This will default to false unless specified.
        """
        guild = ctx.guild
        if top < 1:
            top = 10

        base_embed = discord.Embed(title=_("Economy Leaderboard"))
        if await bank.is_global() and show_global:
            # show_global is only applicable if bank is global
            bank_sorted = await bank.get_leaderboard(positions=top, guild=None)
            base_embed.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        else:
            bank_sorted = await bank.get_leaderboard(positions=top, guild=guild)
            if guild:
                base_embed.set_author(name=guild.name, icon_url=guild.icon_url)

        try:
            bank_sorted[0][1]["balance"]
            # first user is the largest we'll see
        except IndexError:
            return await ctx.send(_("There are no accounts in the bank."))

        await SimpleHybridMenu(
            source=LeaderboardSource(bank_sorted), cog=self, delete_message_after=True,
        ).start(ctx=ctx, wait=False)

    @commands.command()
    @guild_only_check()
    async def payouts(self, ctx: commands.Context):
        """Show the payouts for the slot machine."""
        try:
            await ctx.author.send(SLOT_PAYOUTS_MSG)
        except discord.Forbidden:
            await ctx.send(_("I can't send direct messages to you."))

    @commands.command()
    @guild_only_check()
    async def slot(self, ctx: commands.Context, bid: int):
        """Use the slot machine.

        Example:
            - `[p]slot 50`

        **Arguments**

        - `<bid>` The amount to bet on the slot machine. Winning payouts are higher when you bet more.
        """
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

    @staticmethod
    async def slot_machine(author, channel, bid):
        default_reel = deque(cast(Iterable, SMReel))
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
            slot += "{}{} {} {}\n".format(
                sign, *[c.value for c in row]  # pylint: disable=no-member
            )

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

        pay = 0
        if payout:
            then = await bank.get_balance(author)
            pay = payout["payout"](bid)
            now = then - bid + pay
            try:
                await bank.set_balance(author, now)
            except errors.BalanceTooHigh as exc:
                await bank.set_balance(author, exc.max_balance)
                await channel.send(
                    _(
                        "You've reached the maximum amount of {currency}! "
                        "Please spend some more \N{GRIMACING FACE}\n{old_balance} -> {new_balance}!"
                    ).format(
                        currency=await bank.get_currency_name(getattr(channel, "guild", None)),
                        old_balance=humanize_number(then),
                        new_balance=humanize_number(exc.max_balance),
                    )
                )
                return
            phrase = T_(payout["phrase"])
        else:
            then = await bank.get_balance(author)
            await bank.withdraw_credits(author, bid)
            now = then - bid
            phrase = _("Nothing!")
        await channel.send(
            (
                "{slot}\n{author.mention} {phrase}\n\n"
                + _("Your bid: {bid}")
                + _("\n{old_balance} - {bid} (Your bid) + {pay} (Winnings) → {new_balance}!")
            ).format(
                slot=slot,
                author=author,
                phrase=phrase,
                bid=humanize_number(bid),
                old_balance=humanize_number(then),
                new_balance=humanize_number(now),
                pay=humanize_number(pay),
            )
        )

    @guild_only_check()
    @is_owner_if_bank_global()
    @checks.admin_or_permissions(manage_guild=True)
    @commands.group()
    async def economyset(self, ctx: commands.Context):
        """Base command to manage Economy settings."""

    @economyset.command(name="showsettings")
    async def economyset_showsettings(self, ctx: commands.Context):
        """
        Shows the current economy settings
        """
        guild = ctx.guild
        if await bank.is_global():
            conf = self.config
        else:
            conf = self.config.guild(guild)
        await ctx.send(
            box(
                _(
                    "----Economy Settings---\n"
                    "Minimum slot bid: {slot_min}\n"
                    "Maximum slot bid: {slot_max}\n"
                    "Slot cooldown: {slot_time}\n"
                    "Payday amount: {payday_amount}\n"
                    "Payday cooldown: {payday_time}\n"
                    "Amount given at account registration: {register_amount}\n"
                    "Maximum allowed balance: {maximum_bal}"
                ).format(
                    slot_min=humanize_number(await conf.SLOT_MIN()),
                    slot_max=humanize_number(await conf.SLOT_MAX()),
                    slot_time=humanize_number(await conf.SLOT_TIME()),
                    payday_time=humanize_number(await conf.PAYDAY_TIME()),
                    payday_amount=humanize_number(await conf.PAYDAY_CREDITS()),
                    register_amount=humanize_number(await bank.get_default_balance(guild)),
                    maximum_bal=humanize_number(await bank.get_max_balance(guild)),
                )
            )
        )

    @economyset.command()
    async def slotmin(self, ctx: commands.Context, bid: positive_int):
        """Set the minimum slot machine bid.

        Example:
            - `[p]economyset slotmin 10`

        **Arguments**

        - `<bid>` The new minimum bid for using the slot machine. Default is 5.
        """
        guild = ctx.guild
        is_global = await bank.is_global()
        if is_global:
            slot_max = await self.config.SLOT_MAX()
        else:
            slot_max = await self.config.guild(guild).SLOT_MAX()
        if bid > slot_max:
            await ctx.send(
                _(
                    "Warning: Minimum bid is greater than the maximum bid ({max_bid}). "
                    "Slots will not work."
                ).format(max_bid=humanize_number(slot_max))
            )
        if is_global:
            await self.config.SLOT_MIN.set(bid)
        else:
            await self.config.guild(guild).SLOT_MIN.set(bid)
        credits_name = await bank.get_currency_name(guild)
        await ctx.send(
            _("Minimum bid is now {bid} {currency}.").format(
                bid=humanize_number(bid), currency=credits_name
            )
        )

    @economyset.command()
    async def slotmax(self, ctx: commands.Context, bid: positive_int):
        """Set the maximum slot machine bid.

        Example:
            - `[p]economyset slotmax 50`

        **Arguments**

        - `<bid>` The new maximum bid for using the slot machine. Default is 100.
        """
        guild = ctx.guild
        is_global = await bank.is_global()
        if is_global:
            slot_min = await self.config.SLOT_MIN()
        else:
            slot_min = await self.config.guild(guild).SLOT_MIN()
        if bid < slot_min:
            await ctx.send(
                _(
                    "Warning: Maximum bid is less than the minimum bid ({min_bid}). "
                    "Slots will not work."
                ).format(min_bid=humanize_number(slot_min))
            )
        credits_name = await bank.get_currency_name(guild)
        if is_global:
            await self.config.SLOT_MAX.set(bid)
        else:
            await self.config.guild(guild).SLOT_MAX.set(bid)
        await ctx.send(
            _("Maximum bid is now {bid} {currency}.").format(
                bid=humanize_number(bid), currency=credits_name
            )
        )

    @economyset.command()
    async def slottime(
        self, ctx: commands.Context, *, duration: TimedeltaConverter(default_unit="seconds")
    ):
        """Set the cooldown for the slot machine.

        Examples:
            - `[p]economyset slottime 10`
            - `[p]economyset slottime 10m`

        **Arguments**

        - `<duration>` The new duration to wait in between uses of the slot machine. Default is 5 seconds.
        Accepts: seconds, minutes, hours, days, weeks (if no unit is specified, the duration is assumed to be given in seconds)
        """
        seconds = int(duration.total_seconds())
        guild = ctx.guild
        if await bank.is_global():
            await self.config.SLOT_TIME.set(seconds)
        else:
            await self.config.guild(guild).SLOT_TIME.set(seconds)
        await ctx.send(_("Cooldown is now {num} seconds.").format(num=seconds))

    @economyset.command()
    async def paydaytime(
        self, ctx: commands.Context, *, duration: TimedeltaConverter(default_unit="seconds")
    ):
        """Set the cooldown for the payday command.

        Examples:
            - `[p]economyset paydaytime 86400`
            - `[p]economyset paydaytime 1d`

        **Arguments**

        - `<duration>` The new duration to wait in between uses of payday. Default is 5 minutes.
        Accepts: seconds, minutes, hours, days, weeks (if no unit is specified, the duration is assumed to be given in seconds)
        """
        seconds = int(duration.total_seconds())
        guild = ctx.guild
        if await bank.is_global():
            await self.config.PAYDAY_TIME.set(seconds)
        else:
            await self.config.guild(guild).PAYDAY_TIME.set(seconds)
        await ctx.send(
            _("Value modified. At least {num} seconds must pass between each payday.").format(
                num=seconds
            )
        )

    @economyset.command()
    async def paydayamount(self, ctx: commands.Context, creds: int):
        """Set the amount earned each payday.

        Example:
            - `[p]economyset paydayamount 400`

        **Arguments**

        - `<creds>` The new amount to give when using the payday command. Default is 120.
        """
        guild = ctx.guild
        max_balance = await bank.get_max_balance(ctx.guild)
        if creds <= 0 or creds > max_balance:
            return await ctx.send(
                _("Amount must be greater than zero and less than {maxbal}.").format(
                    maxbal=humanize_number(max_balance)
                )
            )
        credits_name = await bank.get_currency_name(guild)
        if await bank.is_global():
            await self.config.PAYDAY_CREDITS.set(creds)
        else:
            await self.config.guild(guild).PAYDAY_CREDITS.set(creds)
        await ctx.send(
            _("Every payday will now give {num} {currency}.").format(
                num=humanize_number(creds), currency=credits_name
            )
        )

    @economyset.command()
    async def rolepaydayamount(self, ctx: commands.Context, role: discord.Role, creds: int):
        """Set the amount earned each payday for a role.
        Set to `0` to remove the payday amount you set for that role.

        Only available when not using a global bank.

        Example:
            - `[p]economyset rolepaydayamount @Members 400`

        **Arguments**

        - `<role>` The role to assign a custom payday amount to.
        - `<creds>` The new amount to give when using the payday command.
        """
        guild = ctx.guild
        max_balance = await bank.get_max_balance(ctx.guild)
        if creds >= max_balance:
            return await ctx.send(
                _(
                    "The bank requires that you set the payday to be less than"
                    " its maximum balance of {maxbal}."
                ).format(maxbal=humanize_number(max_balance))
            )
        credits_name = await bank.get_currency_name(guild)
        if await bank.is_global():
            await ctx.send(_("The bank must be per-server for per-role paydays to work."))
        else:
            if creds <= 0:  # Because I may as well...
                default_creds = await self.config.guild(guild).PAYDAY_CREDITS()
                await self.config.role(role).clear()
                await ctx.send(
                    _(
                        "The payday value attached to role has been removed. "
                        "Users with this role will now receive the default pay "
                        "of {num} {currency}."
                    ).format(num=humanize_number(default_creds), currency=credits_name)
                )
            else:
                await self.config.role(role).PAYDAY_CREDITS.set(creds)
                await ctx.send(
                    _(
                        "Every payday will now give {num} {currency} "
                        "to people with the role {role_name}."
                    ).format(
                        num=humanize_number(creds), currency=credits_name, role_name=role.name
                    )
                )

    @economyset.command()
    async def registeramount(self, ctx: commands.Context, creds: int):
        """Set the initial balance for new bank accounts.

        Example:
            - `[p]economyset registeramount 5000`

        **Arguments**

        - `<creds>` The new initial balance amount. Default is 0.
        """
        guild = ctx.guild
        max_balance = await bank.get_max_balance(ctx.guild)
        credits_name = await bank.get_currency_name(guild)
        try:
            await bank.set_default_balance(creds, guild)
        except ValueError:
            return await ctx.send(
                _("Amount must be greater than or equal to zero and less than {maxbal}.").format(
                    maxbal=humanize_number(max_balance)
                )
            )
        await ctx.send(
            _("Registering an account will now give {num} {currency}.").format(
                num=humanize_number(creds), currency=credits_name
            )
        )

    # What would I ever do without stackoverflow?
    @staticmethod
    def display_time(seconds, granularity=2):
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
