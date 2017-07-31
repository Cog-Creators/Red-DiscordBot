from discord.ext import commands
from core import Config


class Test:

    def __init__(self, bot):
        self.bot = bot
        self.key = 10294240520345
        self.conf = Config.get_conf(
            self.__class__.__name__,
            self.key
        )
        self.conf.register_guild(asd={})

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Tested?")

    @commands.command(name='eval')
    async def _eval(self, ctx, *, to_eval):
        await ctx.send("```py\n" + str(eval(to_eval)) + "```")

    @commands.command()
    async def tset(self, ctx):
        await self.conf.guild(ctx.guild).set('is_enabled', True)

    @commands.command()
    async def tcheck(self, ctx):
        await ctx.send(str(self.conf.guild(ctx.guild).asd()))


def setup(bot):
    bot.add_cog(Test(bot))
