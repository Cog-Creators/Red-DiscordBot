import discord
from discord.ext import commands
from random import choice as randchoice

class Fuck:
    """Display fuck you statements"""

    def __init__(self, bot):
        self.bot = bot
        self.fuck = ["You are a fucking fucktard {}! ~{}","Fuck you, {}. ~{}", "Fucking fuck off, {}. ~{}","Fuck off, {}. ~{}","Fuck this, {}. ~{}", "Fuck that, {}. ~{}","You are a fucking faggot, {}. ~{}","{}, Thou clay-brained guts, thou knotty-pated fool, thou whoreson obscene greasy tallow-catch! ~{}","Oh fuck off, just really fuck off you total dickface. Christ {}, you are fucking thick. ~{}","{}, why don't you go outside and play hide-and-go-fuck-yourself? ~{} ","Hey {}, what a fascinating story, in what chapter do you shut the fuck up?\n\nSincerly,\n{}","What you've just said is one of the most insanely idiotic things I have ever heard, {}. At no point in your rambling, incoherent response were you even close to anything that could be considered a rational thought. Everyone in this room is now dumber for having listened to it. I award you no points :name, and may God have mercy on your soul. ~{}"]

    @commands.command(pass_context=True, no_pm=True)
    async def fuckyou(self, ctx, user : discord.Member=None):
        """Get fuck you statements"""
        
        auth = ctx.message.author
        if not user:
            data = discord.Embed(colour=auth.colour)
            data.add_field(name="Error:warning:",value="You have to mention a user, {}".format(auth.mention))
            await self.bot.say(embed=data)
        else:
            fuck = randchoice(self.fuck).format(user.mention, auth.mention)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Fuck You!:middle_finger:",value="{}".format(fuck))
            await self.bot.say(embed=data)

def setup(bot):
    bot.add_cog(Fuck(bot))
