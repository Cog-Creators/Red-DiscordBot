from collections import namedtuple
from typing import Union

import discord

from redbot.cogs.mod.converters import RawUserIds
from redbot.core import bank, checks, commands, errors
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

_ = Translator("Bank", __file__)
MOCK_MEMBER = namedtuple("Member", "id guild")


def check_global_setting_guildowner():
    """
    Command decorator. If the bank is not global, it checks if the author is
     either the guildowner or has the administrator permission.
    """

    async def pred(ctx: commands.Context):
        author = ctx.author
        if not await bank.is_global():
            if not isinstance(ctx.channel, discord.abc.GuildChannel):
                return False
            if await ctx.bot.is_owner(author):
                return True
            permissions = ctx.channel.permissions_for(author)
            return author == ctx.guild.owner or permissions.administrator
        else:
            return await ctx.bot.is_owner(author)

    return commands.check(pred)


def check_global_setting_admin():
    """
    Command decorator. If the bank is not global, it checks if the author is
     either a bot admin or has the manage_guild permission.
    """

    async def pred(ctx: commands.Context):
        author = ctx.author
        if not await bank.is_global():
            if not isinstance(ctx.channel, discord.abc.GuildChannel):
                return False
            if await ctx.bot.is_owner(author):
                return True
            if author == ctx.guild.owner:
                return True
            if ctx.channel.permissions_for(author).manage_guild:
                return True
            admin_roles = set(await ctx.bot.db.guild(ctx.guild).admin_role())
            for role in author.roles:
                if role.id in admin_roles:
                    return True
        else:
            return await ctx.bot.is_owner(author)

    return commands.check(pred)


