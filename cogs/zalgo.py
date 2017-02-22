from discord.ext import commands
from random import randint, choice, sample

ZALGO_DEFAULT_AMT = 3
ZALGO_MAX_AMT = 7

ZALGO_PARAMS = {
    'above': (5, 10),
    'below': (5, 10),
    'overlay': (0, 2)
}

ZALGO_CHARS = {
    'above': ['\u0300', '\u0301', '\u0302', '\u0303', '\u0304', '\u0305', '\u0306', '\u0307', '\u0308', '\u0309', '\u030A', '\u030B', '\u030C', '\u030D', '\u030E', '\u030F', '\u0310', '\u0311', '\u0312', '\u0313', '\u0314', '\u0315', '\u031A', '\u031B', '\u033D', '\u033E', '\u033F', '\u0340', '\u0341', '\u0342', '\u0343', '\u0344', '\u0346', '\u034A', '\u034B', '\u034C', '\u0350', '\u0351', '\u0352', '\u0357', '\u0358', '\u035B', '\u035D', '\u035E', '\u0360', '\u0361'],
    'below': ['\u0316', '\u0317', '\u0318', '\u0319', '\u031C', '\u031D', '\u031E', '\u031F', '\u0320', '\u0321', '\u0322', '\u0323', '\u0324', '\u0325', '\u0326', '\u0327', '\u0328', '\u0329', '\u032A', '\u032B', '\u032C', '\u032D', '\u032E', '\u032F', '\u0330', '\u0331', '\u0332', '\u0333', '\u0339', '\u033A', '\u033B', '\u033C', '\u0345', '\u0347', '\u0348', '\u0349', '\u034D', '\u034E', '\u0353', '\u0354', '\u0355', '\u0356', '\u0359', '\u035A', '\u035C', '\u035F', '\u0362'],
    'overlay': ['\u0334', '\u0335', '\u0336', '\u0337', '\u0338']
}

class Zalgo:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def zalgo(self, *, text: str):
        fw = text.split()[0]
        try:
            amount = min(int(fw), ZALGO_MAX_AMT)
            text = text[len(fw):].strip()
        except ValueError:
            amount = ZALGO_DEFAULT_AMT
        text = self.zalgoify(text.upper(), amount)
        await self.bot.say(text)

    def zalgoify(self, text, amount=3):
        zalgo_text = ''
        for c in text:
            zalgo_text += c
            if c != ' ':
                for t, range in ZALGO_PARAMS.items():
                    range = (round(x*amount/5) for x in range)
                    n = min(randint(*range), len(ZALGO_CHARS[t]))
                    zalgo_text += ''.join(sample(ZALGO_CHARS[t], n))
        return zalgo_text

def setup(bot):
    n = Zalgo(bot)
    bot.add_cog(n)
