from redbot.core import commands


class BotUser(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        user = await commands.MemberConverter().convert(ctx, arg)
        if not user.bot:
            raise commands.BadArgument("The member must be a bot")
        return user
