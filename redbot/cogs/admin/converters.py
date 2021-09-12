import discord
from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("AdminConverters", __file__)


class SelfRole(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> discord.Role:
        admin = ctx.command.cog
        if admin is None:
            raise commands.BadArgument(_("The Admin cog is not loaded."))

        role_converter = commands.RoleConverter()
        role = await role_converter.convert(ctx, arg)

        selfroles = await admin.config.guild(ctx.guild).selfroles()

        if role.id not in selfroles:
            raise commands.BadArgument(_("The provided role is not a valid selfrole."))
        return role
