from discord.ext import commands
from __main__ import send_cmd_help
import random
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Dicetable:
    """Rolls a table of dice"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def dicetable(self, ctx):
        """Shows a list under this group commands."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @dicetable.command(name="d20", pass_context=False)
    async def _d20_dicetable(self, number: int, modifier: int):
        """Rolls a number of d20's plus your modifier
        Example: 'dicetable d20 6 2' rolls 6 d20s with a +2 modifier"""
        if number < 20:
            roll_name = ["Roll 1", "Roll 2", "Roll 3", "Roll 4", "Roll 5",
                         "Roll 6", "Roll 7", "Roll 8", "Roll 9", "Roll 10",
                         "Roll 11",  "Roll 12",  "Roll 13",  "Roll 14",
                         "Roll 15", "Roll 16",  "Roll 17",  "Roll 18",
                         "Roll 19",  "Roll 20"
                         ]
            rolls = []
            modplus = []
            totals = []

            k = "+" + str(modifier)
            while number > 0:
                b = random.randint(1, 20)
                total = b + modifier
                totals.append(total)
                rolls.append(b)
                modplus.append(k)
                number = number-1
            m = list(zip(roll_name, rolls,  modplus, totals))
            t = tabulate(m, headers=["Roll #", "Results", "Modifier",
                                     "Totals"
                                     ]
                         )
            await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("```" + "Can only roll 20 dice at a time" +
                               "```")

    @dicetable.command(name="d12", pass_context=False)
    async def _d12_dicetable(self, number: int, modifier: int):
        """Rolls a number of d12's plus your modifier
        Example: `dicetable d12 6 2` rolls 6 d12s with a +2 modifier"""
        if number < 20:
            roll_name = ["Roll 1", "Roll 2", "Roll 3", "Roll 4", "Roll 5",
                         "Roll 6", "Roll 7", "Roll 8", "Roll 9", "Roll 10",
                         "Roll 11",  "Roll 12",  "Roll 13",  "Roll 14",
                         "Roll 15", "Roll 16",  "Roll 17",  "Roll 18",
                         "Roll 19",  "Roll 20"
                         ]
            rolls = []
            modplus = []
            totals = []

            k = "+" + str(modifier)
            while number > 0:
                b = random.randint(1, 12)
                total = b + modifier
                totals.append(total)
                rolls.append(b)
                modplus.append(k)
                number = number-1
            m = list(zip(roll_name, rolls,  modplus, totals))
            t = tabulate(m, headers=["Roll #", "Results", "Modifier",
                                     "Totals"
                                     ]
                         )
            await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("```" + "Can only roll 20 dice at a time" +
                               "```")

    @dicetable.command(name="d10", pass_context=False)
    async def _d10_dicetable(self, number: int, modifier: int):
        """Rolls a number of d10's plus your modifier
        Example: 'dicetable d10 6 2' rolls 6 d10s with a +2 modifier
        """
        if number < 20:
            roll_name = ["Roll 1", "Roll 2", "Roll 3", "Roll 4", "Roll 5",
                         "Roll 6", "Roll 7", "Roll 8", "Roll 9", "Roll 10",
                         "Roll 11",  "Roll 12",  "Roll 13",  "Roll 14",
                         "Roll 15", "Roll 16",  "Roll 17",  "Roll 18",
                         "Roll 19",  "Roll 20"
                         ]
            rolls = []
            modplus = []
            totals = []

            k = "+" + str(modifier)
            while number > 0:
                b = random.randint(1, 10)
                total = b + modifier
                totals.append(total)
                rolls.append(b)
                modplus.append(k)
                number = number-1
            m = list(zip(roll_name, rolls,  modplus, totals))
            t = tabulate(m, headers=["Roll #", "Results", "Modifier",
                                     "Totals"
                                     ]
                         )
            await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("```" + "Can only roll 20 dice at a time" +
                               "```")

    @dicetable.command(name="d8", pass_context=False)
    async def _d8_dicetable(self, number: int, modifier: int):
        """Rolls a number of d8's plus your modifier
        Example: `dicetable d8 6 2` rolls 6 d8s with a +2 modifier"""
        if number < 20:
            roll_name = ["Roll 1", "Roll 2", "Roll 3", "Roll 4", "Roll 5",
                         "Roll 6", "Roll 7", "Roll 8", "Roll 9", "Roll 10",
                         "Roll 11",  "Roll 12",  "Roll 13",  "Roll 14",
                         "Roll 15", "Roll 16",  "Roll 17",  "Roll 18",
                         "Roll 19",  "Roll 20"
                         ]
            rolls = []
            modplus = []
            totals = []

            k = "+" + str(modifier)
            while number > 0:
                b = random.randint(1, 8)
                total = b + modifier
                totals.append(total)
                rolls.append(b)
                modplus.append(k)
                number = number-1
            m = list(zip(roll_name, rolls,  modplus, totals))
            t = tabulate(m, headers=["Roll #", "Results", "Modifier",
                                     "Totals"
                                     ]
                         )
            await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("```" + "Can only roll 20 dice at a time" +
                               "```")

    @dicetable.command(name="d6", pass_context=False)
    async def _d6_dicetable(self, number: int, modifier: int):
        """Rolls a number of d6's plus your modifier
        Example: `dicetable d6 4 2` rolls 4 d6s with a +2 modifier"""
        if number < 20:
            roll_name = ["Roll 1", "Roll 2", "Roll 3", "Roll 4", "Roll 5",
                         "Roll 6", "Roll 7", "Roll 8", "Roll 9", "Roll 10",
                         "Roll 11",  "Roll 12",  "Roll 13",  "Roll 14",
                         "Roll 15", "Roll 16",  "Roll 17",  "Roll 18",
                         "Roll 19",  "Roll 20"
                         ]
            rolls = []
            modplus = []
            totals = []

            k = "+" + str(modifier)
            while number > 0:
                b = random.randint(1, 6)
                total = b + modifier
                totals.append(total)
                rolls.append(b)
                modplus.append(k)
                number = number-1
            m = list(zip(roll_name, rolls,  modplus, totals))
            t = tabulate(m, headers=["Roll #", "Results", "Modifier",
                                     "Totals"
                                     ]
                         )
            await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("```" + "Can only roll 20 dice at a time" +
                               "```")

    @dicetable.command(name="d4", pass_context=False)
    async def _d4_dicetable(self, number: int, modifier: int):
        """Rolls a number of d4's plus your modifier
        Example: `dicetable d4 6 2` rolls 6 d4s with a +2 modifier"""
        if number < 20:
            roll_name = ["Roll 1", "Roll 2", "Roll 3", "Roll 4", "Roll 5",
                         "Roll 6", "Roll 7", "Roll 8", "Roll 9", "Roll 10",
                         "Roll 11",  "Roll 12",  "Roll 13",  "Roll 14",
                         "Roll 15", "Roll 16",  "Roll 17",  "Roll 18",
                         "Roll 19",  "Roll 20"
                         ]
            rolls = []
            modplus = []
            totals = []

            k = "+" + str(modifier)
            while number > 0:
                b = random.randint(1, 4)
                total = b + modifier
                totals.append(total)
                rolls.append(b)
                modplus.append(k)
                number = number-1
            m = list(zip(roll_name, rolls,  modplus, totals))
            t = tabulate(m, headers=["Roll #", "Results", "Modifier",
                                     "Totals"
                                     ]
                         )
            await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("```" + "Can only roll 20 dice at a time" +
                               "```")


def setup(bot):
    bot.add_cog(Dicetable(bot))
