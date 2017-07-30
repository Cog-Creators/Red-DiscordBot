from discord.ext import commands

from core import checks, bank
from core.bot import Red  # Only used for type hints


def check_global_setting_guildowner():
    async def pred(ctx: commands.Context):
        if bank.is_global():
            return checks.is_owner()
        else:
            return checks.guildowner_or_permissions(administrator=True)
    return commands.check(pred)


def check_global_setting_admin():
    async def pred(ctx: commands.Context):
        if bank.is_global():
            return checks.is_owner()
        else:
            return checks.admin_or_permissions(manage_guild=True)
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
            await self.bot.send_cmd_help(ctx)

    @bankset.command(name="toggleglobal")
    @checks.is_owner()
    async def bankset_toggleglobal(self, ctx: commands.Context):
        """Toggles whether the bank is global or not
        If the bank is global, it will become per-guild
        If the bank is per-guild, it will become global"""
        cur_setting = bank.is_global()
        await bank.set_global(not cur_setting, ctx.author)

        word = "per-guild" if cur_setting else "global"

        await ctx.send("The bank is now {}.".format(word))

    @bankset.command(name="bankname")
    @check_global_setting_guildowner()
    async def bankset_bankname(self, ctx: commands.Context, *, name: str):
        """Set the bank's name"""
        await bank.set_bank_name(name, ctx.guild)
        await ctx.send("Bank's name has been set to {}".format(name))

    @bankset.command(name="creditsname")
    @check_global_setting_guildowner()
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency"""
        await bank.set_currency_name(name, ctx.guild)
        await ctx.send("Currency name has been set to {}".format(name))

    # ENDSECTION
