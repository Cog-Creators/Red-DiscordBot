import random
from discord.ext import commands

class Deepthought:
    """Deepthought's Commands."""
    def __init__(self, bot):
        self.bot = bot
        with open('data/deepthought/fortunes.txt', encoding='utf-8', mode="r") as f:
            self._fortunes = f.read().split('\n')

    @commands.command(name='deepthought')
    async def deepthought(self):
        message = random.choice(self._fortunes)
        await self.bot.say('_{}_\n\n_Your Lucky Numbers: **{}, {}, {}, {}, {}, {}**_'.format(message, random.randint(1, 100), random.randint(1, 100), random.randint(1, 100), random.randint(1, 100), random.randint(1, 100), random.randint(1, 100)))


def setup(bot):
    n = Deepthought(bot)
    bot.add_cog(n)