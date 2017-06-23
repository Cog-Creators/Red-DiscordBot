import discord
from discord.ext import commands


class MemberDefaultAuthor(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        member_converter = commands.MemberConverter()
        try:
            member = await member_converter.convert(ctx, arg)
        except commands.BadArgument:
            if arg.strip() != "":
                raise
            else:
                member = ctx.author
        return member