def guild_only_check():
    async def pred(ctx: commands.Context):
        if await bank.is_global() or (not await bank.is_global() and ctx.guild is not None):
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
class Bank(commands.Cog):
    """Bank"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    @guild_only_check()
    @check_global_setting_admin()
    @checks.guildowner_or_permissions(administrator=True)
    @commands.group(autohelp=True)
    async def bankset(self, ctx: commands.Context):
        """Manage the bank settings."""
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            bank_name = await bank.get_bank_name(guild)
            currency_name = await bank.get_currency_name(guild)
            default_balance = await bank.get_default_balance(guild)
            settings = _(
                "Bank settings:\n\n"
                "Bank name: {bank_name}\n"
                "Currency: {currency_name}\n"
                "Initial balance: {default_balance}\n"
                "Maximum allowed balance: {maximum_bal}"
            ).format(
                bank_name=bank_name,
                currency_name=currency_name,
                default_balance=humanize_number(default_balance),
                maximum_bal=humanize_number(await bank.get_max_balance(ctx.guild)),
            )
            await ctx.send(box(settings))

    @bankset.command(name="toggleglobal")
    @checks.is_owner()
    async def bankset_toggleglobal(self, ctx: commands.Context, confirm: bool = False):
        """Toggle whether the bank is global or not.

        If the bank is global, it will become per-server.
        If the bank is per-server, it will become global.
        """
        cur_setting = await bank.is_global()

        word = _("per-server") if cur_setting else _("global")
        if confirm is False:
            await ctx.send(
                _(
                    "This will toggle the bank to be {banktype}, deleting all accounts "
                    "in the process! If you're sure, type `{command}`"
                ).format(banktype=word, command="{}bankset toggleglobal yes".format(ctx.prefix))
            )
        else:
            await bank.set_global(not cur_setting)
            await ctx.send(_("The bank is now {banktype}.").format(banktype=word))

    @bankset.command(name="bankname")
    @check_global_setting_guildowner()
    async def bankset_bankname(self, ctx: commands.Context, *, name: str):
        """Set the bank's name."""
        await bank.set_bank_name(name, ctx.guild)
        await ctx.send(_("Bank name has been set to: {name}").format(name=name))

    @bankset.command(name="creditsname")
    @check_global_setting_guildowner()
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency."""
        await bank.set_currency_name(name, ctx.guild)
        await ctx.send(_("Currency name has been set to: {name}").format(name=name))

    @bankset.command(name="maxbal")
    @check_global_setting_guildowner()
    async def bankset_maxbal(self, ctx: commands.Context, *, amount: int):
        """Set the maximum balance a user can get."""
        try:
            await bank.set_max_balance(amount, ctx.guild)
        except ValueError as e:
            return await ctx.send(str(e))
        await ctx.send(
            _("Maximum balance has been set to: {amount}").format(amount=humanize_number(amount))
        )

    @bankset.command()
    async def initialbalance(self, ctx: commands.Context, creds: int):
        """Set the initial balance for new bank accounts."""
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
            _("New accounts will start with {num} {currency}.").format(
                num=humanize_number(creds), currency=credits_name
            )
        )

    @guild_only_check()
    @commands.group(name="bank")
    async def _bank(self, ctx: commands.Context):
        """Manage the bank."""
        pass

    @_bank.command()
    @check_global_setting_guildowner()
    async def reset(self, ctx, confirmation: bool = False):
        """Delete all bank accounts."""
        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for {scope}.\nIf you're sure, type "
                    "`{prefix}bank reset yes`"
                ).format(
                    scope=self.bot.user.name if await bank.is_global() else _("this server"),
                    prefix=ctx.prefix,
                )
            )
        else:
            await bank.wipe_bank(guild=ctx.guild)
            await ctx.send(
                _("All bank accounts for {scope} have been deleted.").format(
                    scope=self.bot.user.name if await bank.is_global() else _("this server")
                )
            )

    @_bank.group(name="prune")
    @check_global_setting_admin()
    async def _prune(self, ctx):
        """Prune bank accounts."""
        pass

    @_prune.command(name="local")
    @commands.guild_only()
    @checks.guildowner()
    async def _local(self, ctx, confirmation: bool = False):
        """Prune bank accounts for users no longer in the server."""
        global_bank = await bank.is_global()
        if global_bank is True:
            return await ctx.send(_("This command cannot be used with a global bank."))

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for users no longer in this server."
                    "\nIf you're sure, type "
                    "`{prefix}bank prune local yes`"
                ).format(prefix=ctx.prefix)
            )
        else:
            await bank.bank_prune(self.bot, guild=ctx.guild)
            await ctx.send(
                _("Bank accounts for users no longer in this server have been deleted.")
            )

    @_prune.command(name="global")
    @checks.is_owner()
    async def _global(self, ctx, confirmation: bool = False):
        """Prune bank accounts for users who no longer share a server with the bot."""
        global_bank = await bank.is_global()
        if global_bank is False:
            return await ctx.send(_("This command cannot be used with a local bank."))

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for users "
                    "who no longer share a server with the bot."
                    "\nIf you're sure, type `{prefix}bank prune global yes`"
                ).format(prefix=ctx.prefix)
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
        """Delete the bank account of a specified user."""
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
                ).format(prefix=ctx.prefix, id=uid, name=name)
            )
        else:
            await bank.bank_prune(self.bot, guild=ctx.guild, user_id=uid)
            await ctx.send(_("The bank account for {name} has been pruned.").format(name=name))

    @guild_only_check()
    @commands.group(name="balance")
    async def _balance(self, ctx: commands.Context):
        """Manage the currency."""
        pass

    @_balance.command(name="check")
    async def _balance_check(self, ctx: commands.Context, user: discord.Member = None):
        """Show the user's account balance.

        Defaults to yours."""
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

    @_balance.command(name="transfer")
    async def _balance_transfer(self, ctx: commands.Context, to: discord.Member, amount: int):
        """Transfer currency to other users."""
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

    @_balance.command(name="set")
    @check_global_setting_admin()
    async def _balance_set(self, ctx: commands.Context, to: discord.Member, creds: SetParser):
        """Set the balance of user's bank account.

        Passing positive and negative values will add/remove currency instead.

        Examples:
        - `[p]bank set @Twentysix 26` - Sets balance to 26
        - `[p]bank set @Twentysix +2` - Increases balance by 2
        - `[p]bank set @Twentysix -6` - Decreases balance by 6
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

    @commands.command()
    @guild_only_check()
    async def leaderboard(self, ctx: commands.Context, top: int = 10, show_global: bool = False):
        """Print the leaderboard.

        Defaults to top 10.
        """
        guild = ctx.guild
        author = ctx.author
        max_bal = await bank.get_max_balance(ctx.guild)
        if top < 1:
            top = 10
        if await bank.is_global() and show_global:
            # show_global is only applicable if bank is global
            bank_sorted = await bank.get_leaderboard(positions=top, guild=None)
        else:
            bank_sorted = await bank.get_leaderboard(positions=top, guild=guild)
        try:
            if bank_sorted[0][1]["balance"] > max_bal:
                bal_len = len(humanize_number(max_bal))
            else:
                bal_len = len(humanize_number(bank_sorted[0][1]["balance"]))
            # first user is the largest we'll see
        except IndexError:
            return await ctx.send(_("There are no accounts in the bank."))
        pound_len = len(str(len(bank_sorted)))
        header = "{pound:{pound_len}}{score:{bal_len}}{name:2}\n".format(
            pound="#",
            name=_("Name"),
            score=_("Score"),
            bal_len=bal_len + 6,
            pound_len=pound_len + 3,
        )
        highscores = []
        pos = 1
        temp_msg = header
        for acc in bank_sorted:
            try:
                name = guild.get_member(acc[0]).display_name
            except AttributeError:
                user_id = ""
                if await ctx.bot.is_owner(ctx.author):
                    user_id = f"({str(acc[0])})"
                name = f"{acc[1]['name']} {user_id}"

            balance = acc[1]["balance"]
            if balance > max_bal:
                balance = max_bal
                await bank.set_balance(MOCK_MEMBER(acc[0], guild), balance)
            balance = humanize_number(balance)
            if acc[0] != author.id:
                temp_msg += (
                    f"{f'{humanize_number(pos)}.': <{pound_len+2}} "
                    f"{balance: <{bal_len + 5}} {name}\n"
                )

            else:
                temp_msg += (
                    f"{f'{humanize_number(pos)}.': <{pound_len+2}} "
                    f"{balance: <{bal_len + 5}} "
                    f"<<{author.display_name}>>\n"
                )
            if pos % 10 == 0:
                highscores.append(box(temp_msg, lang="md"))
                temp_msg = header
            pos += 1

        if temp_msg != header:
            highscores.append(box(temp_msg, lang="md"))

        if highscores:
            await menu(ctx, highscores, DEFAULT_CONTROLS)
