import discord
from redbot.core import commands


class MemberDefaultAuthor(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> discord.Member:
        member_converter = commands.MemberConverter()
        try:
            member = await member_converter.convert(ctx, arg)
        except commands.BadArgument:
            if arg.strip() != "":
                raise
            else:
                member = ctx.author
        return member


class SelfRole(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> discord.Role:
        admin = ctx.command.instance
        if admin is None:
            raise commands.BadArgument("Admin is not loaded.")

        conf = admin.conf
        selfroles = await conf.guild(ctx.guild).selfroles()

        role_converter = commands.RoleConverter()
        role = await role_converter.convert(ctx, arg)

        if role.id not in selfroles:
            raise commands.BadArgument("The provided role is not a valid selfrole.")
        return role
