# -*- coding: utf-8 -*-
# Red Dependencies
import discord

# Red Imports
from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("AdminConverters", __file__)


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
        admin = ctx.command.cog
        if admin is None:
            raise commands.BadArgument(_("The Admin cog is not loaded."))

        conf = admin.conf
        selfroles = await conf.guild(ctx.guild).selfroles()

        role_converter = commands.RoleConverter()
        role = await role_converter.convert(ctx, arg)

        if role.id not in selfroles:
            raise commands.BadArgument(_("The provided role is not a valid selfrole."))
        return role
