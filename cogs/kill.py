from discord.ext import commands
import random
import discord


class Kill:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def kill(self, context, member: discord.Member):
        """Have you always wanted to kill someone? If so, do it in a creative way!"""
        killer = context.message.author.mention
        victim = member.mention
        ways_to_kill = {}
        ways_to_kill['1'] = '{0} shoves a double barreled shotgun into {1}\'s mouth and squeezes the trigger of the gun, causing {1}\'s head to horrifically explode like a ripe pimple, splattering the young person\'s brain matter, gore, and bone fragments all over the walls and painting it a crimson red.'.format(killer, victim)
        ways_to_kill['3'] = 'Screaming in sheer terror and agony, {0} is horrifically dragged into the darkness by unseen forces, leaving nothing but bloody fingernails and a trail of scratch marks in the ground from which the young person had attempted to halt the dragging process.'.format(victim)
        ways_to_kill['4'] = '{0} takes a machette and starts hacking away on {1}, chopping {1} into dozens of pieces.'.format(killer, victim)
        ways_to_kill['5'] = '{0} pours acid over {1}. *"Well don\'t you look pretty right now?"*'.format(killer, victim)
        ways_to_kill['6'] = '{0} screams in terror as a giant creature with huge muscular arms grab {0}\'s head; {0}\'s screams of terror are cut off as the creature tears off the head with a sickening crunching sound. {0}\'s spinal cord, which is still attached to the dismembered head, is used by the creature as a makeshift sword to slice a perfect asymmetrical line down {0}\'s body, causing the organs to spill out as the two halves fall to their respective sides.'.format(victim)
        ways_to_kill['7'] = '{0} grabs {1}\'s head and tears it off with superhuman speed and efficiency. Using {1}\'s head as a makeshift basketball, {0} expertly slams dunk it into the basketball hoop, much to the applause of the audience watching the gruesome scene.'.format(killer, victim)
        ways_to_kill['8'] = '{0} uses a shiv to horrifically stab {1} multiple times in the chest and throat, causing {1} to gurgle up blood as the young person horrifically dies.'.format(killer, victim)
        ways_to_kill['9'] = '{0} screams as Pyramid Head lifts Sarcen up using his superhuman strength. Before {0} can even utter a scream of terror, Pyramid Head uses his superhuman strength to horrifically tear {0} into two halves; {0} stares at the monstrosity in shock and disbelief as {0} gurgles up blood, the upper body organs spilling out of the dismembered torso, before the eyes roll backward into the skull.'.format(victim)
        ways_to_kill['10'] = '{0} steps on a land mine and is horrifically blown to multiple pieces as the device explodes, the {0}\'s entrails and gore flying up and splattering all around as if someone had thrown a watermelon onto the ground from the top of a multiple story building.'.format(victim)
        ways_to_kill['11'] = '{0} is killed instantly as the top half of his head is blown off by a Red Army sniper armed with a Mosin Nagant, {0}\'s brains splattering everywhere in a horrific fashion.'.format(victim)

        await self.bot.say('**{0}**'.format(random.choice([ways_to_kill[i] for i in ways_to_kill])))


def setup(bot):
    n = Kill(bot)
    bot.add_cog(n)
