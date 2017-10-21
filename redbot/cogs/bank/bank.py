from redbot.core import checks, bank
from redbot.core.i18n import CogI18n
from discord.ext import commands

from redbot.core.bot import Red  # Only used for type hints

_ = CogI18n('Bank', __file__)


def check_global_setting_guildowner():
    """
    Command decorator. If the bank is not global, it checks if the author is
     either the guildowner or has the administrator permission.
    """
    async def pred(ctx: commands.Context):
        author = ctx.author
        if await ctx.bot.is_owner(author):
            return True
        if not await bank.is_global():
            permissions = ctx.channel.permissions_for(author)
            return author == ctx.guild.owner or permissions.administrator

    return commands.check(pred)


def check_global_setting_admin():
    """
    Command decorator. If the bank is not global, it checks if the author is
     either a bot admin or has the manage_guild permission.
    """
    async def pred(ctx: commands.Context):
        author = ctx.author
        if await ctx.bot.is_owner(author):
            return True
        if not await bank.is_global():
            permissions = ctx.channel.permissions_for(author)
            is_guild_owner = author == ctx.guild.owner
            admin_role = await ctx.bot.db.guild(ctx.guild).admin_role()
            return admin_role in author.roles or is_guild_owner or permissions.manage_guild

    return commands.check(pred)


class Bank:
    """Bank"""

    def __init__(self, bot: Red):
        self.bot = bot

    # SECTION commands

    @commands.group()
    @checks.guildowner_or_permissions(administrator=True)
    async def bankset(self, ctx: commands.Context):
        """Base command for bank settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @bankset.command(name="toggleglobal")
    @checks.is_owner()
    async def bankset_toggleglobal(self, ctx: commands.Context):
        """Toggles whether the bank is global or not
        If the bank is global, it will become per-guild
        If the bank is per-guild, it will become global"""
        cur_setting = await bank.is_global()
        await bank.set_global(not cur_setting)

        word = _("per-guild") if cur_setting else _("global")

        await ctx.send(_("The bank is now {}.").format(word))

    @bankset.command(name="bankname")
    @check_global_setting_guildowner()
    async def bankset_bankname(self, ctx: commands.Context, *, name: str):
        """Set the bank's name"""
        await bank.set_bank_name(name, ctx.guild)
        await ctx.send(_("Bank's name has been set to {}").format(name))

    @bankset.command(name="creditsname")
    @check_global_setting_guildowner()
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency"""
        await bank.set_currency_name(name, ctx.guild)
        await ctx.send(_("Currency name has been set to {}").format(name))

    # ENDSECTION
