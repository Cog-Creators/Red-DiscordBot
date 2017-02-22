from random import choice as randchoice
from discord.ext import commands

chucks = {
    1: 'Some kids piss their name in the snow. Chuck Norris can piss his name into concrete.',
    2: 'Chuck Norris once visited the Virgin Islands. They are now The Islands.',
    3: 'Chuck Norris counted to infinity - twice.',
    4: 'Leading hand sanitizers claim they can kill 99.9 percent of germs. Chuck Norris can kill 100 percent of whatever the fuck he wants.',
    5: 'Chuck Norris tears cure cancer. Too bad he has never cried.',
    6: 'Chuck Norris calendar goes straight from March 31st to April 2nd; no one fools Chuck Norris.',
    7: 'Chuck Norris does not sleep. He waits.',
    8: 'Chuck Norris can speak braille.',
    9: 'Once, while having sex in a tractor-trailer, part of Chuck Norris sperm escaped and got into the engine. We now know this truck as Optimus Prime.',
    10: 'Chuck Norris puts the "laughter" in "manslaughter".',
    11: 'If you spell Chuck Norris wrong on Google it does not say, "Did you mean Chuck Norris?" It simply replies, "Run while you still have the chance."',
    12: 'On a high school math test, Chuck Norris put down "Violence" as every one of the answers. He got an A+ on the test because Chuck Norris solves all his problems with Violence.',
    13: 'Chuck Norris owns the greatest Poker Face of all-time. It helped him win the 1983 World Series of Poker despite him holding just a Joker, a Get out of Jail Free Monopoly card, a 2 of clubs, 7 of spades and a green #4 card from the game Uno.',
    14: 'Chuck Norris can do a wheelie on a unicycle.',
    15: 'Chuck Norris once won a game of Connect Four in 3 moves.',
    16: 'Chuck Norris can delete the Recycling Bin.When the Boogeyman goes to sleep every night he checks his closet for Chuck Norris.',
    17: 'Once a cobra bit Chuck Norris leg. After five days of excruciating pain, the cobra died.',
    18: 'Chuck Norris was originally cast as the main character in 24, but was replaced by the producers when he managed to kill every terrorist and save the day in 12 minutes and 37 seconds.',
    19: 'Chuck Norris died ten years ago, but the Grim Reaper cant get up the courage to tell him.',
    20: 'Chuck Norris does not hunt because the word hunting implies the possibility of failure. Chuck Norris goes killing.',
    21: 'Chuck Norris can slam revolving doors.',
    22: 'If it looks like chicken, tastes like chicken, and feels like chicken but Chuck Norris says its beef, then it is fucking beef.',
    23: 'Chuck Norris can have both feet on the ground and kick ass at the same time.',
    24: 'Superman owns a pair of Chuck Norris pajamas.',
    25: 'Giraffes were created when Chuck Norris uppercutted a horse.',
    26: 'Chuck Norris does not read books. He stares them down until he gets the information he wants.',
    27: 'Chuck Norris sleeps with a night light. Not because Chuck Norris is afraid of the dark, but the dark is afraid of Chuck Norris',
    28: 'Chuck Norris secretly sleeps with every woman in the world once a month. They bleed for a week as a result.',
    29: 'When Chuck Norris gives you the finger, he is telling you how many seconds you have left to live.',
    30: 'Chuck Norris dog is trained to pick up his own poop because Chuck Norris will not take shit from anyone.',
    31: 'Chuck Norris sold his soul to the devil for his rugged good looks and unparalleled martial arts ability. Shortly after the transaction was finalized, Chuck roundhouse kicked the devil in the face and took his soul back. The devil, who appreciates irony, couldnt stay mad and admitted he should have seen it coming. They now play poker every second Wednesday of the month.',
    32: 'If you play Led Zeppelins "Stairway to Heaven" backwards, you will hear Chuck Norris banging your sister.',
    33: 'Chuck Norris can kill two stones with one bird',
    34: 'Chuck Norris does not have hair on his testicles, because hair does not grow on steel..',
    35: 'Chuck Norris is always on top during sex because Chuck Norris never fucks up.',
    36: 'Chuck Norris was once on Celebrity Wheel of Fortune and was the first to spin. The next 29 minutes of the show consisted of everyone standing around awkwardly, waiting for the wheel to stop.',
    37: 'Chuck Norris is the only person on the planet that can kick you in the back of the face.',
    38: 'Chuck Norris eats the core of an apple first.',
    39: 'Chuck Norris does not pop his collar, his shirts just get erections when they touch his body.',
    40: 'Bill Gates lives in constant fear that Chuck Norris PC will crash.',
    41: 'Ghosts are actually caused by Chuck Norris killing people faster than Death can process them.',
    42: 'Death once had a near-Chuck-Norris experience.',
    43: 'The best part of waking up is not Folgers in your cup, but knowing that Chuck Norris didnt kill you in your sleep.',
    44: 'Chuck Norris never retreats, he just attacks in the opposite direction.',
    45: 'Chuck Norris house does not have security guards. Rather, he employs a single man in uniform to lead burglars to his bedroom, where they are never heard from again.',
    46: 'Chuck Norris was once charged with three attempted murdered in Boulder County, but the Judge quickly dropped the charges because Chuck Norris does not "attempt" murder.',
    47: 'Chuck Norris can strangle you with a cordless phone.',
    48: 'The reason newborn babies cry is because they know they have just entered a world with Chuck Norris.',
    49: 'Chuck Norris has to maintain a concealed weapon license in all 50 states in order to legally wear pants.',
    50: 'Chuck Norris can build a snowman out of rain.',
    51: 'Chuck Norris plays russian roulette with a fully loded revolver... and wins.',
    52: 'M.C. Hammer learned the hard way that Chuck Norris can touch this.',
    53: 'Chuck Norris once punched a man in the soul.',
    54: 'Chuck Norris is not hung like a horse... horses are hung like Chuck Norris',
    55: 'Chuck Norris likes to knit sweaters in his free time. And by "knit", I mean "kick", and by "sweaters", I mean "babies".',
    56: 'Chuck Norris is 1/8th Cherokee. This has nothing to do with ancestry, the man ate a fucking Jeep.',
    57: 'When Chuck Norris enters a room, he does not turn the lights on, he turns the dark off.',
    58: 'Chuck Norris can play the violin with a piano',
    59: 'Mr. T once defeated Chuck Norris in a game of Tic-Tac-Toe. In retaliation, Chuck Norris invented racism.',
    60: 'It is considered a great accomplishment to go down Niagara Falls in a wooden barrel. Chuck Norris can go up Niagara Falls in a cardboard box.',
    61: 'Chuck Norris once had a heart attack; his heart lost.',
    62: 'Chuck Norris can drown a fish.',
    63: 'When Chuck Norris looks in a mirror the mirror shatters, because not even glass is stupid enough to get in between Chuck Norris and Chuck Norris.',
    64: 'People think Billy Joel is an alcoholic and wrecks lots of cars. In reality, Chuck Norris keeps kicking Billys ass because Chuck is the Piano Man and he started the fire.',
    65: 'Jack was nimble, Jack was quick, but Jack still could not dodge Chuck Norris roundhouse kick.',
    66: 'The only time Chuck Norris was wrong was when he thought he had made a mistake.',
    67: 'Chuck Norris does not need a miracle in order to split the ocean. He just walks in and the water gets the fuck out of the way.',
    68: 'Rosa Parks refused to get out of her seat because she was saving it for Chuck Norris.',
    69: 'A Handicap parking sign does not signify that this spot is for handicapped people. It is actually in fact a warning, that the spot belongs to Chuck Norris and that you will be handicapped if you park there.',
    70: 'A rogue squirrel once challenged Chuck Norris to a nut hunt around the park. Before beginning, Chuck simply dropped his pants, instantly killing the squirrel and 3 small children. Chuck knows you cant find bigger, better nuts than that.',
    71: 'Brett Favre can throw a football over 50 yards. Chuck Norris can throw Brett Favre even further.',
    72: 'When God said, "Let there be light", Chuck Norris said, "say please."',
    73: 'The chief export of Chuck Norris is pain.',
    74: 'Chuck Norris does not use pickup lines, he simply says, "Now."',
    75: 'Chuck Norris can make a paraplegic run for his life.',
    76: 'The last digit of pi is Chuck Norris. He is the end of all things.',
    77: 'Chuck Norris once bowled a 300. Without a ball. He wasnt even in a bowling alley.',
    78: 'Chuck Norris can create a rock so heavy that even he cant lift it. And then he lifts it anyways, just to show you who the fuck Chuck Norris is.',
    79: 'Chuck Norris is the only person that can punch a cyclops between the eye.',
    80: 'Chuck Norris can tie his shoes with his feet.',
    81: 'The quickest way to a mans heart is with Chuck Norris fist.',
    82: 'Pinatas were made in an attempt to get Chuck Norris to stop kicking the people of Mexico. Sadly this backfired, as all it has resulted in is Chuck Norris now looking for candy after he kicks his victims.',
    83: 'The phrase, "You are what you eat" cannot be true based on the amount of pussy Chuck Norris eats.',
    84: 'Chuck Norris was originally offered the role as Frodo in Lord of the Rings. He declined because, "Only a pussy would need three movies to destroy a piece of jewelery."',
    85: 'If you can see Chuck Norris, he can see you. If you cant see Chuck Norris you may be only seconds away from death.',
    86: 'Chuck Norris doesnt play "hide-and-seek." He plays "hide-and-pray-I-dont-find-you."',
    87: 'Chuck Norris does not know where you live, but he knows where you will die.',
    88: 'Chuck Norris once had an erection while lying face down and struck oil.',
    89: 'Chuck Norris is currently suing NBC, claiming Law and Order are trademarked names for his left and right legs.',
    90: 'Chuck Norris is currently in a legal battle with the makers of Bubble Tape. Norris claims "6 Feet of Fun" is actually the trademark for his penis.',
    91: 'The saddest moment for a child is not when he learns Santa Claus isnt real, its when he learns Chuck Norris is.',
    92: 'Most men are okay with their wives fantasizing about Chuck Norris during sex, because they are doing the same thing.',
    93: 'Chuck Norris used to beat the shit out of his shadow because it was following to close. It now stands a safe 30 feet behind him.',
    94: 'Bullets dodge Chuck Norris.',
    95: 'Chuck Norris cannot predict the future; the future just better fucking do what Chuck Norris says.',
    96: 'Someone once tried to tell Chuck Norris that roundhouse kicks arent the best way to kick someone. This has been recorded by historians as the worst mistake anyone has ever made.',
    97: 'Before Chuck Norris was born, the martial arts weapons with two pieces of wood connected by a chain were called NunBarrys. No one ever did find out what happened to Barry.',
    98: 'Upon hearing that his good friend, Lance Armstrong, lost his testicles to cancer, Chuck Norris donated one of his to Lance. With just one of Chucks nuts, Lance was able to win the Tour De France seven times. By the way, Chuck still has two testicles; either he was able to produce a new one simply by flexing, or he had three to begin with. No one knows for sure.',
    99: 'We all know the magic word is please. As in the sentence, "Please dont kill me." Too bad Chuck Norris doesnt believe in magic.',
    100: 'Chuck Norris dose not need 100 quotes... Everything he does is over 9000, So nothing even comes close to his skill, not even code like the Matrix!',
}

class Chucks:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def chuck(self, num: int=None):
        """Chuck Norris Facts... not Fiction, FACTS!"""
        if num:
            if num < 0:
                await self.bot.say('LOL SO FUNNY')
                return
            if num > 101:
                await self.bot.say('Umm.. I wouldnt do that if I were you!')
                return
            await self.bot.say("Article {}: {}".format(num, chucks[num]))
            return
        chuck = randchoice(list(chucks.keys()))
        await self.bot.say("Article {}: {}".format(chuck, chucks[chuck]))

def setup(bot):
    n = Chucks(bot)
    bot.add_cog(n)