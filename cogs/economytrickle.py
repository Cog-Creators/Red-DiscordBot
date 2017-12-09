import discord
from discord.ext import commands
from random import randint
import datetime
import os
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from copy import deepcopy


DEFAULT_SETTINGS = {"TRICKLE_BOT": False, "NEW_ACTIVE_BONUS": 1,
                    "ACTIVE_BONUS_DEFLATE": 1, "PAYOUT_INTERVAL": 2,
                    "BASE_PAYOUT": 0,
                    "CHANCE_TO_PAYOUT": 50, "PAYOUT_PER_ACTIVE": 1,
                    "ACTIVE_TIMEOUT": 10, "TOGGLE": False, "CHANNELS": []}


class Economytrickle:
    """Economy Trickle

    Gives Economy.py currency to active members every so often.
    The more people active, the more currency to go around!
    This cog is dependant on Economy.py; Future updates to
    Economy.py may break this cog.
    """

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/economytrickle/settings.json")
        self.activeUsers = {}
        self.currentUser = {}
        self.tricklePot = {}
        self.previousDrip = {}

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def trickleset(self, ctx):
        """Changes economy trickle settings
        Trickle amount:
            base amount + (# active users - 1) x multiplier + bonus pot
        Every active user gets the trickle amount. 
        It is not distributed between active users.
        """
        server = ctx.message.server
        settings = self.settings.setdefault(server.id,
                                            deepcopy(DEFAULT_SETTINGS))
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            for k, v in settings.items():
                if k == 'CHANNELS':
                    v = ['#' + c.name if c else 'deleted-channel'
                         for c in (server.get_channel(cid) for cid in v)]
                    v = ', '.join(v)
                v = {True: 'On', False: 'Off'}.get(v, v)
                msg += str(k) + ": " + str(v) + "\n"
            msg += "```"
            await self.bot.say(msg)

    @trickleset.command(name="toggle", pass_context=True)
    async def toggle(self, ctx, context: str=None):
        """Toggles trickling in a server.
        Leaving blank defaults to toggling between channel/server and off

        Options:
            channels
            server
            off
        """
        server = ctx.message.server
        channel = ctx.message.channel
        author = ctx.message.author

        settings = self.settings[server.id]
        context = context.lower() if context else context

        toggled = not settings['TOGGLE']
        choices = {'channels': True, 'server': 'SERVER',
                   'off': False, None: toggled}

        if context not in choices:
            return await send_cmd_help(ctx)

        settings['TOGGLE'] = choices[context]

        msgs = {'SERVER': ('Trickling for all channels that '
                           'the bot can see in this server'),
                True    : ('Trickling only for channels listed '
                           'in `{}trickleset channel`'),  # don care if empty
                False   : 'Trickling turned off in this server'}

        if context is None and settings['TOGGLE']:  # was toggled on
            settings['TOGGLE'] = 'SERVER'
            if settings['CHANNELS']:
                fmt = ("There are channels in the `{}trickleset channel` list."
                       " Turn on trickling only for those channels "
                       "or for the whole server? (channels/server)")
                await self.bot.say(fmt.format(ctx.prefix))
                msg = await self.bot.wait_for_message(timeout=30,
                                                      author=author,
                                                      channel=channel)
                if msg is None:
                    msgs[True] = 'No Response. ' + msgs[True]
                    settings['TOGGLE'] = True
                elif 'serv' not in msg.content.lower():
                    settings['TOGGLE'] = True

        await self.bot.say(msgs[settings['TOGGLE']].format(ctx.prefix))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="channel", pass_context=True)
    async def channel(self, ctx, *one_or_more_channels: discord.Channel):
        """Toggles trickling in one or more channels
        Leaving blank will list the current trickle channels
        """
        server = ctx.message.server
        channel = ctx.message.channel
        author = ctx.message.author
        settings = self.settings[server.id]
        fmt = ''
        if settings['TOGGLE'] is not True:
            fmt = ('Note: You will not see these changes take effect '
                   'until you set `{}trickleset toggle` to '
                   '**channels**.\n'.format(ctx.prefix))

        csets = settings['CHANNELS']
        current = sorted(filter(None, (server.get_channel(c) for c in csets)),
                         key=lambda c: c.position)
        channels = set(one_or_more_channels)

        if not channels:  # no channels specified
            if not current:
                fmt += 'There are no channels set to specifically trickle in.'
            else:
                fmt += ('Channels to trickle in:\n' +
                        '\n'.join('\t' + c.mention for c in current))
            return await self.bot.say(fmt)

        current = set(current)
        overlap_choice = ''
        if not (channels.isdisjoint(current) or  # new channels
                current.issuperset(channels)):   # remove channels
            await self.bot.say('Some channels listed are already in the '
                               'trickle list while some are not. Trickle'
                               ' to all the channels you listed, stop '
                               'trickling to them, or cancel? '
                               '(all/stop/cancel)')
            msg = await self.bot.wait_for_message(timeout=30,
                                                  author=author,
                                                  channel=channel)
            overlap_choice = msg.content.lower() if msg else None
            if overlap_choice not in ('all', 'stop'):
                return await self.bot.say('Cancelling. Trickle '
                                          'Channels are unchanged.')

        if overlap_choice == 'all' or channels.isdisjoint(current):
            current.update(channels)
        else:
            current -= channels

        settings['CHANNELS'] = [c.id for c in current]
        await self.bot.say('Trickle channels updated.\n' + fmt)
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="bot", pass_context=True)
    @checks.is_owner()
    async def tricklebot(self, ctx):
        """Enables/disables trickling economy to the bot"""
        sid = ctx.message.server.id
        econ = self.bot.get_cog('Economy')
        settings = self.settings[sid]
        if econ.bank.account_exists(ctx.message.server.me):
            settings["TRICKLE_BOT"] = not settings["TRICKLE_BOT"]
            if self.settings[sid]["TRICKLE_BOT"]:
                await self.bot.say("I will now get currency trickled to me.")
            else:
                await self.bot.say("I will stop getting currency "
                                   "trickled to me.")
            dataIO.save_json("data/economytrickle/settings.json", self.settings)
        else:
            await self.bot.say("I do not have an account registered with the "
                               "`Economy cog`. If you want currency to trickle"
                               " to me too, please use the `registerbot` "
                               "command to open an account for me, then try "
                               "again.")

    @trickleset.command(name="timeout", pass_context=True)
    async def timeout(self, ctx, minutes: float):
        """Sets the amount of time a user is considered active after sending a message
        """
        sid = ctx.message.server.id
        if minutes <= 0:
            await self.bot.say("Timeout interval must be more than 0")
            return
        self.settings[sid]["ACTIVE_TIMEOUT"] = minutes
        await self.bot.say("Active user timeout is now: " +
                           str(self.settings[sid]["ACTIVE_TIMEOUT"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="interval", pass_context=True)
    async def interval(self, ctx, minutes: float):
        """Sets the interval that must pass between each trickle
        """
        sid = ctx.message.server.id
        if minutes <= 0:
            await self.bot.say("```Warning: With an interval this low, "
                               "a trickle will occur after every message```")
        self.settings[sid]["PAYOUT_INTERVAL"] = minutes
        await self.bot.say("Payout interval is now: " +
                           str(self.settings[sid]["PAYOUT_INTERVAL"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="multiplier", pass_context=True)
    async def multiplier(self, ctx, amt: float):
        """Sets the amount added to the trickle amount per active user.
        """
        sid = ctx.message.server.id
        if amt < 0:
            await self.bot.say("```Warning: A negative multiplier would "
                               "be taking away currency the more active "
                               "users you have. This will discourage "
                               "conversations.```")
        self.settings[sid]["PAYOUT_PER_ACTIVE"] = amt
        await self.bot.say("Base payout per active user is now: " +
                           str(self.settings[sid]["PAYOUT_PER_ACTIVE"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="bonus", pass_context=True)
    async def activebonus(self, ctx, amt: int):
        """Sets the bonus amount per new active user.

        When there is a new active user,
        this amount will be added to the bonus pot
        """
        sid = ctx.message.server.id
        if amt < 0:
            await self.bot.say("```Warning: Bonus amount should be positive "
                               "unless you want to discourage conversations"
                               "```")
        self.settings[sid]["NEW_ACTIVE_BONUS"] = amt
        await self.bot.say("Bonus per new active user is now: " +
                           str(self.settings[sid]["NEW_ACTIVE_BONUS"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="base", pass_context=True)
    async def activebase(self, ctx, amt: int):
        """Sets the base amount to give to every active user.

        Every trickle, active users will get *at least* this amount
        """
        sid = ctx.message.server.id
        if amt < 0:
            await self.bot.say("```Warning: Base amount should be positive "
                               "unless you want to discourage conversations"
                               "```")
        self.settings[sid]["BASE_PAYOUT"] = amt
        await self.bot.say("Base amount for active users is now: " +
                           str(self.settings[sid]["BASE_PAYOUT"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="leak", pass_context=True)
    async def bonusdeflate(self, ctx, amt: int):
        """Sets the bonus pot leak amount.

        Whenever a trickle occurs (successful or not),
        this amount is taken out of the bonus pot
        """
        sid = ctx.message.server.id
        if amt < 0:
            await self.bot.say("```Warning: The bonus pot does not reset each "
                               "trickle. With a negative leak, the bonus pot "
                               "will grow each time a trickle occurs.```")
        self.settings[sid]["ACTIVE_BONUS_DEFLATE"] = amt
        await self.bot.say("Bonus pot leak is now: " +
                           str(self.settings[sid]["ACTIVE_BONUS_DEFLATE"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    @trickleset.command(name="chance", pass_context=True)
    async def succeedchance(self, ctx, percentage: int):
        """Sets percentage chance that the trickle will be successful [0-100]
        """
        sid = ctx.message.server.id
        if percentage < 0 or percentage > 100:
            await self.bot.say("Percentage chance must be between 0 and 100")
            return
        if percentage == 0:
            await self.bot.say("```Warning: This will stop all trickling. "
                               "You might as well just unload "
                               "cogs.economytrickle```")
        self.settings[sid]["CHANCE_TO_PAYOUT"] = percentage
        await self.bot.say("Successful trickle chance is now: " +
                           str(self.settings[sid]["CHANCE_TO_PAYOUT"]))
        dataIO.save_json("data/economytrickle/settings.json", self.settings)

    # if Economy.py updates, this may break
    @commands.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def registerbot(self, ctx, agree: str):
        """registers the bot into Economy.py bank.

        Although nothing bad will probably happen,
        this was not how Economy was intended.
        I can't guarantee this and/or the economy cog won't break.
        I can't gaurantee your bank won't get corrupted.
        If you understand this and still want to register
        your bot in the bank, type
        [p]registerbot "I have read and understand. Just give my bot money!"
        """
        if agree.lower() == ("i have read and understand. "
                             "just give my bot money!"):
            econ = self.bot.get_cog('Economy')
            if not econ:
                await self.bot.say('Unable to load Economy cog. '
                                   'Please make sure it is loaded with '
                                   '`{}load economy`'.format(ctx.prefix))
                return
            botuser = ctx.message.server.me
            if not econ.bank.account_exists(botuser):
                econ.bank.create_account(botuser)
                await self.bot.say("Account opened for {}. Current balance: "
                                   "{}".format(botuser.mention,
                                               econ.bank.get_balance(botuser)))
            else:
                await self.bot.say("{} already has an account at the "
                                   "Twentysix bank.".format(botuser.mention))
        else:
            await send_cmd_help(ctx)

    async def trickle(self, message):
        """trickle pb to active users"""
        if message.server is None or not isinstance(message.author,
                                                    discord.Member):
            return

        # if different person speaking
        sid = message.server.id
        if sid not in self.settings:
            self.settings[sid] = deepcopy(DEFAULT_SETTINGS)
            dataIO.save_json("data/economytrickle/settings.json", self.settings)

        toggle = self.settings[sid]['TOGGLE']
        if not toggle:
            return
        if (toggle is True and
                message.channel.id not in self.settings[sid]['CHANNELS']):
            return
        current_user = self.currentUser.get(sid, None)
        diff_user = current_user != message.author.id
        is_self = message.author.id == self.bot.user.id
        is_bot = message.author.bot 
        self_can = self.settings[sid]["TRICKLE_BOT"]
        if (((not is_bot) or (is_self and self_can)) and diff_user):
            # print("----Trickle----")
            # add user or update timestamp and make him current user
            if not is_self:  # don't allow self to be the current user
                self.currentUser[sid] = message.author.id
            if not self.currentUser.get(sid, None):
                return

            now = datetime.datetime.now()
            # new active user bonus
            # if server has a list yet
            active_users = self.activeUsers.get(sid, None)
            if sid in self.activeUsers.keys():
                # self.bot doesn't add to active bonus
                if self.currentUser[sid] not in active_users.keys():
                    # might be redundant
                    # if self.tricklePot.get(sid,None) is None:
                    #   self.tricklePot[sid] = 0
                    # don't wanna add to the pot for bot
                    if message.author.id != self.bot.user.id:
                        self.tricklePot[sid] += self.settings[sid]["NEW_ACTIVE_BONUS"]
            else:
                self.activeUsers[sid] = {}
                self.tricklePot[sid] = 0
            # timestamp is UTC time, not my time
            self.activeUsers[sid][message.author.id] = now

            payout_interval = self.settings[sid]["PAYOUT_INTERVAL"]
            threshold = (now - datetime.timedelta(minutes=payout_interval))
            if sid not in self.previousDrip.keys():
                self.previousDrip[sid] = now
            elif self.previousDrip[sid] < threshold:
                self.previousDrip[sid] = now
                # stuffs
                # amount to give it dependant on how many people are active
                # half the time don't give anything
                trickleAmt = 0
                if randint(1, 100) <= self.settings[sid]["CHANCE_TO_PAYOUT"]:
                    numActive = len(self.activeUsers[sid])
                    # don't want bot to add to payout
                    if self.bot.user.id in self.activeUsers[sid]:
                        numActive -= 1
                    trickleAmt = int(self.settings[sid]["BASE_PAYOUT"] +
                                     (numActive - 1) *
                                     self.settings[sid]["PAYOUT_PER_ACTIVE"] +
                                     self.tricklePot[sid])
                # debug
                debug = "{} - trickle: {} > ".format(message.server.name,
                                                     trickleAmt)
                active_timeout = self.settings[sid]["ACTIVE_TIMEOUT"]
                expireTime = now - datetime.timedelta(minutes=active_timeout)

                econ = None  # <-- lol wtf who write this ( ͡° ͜ʖ ͡°)
                econ = self.bot.get_cog('Economy')
                if econ is None:
                    print("--- Error: Was not able to load Economy cog "
                          "into Economytrickle. ---")
                # all active users
                # print(message.author.id + " " + message.author.name)
                templist = []
                for u in self.activeUsers[sid].keys():
                    us = message.server.get_member(u)
                    # print(str(now) + " | " + str(self.activeUsers[u]) + " " + str(expireTime) + str(self.activeUsers[u] > expireTime))
                    if self.activeUsers[sid][u] < expireTime or us is None:
                        templist.append(u)
                    elif econ.bank.account_exists(us):
                        econ.bank.deposit_credits(us, trickleAmt)
                        # debug
                        debug += message.server._members[u].name + ", "
                # debug
                if len(templist) != 0:
                    debug += "\n--- expired - removing | "
                for u in templist:
                    del self.activeUsers[sid][u]
                    debug += message.server._members[u].name + ", "
                debug += ("\n{} ausers left in server--"
                          .format(len(self.activeUsers[sid])))
                print(debug)
                # new active user bonus reduce
                if self.tricklePot[sid] > 0:
                    self.tricklePot[sid] -= self.settings[sid]["ACTIVE_BONUS_DEFLATE"]
                    if self.tricklePot[sid] < 0:
                        self.tricklePot[sid] = 0


def check_folders():
    if not os.path.exists("data/economytrickle"):
        print("Creating data/economytrickle folder...")
        os.makedirs("data/economytrickle")


def check_files():
    serverSettings = {}

    f = "data/economytrickle/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty economytrickle's settings.json...")
        dataIO.save_json(f, serverSettings)

    settings = dataIO.load_json(f)
    dirty = False
    for v in settings.values():  # consistency check
        missing_keys = set(DEFAULT_SETTINGS) - set(v)
        fill = {k: DEFAULT_SETTINGS[k] for k in missing_keys}
        v.update(fill)
        if missing_keys:
            dirty = True

    if dirty:
        dataIO.save_json(f, settings)


# unload cog if economy isn't loaded

def setup(bot):
    check_folders()
    check_files()
    n = Economytrickle(bot)
    bot.add_listener(n.trickle, "on_message")
    bot.add_cog(n)
