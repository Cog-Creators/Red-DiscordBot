# Developed by Redjumpman for Redbot.
# Inspired by the snail race mini game

# STD Library
import asyncio
import random
import os

# Discord and Red Utils
import discord
from discord.ext import commands
from __main__ import send_cmd_help
from .utils import checks
from .utils.dataIO import dataIO

animals = ((':rabbit2:', 'fast'), (':monkey:', 'fast'), (':cat2:', 'fast'), (':mouse2:', 'slow'),
           (':chipmunk:', 'fast'), (':rat:', 'fast'), (':dove:', 'fast'), (':bird:', 'fast'),
           (':dromedary_camel:', 'steady'), (':camel:', 'steady'), (':dog2:', 'steady'),
           (':poodle:', 'steady'), (':racehorse:', 'steady'), (':ox:', 'abberant'),
           (':cow2:', 'abberant'), (':elephant:', 'abberant'), (':water_buffalo:', 'abberant'),
           (':ram:', 'abberant'), (':goat:', 'abberant'), (':sheep:', 'abberant'),
           (':leopard:', 'predator'), (':tiger2:', 'predator'), (':dragon:', 'special'),
           (':turtle:', 'slow'), (':bug:', 'slow'), (':rooster:', 'slow'),
           (':snail:', 'slow'), (':scorpion:', 'slow'), (':crocodile:', 'slow'), (':pig2:', 'slow'),
           (':turkey:', 'slow'), (':duck:', 'slow'), (':baby_chick:', 'slow'))


class Racer:

    track = '•   ' * 20

    def __init__(self, animal, mode, user):
        self.animal = animal
        self.mode = mode
        self.user = user
        self.turn = 0
        self.position = 80
        self.placed = False
        self.current = Racer.track + self.animal

    def field(self):
        field = ":carrot: **{}** :flag_black:  [{}]".format(self.current, self.user)
        return field

    def get_position(self):
        return self.current.find(self.animal)

    def update_track(self):
        distance = self.move()
        self.current = (Racer.track[:max(0, self.position - distance)] + self.animal +
                        Racer.track[max(0, self.position - distance):])

    def update_position(self):
        self.turn = self.turn + 1
        self.update_track()
        self.position = self.get_position()

    def move(self):
        if self.mode == 'slow':
            return random.randint(1, 3) * 3

        elif self.mode == 'fast':
            return random.randint(0, 4) * 3

        elif self.mode == 'steady':
            return 2 * 3

        elif self.mode == 'abberant':
            if random.randint(1, 100) >= 90:
                return 5 * 3
            else:
                return random.randint(0, 2) * 3

        elif self.mode == 'predator':
            if self.turn % 2 == 0:
                return 0
            else:
                return random.randint(2, 5) * 3

        elif self.animal == ':unicorn:':
            if self.turn % 3:
                return random.choice([len('blue'), len('red'), len('green')]) * 3
            else:
                return 0
        else:
            if self.turn == 1:
                return 14 * 3
            elif self.turn == 2:
                return 0
            else:
                return random.randint(0, 2) * 3


