import discord
from redbot.core.utils.chat_formatting import box

from redbot.core import checks, bank, commands
from redbot.core.i18n import Translator, cog_i18n

from redbot.core.bot import Red  # Only used for type hints

_ = Translator("Bank", __file__)


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
            permissions = ctx.channel.permissions_for(author)
            is_guild_owner = author == ctx.guild.owner
            admin_role = await ctx.bot.db.guild(ctx.guild).admin_role()
            return admin_role in author.roles or is_guild_owner or permissions.manage_guild
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

    @check_global_setting_guildowner()
    @checks.guildowner_or_permissions(administrator=True)
    @commands.group(autohelp=True)
    async def bankset(self, ctx: commands.Context):
        """Base command for bank settings"""
        if ctx.invoked_subcommand is None:
            if await bank.is_global():
                bank_name = await bank._conf.bank_name()
                currency_name = await bank._conf.currency()
                default_balance = await bank._conf.default_balance()
            else:
                if not ctx.guild:
                    return
                bank_name = await bank._conf.guild(ctx.guild).bank_name()
                currency_name = await bank._conf.guild(ctx.guild).currency()
                default_balance = await bank._conf.guild(ctx.guild).default_balance()

            settings = _(
                "Bank settings:\n\nBank name: {bank_name}\nCurrency: {currency_name}\n"
                "Default balance: {default_balance}"
            ).format(
                bank_name=bank_name, currency_name=currency_name, default_balance=default_balance
            )
            await ctx.send(box(settings))

    @bankset.command(name="toggleglobal")
    @checks.is_owner()
    async def bankset_toggleglobal(self, ctx: commands.Context, confirm: bool = False):
        """Toggles whether the bank is global or not
        If the bank is global, it will become per-server
        If the bank is per-server, it will become global"""
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
        """Set the bank's name"""
        await bank.set_bank_name(name, ctx.guild)
        await ctx.send(_("Bank name has been set to: {name}").format(name=name))

    @bankset.command(name="creditsname")
    @check_global_setting_guildowner()
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency"""
        await bank.set_currency_name(name, ctx.guild)
        await ctx.send(_("Currency name has been set to: {name}").format(name=name))

    # ENDSECTION
