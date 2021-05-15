import asyncio

from redbot.core.utils.chat_formatting import box, humanize_number

from redbot.core import checks, bank, commands
from redbot.core.i18n import Translator, cog_i18n

from redbot.core.bot import Red  # Only used for type hints

_ = Translator("Bank", __file__)


def is_owner_if_bank_global():
    """
    Command decorator. If the bank is global, it checks if the author is
    bot owner, otherwise it only checks
    if command was used in guild - it DOES NOT check any permissions.

    When used on the command, this should be combined
    with permissions check like `guildowner_or_permissions()`.
    """

    async def pred(ctx: commands.Context):
        author = ctx.author
        if not await bank.is_global():
            if not ctx.guild:
                return False
            return True
        else:
            return await ctx.bot.is_owner(author)

    return commands.check(pred)


@cog_i18n(_)
class Bank(commands.Cog):
    """Bank"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    # SECTION commands

    @is_owner_if_bank_global()
    @checks.guildowner_or_permissions(administrator=True)
    @commands.group()
    async def bankset(self, ctx: commands.Context):
        """Base command for bank settings."""

    @bankset.command(name="showsettings")
    async def bankset_showsettings(self, ctx: commands.Context):
        """Show the current bank settings."""
        cur_setting = await bank.is_global()
        if cur_setting:
            group = bank._config
        else:
            if not ctx.guild:
                return
            group = bank._config.guild(ctx.guild)
        group_data = await group.all()
        bank_name = group_data["bank_name"]
        bank_scope = _("Global") if cur_setting else _("Server")
        currency_name = group_data["currency"]
        default_balance = group_data["default_balance"]
        max_balance = group_data["max_balance"]

        settings = _(
            "Bank settings:\n\nBank name: {bank_name}\nBank scope: {bank_scope}\n"
            "Currency: {currency_name}\nDefault balance: {default_balance}\n"
            "Maximum allowed balance: {maximum_bal}\n"
        ).format(
            bank_name=bank_name,
            bank_scope=bank_scope,
            currency_name=currency_name,
            default_balance=humanize_number(default_balance),
            maximum_bal=humanize_number(max_balance),
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
                ).format(banktype=word, command=f"{ctx.clean_prefix}bankset toggleglobal yes")
            )
        else:
            await bank.set_global(not cur_setting)
            await ctx.send(_("The bank is now {banktype}.").format(banktype=word))

    @is_owner_if_bank_global()
    @checks.guildowner_or_permissions(administrator=True)
    @bankset.command(name="bankname")
    async def bankset_bankname(self, ctx: commands.Context, *, name: str):
        """Set the bank's name."""
        await bank.set_bank_name(name, ctx.guild)
        await ctx.send(_("Bank name has been set to: {name}").format(name=name))

    @is_owner_if_bank_global()
    @checks.guildowner_or_permissions(administrator=True)
    @bankset.command(name="creditsname")
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency."""
        await bank.set_currency_name(name, ctx.guild)
        await ctx.send(_("Currency name has been set to: {name}").format(name=name))

    @is_owner_if_bank_global()
    @checks.guildowner_or_permissions(administrator=True)
    @bankset.command(name="maxbal")
    async def bankset_maxbal(self, ctx: commands.Context, *, amount: int):
        """Set the maximum balance a user can get."""
        try:
            await bank.set_max_balance(amount, ctx.guild)
        except ValueError:
            # noinspection PyProtectedMember
            return await ctx.send(
                _("Amount must be greater than zero and less than {max}.").format(
                    max=humanize_number(bank._MAX_BALANCE)
                )
            )
        await ctx.send(
            _("Maximum balance has been set to: {amount}").format(amount=humanize_number(amount))
        )

    # ENDSECTION

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return
