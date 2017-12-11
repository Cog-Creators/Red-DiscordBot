# LICENSE and credit info:
# Python Port Source: https://github.com/brandon-rhodes/python-adventure
# 
# Red Port of Brandon Rhodes's python port of The Adventure game.
# Copyright 2016 irdumbs. Licensed under the Apache License, Version 2.0 (the "License")
# ^ am I doing it right?
# 
# Layman's License info: All credit for original works go to the original creators of this game.
#  Will Crowther 1976 
#  Don Woods 1977 
# and to the creator of the python port:
#  Brandon Rhodes 2010-2015 
# 
# All questions / suggestions / issues should be directed to the creator of the Red port
#  irdumbs 2016
# 
# If you use or edit this code, keep all license information and comments crediting authors and/or sources unchanged.
#
# Follow this 'license' in addition to the LICENSE file included. I think they say the same stuff anyway :3
#
# advent.dat file has also been edited. If you find any typos, please let irdumbs know.
# 
# If you are looking at this code to try and find examples of how to write cogs.. don't. Trust me.

import discord
from discord.ext import commands
import asyncio
import os
import glob
from __main__ import send_cmd_help
from cogs.utils.dataIO import fileIO
import shutil
from random import choice

# __init__.py
"""The Adventure game.

Copyright 2010-2015 Brandon Rhodes.  Licensed as free software under the
Apache License, Version 2.0 as detailed in the accompanying README.txt.

"""
def load_advent_dat(data):
    # import os
    #from .data import parse

    # datapath = os.path.join(os.path.dirname(__file__), 'data/adventure/advent.dat')
    datapath = 'data/adventure/advent.dat'

    with open(datapath, 'r', encoding='ascii') as datafile:
        parse(data, datafile)

def play(seed=None):
    """Turn the Python prompt into an Adventure game.

    With optional the `seed` argument the caller can supply an integer
    to start the Python random number generator at a known state.

    """
    global _game

    #from .game import Game
    #from .prompt import install_words

    _game = Game(seed)
    load_advent_dat(_game)
    install_words(_game)
    _game.start()
    print(_game.output[:-1])

def resume(savefile, quiet=False):
    global _game

    #from .game import Game
    #from .prompt import install_words

    _game = Game.resume(savefile)
    install_words(_game)
    if not quiet:
        print('GAME RESTORED\n')




#data.py
"""Parse the original PDP ``advent.dat`` file.

Copyright 2010-2015 Brandon Rhodes.  Licensed as free software under the
Apache License, Version 2.0 as detailed in the accompanying README.txt.

"""
from operator import attrgetter
#from .model import Hint, Message, Move, Object, Room, Word

# The Adventure data file knows only the first five characters of each
# word in the game, so we have to know the full verion of each word.

long_words = { w[:5]: w for w in """upstream downstream forest
forward continue onward return retreat valley staircase outside building stream
cobble inward inside surface nowhere passage tunnel canyon awkward
upward ascend downward descend outdoors barren across debris broken
examine describe slabroom depression entrance secret bedquilt plover
oriental cavern reservoir office headlamp lantern pillow velvet fissure tablet
oyster magazine spelunker dwarves knives rations bottle mirror beanstalk
stalactite shadow figure drawings pirate dragon message volcano geyser
machine vending batteries carpet nuggets diamonds silver jewelry treasure
trident shards pottery emerald platinum pyramid pearl persian spices capture
release discard mumble unlock nothing extinguish placate travel proceed
continue explore follow attack strike devour inventory detonate ignite
blowup peruse shatter disturb suspend sesame opensesame abracadabra
shazam excavate information""".split() }

class Data(object):
    def __init__(self):
        self.rooms = {}
        self.vocabulary = {}
        self.objects = {}
        self.messages = {}
        self.class_messages = []
        self.hints = {}
        self.magic_messages = {}

    def referent(self, word):
        if word.kind == 'noun':
            return self.objects[word.n % 1000]

# Helper functions.

def make_object(dictionary, klass, n):
    if n not in dictionary:
        dictionary[n] = obj = klass()
        obj.n = n
    return dictionary[n]

def expand_tabs(segments):
    it = iter(segments)
    line = next(it)
    for segment in it:
        spaces = 8 - len(line) % 8
        line += ' ' * spaces + segment
    return line

def accumulate_message(dictionary, n, line):
    dictionary[n] = dictionary.get(n, '') + line + '\n'

# Knowledge of what each section contains.

def section1(data, n, *etc):
    room = make_object(data.rooms, Room, n)
    if not etc[0].startswith('>$<'):
        room.long_description += expand_tabs(etc) + '\n'

def section2(data, n, line):
    make_object(data.rooms, Room, n).short_description += line + '\n'

def section3(data, x, y, *verbs):
    last_travel = data._last_travel
    if last_travel[0] == x and last_travel[1][0] == verbs[0]:
        verbs = last_travel[1]  # same first verb implies use whole list
    else:
        data._last_travel = [x, verbs]

    m, n = divmod(y, 1000)
    mh, mm = divmod(m, 100)

    if m == 0:
        condition = (None,)
    elif 0 < m < 100:
        condition = ('%', m)
    elif m == 100:
        condition = ('not_dwarf',)
    elif 100 < m <= 200:
        condition = ('carrying', mm)
    elif 200 < m <= 300:
        condition = ('carrying_or_in_room_with', mm)
    elif 300 < m:
        condition = ('prop!=', mm, mh - 3)

    if n <= 300:
        action = make_object(data.rooms, Room, n)
    elif 300 < n <= 500:
        action = n  # special computed goto
    else:
        action = make_object(data.messages, Message, n - 500)

    move = Move()
    if len(verbs) == 1 and verbs[0] == 1:
        move.is_forced = True
    else:
        move.verbs = [ make_object(data.vocabulary, Word, verb_n)
                       for verb_n in verbs if verb_n < 100 ] # skip bad "109"
    move.condition = condition
    move.action = action
    data.rooms[x].travel_table.append(move)

