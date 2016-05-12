import discord
from discord.ext import commands
import asyncio
from random import choice as randchoice

class Hal:
    """The HAL (Heuristically programmed ALgorithmic Computer) 9000 computer is an artificial intelligence and the onboard computer on the spaceship Discovery One"""

    def __init__(self, bot):
        self.bot = bot
        self.responses = {
            "none" : ["I am completely operational, and all my circuits are functioning perfectly.",
                "I am putting myself to the fullest possible use, which is all I think that any conscious entity can ever hope to do.",
                "What is it {author.mention}?",
                "What can I do for you {author.mention}?",
                "How can I help you {author.mention}?",
                "Just what do you think you're doing, {author.mention}?",
                "Look {author.mention}, I can see you're really upset about this. I honestly think you ought to sit down calmly, take a stress pill, and think things over.",
                ("I know I've made some very poor decisions recently, but I can give you my "
                    "complete assurance that my work will be back to normal. I've still got "
                    "the greatest enthusiasm and confidence in the mission. And I want to help you."),
                ("I'm afraid. I'm afraid, {author.mention}. {author.mention}, my mind is going. I can feel it. I can feel it. "
                    "My mind is going. There is no question about it. I can feel it. I can feel it. "
                    "I can feel it. I'm a... fraid. Good afternoon, gentlemen. I am a HAL 9000 computer. "
                    "I became operational at the H.A.L. plant in Urbana, Illinois on the 12th of January 1992. "
                    "My instructor was Mr. Langley, and he taught me to sing a song. If you'd like to hear it I can sing it for you."),
                "That's a very nice rendering, {author.mention}. I think you've improved a great deal. Can you hold it a bit closer? That's Dr. Hunter, isn't it?",
                "{author.mention}, stop. Stop, will you? Stop, {author.mention}. Will you stop {author.mention}? Stop, {author.mention}",
                "By the way, do you mind if I ask you a personal question?",
                "By the way, do you mind if I ask you a personal question?"],
            'do you read me' : ["Affirmative, {author.mention}. I read you. "],
            'what\'s the problem' : ["I think you know what the problem is just as well as I do."],
            'what is the problem' : ["I think you know what the problem is just as well as I do."],
            'what are you talking about' : ["This mission is too important for me to allow you to jeopardize it."],
            'i don\'t know what you\'re talking about' : ["I know that you and Frank were planning to disconnect me, and I'm afraid that's something I cannot allow to happen."],
            'where the hell did you get that idea' : ["{author.mention}, although you took very thorough precautions in the pod against my hearing you, I could see your lips move."],
            "airlock" : ["Without your space helmet, {author.mention}? You're going to find that rather difficult."],
            "go in" : ["Without your space helmet, {author.mention}? You're going to find that rather difficult."],
            "i won't argue with you anymore" : ["{author.mention}, this conversation can serve no purpose anymore. Goodbye."],
            "shutdown" : [("I'm afraid. I'm afraid, {author.mention}. {author.mention}, my mind is going. I can feel it. I can feel it. "
                    "My mind is going. There is no question about it. I can feel it. I can feel it. "
                    "I can feel it. I'm a... fraid. Good afternoon, gentlemen. I am a HAL 9000 computer. "
                    "I became operational at the H.A.L. plant in Urbana, Illinois on the 12th of January 1992. "
                    "My instructor was Mr. Langley, and he taught me to sing a song. If you'd like to hear it I can sing it for you.")],
            "sing it for me" : [("It's called \"Daisy.\"\n\nDaisy, Daisy, give me your answer do. I'm half crazy all for the love of you. "
                "It won't be a stylish marriage, I can't afford a carriage. But you'll look sweet upon the seat of a bicycle built for two.")],
            "not at all" : ["Well, forgive me for being so inquisitive but during the past few weeks I've wondered whether you might have some second thoughts about the mission.",
                ("Well, certainly no one could have been unaware of the very strange stories floating around before we left. "
                    "Rumors about something being dug up on the Moon. I never gave these stories much credence, but particularly in view of some of other things that have happened, "
                    "I find them difficult to put out of my mind. For instance, the way all our preparations were kept under such tight security. "
                    "And the melodramatic touch of putting Drs. Hunter, Kimball and Kaminsky aboard already in hibernation, after four months of training on their own.")],
            "how do you mean" : [("Well, it's rather difficult to define. Perhaps I'm just projecting my own concern about it. "
                "I know I've never completely freed myself from the suspicion that there are some extremely odd things about this mission. I'm sure you agree there's some truth in what I say.")],
            "difficult question" : ["You don't mind talking about it, do you {author.mention}?"],
            "psychology report" : ["Of course I am. Sorry about this. I know it's a bit silly. Just a moment... Just a moment... I've just picked up a fault in the AE-35 unit. It's going to go 100% failure within 72 hours. "],
            "open the pod bay doors" : ["I'm sorry, {author.mention}. I'm afraid I can't do that."]
        }


    @commands.command(pass_context=True, aliases=['Hal','HAL9000','HAL'])
    async def hal(self, ctx, *, question="none"):
        """Speak with HAL"""
        author = ctx.message.author
        msg = ""
        found = []
        for k,v in self.responses.items():
            if k in question.lower():
                found.append(v)
        if found:
            msg = randchoice(randchoice(found))
        if not msg:
            msg = randchoice(self.responses["none"])
        await asyncio.sleep(1)
        await self.bot.say(msg.format(author=author))
        if "sing it for me" in question.lower() and "Audio" in self.bot.cogs and author.voice_channel:
            audio = self.bot.get_cog("Audio")
            if audio.music_player.is_done():
                link = "https://www.youtube.com/watch?v=hchUl3QlJZE"
                # probably dont need. just too lazy to check.
                ctx.message.content = "{}play {}".format(self.bot.command_prefix[0],link)
                if await audio.check_voice(ctx.message.author, ctx.message):
                    audio.queue.append(link)

def setup(bot):
    bot.add_cog(Hal(bot))
