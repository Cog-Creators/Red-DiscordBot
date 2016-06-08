import discord
import random
import time
from discord.ext import commands

class Muddycog:
    """The MuddyCog, it looks like a Butterfree."""

    def __init__(self, bot):
        self.bot = bot
        self.funFact = ["Fun fact: It's high noon somewhere in the world", "Fun fact: Scootaloo is best filly",
                                "Fun fact: Banging your head against a wall burns 150 calories an hour.",
                                "Fun fact: Cherophobia is the fear of fun.", "Fun fact: An eagle can kill a young deer and fly away with it.",
                                "Fun fact: A sheep, a duck and a rooster were the first passengers in a hot air balloon.",
                                "Fun fact: 95% of people text things they could never say in person.",
                                "Fun fact: There is a species of spider called the Hobo Spider.",
                                "Fun fact: Why did the chicken cross the road? Because it wanted to, you oppressive bully.",
                                "Fun fact: Heart attacks are more likely to happen on a Monday.",
                                "Fun fact: The Titanic was the first ship to use the SOS signal.",
                                "Fun fact: About 8,000 Americans are injured by musical instruments each year.",
                                "Fun fact: Jarrodfeng likes long walks on the beach and candlelit dinners.",
                                "Fun fact: DT likes Applejack. A lot. Like, authority alarming levels, someone call a doctor."
                                "Fun fact: MuddyHikoku is a butt",
                                "Fun fact: Superxavman believes in triangle magic",
                                "Fun fact: The total number of steps in the Eiffel Tower are 1665.",
                                "Fun fact: [](/cmcexcited) We're adorable!",
                                "Fun fact: MuddyHikoku doesn't know how to code. He just face smashes his keyboard and out pops something useful",
                                "Fun fact: The 20th of March is known as Snowman Burning Day!",
                                "Fun fact: If you leave everything to the last minute… it will only take a minute.",
                                "Fun fact: Dota 2 is a game.",
                                "Fun fact: Paraskavedekatriaphobia is the fear of Friday the 13th!",
                                "Fun fact: Every year more than 2500 left-handed people are killed from using right-handed products.",
                                "Fun fact: George W. Bush was once a cheerleader.",
                                "Fun fact: Muddy thought he could sneak Lunarity past Dog, he was wrong.",
                                "Fun fact: Squirrels forget where they hide about half of their nuts."]

                              

		
		
    @commands.command(hidden=True) #Fun fact generator. 10 minute cooldown.
    async def funfact(self):
                mins = 0
                funFactCD = False
                if mins == 0:
                        return await self.bot.say(random.choice(self.funFact))
                        funFactCD = True
                else:
                        return await self.bot.say("Sorry! One fun fact every 10 minutes, try again in a bit!")
                while funFactCD == True:
                        time.sleep(60)
                        mins += 1
                        if mins == 10:
                                mins = 0
                                funFactCD = False
                        		

def setup(bot):
    bot.add_cog(Muddycog(bot))
