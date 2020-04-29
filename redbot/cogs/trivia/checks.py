from redbot.core import commands
from redbot.core.i18n import Translator

__all__ = ("trivia_stop_check",)

_ = Translator("Trivia", __file__)


def trivia_stop_check():
    async def predicate(ctx: commands.GuildContext) -> bool:
        session = ctx.cog._get_trivia_session(ctx.channel)
        if session is None:
            raise commands.CheckFailure(_("There is no ongoing trivia session in this channel."))

        author = ctx.author
        auth_checks = (
            await ctx.bot.is_owner(author),
            await ctx.bot.is_mod(author),
            await ctx.bot.is_admin(author),
            author == ctx.guild.owner,
            author == session.ctx.author,
        )
        return any(auth_checks)

    return commands.permissions_check(predicate)
