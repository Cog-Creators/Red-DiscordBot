import os
import random
import asyncio
from .utils.dataIO import dataIO
from discord.ext import commands
from .utils import checks


class Russianroulette:
    """Allows 6 players to play Russian Roulette"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/roulette/rrgame.json"
        self.rrgame = dataIO.load_json(self.file_path)

    @commands.command(pass_context=True, no_pm=True)
    async def russian(self, ctx, bet: int):
        """Russian Roulette, requires 2 players, up to 6 max"""
        user = ctx.message.author
        server = ctx.message.server
        if not self.rrgame["System"]["Active"]:
            if bet >= self.rrgame["Config"]["Min Bet"]:
                if self.rrgame["System"]["Player Count"] < 6:
                    if self.enough_points(user, bet):
                        if not self.rrgame["System"]["Roulette Initial"]:
                            bank = self.bot.get_cog('Economy').bank
                            bank.withdraw_credits(user, bet)
                            self.rrgame["System"]["Player Count"] += 1
                            self.rrgame["System"]["Pot"] += bet
                            self.rrgame["System"]["Start Bet"] += bet
                            self.rrgame["Players"][user.mention] = {"Name": user.name,
                                                                    "ID": user.id,
                                                                    "Mention": user.mention,
                                                                    "Bet": bet}
                            self.rrgame["System"]["Roulette Initial"] = True
                            dataIO.save_json(self.file_path, self.rrgame)
                            await self.bot.say(user.name + " has started a game of roulette, with a starting bet of " +
                                               str(bet) + ".\n" "The game will start in 30 seconds or until I get 5 more players")
                            await asyncio.sleep(30)
                            if self.rrgame["System"]["Player Count"] > 1 and self.rrgame["System"]["Player Count"] < 6:
                                self.rrgame["System"]["Active"] = True
                                await self.bot.say("I'm going to load some shells into the cylinder of this 6 shot revolver.")
                                await asyncio.sleep(4)
                                await self.bot.say("Then I'll give it a good spin, and pass it off, until one of you blows your head off.")
                                await asyncio.sleep(5)
                                await self.bot.say("The winner is the last one alive!")
                                await asyncio.sleep(3)
                                await self.bot.say("Good Luck!")
                                await asyncio.sleep(1)
                                await self.roulette_game(server)
                            elif self.rrgame["System"]["Player Count"] < 2:
                                bank.deposit_credits(user, bet)
                                await self.bot.say("Sorry I can't let you play by yourself, that's just suicide." + "\n" +
                                                   "Try again later when you find some 'friends'.")
                                self.system_reset()
                        elif user.mention not in self.rrgame["Players"]:
                            if bet >= self.rrgame["System"]["Start Bet"]:
                                bank = self.bot.get_cog('Economy').bank
                                bank.withdraw_credits(user, bet)
                                self.rrgame["System"]["Pot"] += bet
                                self.rrgame["System"]["Player Count"] += 1
                                self.rrgame["Players"][user.mention] = {"Name": user.name,
                                                                        "ID": user.id,
                                                                        "Mention": user.mention,
                                                                        "Bet": bet}
                                dataIO.save_json(self.file_path, self.rrgame)
                                players = self.rrgame["System"]["Player Count"]
                                needed_players = 6 - players
                                if self.rrgame["System"]["Player Count"] > 5:
                                    self.rrgame["System"]["Active"] = True
                                    await self.bot.say("I'm going to load exactly **one** shell into the cylinder of this 6 shot revolver.")
                                    await asyncio.sleep(4)
                                    await self.bot.say("Then I'll give it a good spin, and pass it of until one of you blows your head off.")
                                    await asyncio.sleep(5)
                                    await self.bot.say("The winner is the last one alive!")
                                    await asyncio.sleep(3)
                                    await self.bot.say("Good Luck!")
                                    await asyncio.sleep(1)
                                    await self.roulette_game(server)
                                else:
                                    await self.bot.say(user.name + " has joined the roulette circle. I need " +
                                                       str(needed_players) + " to start the game immediately.")
                            else:
                                await self.bot.say("Your bet needs to match the initial bet or be higher.")
                        else:
                            await self.bot.say("You are already in the roulette circle.")
                    else:
                        await self.bot.say("You do not have enough points")
                else:
                    await self.bot.say("There are too many players playing at the moment")
            else:
                min_bet = self.rrgame["Config"]["Min Bet"]
                await self.bot.say("Your bet needs to be greater than or equal to the min bet of " + str(min_bet))
        else:
            await self.bot.say("There is an active game of roulette, wait until it's over to join in.")

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def rrclear(self):
        """Clear command if the game sticks. ONLY use if the game hangs. if this
        occurs please contact nFxus#5631 on Discord"""
        self.system_reset()
        await self.bot.say("Roulette system reset")

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def russianset(self, ctx, bet: int):
        """Set the initial starting bet to play the game"""
        if bet > 0:
            self.rrgame["Config"]["Min Bet"] = bet
            dataIO.save_json(self.file_path, self.rrgame)
            await self.bot.say("The initial bet to play is now set to " + str(bet))
        else:
            await self.bot.say("I need a number higher than 0.")

    async def roulette_game(self, server):
        i = self.rrgame["System"]["Player Count"]
        players = [subdict for subdict in self.rrgame["Players"]]
        count = len(players)
        turn = 0
        high_noon = random.randint(1, 100)
        if high_noon > 1:
            while i > 0:
                if i == 1:
                    mention = [subdict["Mention"] for subdict in self.rrgame["Players"].values()]
                    player_id = [subdict["ID"] for subdict in self.rrgame["Players"].values()]
                    mobj = server.get_member(player_id[0])
                    pot = self.rrgame["System"]["Pot"]
                    await asyncio.sleep(2)
                    await self.bot.say("Congratulations " + str(mention[0]) + ". You just won " + str(pot) + " points!")
                    bank = self.bot.get_cog('Economy').bank
                    bank.deposit_credits(mobj, pot)
                    self.system_reset()
                    await self.bot.say("Game Over")
                    break
                elif i > 1:
                    i = i - 1
                    turn = turn + 1
                    names = [subdict for subdict in self.rrgame["Players"]]
                    count = len(names)
                    await self.roulette_round(count, names, turn)
        elif high_noon == 12:
            noon_names = []
            for player in players:
                name = self.rrgame["Players"][player]["Name"]
                noon_names.append(name)
            v = ", ".join(noon_names)
            boom = " **BOOM!** " * i
            await self.bot.say("A wild BogHog appears!")
            await asyncio.sleep(1)
            await self.bot.say("It's high noon...")
            await asyncio.sleep(3)
            await self.bot.say(str(boom))
            await asyncio.sleep(1)
            await self.bot.say("```" + str(v) + " just bit the dust." + "```")
            await asyncio.sleep(2)
            await self.bot.say("Sorry partner, this pot of points is mine")
            self.system_reset()
            await asyncio.sleep(2)
            await self.bot.say("Game Over")

    async def roulette_round(self, count, player_names, turn):
        list_names = player_names
        furd = 0
        await self.bot.say("Round " + str(turn))
        await asyncio.sleep(2)
        while furd == 0:
            chance = random.randint(1, count)
            name_mention = random.choice(list_names)
            name = self.rrgame["Players"][name_mention]["Name"]
            if chance > 1:
                await self.bot.say(str(name) + " slowly squeezes the trigger...")
                await asyncio.sleep(4)
                await self.bot.say("**CLICK!**")
                await asyncio.sleep(2)
                await self.bot.say("```" + str(name) + " survived" + "```")
                list_names.remove(name_mention)
                count = count - 1
            elif chance <= 1:
                await self.bot.say(str(name) + " slowly squeezes the trigger...")
                await asyncio.sleep(4)
                await self.bot.say("**BOOM!**")
                await asyncio.sleep(1)
                await self.bot.say(str(name_mention) + " just blew their brains out")
                await asyncio.sleep(2)
                await self.bot.say("Let me just clean this up before we move on...")
                await asyncio.sleep(2)
                await self.bot.say("Done.")
                del self.rrgame["Players"][name_mention]
                dataIO.save_json(self.file_path, self.rrgame)
                break

    def account_check(self, uid):
        bank = self.bot.get_cog('Economy').bank
        if bank.account_exists(uid):
            return True
        else:
            return False

    def enough_points(self, uid, amount):
        bank = self.bot.get_cog('Economy').bank
        if self.account_check(uid):
            if bank.can_spend(uid, amount):
                return True
            else:
                return False
        else:
            return False

    def system_reset(self):
        self.rrgame["System"]["Pot"] = 0
        self.rrgame["System"]["Player Count"] = 0
        self.rrgame["System"]["Active"] = False
        self.rrgame["System"]["Roulette Initial"] = False
        self.rrgame["System"]["Start Bet"] = 0
        del self.rrgame["Players"]
        self.rrgame["Players"] = {}
        dataIO.save_json(self.file_path, self.rrgame)


def check_folders():
    if not os.path.exists("data/roulette"):
        print("Creating data/roulette folder...")
        os.makedirs("data/roulette")


def check_files():
    system = {"System": {"Pot": 0,
                         "Active": False,
                         "Start Bet": 0,
                         "Roulette Initial": False,
                         "Player Count": 0},
              "Players": {},
              "Config": {"Min Bet": 50}}

    f = "data/roulette/rrgame.json"
    if not dataIO.is_valid_json(f):
        print("Creating default rrgame.json...")
        dataIO.save_json(f, system)
    else:  # consistency check
        current = dataIO.load_json(f)
        if current.keys() != system.keys():
            for key in system.keys():
                if key not in current.keys():
                    current[key] = system[key]
                    print("Adding " + str(key) +
                          " field to russian roulette rrgame.json")
            dataIO.save_json(f, current)


def setup(bot):
    check_folders()
    check_files()
    n = Russianroulette(bot)
    bot.add_cog(n)