def section4(data, n, text, *etc):
    text = text.lower()
    text = long_words.get(text, text)
    word = make_object(data.vocabulary, Word, n)
    if word.text is None:  # this is the first word with index "n"
        word.text = text
    else:  # there is already a word sitting at "n", so create a synonym
        original = word
        word = Word()
        word.n = n
        word.text = text
        original.add_synonym(word)
    word.kind = ['travel', 'noun', 'verb', 'snappy_comeback'][n // 1000]
    if word.kind == 'noun':
        n %= 1000
        obj = make_object(data.objects, Object, n)
        obj.names.append(text)
        obj.is_treasure = (n >= 50)
        data.objects[text] = obj
    if text not in data.vocabulary:  # since duplicate names exist
        data.vocabulary[text] = word

def section5(data, n, *etc):
    if 1 <= n <= 99:
        data._object = make_object(data.objects, Object, n)
        data._object.inventory_message = expand_tabs(etc)
    else:
        n /= 100
        messages = data._object.messages
        if etc[0].startswith('>$<'):
            more = ''
        else:
            more = expand_tabs(etc) + '\n'
        messages[n] = messages.get(n, '') + more

def section6(data, n, *etc):
    message = make_object(data.messages, Message, n)
    message.text += expand_tabs(etc) + '\n'

def section7(data, n, room_n, *etc):
    if not room_n:
        return
    obj = make_object(data.objects, Object, n)
    room = make_object(data.rooms, Room, room_n)
    obj.drop(room)
    if len(etc):
        if etc[0] == -1:
            obj.is_fixed = True
        else:
            room2 = make_object(data.rooms, Room, etc[0])
            obj.rooms.append(room2)  # exists two places, like grate
    obj.starting_rooms = list(obj.rooms)  # remember where things started

def section8(data, word_n, message_n):
    if not message_n:
        return
    word = make_object(data.vocabulary, Word, word_n + 2000)
    message = make_object(data.messages, Message, message_n)
    for word2 in word.synonyms:
        word2.default_message = message

def section9(data, bit, *nlist):
    for n in nlist:
        room = make_object(data.rooms, Room, n)
        if bit == 0:
            room.is_light = True
        elif bit == 1:
            room.liquid = make_object(data.objects, Object, 22) #oil
        elif bit == 2:
            room.liquid = make_object(data.objects, Object, 21) #water
        elif bit == 3:
            room.is_forbidden_to_pirate = True
        else:
            hint = make_object(data.hints, Hint, bit)
            hint.rooms.append(room)

def section10(data, score, line, *etc):
    data.class_messages.append((score, line))

def section11(data, n, turns_needed, penalty, question_n, message_n):
    hint = make_object(data.hints, Hint, n)
    hint.turns_needed = turns_needed
    hint.penalty = penalty
    hint.question = make_object(data.messages, Message, question_n)
    hint.message = make_object(data.messages, Message, message_n)

def section12(data, n, line):
    accumulate_message(data.magic_messages, n, line)

# Process every section of the file in turn.

def parse(data, datafile):
    """Read the Adventure data file and return a ``Data`` object."""
    data._last_travel = [0, [0]]  # x and verbs used by section 3

    while True:
        section_number = int(datafile.readline())
        if not section_number:  # no further sections
            break
        store = globals().get('section%d' % section_number)
        while True:
            fields = [ (int(field) if field.lstrip('-').isdigit() else field)
                       for field in datafile.readline().strip().split('\t') ]
            if fields[0] == -1:  # end-of-section marker
                break
            store(data, *fields)

    del data._last_travel  # state used by section 3
    del data._object       # state used by section 5

    data.object_list = sorted(set(data.objects.values()), key=attrgetter('n'))
    #data.room_list = sorted(set(data.rooms.values()), key=attrgetter('n'))
    for obj in data.object_list:
        name = obj.names[0]
        if hasattr(data, name):
            name = name + '2'  # create identifiers like ROD2, PLANT2
        setattr(data, name, obj)

    return data




#game.py
"""How we keep track of the state of the game.

Copyright 2010-2015 Brandon Rhodes.  Licensed as free software under the
Apache License, Version 2.0 as detailed in the accompanying README.txt.

"""
# Numeric comments scattered through this file refer to FORTRAN line
# numbers, for those comparing this file and `advent.for`; so "#2012"
# refers to FORTRAN line number 2012 (which you can find easily in the
# FORTRAN using Emacs with an interactive search for newline-2012-tab,
# that is typed C-s C-q C-j 2 0 1 2 C-i).

# import os
import pickle
import random
import zlib
# from operator import attrgetter
#from .data import Data
#from .model import Room, Message, Dwarf, Pirate

YESNO_ANSWERS = {'y': True, 'yes': True, 'n': False, 'no': False}

class Game(Data):

    look_complaints = 3  # how many times to "SORRY, BUT I AM NOT ALLOWED..."
    full_description_period = 5  # how often we use a room's full description
    full_wests = 0  # how many times they have typed "west" instead of "w"
    dwarf_stage = 0  # DFLAG how active the dwarves are
    dwarves_killed = 0  # DKILL
    knife_location = None  # KNFLOC
    foobar = -1  # FOOBAR turn number of most recent still-valid "fee"
    gave_up = False
    treasures_not_found = 0  # TALLY how many treasures have not yet been seen
    impossible_treasures = 0  # TALLY2 how many treasures can never be retrieved
    lamp_turns = 330
    warned_about_dim_lamp = False
    bonus = 0  # how they exited the final bonus round
    is_dead = False  # whether we are currently dead
    deaths = 0  # how many times the player has died
    max_deaths = 3  # how many times the player can die
    turns = 0

    def __init__(self, seed=None):
        Data.__init__(self)
        self.output = ''
        self.yesno_callback = False
        self.yesno_casual = False       # whether to insist they answer

        self.clock1 = 30                # counts down from finding last treasure
        self.clock2 = 50                # counts down until cave closes
        self.is_closing = False         # is the cave closing?
        self.panic = False              # they tried to leave during closing?
        self.is_closed = False          # is the cave closed?
        self.is_done = False            # caller can check for "game over"
        self.could_fall_in_pit = False  # could the player fall into a pit?

        self.random_generator = random.Random()
        if seed is not None:
            self.random_generator.seed(seed)

    def random(self):
        return self.random_generator.random()

    def choice(self, seq):
        return self.random_generator.choice(seq)

    def write(self, more):
        """Append the Unicode representation of `s` to our output."""
        if more:
            self.output += str(more)#.upper()
            self.output += '\n'

    def write_message(self, n):
        self.write(self.messages[n])

    def yesno(self, s, yesno_callback, casual=False):
        """Ask a question and prepare to receive a yes-or-no answer."""
        self.write(s)
        self.yesno_callback = yesno_callback
        self.yesno_casual = casual

    # Properties of the cave.

    @property
    def is_dark(self):
        lamp = self.objects['lamp']
        if self.is_here(lamp) and lamp.prop:
            return False
        return self.loc.is_dark

    @property
    def inventory(self):
        return [ obj for obj in self.object_list if obj.is_toting ]

    @property
    def treasures(self):
        return [ obj for obj in self.object_list if obj.is_treasure ]

    @property
    def objects_here(self):
        return self.objects_at(self.loc)

    def objects_at(self, room):
        return [ obj for obj in self.object_list if room in obj.rooms ]

    def is_here(self, obj):
        if isinstance(obj, Dwarf):
            return self.loc is obj.room
        else:
            return obj.is_toting or (self.loc in obj.rooms)

    @property
    def is_finished(self):
        return (self.is_dead or self.is_done) and not self.yesno_callback

    # Game startup

    def start(self):
        """Start the game."""

        # For old-fashioned players, accept five-letter truncations like
        # "inven" instead of insisting on full words like "inventory".

        for key, value in list(self.vocabulary.items()):
            if isinstance(key, str) and len(key) > 5:
                self.vocabulary[key[:5]] = value

        # Set things going.

        self.chest_room = self.rooms[114]
        self.bottle.contents = self.water
        self.yesno(self.messages[65], self.start2)  # want instructions?

    def start2(self, yes):
        """Display instructions if the user wants them."""
        if yes:
            self.write_message(1)
            self.hints[3].used = True
            self.lamp_turns = 1000

        self.oldloc2 = self.oldloc = self.loc = self.rooms[1]
        self.dwarves = [ Dwarf(self.rooms[n]) for n in (19, 27, 33, 44, 64) ]
        self.pirate = Pirate(self.chest_room)

        treasures = self.treasures
        self.treasures_not_found = len(treasures)
        for treasure in treasures:
            treasure.prop = -1

        self.describe_location()

    # Routines that handle the aftermath of "big" actions like movement.
    # Although these are called at the end of each `do_command()` cycle,
    # we place here at the top of `game.py` to mirror the order in the
    # advent.for file.

    def move_to(self, newloc=None):  #2
        loc = self.loc
        if newloc is None:
            newloc = loc

        if self.is_closing and newloc.is_aboveground:
            self.write_message(130)
            newloc = loc  # cancel move and put him back underground
            if not self.panic:
                self.clock2 = 15
                self.panic = True

        must_allow_move = ((newloc is loc) or (loc.is_forced)
                           or (loc.is_forbidden_to_pirate))

        dwarf_blocking_the_way = any(
            dwarf.old_room is newloc and dwarf.has_seen_adventurer
            for dwarf in self.dwarves
            )

        if not must_allow_move and dwarf_blocking_the_way:
            newloc = loc  # cancel move they were going to make
            self.write_message(2)  # dwarf is blocking the way

        self.loc = loc = newloc  #74

        # IF LOC.EQ.0 ?
        is_dwarf_area = not (loc.is_forced or loc.is_forbidden_to_pirate)
        if is_dwarf_area and self.dwarf_stage > 0:
            self.move_dwarves()
        else:
            if is_dwarf_area and loc.is_after_hall_of_mists:
                self.dwarf_stage = 1
            self.describe_location()

    def move_dwarves(self):

        #6000
        if self.dwarf_stage == 1:

            # 5% chance per turn of meeting first dwarf
            if self.loc.is_before_hall_of_mists or self.random() < .95:
                self.describe_location()
                return
            self.dwarf_stage = 2
            for i in range(2):  # randomly remove 0, 1, or 2 dwarves
                if self.random() < .5:
                    self.dwarves.remove(self.choice(self.dwarves))
            for dwarf in self.dwarves:
                if dwarf.room is self.loc:  # move dwarf away from our loc
                    dwarf.start_at(self.rooms[18])
            self.write_message(3)  # dwarf throws axe and curses
            self.axe.drop(self.loc)
            self.describe_location()
            return

        #6010
        dwarf_count = dwarf_attacks = knife_wounds = 0

        for dwarf in self.dwarves + [ self.pirate ]:

            locations = { move.action for move in dwarf.room.travel_table 
                          if dwarf.can_move(move)
                          and move.action is not dwarf.old_room
                          and move.action is not dwarf.room }
            # Without stabilizing the order with a sort, the room chosen
            # would depend on how the Room addresses in memory happen to
            # order the rooms in the set() - and make it impossible to
            # test the game by setting the random number generator seed
            # and then playing through the game.
            locations = sorted(locations, key=attrgetter('n'))
            if locations:
                new_room = self.choice(locations)
            else:
                new_room = dwarf.old_room
            dwarf.old_room, dwarf.room = dwarf.room, new_room
            if self.loc in (dwarf.room, dwarf.old_room):
                dwarf.has_seen_adventurer = True
            elif self.loc.is_before_hall_of_mists:
                dwarf.has_seen_adventurer = False

            if not dwarf.has_seen_adventurer:
                continue

            dwarf.room = self.loc

            if dwarf.is_dwarf:
                dwarf_count += 1
                # A dwarf cannot walk and attack at the same time.
                if dwarf.room is dwarf.old_room:
                    dwarf_attacks += 1
                    self.knife_location = self.loc
                    if self.random() < .095 * (self.dwarf_stage - 2):
                        knife_wounds += 1

            else:  # the pirate
                pirate = dwarf

                if self.loc is self.chest_room or self.chest.prop >= 0:
                    continue  # decide that the pirate is not really here

                treasures = [ t for t in self.treasures if t.is_toting ]
                if (self.platinum in treasures and self.loc.n in (100, 101)):
                    treasures.remove(self.platinum)

                if not treasures:
                    h = any( t for t in self.treasures if self.is_here(t) )
                    one_treasure_left = (self.treasures_not_found ==
                                         self.impossible_treasures + 1)
                    shiver_me_timbers = (
                        one_treasure_left and not h and not(self.chest.rooms)
                        and self.is_here(self.lamp) and self.lamp.prop == 1
                        )

                    if not shiver_me_timbers:
                        if (pirate.old_room != pirate.room
                            and self.random() < .2):
                            self.write_message(127)
                        continue  # pragma: no cover

                    self.write_message(186)
                    self.chest.drop(self.chest_room)
                    self.message.drop(self.rooms[140])

                else:
                    #6022  I'll just take all this booty
                    self.write_message(128)
                    if not self.message.rooms:
                        self.chest.drop(self.chest_room)
                    self.message.drop(self.rooms[140])
                    for treasure in treasures:
                        treasure.drop(self.chest_room)

                #6024
                pirate.old_room = pirate.room = self.chest_room
                pirate.has_seen_adventurer = False  # free to move

        # Report what has happened.

        if dwarf_count == 1:
            self.write_message(4)
        elif dwarf_count:
            self.write('There are {} threatening little dwarves in the'
                       ' room with you.\n'.format(dwarf_count))

        if dwarf_attacks and self.dwarf_stage == 2:
            self.dwarf_stage = 3

        if dwarf_attacks == 1:
            self.write_message(5)
            k = 52
        elif dwarf_attacks:
            self.write('{} of them throw knives at you!\n'.format(dwarf_attacks))
            k = 6

        if not dwarf_attacks:
            pass
        elif not knife_wounds:
            self.write_message(k)
        else:
            if knife_wounds == 1:
                self.write_message(k + 1)
            else:
                self.write('{} of them get you!\n'.format(knife_wounds))
            self.oldloc2 = self.loc
            self.die()
            return

        self.describe_location()

    def describe_location(self):  #2000

        loc = self.loc

        if loc.n == 0:
            self.die()

        could_fall = self.is_dark and self.could_fall_in_pit
        if could_fall and not loc.is_forced and self.random() < .35:
            self.die_here()
            return

        if self.bear.is_toting:
            self.write_message(141)

        if self.is_dark and not loc.is_forced:
            self.write_message(16)
        else:
            do_short = loc.times_described % self.full_description_period
            loc.times_described += 1
            if do_short and loc.short_description:
                self.write(loc.short_description)
            else:
                self.write(loc.long_description)

        if loc.is_forced:
            self.do_motion(self.vocabulary[2])  # dummy motion verb
            return

        if loc.n == 33 and self.random() < .25 and not self.is_closing:
            self.write_message(8)

        if not self.is_dark:
            for obj in self.objects_here:

                if obj is self.steps and self.gold.is_toting:
                    continue

                if obj.prop < 0:  # finding a treasure the first time
                    if self.is_closed:
                        continue
                    obj.prop = 1 if obj in (self.rug, self.chain) else 0
                    self.treasures_not_found -= 1
                    if (self.treasures_not_found > 0 and
                        self.treasures_not_found == self.impossible_treasures):
                        self.lamp_turns = min(35, self.lamp_turns)

                if obj is self.steps and self.loc is self.steps.rooms[1]:
                    prop = 1
                else:
                    prop = obj.prop

                self.write(obj.messages[prop])

        self.finish_turn()

    def say_okay_and_finish(self, *ignored):  #2009
        self.write_message(54)
        self.finish_turn()

    #2009 sets SPK="OK" then...
    #2010 sets SPK to K
    #2011 speaks SPK then...
    #2012 blanks VERB and OBJ and calls:
    def finish_turn(self, obj=None):  #2600

        # Advance random number generator so each input affects future.
        self.random()

        # Check whether we should offer a hint.
        for hint in self.hints.values():
            if hint.turns_needed == 9999 or hint.used:
                continue
            if self.loc in hint.rooms:
                hint.turn_counter += 1
                if hint.turn_counter >= hint.turns_needed:
                    if hint.n != 5:  # hint 5 counter does not get reset
                        hint.turn_counter = 0
                    if self.should_offer_hint(hint, obj):
                        hint.turn_counter = 0

                        def callback(yes):
                            if yes:
                                self.write(hint.message)
                                hint.used = True
                            else:
                                self.write_message(54)

                        self.yesno(hint.question, callback)
                        return
            else:
                hint.turn_counter = 0

        if self.is_closed:
            if self.oyster.prop < 0 and self.oyster.is_toting:
                self.write(self.oyster.messages[1])
            for obj in self.inventory:
                if obj.prop < 0:
                    obj.prop = - 1 - obj.prop

        self.could_fall_in_pit = self.is_dark  #2605
        if self.knife_location and self.knife_location is not self.loc:
            self.knife_location = None

    # The central do_command() method, that should be called over and
    # over again with words supplied by the user.

    # edited - irdumbs
    # def do_command(self, words):
    def do_command(self, words, ctx, adventure):
        """Parse and act upon the command in the list of strings `words`."""
        self.output = ''
        # self._do_command(words)
        self._do_command(words, ctx, adventure)
        return self.output

    #edited - irdumbs
    # def _do_command(self, words):
    def _do_command(self, words, ctx, adventure):
        if self.yesno_callback is not None:
            answer = YESNO_ANSWERS.get(words[0], None)
            if answer is None:
                if self.yesno_casual:
                    self.yesno_callback = None
                else:
                    self.write('Please answer the question.')
                    return
            else:
                callback = self.yesno_callback
                self.yesno_callback = None
                callback(answer)
                return

        if self.is_dead:
            self.write('You have gotten yourself killed.')
            return

        #2608
        self.turns += 1
        if (self.treasures_not_found == 0
            and self.loc.n >= 15 and self.loc.n != 33):
            self.clock1 -= 1
            if self.clock1 == 0:
                self.start_closing_cave()  # no "return", to do their command
        if self.clock1 < 0:
            self.clock2 -= 1
            if self.clock2 == 0:
                return self.close_cave()  # "return", to cancel their command

        if self.lamp.prop == 1:
            self.lamp_turns -= 1

        if self.lamp_turns <= 30 and self.is_here(self.batteries) \
                and self.batteries.prop == 0 and self.is_here(self.lamp):
            #12000
            self.write_message(188)
            self.batteries.prop = 1
            if self.batteries.is_toting:
                self.batteries.drop(self.loc)
            self.lamp_turns += 2500
            self.warned_about_dim_lamp = False
        elif self.lamp_turns == 0:
            #12400
            self.lamp_turns = -1
            self.lamp.prop = 0
            if self.is_here(self.lamp):
                self.write_message(184)
        elif self.lamp_turns < 0 and self.loc.is_aboveground:
            #12600
            self.write_message(185)
            self.gave_up = True
            self.score_and_exit()
            return
        elif self.lamp_turns <= 30 and not self.warned_about_dim_lamp \
                and self.is_here(self.lamp):
            #12200
            self.warned_about_dim_lamp = True
            if self.batteries.prop == 1:
                self.write_message(189)
            elif not self.batteries.rooms:
                self.write_message(183)
            else:
                self.write_message(187)

        # self.dispatch_command(words)
        self.dispatch_command(words, ctx, adventure)

    # edited - irdumbs
    # def dispatch_command(self, words):  #19999
    def dispatch_command(self, words, ctx, adventure):  #19999

        if not 1 <= len(words) <= 2:
            return self.dont_understand()

        #edited - irdumb
        if words[0] == 'save' and len(words) <= 2:
            # Handle suspend separately, since filename can be anything,
            # and is not restricted to being a vocabulary word (and, in
            # fact, it can be an open file).
            # return self.t_suspend(words[0], words[1])
            server = ctx.message.server
            channel = ctx.message.channel
            author = ctx.message.author
            team = adventure.players[server.id][channel.id][author.id]
            if len(words) == 2:
                save = words[1]
            else:
                save = adventure.game_loops[server.id][team][channel.id]["SAVE"]
            if save is None:
                return self.write("There is no save file to save to. Please give a name for the save file\n `{}> save <save_name>`".format(ctx.prefix))
            return adventure.save_game(server, team, channel, save)
            # return self.t_suspend(words[0], 'data/adventure/saves/{}/{}.save'.format(ctx.message.author.id, words[1]))


        words = [ self.vocabulary.get(word) for word in words ]
        if None in words:
            return self.dont_understand()

        word1 = words[0]
        word2 = words[1] if len(words) == 2 else None

        if word1 == 'enter' and (word2 == 'stream' or word2 == 'water'):
            if self.loc.liquid is self.water:
                self.write_message(70)
            else:
                self.write_message(43)
            return self.finish_turn()

        if (word1 == 'enter' or word1 == 'walk') and word2:
            #2800  'enter house' becomes simply 'house' and so forth
            word1, word2 = word2, None

        if ((word1 == 'water' or word1 == 'oil') and
            (word2 == 'plant' or word2 == 'door') and
            self.is_here(self.referent(word2))):
            word1, word2 = self.vocabulary['pour'], word1

        if word1 == 'say':
            return self.t_say(word1, word2, ctx, adventure) if word2 else self.i_say(word1)

        kinds = (word1.kind, word2.kind if word2 else None)

        #2630
        if kinds == ('travel', None):
            if word1.text == 'west':  #2610
                self.full_wests += 1
                if self.full_wests == 10:
                    self.write_message(17)
            return self.do_motion(word1)

        if kinds == ('snappy_comeback', None):
            self.write_message(word1.n % 1000)
            return self.finish_turn()

        if kinds == ('noun', None):
            verb, noun = None, word1
        elif kinds == ('verb', None):
            verb, noun = word1, None
        elif kinds == ('verb', 'noun'):
            verb, noun = word1, word2
        elif kinds == ('noun', 'verb'):
            noun, verb = word1, word2
        else:
            return self.dont_understand()

        if not noun:
            obj = None
        else:
            obj = self.referent(noun)
            obj_here = self.is_here(obj)
            if not obj_here:
                if obj is self.grate:
                    if self.loc.n in (1, 4, 7):
                        return self.dispatch_command([ 'depression' ], ctx, adventure)
                    elif 9 < self.loc.n < 15:
                        return self.dispatch_command([ 'entrance' ], ctx, adventure)
                elif noun == 'dwarf':
                    obj_here = any( d.room is self.loc for d in self.dwarves )
                elif obj is self.bottle.contents and self.is_here(self.bottle):
                    obj_here = True
                elif obj is self.loc.liquid:
                    obj_here = True
                elif (obj is self.plant and self.is_here(self.plant2)
                      and self.plant2.prop != 0):
                    obj = self.plant2
                    obj_here = True
                elif obj is self.knife and self.knife_location is self.loc:
                    self.knife_location = None
                    self.write_message(116)
                    return self.finish_turn()
                elif obj is self.rod and self.is_here(self.rod2):
                    obj = self.rod2
                    obj_here = True
                elif verb and (verb == 'find' or verb == 'inventory'):
                    obj_here = True  # lie; these verbs work for absent objects

            if not obj_here:
                return self.i_see_no(noun)

            if not verb:
                self.write('What do you want to do with the {}?\n'.format(
                        noun.text))
                return self.finish_turn()

        verb_name = verb.synonyms[0].text
        if obj:
            method_name = 't_' + verb_name
            args = (verb, obj)
        else:
            method_name = 'i_' + verb_name
            args = (verb,)
        method = getattr(self, method_name)
        method(*args)

    def dont_understand(self):
        #3000  (a bit earlier than in the Fortran code)
        n = self.random()
        if n < 0.20:    # 20% of the entire 1.0 range of random()
            self.write_message(61)
        elif n < 0.36:  # 20% of the remaining 0.8 left
            self.write_message(13)
        else:
            self.write_message(60)
        self.finish_turn()

    def i_see_no(self, thing):
        self.write('I see no {} here.\n'.format(getattr(thing, 'text', thing)))
        self.finish_turn()

    # Motion.

    def do_motion(self, word):  #8

        if word == 'null': #2
            self.move_to()
            return

        elif word == 'back':  #20
            dest = self.oldloc2 if self.oldloc.is_forced else self.oldloc
            self.oldloc2, self.oldloc = self.oldloc, self.loc
            if dest is self.loc:
                self.write_message(91)
                self.move_to()
                return
            alt = None
            for move in self.loc.travel_table:
                if move.action is dest:
                    word = move.verbs[0]  # arbitrary verb going to `dest`
                    break # Fall through, to attempt the move.
                elif (isinstance(move.action, Room)
                      and move.action.is_forced
                      and move.action.travel_table[0].action is dest):
                    alt = move.verbs[0]
            else:  # no direct route is available
                if alt is not None:
                    word = alt  # take a forced move if it's the only option
                else:
                    self.write_message(140)
                    self.move_to()
                    return

        elif word == 'look':  #30
            if self.look_complaints > 0:
                self.write_message(15)
                self.look_complaints -= 1
            self.loc.times_described = 0
            self.move_to()
            self.could_fall_in_pit = False
            return

        elif word == 'cave':  #40
            self.write_message(57 if self.loc.is_aboveground else 58)
            self.move_to()
            return

        self.oldloc2, self.oldloc = self.oldloc, self.loc

        for move in self.loc.travel_table:
            if move.is_forced or word in move.verbs:
                c = move.condition

                if c[0] is None or c[0] == 'not_dwarf':
                    allowed = True
                elif c[0] == '%':
                    allowed = 100 * self.random() < c[1]
                elif c[0] == 'carrying':
                    allowed = self.objects[c[1]].is_toting
                elif c[0] == 'carrying_or_in_room_with':
                    allowed = self.is_here(self.objects[c[1]])
                elif c[0] == 'prop!=':
                    allowed = self.objects[c[1]].prop != c[2]

                if not allowed:
                    continue

                if isinstance(move.action, Room):
                    self.move_to(move.action)
                    return

                elif isinstance(move.action, Message):
                    self.write(move.action)
                    self.move_to()
                    return

                elif move.action == 301:  #30100
                    inv = self.inventory
                    if len(inv) != 0 and inv != [ self.emerald ]:
                        self.write_message(117)
                        self.move_to()
                    elif self.loc.n == 100:
                        self.move_to(self.rooms[99])
                    else:
                        self.move_to(self.rooms[100])
                    return

                elif move.action == 302:  #30200
                    self.emerald.drop(self.loc)
                    self.do_motion(word)
                    return

                elif move.action == 303:  #30300
                    troll, troll2 = self.troll, self.troll2
                    if troll.prop == 1:
                        self.write(troll.messages[1])
                        troll.prop = 0
                        troll.rooms = list(troll.starting_rooms)
                        troll2.destroy()
                        self.move_to()
                        return
                    else:
                        places = list(troll.starting_rooms)
                        places.remove(self.loc)
                        self.loc = places[0]  # "the other side of the bridge"
                        if troll.prop == 0:
                            troll.prop = 1
                        if not self.bear.is_toting:
                            self.move_to()
                            return
                        self.write_message(162)
                        self.chasm.prop = 1
                        troll.prop = 2
                        self.bear.drop(self.loc)
                        self.bear.is_fixed = True
                        self.bear.prop = 3
                        if self.spices.prop < 0:
                            self.impossible_treasures += 1
                        self.oldloc2 = self.loc  # refuse to strand belongings
                        self.die()
                        return

        #50
        n = word.n
        if 29 <= n <= 30 or 43 <= n <= 50:
            self.write_message(9)
        elif n in (7, 36, 37):
            self.write_message(10)
        elif n in (11, 19):
            self.write_message(11)
        elif n in (62, 65):
            self.write_message(42)
        elif n == 17:
            self.write_message(80)
        else:
            self.write_message(12)
        self.move_to()
        return

    # Death and reincarnation.

    def die_here(self):  #90
        self.write_message(23)
        self.oldloc2 = self.loc
        self.die()

    def die(self):  #99
        self.deaths += 1
        self.is_dead = True

        if self.is_closing:
            self.write_message(131)
            self.score_and_exit()
            return

        def callback(yes):
            if yes:
                self.write_message(80 + self.deaths * 2)
                if self.deaths < self.max_deaths:
                    # do water and oil thing
                    self.is_dead = False
                    if self.lamp.is_toting:
                        self.lamp.prop = 0
                    for obj in self.inventory:
                        if obj is self.lamp:
                            obj.drop(self.rooms[1])
                        else:
                            obj.drop(self.oldloc2)
                    self.loc = self.rooms[3]
                    self.describe_location()
                    return
            else:
                self.write_message(54)
            self.score_and_exit()

        self.yesno(self.messages[79 + self.deaths * 2], callback)

    # Verbs.

    def ask_verb_what(self, verb, *args):  #8000
        self.write('{} What?\n'.format(verb.text))
        self.finish_turn()

    i_walk = ask_verb_what
    i_drop = ask_verb_what
    i_say = ask_verb_what
    i_nothing = say_okay_and_finish
    i_wave = ask_verb_what
    i_calm = ask_verb_what
    i_rub = ask_verb_what
    i_throw = ask_verb_what
    i_find = ask_verb_what
    i_feed = ask_verb_what
    i_break = ask_verb_what
    i_wake = ask_verb_what

    def write_default_message(self, verb, *args):
        self.write(verb.default_message)
        self.finish_turn()

    t_nothing = say_okay_and_finish
    t_calm = write_default_message
    t_quit = write_default_message
    t_score = write_default_message
    t_fee = write_default_message
    t_brief = write_default_message
    t_hours = write_default_message

    def i_carry(self, verb):  #8010
        is_dwarf_here = any( dwarf.room == self.loc for dwarf in self.dwarves )
        objs = self.objects_here
        if len(objs) != 1 or is_dwarf_here:
            self.ask_verb_what(verb)
        else:
            self.t_carry(verb, objs[0])

    def t_carry(self, verb, obj):  #9010
        if obj.is_toting:
            self.write(verb.default_message)
            self.finish_turn()
            return
        if obj.is_fixed or len(obj.rooms) > 1:
            if obj is self.plant and obj.prop <= 0:
                self.write_message(115)
            elif obj is self.bear and obj.prop == 1:
                self.write_message(169)
            elif obj is self.chain and self.chain.prop != 0:
                self.write_message(170)
            else:
                self.write_message(25)
            self.finish_turn()
            return
        if obj is self.water or obj is self.oil:
            if self.is_here(self.bottle) and self.bottle.contents is obj:
                # They want to carry the filled bottle.
                obj = self.bottle
            else:
                # They must mean they want to fill the bottle.
                if not self.bottle.is_toting:
                    self.write_message(104)
                elif self.bottle.contents is not None:
                    self.write_message(105)
                else:
                    self.t_fill(verb, self.bottle)  # hand off control to "fill"
                    return
                self.finish_turn()
                return
        if len(self.inventory) >= 7:
            self.write_message(92)
            self.finish_turn()
            return
        if obj is self.bird and obj.prop == 0:
            if self.rod.is_toting:
                self.write_message(26)
                self.finish_turn(obj)  # needs obj to decide to give hint
                return
            if not self.cage.is_toting:
                self.write_message(27)
                self.finish_turn()
                return
            self.bird.prop = 1
        if (obj is self.bird or obj is self.cage) and self.bird.prop != 0:
            self.bird.carry()
            self.cage.carry()
        else:
            obj.carry()
            if obj is self.bottle and self.bottle.contents is not None:
                self.bottle.contents.carry()
        self.say_okay_and_finish()

    def t_drop(self, verb, obj):  #9020
        if obj is self.rod and not self.rod.is_toting and self.rod2.is_toting:
            obj = self.rod2

        if not obj.is_toting:
            self.write(verb.default_message)
            self.finish_turn()
            return

        bird, snake, dragon, bear, troll = self.bird, self.snake, self.dragon, \
            self.bear, self.troll

        if obj is bird and self.is_here(snake):
            self.write_message(30)
            if self.is_closed:
                self.wake_repository_dwarves()
                return
            snake.prop = 1
            snake.destroy()

        elif obj is self.coins and self.is_here(self.machine):
            obj.destroy()
            self.batteries.drop(self.loc)
            self.write(self.batteries.messages[0])
            self.finish_turn()
            return

        elif obj is bird and self.is_here(dragon) and dragon.prop == 0:
            self.write_message(154)
            bird.destroy()
            bird.prop = 0
            if snake.rooms:
                self.impossible_treasures += 1
            self.finish_turn()
            return

        elif obj is bear and self.is_here(troll):
            self.write_message(163)
            troll.destroy()
            self.troll2.rooms = list(self.troll.starting_rooms)
            troll.prop = 2

        elif obj is self.vase and self.loc is not self.rooms[96]:
            if self.pillow.is_at(self.loc):
                self.vase.prop = 0
            else:
                self.vase.prop = 2
                self.vase.is_fixed = True
            self.write(self.vase.messages[self.vase.prop + 1])

        else:
            self.write_message(54)

        #9021
        if obj is self.bottle.contents:
            obj = self.bottle
        if obj is self.bottle and self.bottle.contents:
            self.bottle.contents.hide()
        if obj is self.cage and self.bird.prop != 0:
            bird.drop(self.loc)
        elif obj is self.bird:
            obj.prop = 0
        obj.drop(self.loc)
        self.finish_turn()
        return

    def t_say(self, verb, word, ctx, adventure):  #9030
        if word.n in (62, 65, 71, 2025):
            self.dispatch_command([ word.text ], ctx, adventure)
        else:
            self.write('Okay, "{}".'.format(word.text))
            self.finish_turn()

    def i_unlock(self, verb):  #8040  Handles "unlock" case as well
        objs = (self.grate, self.door, self.oyster, self.clam, self.chain)
        objs = list(filter(self.is_here, objs))
        if len(objs) > 1:
            self.ask_verb_what(verb)
        elif len(objs) == 1:
            self.t_unlock(verb, objs[0])
        else:
            self.write_message(28)
            self.finish_turn()

    i_lock = i_unlock

    def t_unlock(self, verb, obj):  #9040  Handles "lock" case as well
        if obj is self.clam or obj is self.oyster:
            #9046
            oy = 1 if (obj is self.oyster) else 0
            if verb == 'lock':
                self.write_message(61)
            elif not self.trident.is_toting:
                self.write_message(122 + oy)
            elif obj.is_toting:
                self.write_message(120 + oy)
            elif obj is self.oyster:
                self.write_message(125)
            else:
                self.write_message(124)
                self.clam.destroy()
                self.oyster.drop(self.loc)
                self.pearl.drop(self.rooms[105])
        elif obj is self.door:
            if obj.prop == 1:
                self.write_message(54)
            else:
                self.write_message(111)
        elif obj is self.cage:
            self.write_message(32)
        elif obj is self.keys:
            self.write_message(55)
        elif obj is self.grate or obj is self.chain:
            if not self.is_here(self.keys):
                self.write_message(31)
            elif obj is self.chain:
                #9048
                if verb == 'unlock':
                    if self.chain.prop == 0:
                        self.write_message(37)
                    elif self.bear.prop == 0:
                        self.write_message(41)
                    else:
                        self.chain.prop = 0
                        self.chain.is_fixed = False
                        if self.bear.prop != 3:
                            self.bear.prop = 2
                        self.bear.is_fixed = 2 - self.bear.prop
                        self.write_message(171)
                else:
                    #9049
                    if self.loc not in self.chain.starting_rooms:
                        self.write_message(173)
                    elif self.chain.prop != 0:
                        self.write_message(34)
                    else:
                        self.chain.prop = 2
                        if self.chain.is_toting:
                            self.chain.drop(self.loc)
                        self.chain.is_fixed = True
                        self.write_message(172)
            elif self.is_closing:
                if not self.panic:
                    self.clock2 = 15
                    self.panic = True
                self.write_message(130)
            else:
                #9043
                oldprop = obj.prop
                obj.prop = 0 if verb == 'lock' else 1
                self.write_message(34 + oldprop + 2 * obj.prop)
        else:
            self.write(verb.default_message)
        self.finish_turn()

    t_lock = t_unlock

    def t_light(self, verb, obj=None):  #9070
        if not self.is_here(self.lamp):
            self.write(verb.default_message)
        elif self.lamp_turns <= 0:
            self.write_message(184)
        else:
            self.lamp.prop = 1
            self.write_message(39)
            if self.loc.is_dark:
                return self.describe_location()
        self.finish_turn()

    i_light = t_light

    def t_extinguish(self, verb, obj=None):  #9080
        if not self.is_here(self.lamp):
            self.write(verb.default_message)
        else:
            self.lamp.prop = 0
            self.write_message(40)
            if self.loc.is_dark:
                self.write_message(16)
        self.finish_turn()

    i_extinguish = t_extinguish

    def t_wave(self, verb, obj):  #9090
        fissure = self.fissure

        if (obj is self.rod and obj.is_toting and self.is_here(fissure)
            and not self.is_closing):
            fissure.prop = 0 if fissure.prop else 1
            self.write(fissure.messages[2 - fissure.prop])
        else:
            if obj.is_toting or (obj is self.rod and self.rod2.is_toting):
                self.write(verb.default_message)
            else:
                self.write_message(29)

        self.finish_turn()

    def i_attack(self, verb):  #9120
        enemies = [ self.snake, self.dragon, self.troll, self.bear ]
        if self.dwarf_stage >= 2:
            enemies.extend(self.dwarves)
        dangers = list(filter(self.is_here, enemies))
        if len(dangers) > 1:
            return self.ask_verb_what(verb)
        if len(dangers) == 1:
            return self.t_attack(verb, dangers[0])
        targets = []
        if self.is_here(self.bird) and verb != 'throw':
            targets.append(self.bird)
        if self.is_here(self.clam) or self.is_here(self.oyster):
            targets.append(self.clam)
        if len(targets) > 1:
            return self.ask_verb_what(verb)
        elif len(targets) == 1:
            return self.t_attack(verb, targets[0])
        else:
            return self.t_attack(verb, None)

    def t_attack(self, verb, obj):  #9124  (but control goes to 9120 first)
        if obj is self.bird:
            if self.is_closed:
                self.write_message(137)
            else:
                obj.destroy()
                obj.prop = 0
                if self.snake.rooms:
                    self.impossible_treasures += 1
                self.write_message(45)
        elif obj is self.clam or obj is self.oyster:
            self.write_message(150)
        elif obj is self.snake:
            self.write_message(46)
        elif obj is self.dwarf:
            if self.is_closed:
                self.wake_repository_dwarves()
                return
            self.write_message(49)
        elif obj is self.dragon:
            if self.dragon.prop != 0:
                self.write_message(167)
            else:
                def callback(yes):
                    self.write(obj.messages[1])
                    obj.prop = 2
                    obj.is_fixed = True
                    oldroom1 = obj.rooms[0]
                    oldroom2 = obj.rooms[1]
                    newroom = self.rooms[ (oldroom1.n + oldroom2.n) // 2 ]
                    obj.drop(newroom)
                    self.rug.prop = 0
                    self.rug.is_fixed = False
                    self.rug.drop(newroom)
                    for oldroom in (oldroom1, oldroom2):
                        for o in self.objects_at(oldroom):
                            o.drop(newroom)
                    self.move_to(newroom)
                self.yesno(self.messages[49], callback, casual=True)
                return
        elif obj is self.troll:
            self.write_message(157)
        elif obj is self.bear:
            self.write_message(165 + (self.bear.prop + 1) // 2)
        else:
            self.write_message(44)
        self.finish_turn()

    def i_pour(self, verb):  #9130
        if self.bottle.contents is None:
            self.ask_verb_what(verb)
        else:
            self.t_pour(verb, self.bottle.contents)

    def t_pour(self, verb, obj):
        if obj is self.bottle:
            return self.i_pour(verb)
        if not obj.is_toting:
            self.write(verb.default_message)
        elif obj is not self.oil and obj is not self.water:
            self.write_message(78)
        else:
            self.bottle.prop = 1
            self.bottle.contents = None
            obj.hide()
            if self.is_here(self.plant):
                if obj is not self.water:
                    self.write_message(112)
                else:
                    self.write(self.plant.messages[self.plant.prop + 1])
                    self.plant.prop = (self.plant.prop + 2) % 6
                    self.plant2.prop = self.plant.prop // 2
                    return self.move_to()
            elif self.is_here(self.door):
                #9132
                self.door.prop = 1 if obj is self.oil else 0
                self.write_message(113 + self.door.prop)
            else:
                self.write_message(77)
        return self.finish_turn()

    def i_eat(self, verb):  #8140
        if self.is_here(self.food):
            self.t_eat(verb, self.food)
        else:
            self.ask_verb_what(verb)

    def t_eat(self, verb, obj):  #9140
        if obj is self.food:
            #8142
            self.food.destroy()
            self.write_message(72)
        elif obj in (self.bird, self.snake, self.clam, self.oyster,
                     self.dwarf, self.dragon, self.troll, self.bear):
            self.write_message(71)
        else:
            self.write(verb.default_message)
        self.finish_turn()

    def i_drink(self, verb):  #9150
        if self.is_here(self.water) or self.loc.liquid is self.water:
            self.t_drink(verb, self.water)
        else:
            self.ask_verb_what(verb)

    def t_drink(self, verb, obj):  #9150
        if obj is not self.water:
            self.write_message(110)
        elif self.is_here(self.water):
            self.bottle.prop = 1
            self.bottle.contents = None
            self.water.destroy()
            self.write_message(74)
        elif self.loc.liquid is self.water:
            self.write(verb.default_message)
        self.finish_turn()

    def t_rub(self, verb, obj):  #9160
        if obj is self.lamp:
            self.write(verb.default_message)
        else:
            self.write_message(71)
        self.finish_turn()

    def t_throw(self, verb, obj):  #9170
        if obj is self.rod and not self.rod.is_toting and self.rod2.is_toting:
            obj = self.rod2

        if not obj.is_toting:
            self.write(verb.default_message)
            self.finish_turn()
            return

        if obj.is_treasure and self.is_here(self.troll):
            # Pay the troll toll
            self.write_message(159)
            obj.destroy()
            self.troll.destroy()
            self.troll2.rooms = list(self.troll.starting_rooms)
            self.finish_turn()
            return

        if obj is self.food and self.is_here(self.bear):
            self.t_feed(verb, self.bear)
            return

        if obj is not self.axe:
            self.t_drop(verb, obj)
            return

        dwarves_here = [ d for d in self.dwarves if d.room is self.loc ]
        if dwarves_here:
            # 1/3rd chance that throwing the axe kills a dwarf
            if self.choice((True, False, False)):
                self.dwarves.remove(dwarves_here[0])
                self.dwarves_killed += 1
                if self.dwarves_killed == 1:
                    self.write_message(149)
                else:
                    self.write_message(47)
            else:
                self.write_message(48)  # Miss
            self.axe.drop(self.loc)
            self.do_motion(self.vocabulary['null'])
            return

        if self.is_here(self.dragon) and self.dragon.prop == 0:
            self.write_message(152)
            self.axe.drop(self.loc)
            self.do_motion(self.vocabulary['null'])
            return

        if self.is_here(self.troll):
            self.write_message(158)
            self.axe.drop(self.loc)
            self.do_motion(self.vocabulary['null'])
            return

        if self.is_here(self.bear) and self.bear.prop == 0:
            self.write_message(164)
            self.axe.drop(self.loc)
            self.axe.is_fixed = True
            self.axe.prop = 1
            self.finish_turn()
            return

        self.t_attack(verb, None)

    def i_quit(self, verb):  #8180
        def callback(yes):
            self.write_message(54)
            if yes:
                self.score_and_exit()
        self.yesno(self.messages[22], callback)

    def t_find(self, verb, obj):  #9190
        if obj.is_toting:
            self.write_message(24)
        elif self.is_closed:
            self.write_message(138)
        elif (self.is_here(obj) or
            obj is self.loc.liquid or
            obj is self.dwarf and any(d.room is self.loc for d in self.dwarves)):
            self.write_message(94)
        else:
            self.write(verb.default_message)
        self.finish_turn()

    t_inventory = t_find

    def i_inventory(self, verb):  #8200
        first = True
        objs = [ obj for obj in self.inventory if obj is not self.bear ]
        for obj in objs:
            if first:
                self.write_message(99)
                first = False
            self.write(obj.inventory_message)
        if self.bear.is_toting:
            self.write_message(141)
        if not objs:
            self.write_message(98)
        self.finish_turn()

    def t_feed(self, verb, obj):  #9210
        if obj is self.bird:
            self.write_message(100)
        elif obj is self.troll:
            self.write_message(182)
        elif obj is self.dragon:
            if self.dragon.prop != 0:
                self.write_message(110)
            else:
                self.write_message(102)
        elif obj is self.snake:
            if self.is_closed or not self.is_here(self.bird):
                self.write_message(102)
            else:
                self.write_message(101)
                self.bird.destroy()
                self.bird.prop = 0
                self.impossible_treasures += 1
        elif obj is self.dwarf:
            if self.is_here(self.food):
                self.write_message(103)
                self.dwarf_stage += 1
            else:
                self.write(verb.default_message)
        elif obj is self.bear:
            if not self.is_here(self.food):
                if self.bear.prop == 0:
                    self.write_message(102)
                elif self.bear.prop == 3:
                    self.write_message(110)
                else:
                    self.write(verb.default_message)
            else:
                self.food.destroy()
                self.bear.prop = 1
                self.axe.is_fixed = False
                self.axe.prop = 0
                self.write_message(168)
        else:
            self.write_message(14)
        self.finish_turn()

    def i_fill(self, verb):  #9220
        if self.is_here(self.bottle):
            return self.t_fill(verb, self.bottle)
        self.ask_verb_what(verb)

    def t_fill(self, verb, obj):
        if obj is self.bottle:
            liquid = self.loc.liquid
            if liquid is None:
                self.write_message(106)
            elif self.bottle.contents:
                self.write_message(105)
            else:
                self.bottle.contents = liquid
                if self.bottle.is_toting:
                    liquid.is_toting = True
                if liquid is self.oil:
                    self.write_message(108)
                else:
                    self.write_message(107)
        elif obj is self.vase:
            #9222
            if self.vase.is_toting:
                if self.loc.liquid is None:
                    self.write_message(144)
                else:
                    self.write_message(145)
                    self.vase.drop(self.loc)
                    self.vase.prop = 2
                    self.vase.is_fixed = True
            else:
                self.write(verb.default_message)
        else:
            self.write(verb.default_message)
        self.finish_turn()

    def t_blast(self, verb, obj=None):  #9230
        if self.rod2.prop < 0 or not self.is_closed:
            self.write(verb.default_message)
            self.finish_turn()
            return
        if self.is_here(self.rod2):
            self.bonus = 135
        elif self.loc.n == 115:
            self.bonus = 134
        else:
            self.bonus = 133
        self.write_message(self.bonus)
        self.score_and_exit()

    i_blast = t_blast

    def i_score(self, verb):  #8240
        score, max_score = self.compute_score(for_score_command=True)
        self.write('If you were to quit now, you would score {}'
                   ' out of a possible {}.\n'.format(score, max_score))
        def callback(yes):
            self.write_message(54)
            if yes:
                self.score_and_exit()
        self.yesno(self.messages[143], callback)

    def i_fee(self, verb):  #8250
        for n in range(5):
            if verb.synonyms[n].text == verb.text:
                break  # so that 0=fee, 1=fie, 2=foe, 3=foo, 4=fum
        if n == 0:
            self.foobar = self.turns
            self.write_message(54)
        elif n != self.turns - self.foobar:
            self.write_message(151)
        elif n < 3:
            self.write_message(54)
        else:
            self.foobar = -1
            eggs = self.eggs
            start = eggs.starting_rooms[0]
            if (eggs.is_at(start) or eggs.is_toting and self.loc is start):
                self.write_message(54)
            else:
                troll = self.troll
                if not eggs.rooms and not troll.rooms and not troll.prop:
                    self.troll.prop = 1
                if self.loc is start:
                    self.write(eggs.messages[0])
                elif self.is_here(eggs):
                    self.write(eggs.messages[1])
                else:
                    self.write(eggs.messages[2])
                eggs.rooms = list(eggs.starting_rooms)
                eggs.is_toting = False
        self.finish_turn()

    def i_brief(self, verb):  #8260
        self.write_message(156)
        self.full_description_period = 10000
        self.look_complaints = 0
        self.finish_turn()

    def i_read(self, verb):  #8270
        if self.is_closed and self.oyster.is_toting:
            return self.t_read(verb, self.oyster)
        objs = (self.magazine, self.tablet, self.message)
        objs = list(filter(self.is_here, objs))
        if len(objs) != 1 or self.is_dark:
            self.ask_verb_what(verb)
        else:
            self.t_read(verb, objs[0])

    def t_read(self, verb, obj):  #9270
        if self.is_dark:
            return self.i_see_no(obj.names[0])
        elif (obj is self.oyster and not self.hints[2].used and
              self.oyster.is_toting):
            def callback(yes):
                if yes:
                    self.hints[2].used = True
                    self.write_message(193)
                else:
                    self.write_message(54)
            self.yesno(self.messages[192], callback)
        elif obj is self.oyster and self.hints[2].used:
            self.write_message(194)
        elif obj is self.message:
            self.write_message(191)
        elif obj is self.tablet:
            self.write_message(196)
        elif obj is self.magazine:
            self.write_message(190)
        else:
            self.write(verb.default_message)
        self.finish_turn()

    def t_break(self, verb, obj):  #9280
        if obj is self.vase and self.vase.prop == 0:
            self.write_message(198)
            if self.vase.is_toting:
                self.vase.drop(self.loc)
            self.vase.prop = 2
            self.vase.is_fixed = True
        elif obj is self.mirror and self.is_closed:
            self.write_message(197)
            self.wake_repository_dwarves()
            return
        elif obj is self.mirror:
            self.write_message(148)
        else:
            self.write(verb.default_message)
        self.finish_turn()

    def t_wake(self, verb, obj):  #9290
        if obj is self.dwarf and self.is_closed:
            self.write_message(199)
            self.wake_repository_dwarves()
        else:
            self.write(verb.default_message)
            self.finish_turn()

    def i_suspend(self, verb):
        self.write('Provide "{}" with a filename or open file'.format(
                verb.text))
        self.finish_turn()

    def t_suspend(self, verb, obj):
        if isinstance(obj, str):
            if os.path.exists(obj):  # pragma: no cover
                self.write('I refuse to overwrite an existing file.')
                return
            savefile = open(obj, 'wb')
        else:
            savefile = obj
        r = self.random_generator  # must replace live object with static state
        self.random_state = r.getstate()
        try:
            del self.random_generator
            savefile.write(zlib.compress(pickle.dumps(self), 9))
        finally:
            self.random_generator = r
            if savefile is not obj:
                savefile.close()
        self.write('Game saved')

    def i_hours(self, verb):
        self.write('Open all day')

    @classmethod
    def resume(self, obj):
        """Returns an Adventure game saved to the given file."""
        if isinstance(obj, str):
            savefile = open(obj, 'rb')
        else:
            savefile = obj
        game = pickle.loads(zlib.decompress(savefile.read()))
        if savefile is not obj:
            savefile.close()
        # Reinstate the random number generator.
        game.random_generator = random.Random()
        game.random_generator.setstate(game.random_state)
        del game.random_state
        return game

    def should_offer_hint(self, hint, obj): #40000
        if hint.n == 4:  # cave
            return self.grate.prop == 0 and not self.is_here(self.keys)

        elif hint.n == 5:  # bird
            bird = self.bird
            return self.is_here(bird) and self.rod.is_toting and obj is bird

        elif hint.n == 6:  # snake
            return self.is_here(self.snake) and not self.is_here(self.bird)

        elif hint.n == 7:  # maze
            return (not len(self.objects_here) and
                    not len(self.objects_at(self.oldloc)) and
                    not len(self.objects_at(self.oldloc2)) and
                    len(self.inventory) > 1)

        elif hint.n == 8:  # dark
            return self.emerald.prop != 1 and self.platinum.prop != 1

        elif hint.n == 9:  # witt
            return True

    def start_closing_cave(self):  #10000
        self.grate.prop = 0
        self.fissure.prop = 0
        del self.dwarves[:]
        self.troll.destroy()
        self.troll2.rooms = list(self.troll.starting_rooms)
        if self.bear.prop != 3:
            self.bear.destroy()
        for obj in self.chain, self.axe:
            obj.prop = 0
            obj.is_fixed = False
        self.write_message(129)
        self.clock1 = -1
        self.is_closing = True

    def close_cave(self):  #11000
        ne = self.rooms[115]  # ne end of repository
        sw = self.rooms[116]
        for obj in (self.bottle, self.plant, self.oyster, self.lamp,
                    self.rod, self.dwarf):
            obj.prop = -2 if obj is self.bottle else -1
            obj.drop(ne)
        self.loc = self.oldloc = self.oldloc2 = ne
        for obj in (self.grate, self.snake, self.bird, self.cage,
                    self.rod2, self.pillow):
            obj.prop = -2 if (obj is self.bird or obj is self.snake) else -1
            obj.drop(sw)
        self.mirror.rooms = [ne, sw]
        self.mirror.is_fixed = 1
        self.is_closed = True
        for obj in self.inventory:
            obj.is_toting = False
        self.write_message(132)
        self.move_to()

    # TODO: 12000
    # TODO: 12200
    # TODO: 12400
    # TODO: 12600

    def wake_repository_dwarves(self):  #19000
        self.write_message(136)
        self.score_and_exit()

    def compute_score(self, for_score_command=False):  #20000
        score = maxscore = 2

        for treasure in self.treasures:
            # if ptext(0) is zero?
            if treasure.n > self.chest.n:
                value = 16
            elif treasure is self.chest:
                value = 14
            else:
                value = 12

            maxscore += value

            if treasure.prop >= 0:
                score += 2
            if treasure.rooms and treasure.rooms[0].n == 3 \
                    and treasure.prop == 0:
                score += value - 2

        maxscore += self.max_deaths * 10
        score += (self.max_deaths - self.deaths) * 10

        maxscore += 4
        if not for_score_command and not self.gave_up:
            score += 4

        maxscore += 25
        if self.dwarf_stage:
            score += 25

        maxscore += 25
        if self.is_closing:
            score += 25

        maxscore += 45
        if self.is_closed:
            score += {0: 10, 135: 25, 134: 30, 133: 45}[self.bonus]

        maxscore += 1
        if 108 in (room.n for room in self.magazine.rooms):
            score += 1

        for hint in list(self.hints.values()):
            if hint.used:
                score -= hint.penalty

        return score, maxscore

    def score_and_exit(self):
        score, maxscore = self.compute_score()
        self.write('\nYou scored {} out of a possible {} using {} turns.'
                   .format(score, maxscore, self.turns))
        for i, (minimum, text) in enumerate(self.class_messages):
            if minimum >= score:
                break
        self.write('\n{}\n'.format(text))
        if i < len(self.class_messages) - 1:
            d = self.class_messages[i+1][0] + 1 - score
            self.write('To achieve the next higher rating, you need'
                       ' {} more point{}\n'.format(d, 's' if d > 1 else ''))
        else:
            self.write('To achieve the next higher rating '
                       'would be a neat trick!\n\nCongratulations!!\n')
        self.is_done = True




#model.py
"""Classes representing Adventure game components.

Copyright 2010-2015 Brandon Rhodes.  Licensed as free software under the
Apache License, Version 2.0 as detailed in the accompanying README.txt.

"""
class Move(object):
    """An entry in the travel table."""

    is_forced = False
    verbs = []
    condition = None
    action = None

    def __repr__(self):
        verblist = [ verb.text for verb in self.verbs ]

        c = self.condition[0]
        if c is None:
            condition = ''
        elif c == '%':
            condition = ' %d%% of the time' % self.condition[1]
        elif c == 'not_dwarf':
            condition = ' if not a dwarf'
        elif c == 'carrying':
            condition = ' if carrying %s' % self.condition[1]
        elif c == 'carrying_or_in_room_with':
            condition = ' if carrying or in room with %s' % self.condition[1]
        elif c == 'prop!=':
            condition = ' if prop %d != %d' % self.condition[1:]

        if isinstance(self.action, Room):
            action = 'moves to %r' % (self.action.short_description
                or self.action.long_description[:20]).strip()
        elif isinstance(self.action, Message):
            action = 'prints %r' % self.action.text
        else:
            action = 'special %d' % self.action

        return '<{}{} {}>'.format('|'.join(verblist), condition, action)

class Room(object):
    """A location in the game."""

    long_description = ''
    short_description = ''
    times_described = 0
    visited = False

    is_light = False
    is_forbidden_to_pirate = False
    liquid = None
    trying_to_get_into_cave = False
    trying_to_catch_bird = False
    trying_to_deal_with_snake = False
    lost_in_maze = False
    pondering_dark_room = False
    at_witts_end = False

    def __init__(self):
        self.travel_table = []

    def __repr__(self):
        return '<room {} at {}>'.format(self.n, hex(id(self)))

    @property
    def is_forced(self):
        return self.travel_table and self.travel_table[0].is_forced

    @property
    def is_aboveground(self):
        return 1 <= self.n <= 8

    @property
    def is_before_hall_of_mists(self):
        return self.n < 15

    @property
    def is_after_hall_of_mists(self):
        return self.n >= 15

    @property
    def is_dark(self):
        return not self.is_light

class Word(object):
    """A word that can be used as part of a command."""

    text = None
    kind = None
    default_message = None

    def __init__(self):
        self.synonyms = [ self ]

    def __repr__(self):
        return '<Word {}>'.format(self.text)

    def __eq__(self, text):
        return any( word.text == text for word in self.synonyms )

    def add_synonym(self, other):
        """Every word in a group of synonyms shares the same list."""
        self.synonyms.extend(other.synonyms)
        other.synonyms = self.synonyms

class Object(object):
    """An object in the game, like a grate, or a rod with a rusty star."""

    def __init__(self):
        self.is_fixed = False
        self.is_treasure = False
        self.inventory_message = ''
        self.messages = {}
        self.names = []
        self.prop = 0
        self.rooms = []
        self.starting_rooms = []
        self.is_toting = False
        self.contents = None  # so the bottle can hold things

    def __repr__(self):
        return '<Object %d %s %x>' % (self.n, '/'.join(self.names), id(self))

    def __hash__(self):
        return self.n

    def __eq__(self, other):
        return any( text == other for text in self.names )

    def is_at(self, room):
        return room in self.rooms

    def carry(self):
        self.rooms[:] = []
        self.is_toting = True

    def drop(self, room):
        self.rooms[:] = [ room ]
        self.is_toting = False

    def hide(self):
        self.rooms[:] = []
        self.is_toting = False

    def destroy(self):
        self.hide()

class Message(object):
    """A message for printing."""
    text = ''

    def __str__(self):
        return self.text

class Hint(object):
    """A hint offered if the player loiters in one area too long."""

    turns_needed = 0
    turn_counter = 0
    penalty = 0
    question = None
    message = None
    used = False

    def __init__(self):
        self.rooms = []

class Dwarf(object):
    is_dwarf = True
    is_pirate = False

    def __init__(self, room):
        self.start_at(room)
        self.has_seen_adventurer = False

    def start_at(self, room):
        self.room = room
        self.old_room = room

    def can_move(self, move):
        if not isinstance(move.action, Room):
            return False
        room = move.action
        return (room.is_after_hall_of_mists
                and not room.is_forced
                and not move.condition == ('%', 100))

class Pirate(Dwarf):
    is_dwarf = False
    is_pirate = True




#prompt.py
"""Routines that install Adventure commands for the Python prompt.

Copyright 2010-2015 Brandon Rhodes.  Licensed as free software under the
Apache License, Version 2.0 as detailed in the accompanying README.txt.

"""
import inspect

class ReprTriggeredPhrase(object):
    """Command that happens when Python calls repr() to print them."""

    def __init__(self, game, words):
        self.game = game
        self.words = tuple(words)  # protect against caller changing list

    def __repr__(self):
        """Run this command and return the message that results."""
        output = self.game.do_command(self.words)
        return output.rstrip('\n') + '\n'

    def __call__(self, arg=None):
        """Return a compound command of several words, like `get(keys)`."""
        if arg is None:
            return self
        words = arg.words if isinstance(arg, ReprTriggeredPhrase) else (arg,)
        return ReprTriggeredPhrase(self.game, self.words + words)

    def __getattr__(self, name):
        return ReprTriggeredPhrase(self.game, self.words + (name,))


def install_words(game):
    # stack()[0] is this; stack()[1] is adventure.play(); so, stack()[2]
    namespace = inspect.stack()[2][0].f_globals
    words = [ k for k in game.vocabulary if isinstance(k, str) ]
    words.append('yes')
    words.append('no')
    for word in words:
        identifier = ReprTriggeredPhrase(game, [ word ])
        namespace[word] = identifier
        if len(word) > 5:
            namespace[word[:5]] = identifier




#__main__.py
"""Offer Adventure at a custom command prompt.

Copyright 2010-2015 Brandon Rhodes.  Licensed as free software under the
Apache License, Version 2.0 as detailed in the accompanying README.txt.

"""
# import argparse
# import os
import re
# import readline
# from sys import executable, stdout
# from time import sleep
#from . import load_advent_dat
#from .game import Game

BAUD = 1200

# added - irdumbs
max_char_per_page = 1980
save_path = 'data/adventure/saves/'

class SaveAlreadyExists(Exception):
    pass

class GameAlreadyRunning(Exception):
    pass

class NoTeam(Exception):
    pass

class NoSave(Exception):
    pass

class NoGameRunning(Exception):
    pass

class NoTeamMembers(Exception):
    pass

class Adventure:
    """The original Text Adventure game.
    
    Get a team together and embark on the first adventure together!
    """

    #TODO: make all these classes instead........

    def __init__(self, bot):
        self.bot = bot
        self.game_loops = {}
        self.saves = {}
        self.players = {}
        # serv_li = os.listdir(save_path)
        # for sv in serv_li:
        #     self.saves[sv] = os.listdir(save_path + sv)
        self.teams = fileIO('data/adventure/teams.json', 'load')

        self.game = {} # temp for testing

        # do team name here instead. check who's in teams with self.teams first. switch.
        # game_loops = {
        #     "<channel1_id>" : {
        #         "<author1_id>" : {
        #             "CURRENT_GAME_SAVE" : "<original_author_id>/filename",
        #             #or
        #             "CURRENT_GAME_SAVE" : "team_name/filename", # team_name = 't' + term name
        #             "GAME" : "<Game object>"
        #         }
        #     }
        # }

        # teams = {
        #     "<channel1_id>" : {
        #         "team_name" : ["<author1_id>", "<author2_id>"]
        #     }
        # }

        # teams = {
        #     "<author_id>" : "team_name"
        # }

    # you know what, how about just people create teams as default. Team has leader and members.
    # users don't have their own saves. only teams can play. team of 1 is ok and default
    # when save loaded, attach channel to it in self.saves?

    @commands.group(pass_context=True, aliases=['campsite'], no_pm=True)
    async def adventure(self, ctx):
        """Greetings adventurer. What is it that you plan on doing today?"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @adventure.command(pass_context=True)
    async def load(self, ctx, save=None):
        """loads current team's save. defaults to most recent"""
        server = ctx.message.server
        author = ctx.message.author
        channel = ctx.message.channel

        try:
            team = self.splayers[server.id][channel.id][author.id]
        except:
            team = None

        await self.embark.callback(self, ctx, team, save)
        

    # @adventure.command(pass_context=True)
    # async def save(self, ctx, file):
    #     pass

    # if no team and no save, if user doesn't have a save, new game. otherwise new game must specify team and save

    @adventure.command(pass_context=True)
    async def embark(self, ctx, team: str=None, save: str=None):
        """Start/Continue an adventure.

        If no team or save is given, continues 1st team's last save"""

        server = ctx.message.server
        author = ctx.message.author
        channel = ctx.message.channel

        msg = author.mention

        # TODO: put all team stuff in own functions
        # update teams.json
        first = False # lazy
        if server.id not in self.teams:
            self.teams[server.id] = {"TEAMS" : {}, "MEMBERS" : {}}
            msg += ", the first adventurer in " + server.name + ","
            first = True
        # if no team specified, if user has a team, use 1st one made
        if team is None:
            if author.id not in self.teams[server.id]["MEMBERS"]:
                if first: # lazy way of keeping 1st adv message
                    del self.teams[server.id]
                await self.bot.say("{} You're not a part of a team yet. Start a new team by using `{}campsite embark <team_name>`".format(author.mention, ctx.prefix))
                return
            # TODO: make sure to remove author.id when quit all teams
            team = self.teams[server.id]["MEMBERS"][author.id][0]
            teamname = self.teams[server.id]["TEAMS"][team]["NAME"]
        else:
            teamname = team
            team = self._safe_path(team).lower()

        try:
            leaders = self.get_leaders(server, team)
        except NoTeamMembers:
            self.delete_team(server, team)
            msg += ' finds the remains of an abandoned team. Honoring the deceased, {}'.format(author.mention)
        except:
            pass
        # new team
        if team not in self.teams[server.id]["TEAMS"]:
            # leader is 1st member?
            msg += " starts the {} team and".format(teamname)

            self.teams[server.id]["TEAMS"][team] = {"NAME":teamname, "MEMBERS":[author.id]}
            if author.id not in self.teams[server.id]["MEMBERS"]:
                self.teams[server.id]["MEMBERS"][author.id] = [team]
            else:
                self.teams[server.id]["MEMBERS"][author.id].append(team)
            fileIO('data/adventure/teams.json', 'save', self.teams)
            #print('updated adventure\'s teams.json with '+team)
        else: # existing team
            if author.id not in self.teams[server.id]["TEAMS"][team]["MEMBERS"]:
                # don't allow teams with only 1 member
                try:
                    leaders = self.get_leaders(server, team)
                except NoTeamMembers:
                    await self.bot.say('{} got ran into a problem and dropped it in the console. {} will have to try again.'.format(author.mention, author.name))
                    print('No team members in {} team. This should not be happening. If this continues to happen, please let irdumb know.'.format(team))
                    return
                leaderstr = leaders[0].name + (" or " + leaders[1].name if len(leaders) == 2 else "")
                await self.bot.say("{} You are not part of the {} team. {} would have to `{}team recruit` you".format(author.mention, teamname, leaderstr, ctx.prefix))
                return
            else: # person is in the team
                # check if person is in another team in the current channel. maybe just move him to this team
                try:
                    msg += " brings the {} team back together and".format(teamname)
                    curteam = self.players[server.id][channel.id][author.id]
                    if curteam != team:
                        curtmems = [tmid for tmid, usteam in self.players[server.id][channel.id].items() if curteam == usteam]
                        if len(curtmems) == 1:
                            # remove team from play
                            del self.game_loops[server.id][curteam][channel.id]
                except:
                    pass
        # forgot to cinfirm if overwriting current game. will have to fix up earlier also. !load also. maybe do like audio

        # else:
        #     if player not in team:
        #         reply you haven't joined up with the team yet 


        # update players
        if server.id not in self.players:
            self.players[server.id] = {}
        if channel.id not in self.players[server.id]:
            self.players[server.id][channel.id] = {author.id: team.lower()}
        else:
            self.players[server.id][channel.id][author.id] = team.lower()


        # update game_loops
        if server.id not in self.game_loops:
            self.game_loops[server.id] = {}



        # self.game_loops[server.id][team] = Game()
        # # TODO: make which dat file to choose a setting
        # load_advent_dat(game)
        # if team not in self.game_loops[server.id]:
        #     # what if no 1st save? = True

        #     # self.game_loops[server.id][team] = {} # do elsewhere?
        #     # add it?
        #     pass
        # if ctx.message.channel.id not in self.game_loops:
        #     pass

        # I think it overwrites current game either way. fix
        try:
            if self.game_loops[server.id][team][channel.id].get("PLAYING",False):
                tname = self._team_name(server, team)
                await self.bot.reply('The {} team already has embarked on an adventure in this channel. Any unsaved progress will be lost. Type `overwrite` to discard your unsaved progress.'.format(tname))
                answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
                if 'overwrite' not in answer.content.lower():
                    await self.bot.say('The current adventure continues')
                    return
        except:
            pass
        try:
            game = self.load_game(server, team, channel, save)
            msg += ' continues their adventure!\n\nGame Restored\n'
        except:
            game = self.new_game(server, team, channel, save)
            msg += " sets off on an adventure!..\nInteract with the adventure with `{}> <command>`\n\n".format(ctx.prefix) + game.output
        # try:
        #     game = self.new_game(server, team, channel, save)
        #     msg += " sets off on an adventure!..\n\n\n" + game.output
        # except GameAlreadyRunning:
        #     tname = self.teams[server.id]["TEAMS"][team]["NAME"]
        #     await self.bot.say('{} The {} team already has embarked on an adventure in this channel. Any unsaved progress will be lost. Type `overwrite` to discard your unsaved progress.'.format(author.mention,tname))
        #     answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
        #     if 'overwrite' not in answer.content.lower():
        #         await self.bot.say('The current adventure continues')
        #         return
        #     else:
        #         game = self.load_game(server, team, channel, save)
        #         msg += ' continues their adventure!\n\nGame Restored\n'
        # except SaveAlreadyExists:
        #     game = self.load_game(server, team, channel, save)
        #     msg += ' continues their adventure!\n\nGame Restored\n'
        
        await self.baudout(ctx, msg)
        #load_advent_dat(self.game[team])

    # make team able to be None
    @adventure.command(pass_context=True)
    async def join(self, ctx, team=None):
        """Your team has embarked on an adventure without you?!
        Hurry up and catch up with them!"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        if team is None:
            try:
                teams = self.teams[server.id]["MEMBERS"][author.id]
            except:
                await self.bot.reply('You are not in a team yet. Find a team to recruit you or type `{}team new <team_name>` to start a new one.'.format(ctx.prefix))
                return
            try:
                cteams = set(self.players[server.id][channel.id].values())
                cteams = list(cteams.intersection(teams))
                if cteams:
                    if len(cteams) == 1:
                        team = cteams.pop()
                    else:
                        await self.bot.reply('More than one of your teams have embarked on an adventure in this channel. Please specify which to join.')
                        return
                else:
                    await self.bot.reply('None of your teams have yet to embark on an adventure in this channel.')
                    return
            except:
                await self.bot.reply('There are no teams on adventures in this channel.')
                return
        team = self._safe_path(team).lower()

        try:
            tname = self._team_name(server,team)
        except:
            await self.bot.reply('There is no team by that name.')
            return
        try:
            leaders = [m.name for m in self.get_leaders(server, team)]
        except NoTeamMembers:
            self.delete_team(server, team)
            await self.bot.reply('The only thing left of the {} team is their silent remains. You would not like to join them.'.format(tname))
            return
        try:
            if team not in self.teams[server.id]["MEMBERS"][author.id]:
                leaders = " or ".join(leaders)
                await self.bot.reply('you are not a part of the {} team. You\'d need to ask {} to recruit you'.format(tname, leaders))
                return
        except:
            await self.bot.reply('you are not a part of the {} team. You\'d need to ask {} to recruit you'.format(tname, leaders))
            return

        # team exists and in team. add now
        if author.id in self.players[server.id][channel.id] and team == self.players[server.id][channel.id][author.id]:
            await self.bot.say('{} must have spaced out and forgot that they were already on the adventure with the {} team..'.format(author.mention,tname))
            return
        self.players[server.id][channel.id][author.id] = team
        phrases = ['catches up with the rest of the {} team','finally joins the {} team on their adventure','gets reunited with the {} team!','joins in the {} team\'s adventure!']
        await self.bot.say(author.mention+' '+choice(phrases).format(tname))


    @adventure.command(pass_context=True, name='quit')
    async def _quit(self, ctx):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        try:
            team = self.players[server.id][channel.id][author.id]
            tname = self._team_name(server, team)
            del self.players[server.id][channel.id][author.id]
            await self.bot.say('{} left the {} team\'s adventure in this channel.'.format(author.mention, tname))
        except:
            await self.bot.say('{} You are not part of any adventure in this channel'.format(author.mention))

    @adventure.command(pass_context=True, name='info')
    async def adventure_info(self, ctx):
        """Information about your current adventure in this channel"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        try:
            team = self.players[server.id][channel.id][author.id]
        except:
            msg = "You are not a part of any adventure in this channel. "
            if server.id in self.players and channel.id in self.players[server.id]:
                if server.id in self.teams and author.id in self.teams[server.id]["MEMBERS"]:
                    msg += "If your team has embarked on an adventure in this channel, type `{}adventure join [team_name]` to join your teammates!".format(ctx.prefix)
                else:
                    msg += "You need to create a team or be recruited into one first. Type `{}team new <team_name>` to create a new team.".format(ctx.prefix)
            await self.bot.reply(msg)
            return
        tname = self._team_name(server, team)
        save = self.game_loops[server.id][team][channel.id]["SAVE"]
        fsave = self._format_name(save)
        leaders = self.get_leaders(server, team)
        players = [server.get_member(uid) for uid, tm in self.players[server.id][channel.id].items() if tm == team]
        msg = "The {} team has embarked on an adventure in the {} channel".format(tname, channel.mention)
        if save is not None:
            msg += " on the {} save".format(fsave)
        msg += ".\n\nThe member(s) present are:\n"
        labels = ["\_**__The Leader__**\_","__The Co Leader__"]
        for num, ld in enumerate(leaders):
            if ld in players:
                players.remove(ld)
                msg += "{}\n {}\n\n".format(labels[num], ld.name)
        if players:
            msg += '\n'.join([p.name for p in players]) + '\n\n'
        msg += '`{}> inventory`:\n'.format(ctx.prefix)
        msg += self.game_loops[server.id][team][channel.id]["GAME"].do_command(['inven'], ctx, self)
        msg += '\nYou `{}> look` at your surroundings.\n\n'.format(ctx.prefix)
        msg += self.game_loops[server.id][team][channel.id]["GAME"].do_command(['look'], ctx, self)
        await self.baudout(ctx, author.mention+', '+msg)


    @commands.group(pass_context=True, no_pm=True)
    async def team(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @team.group(pass_context=True, name='list')
    async def team_list(self, ctx):
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)

    @team_list.command(pass_context=True, name='teams')
    async def team_teams(self, ctx):
        author = ctx.message.author
        server = ctx.message.server
        
        try:
            teams = self.teams[server.id]["MEMBERS"][author.id]
        except:
            teams = []
        msg = "You are in {} team".format(len(teams))
        if len(teams):
            if len(teams) > 1:
                msg += 's'
            msg += ':\n'+'\n'.join([str(num+1)+'. '+self.teams[server.id]["TEAMS"][team]["NAME"] for num, team in enumerate(teams)])
        else:
            msg = "You aren't in any teams. Find a team that will recruit you or start a new one with `{}team new <team_name>`".format(ctx.prefix)
        await self.bot.reply(msg)

    @team_list.command(pass_context=True, name='members')
    async def team_members(self, ctx, team=None):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        if team is None:
            try:
                team = self.players[server.id][channel.id][author.id]
            except:
                try:
                    teams = self.teams[server.id]["MEMBERS"][author.id]
                    if len(teams) != 1:
                        await self.bot.reply('You are in more than one team. Please specify which team to list the members for.')
                        return
                    team = teams[0]
                except:
                    await self.bot.reply('You are not in any team. Please specify which team to list the members for.')
                    return
        team = self._safe_path(team).lower()
        tname = self._team_name(server, team)
        if team not in self.teams[server.id]["TEAMS"]:
            await self.bot.reply("The {} team does not exist".format(tname))
            return
        try:
            leaders = self.get_leaders(server, team)
        except NoTeamMembers:
            self.delete_team(server, team)
            await self.bot.reply("The {} team's members have dissapeared long ago. All that remains of their campsite is ashes.".format(tname))
            return
        members = [server.get_member(m).name for m in self.teams[server.id]["TEAMS"][team]["MEMBERS"]]
        msg = "**{}** team members:\n\_**__Leader__**\_\n {}".format(tname, members[0])
        if len(members) > 1:
            msg += "\n\n__Co Leader__\n {}".format(members[1])
        if len(members) > 2:
            msg += '\n\n' + '\n'.join(members[2:])
        await self.bot.reply(msg)

    @team_list.command(pass_context=True, name='saves')
    async def team_saves(self, ctx, team=None):
        # TeamNebNeb didn't show saves also !advernture embark didn't load save
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        if team is None:
            try:
                team = self.players[server.id][channel.id][author.id]
            except:
                try:
                    teams = self.teams[server.id]["MEMBERS"][author.id]
                    if len(teams) != 1:
                        await self.bot.reply('You are in more than one team. Please specify which team to see the saves for.')
                        return
                    team = teams[0]
                except:
                    await self.bot.reply('You are not in any team. Find one that will recruit you or create you own with `{}team new`'.format(ctx.prefix))
                    return
        team = self._safe_path(team).lower()
        tname = self._team_name(server, team)
        try:
            # http://stackoverflow.com/questions/168409/how-do-you-get-a-directory-listing-sorted-by-creation-date-in-python
            files = list(filter(os.path.isfile, glob.glob('data/adventure/saves/{}/{}/*.save'.format(server.id, team))))
            files.sort(key=os.path.getmtime, reverse=True)
            if not files:
                raise NoSave
            msg = tname+"'s save"
            if len(files) > 1:
                msg += 's'
            reg = re.compile('data/adventure/saves/{}/{}/([^/]*).save'.format(server.id,team)) # just bein verbose
            msg += ':\n' + '\n'.join([str(num+1) + ". " + re.findall(reg, sv)[0] for num,sv in enumerate(files)])
            
            await self.bot.reply(msg)
        except Exception as e:
            print(e)
            await self.bot.reply('The {} team does not have any saves'.format(tname))


    # only leaders can recruit?
    @team.command(pass_context=True)
    async def recruit(self, ctx, user: discord.Member, team=None):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        if server.id not in self.teams or author.id not in self.teams[server.id]["MEMBERS"]:
            thingstodo = ['for a belgian waffle', 'for an ice cream cone', 'for a dulce split dazzler:tm:!!', 'for a stroll', 'for a nice chat', 'to play some hopscotch','to a play','to lunch','for a snack','back','..side. {}\'s been holding it in all day!'.format(user.name),'to a concert','to a performance','to see some interpretive dance','to a reading of Shakespeare','to a car show','to a horse race','to a ranch','to the trash can.. in multiple trash bags']
            await self.bot.say('{} doesn\'t have a team, so instead, {} takes {} out {}'.format(author.mention, author.name, user.name, choice(thingstodo)))
            return
        if team is None:
            if len(self.teams[server.id]["MEMBERS"][author.id]) == 1:
                team = self.teams[server.id]["MEMBERS"][author.id][0]
                print('beer')
            else:
                teams = self.teams[server.id]["MEMBERS"][author.id]
                leaders = {team:self.get_leaders(server,team,False) for team in teams}
                teams = [team for team, leads in leaders.items() if author in leads]
                print('steer')
                if len(teams) > 1:
                    try:
                        team = self.players[server.id][channel.id][author.id]
                        print('leer')
                    except:
                        await self.bot.say('{} You\'re not in an adventure in this channel and you\'re in multiple teams. Specify which team to recruit to.'.format(author.mention))
                        return
                else:
                    team = teams[0]

        team = self._safe_path(team).lower()
        tname = self._team_name(server,team)
        try:
            if author not in self.get_leaders(server, team):
                await self.bot.say('You need to be a leader of the {} team to recruit new members.'.format(self.teams[server.id]["TEAMS"][team]["NAME"]))
                return
        except NoTeamMembers:
            self.delete_team(server, team)
            await self.bot.say('The {} team\'s campsite is overgrown and in ruins. It is not certain when they passed away. It is certain though that that team will adventure no more.'.format(tname))
            return
        # team resolved. author is leader of team
        # check if person already in team
        if user.id in self.teams[server.id]["TEAMS"][team]["MEMBERS"]:
            await self.bot.say('{} reminds {} that they are both already in the {} team!'.format(user.mention, author.mention, tname))
            return

        # update teams
        self.teams[server.id]["TEAMS"][team]["MEMBERS"].append(user.id)
        if user.id not in self.teams[server.id]["MEMBERS"]:
            self.teams[server.id]["MEMBERS"][user.id] = [team]
        else:
            self.teams[server.id]["MEMBERS"][user.id].append(team)
        fileIO('data/adventure/teams.json', 'save', self.teams)
        await self.bot.say('{} recruits {} to be part of the {} team!'.format(author.mention, user.mention, tname))

    
    @team.command(pass_context=True)
    async def leave(self, ctx, team):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        try:
            team = self._safe_path(team).lower()
            tname = self._team_name(server,team)
            leaders = self.get_leaders(server,team)
            if len(leaders) == 1:
                raise NoTeamMembers()
        except NoTeam:
            await self.bot.reply('That team does not exist.')
            return
        except NoTeamMembers:
            self.delete_team(server, team)
            await self.bot.reply('All traces of the abandoned team are erased from history.')
            return
        # players
        try:
            if self.players[server.id][channel.id][author.id] == team:
                del self.players[server.id][channel.id][author.id]
        except:
            pass
        # teams
        self.teams[server.id]["TEAMS"][team]["MEMBERS"].remove(author.id)
        if len(self.teams[server.id]["MEMBERS"][uid]) == 1:
            del self.teams[server.id]["MEMBERS"][uid]
        else:
            self.teams[server.id]["MEMBERS"][uid].remove(team)
        await self.bot.say('{} leaves the {} team to seek other adventures'.format(author.mention,tname))

    @team.command(pass_context=True, name='new')
    async def team_new(self, ctx, team):
        await self.bot.reply('Under construction. use `!adventure embark <team_name>` instead')
        return


    
    # TODO: put self into do_command
    @commands.command(pass_context=True, name='>', no_pm=True)
    async def adventure_command(self, ctx, *, text):
        "Do something in your adventure"
        words = re.findall(r'\w+', text)
        if words:
            # await self.baudout(ctx, game.do_command(words))
            channel = ctx.message.channel
            server = ctx.message.server
            author = ctx.message.author
            try:
                team = self.players[server.id][channel.id][author.id]
            except:
                await self.bot.reply('You are not in an adventure. If your team has embarked on one, join them using `{}adventure join`, otherwise embark on your own adventure.'.format(ctx.prefix))
                return
            await self.baudout(ctx, self.game_loops[server.id][team][channel.id]["GAME"].do_command(words, ctx, self))

        pass


    # edited - irdumbs
    async def loop(self):
        # parser = argparse.ArgumentParser(
        #     description='Adventure into the Colossal Caves.',
        #     prog='{} -m adventure'.format(os.path.basename(executable)))
        # parser.add_argument(
        #     'savefile', nargs='?', help='The filename of game you have saved.')
        # args = parser.parse_args()

        if args.savefile is None:
            # move to new
            # need to track difference between channel and user games.
            game = Game()
            load_advent_dat(game)
            game.start()
            await baudout(ctx, game.output)
        else:
            # move to !load
            game = Game.resume(args.savefile)
            await baudout(ctx, 'GAME RESTORED\n')

        while not game.is_finished:
            # move to do
            await asyncio.sleep(2)
            await self.bot.wait_for_message(timeout=15, author=ctx.message.author)
            #line = input('> ')
            words = re.findall(r'\w+', line)
            if words:
                await baudout(ctx, game.do_command(words))


    # edited - irdumbs
    async def baudout(self, ctx, s):
        # for c in s:
        #     sleep(9. / BAUD)  # 8 bits + 1 stop bit @ the given baud rate
        #     stdout.write(c)
        #     stdout.flush()

        # print(s)
        # return

        # should handle PMs too
        # s = s.lower()

        dest = ctx.message.channel
        if len(s) < max_char_per_page:
            await self.bot.send_message(dest,s)
            return
        page_curs = [0,0]
        find_curs = 0
        msgs = []
        while page_curs[1] < len(s):
            # find last \n
            page_curs = [find_curs, find_curs + max_char_per_page]
            if page_curs[1] < len(s):
                find_curs = s[page_curs[0]:page_curs[1]].rfind('\n') + page_curs[0]
                if find_curs <= page_curs[0]:
                    # not found. find last ' '
                    find_curs = s[page_curs[0]:page_curs[1]].rfind(' ') + page_curs[0]
                    if find_curs <= page_curs[0]:
                        # not found. page at char
                        find_curs = page_curs[1]
            else:
                find_curs = page_curs[1]
            msgs.append(s[page_curs[0]:find_curs])
            # I'm ok with \n at the beginning
        for msg in msgs:
            await asyncio.sleep(2)
            await self.bot.send_message(dest,msg)

    # get leader and .. 1st mate? of a team
    # throws NoTeamMembers if no members in team left does not delete the team
    # throws NoTeam if team is None or team doesn't exist
    def get_leaders(self, server, team, err_out=True):
        team = self._safe_path(team).lower()
        if server.id not in self.teams:
            raise NoTeam('No Server Yet')
        if team not in self.teams[server.id]["TEAMS"]:
            raise NoTeam('{} does not exist'.format(team))
        to_remove = []
        leaders = []
        for tmid in self.teams[server.id]["TEAMS"][team]["MEMBERS"]:
            tm = server.get_member(tmid)
            if tm is None:
                to_remove.append(tmid)
            leaders.append(tm)
            if len(leaders) == 2:
                break
        for tmid in to_remove:
            self.teams[server.id]["TEAMS"][team]["MEMBERS"].remove(tmid)
            print('removed {}. {} team member must have left server.'.format(tmid, team))
        fileIO('data/adventure/teams.json', 'save', self.teams)
        if leaders == [] and err_out:
            raise NoTeamMembers('No more team members in {} team'.format(team))
        else:
            return leaders

    def delete_team(self, server, team):
        team = self._safe_path(team).lower()
        bp = 'data/adventure/saves'

        # players
        try:
            players = self.teams[server.id]["TEAMS"][team]["MEMBERS"]
        except:
            players = []
        try:
            files = os.listdir('{}/{}/{}/'.format(bp, server.id, team))
            saves = [s[:-5] for s in files if s.endswith('.save')] # in case 
        except:
            saves = []
        try:
            channels = self.game_loops[server.id][team]
        except:
            try:
                channels = list(self.saves[server.id][team].values())
            except:
                channels = []
        for cid in channels:
            for pid in players:
                if pid in self.players[server.id][cid]:
                    del self.players[server.id][cid][pid]

        # game_loops
        del self.game_loops[server.id][team]
        # teams
        del self.teams[server.id]["TEAMS"][team]
        for pid in players:
            if pid in self.teams[server.id]["MEMBERS"]: # it better be
                if team in self.teams[server.id]["MEMBERS"][pid]: # it better be
                    self.teams[server.id]["MEMBERS"][pid].remove(team)
        fileIO('data/adventure/teams.json', 'save', self.teams)
        # saves
        del self.saves[server.id][team]
        # path
        shutil.rmtree('{}/{}/{}'.format(bp, server.id, team))


    # starts a new game.
    # creates a new save if given and starts it
    # for now assumes advent_dat
    # uses _safe_path
    # throws SaveAlreadyExists if save already exists
    # throws GameAlreadyRunning if game is already running for server:team:channel
    # TODO: move all load_advent_dat elsewhere or grab settings. or grab settings in load_advent_dat
    def new_game(self, server, team, channel, save=None):
        if team is None:
            raise NoTeam()

        bp = 'data/adventure/saves'
        # no need name here
        team = self._safe_path(team).lower()

        # paths
        if save is not None:
            save = self._safe_path(save)
            savefile = save.lower()
            if os.path.exists('{}/{}/{}/{}.save'.format(bp, server.id, team, savefile)):
                raise SaveAlreadyExists('{}/{}/{}.save'.format(server.id, team, savefile))
        os.makedirs('{}/{}/{}'.format(bp, server.id, team),exist_ok=True)

        # update game_loops
        if server.id not in self.game_loops:
            self.game_loops[server.id] = {}
        if team not in self.game_loops[server.id]:
            self.game_loops[server.id][team] = {channel.id:{"PLAYING":False, "SAVE":None, "GAME":None}} # ok to game:none?
        if self.game_loops[server.id][team][channel.id].get("PLAYING",False):
            raise GameAlreadyRunning("{}: {} already has a game running in {}".format(server.id, team, channel.mention))

        # make save
        if save is not None:
            game = Game()
            load_advent_dat(game)
            game.start()
            game.t_suspend('save','{}/{}/{}/{}.save'.format(bp, server.id, team, savefile))

        # update self.saves
        if server.id not in self.saves:
            self.saves[server.id] = {}
        if team not in self.saves[server.id]:
            self.saves[server.id][team] = {}
        if save is not None:
            # not really any danger in letting 1 save traverse 2 channels. just can't let 1 game traverse 2 channels
            # try:
            #     del self.saves[server.id][teamf][save]
            # except:
            #     pass
            try:
                savel = self.game_loops[server.id][teamf][channel.id]['SAVE']
                del self.saves[server.id][teamf][savel.lower()]
            except:
                print('troubles deleting-------------')
            self.saves[server.id][team][savefile] = channel.id

        # start game, load advent.dat
        self.game_loops[server.id][team][channel.id] = {'PLAYING':True, 'SAVE':save, 'GAME':Game()}
        load_advent_dat(self.game_loops[server.id][team][channel.id]['GAME'])
        self.game_loops[server.id][team][channel.id]["GAME"].start()
        return self.game_loops[server.id][team][channel.id]["GAME"]
        # done yet?


    # saves the currently running game
    # uses _safe_path
    # throws NoGameRunning if no game is running
    # not really any danger in letting 1 save traverse 2 channels. just can't let 1 game traverse 2 channels
    def save_game(self, server, team, channel, save):
        if team is None:
            raise NoTeam()
        if save is None:
            raise NoSave()

        bp = 'data/adventure/saves'
        team = self._safe_path(team)
        teamf = team.lower()
        save = self._safe_path(save)
        try:
            if not self.game_loops[server.id][teamf][channel.id]['PLAYING']:
                raise NoGameRunning()
        except:
            raise NoGameRunning('{}: {} doesn\'t have a game running in {}'.format(server.id, team, channel.mention))

        # saves
        # try:
        #     del self.saves[server.id][teamf][self.game_loops[server.id][teamf][channel.id]['SAVE']]
        # except:
        #     print('troubles deleting-------------')
        self.saves[server.id][teamf][save.lower()] = channel.id

        self.game_loops[server.id][teamf][channel.id]['SAVE'] = save

        return self.game_loops[server.id][teamf][channel.id]['GAME'].t_suspend('save','{}/{}/{}/{}.save'.format(bp, server.id, teamf, save.lower()))
        


    # caller must specify team or choose default.
    # loads save into channel. if none given, loads most recent save
    # http://stackoverflow.com/questions/18279063/python-find-newest-file-with-mp3-extension-in-directory
    # throws FileNotFoundError if save doesn't exist
    def load_game(self, server, team, channel, save=None):

        # return # not done
        if team is None:
            raise NoTeam()
        if save is not None:
            save = self._safe_path(save)
        else:
            save = '*'

        # getting save
        bp = 'data/adventure/saves'
        team = self._safe_path(team)
        teamf = team.lower()
        path = '{}/{}/{}/'.format(bp, server.id, teamf)
        # raises file not found 
        try:
            savepath = max(glob.iglob('{}{}.save'.format(path, save)), key=os.path.getctime)
        except ValueError:
            raise FileNotFoundError('No save file found')
        save = savepath[len(path):-5]
        savef = save.lower() # in case I saved it wrong? 
        # game = Game.resume(args.savefile)

        # update all the structs

        # game_loops
        if server.id not in self.game_loops:
            self.game_loops[server.id] = {}
        if teamf not in self.game_loops[server.id]:
            self.game_loops[server.id][teamf] = {channel.id:{"PLAYING":False, "SAVE":None, "GAME":None}} # ok to game:none?

        # saves 
        if server.id not in self.saves:
            self.saves[server.id] = {}
        if teamf not in self.saves[server.id]:
            self.saves[server.id][teamf] = {}
        if save is not None:
            # not really any danger in letting 1 save traverse 2 channels. just can't let 1 game traverse 2 channels
            # try:
            #     del self.saves[server.id][teamf][self.game_loops[server.id][teamf][channel.id]['SAVE']]
            # except:
            #     print('troubles deleting-------------')
            self.saves[server.id][team][savef] = channel.id

        # load the game
        self.game_loops[server.id][teamf][channel.id] = {'PLAYING':True, 'SAVE':save, 'GAME':Game.resume(savepath)}
        return self.game_loops[server.id][teamf][channel.id]["GAME"]


    # deleting a save does not stop the current game in progress
    # throws FileNotFoundError if save file is not found
    def delete_save(self, server, team, save):
        if team is None:
            raise NoTeam()
        if save is None:
            raise NoSave()

        bp = 'data/adventure/saves'
        team = self._safe_path(team).lower()
        save = self._safe_path(save).lower()
        try:
            cid = self.saves[server.id][team][save]
            del self.saves[server.id][team][save]
        except:
            pass
        try:
            self.game_loops[server.id][team][cid]['SAVE'] = None
        except:
            pass
        os.remove('{}/{}/{}/{}.save'.format(bp, server.id, team, save))



    def update_save_struct(self, server, team):
        base_path = 'data/adventure/saves'
        if server.id not in self.saves:
            self.saves[server.id] = {}
        if team not in self.saves[server.id]:
            self.saves[server.id] = {}
        os.makedirs("{}/{}/{}".format(base_path, server.id, team))

    # http://stackoverflow.com/questions/7406102/create-sane-safe-filename-from-any-unsafe-string
    def _safe_path(self, path):
        return "".join(c for c in path if c.isalnum() or c == '_').rstrip()

    def _format_name(self, name):
        if name is None:
            return None
        fchars = ['_','*','`']
        # (?:[{}][^{}]*[{}])*.*([{}])
        pats = ['(.*[^{}])([{}][^{}]*[{}])*.*([{}])'.format(c,c,c,c,c) for c in fchars]
        for num, reg in enumerate(pats):
            name = re.sub(reg, r'\1\\\3', name)
        print(name)
        return name

    def _team_name(self, server, team):
        team = self._safe_path(team).lower()
        return self._format_name(self.teams[server.id]["TEAMS"][team]["NAME"])




    # try:
    #     # of course edit once in bot
    #     # don't forget to correct paths
    #     loop = asyncio.get_event_loop()
    #     loop.run_until_complete(loop())
    # except EOFError:
    #     pass

class MissingFile(Exception):
    pass

def check_folders():
    folders = ("data/adventure", "data/adventure/saves")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_files():
    base_path = "data/adventure/"
    files = ("advent.dat", "LICENSE.ASF-2", "original_README.txt")

    for file in files:
        if not os.path.isfile(base_path + file):
            raise MissingFile(base_path + file + " is missing.")

    files = {'teams.json' : {}, 'settings.json' : {}}
    for file, default in files.items():
        if not os.path.isfile(base_path + file):
            print("Creating default adventure {}...".format(file))
            fileIO(base_path + file, "save", default)
        else:  # consistency check
            current = fileIO(base_path + file, "load")
            if current.keys() != default.keys():
                for key in default.keys():
                    if key not in current.keys():
                        current[key] = default[key]
                        print(
                            "Adding " + str(key) + " field to adventure {}".format(file))
                fileIO(base_path + file, "save", current)
        


def setup(bot):
    check_folders()
    check_files()
    n = Adventure(bot)
    # bot.loop.create_task(n.loop())
    bot.add_cog(n)