class Race:
    """Cog for racing animals"""

    def __init__(self, bot):
        self.bot = bot
        self.system = {}
        self.config = dataIO.load_json('data/race/race.json')
        self.version = "1.1.02"

    @commands.group(pass_context=True, no_pm=True)
    async def race(self, ctx):
        """Race cog's group command"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @commands.group(pass_context=True, no_pm=True)
    async def setrace(self, ctx):
        """Race cog's settings group command"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setrace.command(name="prize", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _prize_setrace(self, ctx, minimum: int, maximum: int):
        """Set the prize range

        A number of credits will be randomly picked from the set
        miminum to the set maximum.

        Parameters:
            minimum: integer
                Must be lower than maximum
            maximum: integer
                Must be higher than minimum

        Returns:
            Bot replies with invalid mode
            Bot replies with valid mode and saves choice
        """

        if minimum > maximum:
            return await self.bot.say("https://simple.wikipedia.org/wiki/Maximum_and_minimum")
        server = ctx.message.server
        settings = self.check_config(server)
        settings['Prize'] = (minimum, maximum)
        self.save_settings()
        await self.bot.say("Prize range set to {}-{}".format(minimum, maximum))

    @setrace.command(name="time", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _time_setrace(self, ctx, time: int):
        """Set the time players have to enter a race

        Amount of time for the bot to wait for entrants until the race
        is ready to begin.

        Parameters:
            time: integer
                Unit is expressed in seconds
                Default is set to 60 seconds

        Returns:
            Bo
        """
        author = ctx.message.author
        if time < 0:
            return await self.bot.say("{}. You are a dumbass. I can't turn back"
                                      "time.".format(author.name))

        settings = self.check_config(author.server)
        settings['Time'] = time
        self.save_settings()
        await self.bot.say("Wait time set to {}s".format(time))

    @setrace.command(name="mode", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _mode_setrace(self, ctx, mode: str):
        """Set the race mode

        Standard Mode assigns everyone a turtle. Everyone has the same
        random movement formula.

        Zoo Mode assigns every entrant a random animal. Animals are grouped into
        classes that meet a special formula for movement. 8 different animal classes!

        Parameters:
            mode: string
                Must be standard or zoo
        Returns:
            Bot replies with invalid mode
            Bot replies with valid mode and saves choice
        """
        server = ctx.message.server
        settings = self.check_config(server)
        mode = mode.lower()
        modes = ['standard', 'zoo']
        if mode not in modes:
            return await self.bot.say("Invalid mode. Acceptable responses "
                                      "include: {}.".format(', '.join(modes)))
        settings['Mode'] = mode
        self.save_settings()
        await self.bot.say("Mode now set to {}.".format(mode))

    @race.command(name="reset", pass_context=True, hidden=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _reset_race(self, ctx):
        """Reset race parameters DEBUG USE ONLY"""
        server = ctx.message.server
        data = self.check_server(server)
        self.game_teardown(data, force=True)
        await self.bot.say("Parameters reset.")

    @race.command(name="start", aliases=["s"], pass_context=True)
    @commands.cooldown(1, 120, commands.BucketType.server)
    async def _start_race(self, ctx):
        """Start an animal race and enter yourself as participant

            Returns:
                Two text outputs. One to start the race,
                and the second to represent the race. The second
                msg will be edited multiple times to represent the race.

            Notes:
                Must wait 2 minutes after every race to start a new one.
                You cannot start a race if a race is already active.
                A race is considered active once this command is used.
                A race is considered started once the track is displayed.
                The user who starts a race, will be automatically entered.
                The bot will always join a race.
                There are no cheaters and it isn't rigged.
        """
        author = ctx.message.author
        data = self.check_server(author.server)
        settings = self.check_config(author.server)

        if data['Race Active']:
            return

        self.game_teardown(data, force=True)
        data['Race Active'] = True
        data['Players'][author.id] = {}
        wait = settings['Time']
        await self.bot.say(":triangular_flag_on_post: A race has begun! Type {}race enter "
                           "to join the race! :triangular_flag_on_post:\n{}The race will "
                           "begin in {} seconds!\n\n**{}** entered the "
                           "race!".format(ctx.prefix, ' ' * 25, wait, author.mention))
        await asyncio.sleep(wait)
        await self.bot.say(":checkered_flag: The race is now in progress :checkered_flag:")

        data['Race Start'] = True

        racers = self.game_setup(author, data, settings['Mode'])
        race_msg = await self.bot.say('\n'.join([player.field() for player in racers]))
        await self.run_game(racers, race_msg, data)

        footer = "Type {}race claim to receive prize money. You must claim it before the next race!"
        first = ':first_place:  {0}'.format(*data['First'])
        fv = '{1}\n{2:.2f}s'.format(*data['First'])
        second = ':second_place: {0}'.format(*data['Second'])
        sv = '{1}\n{2:.2f}s'.format(*data['Second'])
        if data['Third']:
            third = ':third_place:  {0}'.format(*data['Third'])
            tv = '{1}\n{2:.2f}s'.format(*data['Third'])
        else:
            third = ':third_place:'
            tv = '--\n--'

        embed = discord.Embed(colour=0x00CC33)
        embed.add_field(name=first, value=fv)
        embed.add_field(name=second, value=sv)
        embed.add_field(name=third, value=tv)
        embed.add_field(name='-' * 99, value='{} is the winner!'.format(data['Winner']))
        embed.title = "Race Results"
        embed.set_footer(text=footer.format(ctx.prefix))
        await self.bot.say(embed=embed)
        self.game_teardown(data)

    @race.command(name="enter", aliases=["e"], pass_context=True)
    async def _enter_race(self, ctx):
        """Enter an animal race

        Returns:
            Text informing the user they have entered the race.
            If they cannot join for any reason (look at notes) then
            it will return silently with no response.

        Notes:
            Users cannot join if a race is not active, has 5 (exluding the bot)
            or more players, or is already in the race.
        """
        author = ctx.message.author
        data = self.check_server(author.server)

        if data['Race Start']:
            return
        elif not data['Race Active']:
            return
        elif author.id in data['Players']:
            return
        elif len(data['Players']) == 8:
            return
        else:
            data['Players'][author.id] = {}
            await self.bot.say("**{}** entered the race!".format(author.name))

    @race.command(name="claim", aliases=["c"], pass_context=True)
    async def _claim_race(self, ctx):
        """Claim your prize from the animal race

        Returns:
                One of three outcomes based on result
            :Text output giving random credits from 10-100
            :Text output telling you are not the winner
            :Text output telling you to get a bank account

        Raises:
            cogs.economy.NoAccount Error when bank account not found.

        Notes:
            If you do not have a bank account with economy, the bot will take your money
            and spend it on cheap booze and potatoes.
        """
        author = ctx.message.author
        data = self.check_server(author.server)
        settings = self.check_config(author.server)

        if data['Race Active']:
            return

        if data['Winner'] != author:
            return await self.bot.say("Scram kid. You didn't win nothing yet.")
        try:
            bank = self.bot.get_cog('Economy').bank
        except AttributeError:
            return await self.bot.say("Economy is not loaded.")

        prize_range = settings['Prize']
        prize = random.randint(*prize_range)

        try:  # Because people will play games for money without a fucking account smh
            bank.deposit_credits(author, prize)
        except Exception as e:
            print('{} raised {} because they are stupid.'.format(author.name, type(e)))
            await self.bot.say("We wanted to give you a prize, but you didn't have a bank "
                               "account.\nTo teach you a lesson, your winnings are mine this "
                               "time. Now go register!")
        else:
            await self.bot.say("After paying for animal feed, entrance fees, track fees, "
                               "you get {} credits.".format(prize))
        finally:
            data['Winner'] = None

    def check_server(self, server):
        if server.id in self.system:
            return self.system[server.id]
        else:
            self.system[server.id] = {'Race Start': False, 'Race Active': False, 'Players': {},
                                      'Winner': None, 'First': None, 'Second': None, 'Third': None
                                      }
            return self.system[server.id]

    def check_config(self, server):
        if server.id in self.config['Servers']:
            return self.config['Servers'][server.id]
        else:
            self.config['Servers'][server.id] = {'Prize': (1, 100), 'Mode': 'standard', 'Time': 60}
            self.save_settings()
            return self.config['Servers'][server.id]

    def game_teardown(self, data, force=False):
        if data['Winner'] == self.bot.user or force:
            data['Winner'] = None
        data['Race Active'] = False
        data['Race Start'] = False
        data['First'] = None
        data['Second'] = None
        data['Third'] = None
        data['Players'].clear()

    def save_settings(self):
        dataIO.save_json('data/race/race.json', self.config)

    def game_setup(self, author, data, mode):

        racers = []

        if mode == 'zoo':
            if len(data['Players']) == 1:
                bot_set = random.choice(animals)
                racers = [Racer(bot_set[0], bot_set[1], self.bot.user)]

            for user in data['Players']:
                mobj = author.server.get_member(user)
                animal_set = random.choice(animals)
                racers.append(Racer(animal_set[0], animal_set[1], mobj))
        else:
            animal_set = (":turtle:", "slow")
            if len(data['Players']) == 1:
                racers = [Racer(animal_set[0], animal_set[1], self.bot.user)]

            for user in data['Players']:
                mobj = author.server.get_member(user)
                racers.append(Racer(animal_set[0], animal_set[1], mobj))

        return racers

    async def run_game(self, racers, game, data):
        while True:
            await asyncio.sleep(2.0)
            for player in racers:
                player.update_position()
                position = player.get_position()
                if position == 0:
                    if not data['Winner']:
                        speed = player.turn + random.uniform(0.1, 0.88)
                        data['Winner'] = player.user
                        data['First'] = (player.user, player.animal, speed)
                        player.placed = True
                    elif not data['Second'] and not player.placed:
                        if data['First'][2] > player.turn:
                            speed = player.turn + random.uniform(0.89, 0.99)
                        else:
                            speed = player.turn + random.uniform(0.1, 0.88)
                        data['Second'] = (player.user, player.animal, speed)
                        player.placed = True
                    elif not data['Third'] and not player.placed:
                        if data['Second'][2] > player.turn:
                            speed = player.turn + random.uniform(0.89, 0.99)
                        else:
                            speed = player.turn + random.uniform(0.1, 0.88)
                        data['Third'] = (player.user, player.animal, speed)
                        player.placed = True
            field = [player.field() for player in racers]
            await self.bot.edit_message(game, '\n'.join(field))

            if [player.get_position() for player in racers].count(0) == len(racers):
                break

        prize = random.randint(10, 100)
        data['Prize'] = prize


def check_folders():
    if not os.path.exists('data/race'):
        print("Creating data/race folder...")
        os.makedirs('data/race')


def check_files():
    system = {"Servers": {}}

    f = 'data/race/race.json'
    if not dataIO.is_valid_json(f):
        print('data/race/race.json')
        dataIO.save_json(f, system)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Race(bot))
