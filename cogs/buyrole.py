import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
import asyncio
from .utils import checks
import os


class InvalidRole(Exception):
    pass


class InsufficientBalance(Exception):
    pass


class Buyrole:
    """Allows the user to buy a role with economy balance"""

    __author__ = "Kowlin"
    __version__ = "BR-V2.2.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings_loc = 'data/buyrole/settings.json'
        self.settings_dict = dataIO.load_json(self.settings_loc)

    @commands.command(pass_context=True, aliases=['requestrole'], no_pm=True)
    async def buyrole(self, ctx, *, role: str = None):
        """Buy roles with economy credits,
        To see the list of roles you can buy use ``buyrole``"""
        server = ctx.message.server
        str_role = role
        role = discord.utils.get(server.roles, name=str_role)
        if role is None:
            await self.bot.say('I cannot find the role you\'re trying to buy.\n'
                               'Please make sure that you\'ve capitalised the role name.')
            return
        if server.id not in self.settings_dict:
            await self.bot.say('This server doesn\'t have a shop yet')
        elif role in ctx.message.author.roles:
            await self.bot.say('You already own this role.')
        elif 'Economy' not in self.bot.cogs:
            await self.bot.say('Economy isn\'t loaded. Please load economy.')
        elif role is None:
            embed = await self._create_list(server)  # Return the list on a empty command
            await self.bot.say(embed=embed)
        elif self.settings_dict[server.id]['toggle'] is False:
            await self.bot.say('The shop is disabled')
        else:
            try:
                await self._process_role(server, ctx.message.author, role, False)
                await self.bot.say('Done! You\'re now the proud owner of {}'.format(role.name))
            except InvalidRole:
                await self.bot.say('This role cannot be bought')
            except InsufficientBalance:
                await self.bot.say('You do not have enough balance to buy this role')

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def buyroleset(self, ctx):
        """Manage buyrole"""
        if 'Economy' not in self.bot.cogs:
            raise RuntimeError('The Economy cog needs to be loaded for this cog to work')
        server = ctx.message.server
        if server.id not in self.settings_dict:
            self.settings_dict[server.id] = {'toggle': True, 'roles': {}, 'colour': 0x72198b}
            self.save_json()
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @buyroleset.command(pass_context=True, no_pm=True, aliases=['edit'])
    async def add(self, ctx, role: discord.Role, price: int):
        """Add a role for users to buy"""
        server = ctx.message.server
        if price < 0:
            await self.bot.say('The price cannot be below 0. To make it free use 0 as the price.')  # In command error handling, no excetion due the rarity.
        elif role.id in self.settings_dict[server.id]['roles']:
            await self.bot.say('{0} was already in the list. The price of {0} is now {1}.'.format(role.name, self._price_string(price, False)))
            self.settings_dict[server.id]['roles'][role.id]['price'] = price
        else:
            self.settings_dict[server.id]['roles'][role.id] = {'price': price, 'uniquegroup': 0}
            await self.bot.say('{0} added to the buyrole list. The price of {0} is now {1}.'.format(role.name, self._price_string(price, False)))
        self.save_json()

    @buyroleset.command(pass_context=True, no_pm=True)
    async def remove(self, ctx, role: discord.Role):
        """Remove a role for users to buy"""
        server = ctx.message.server
        try:
            del self.settings_dict[server.id]['roles'][role.id]
            self.save_json()
            await self.bot.say('Removed {} from the buyrole list.'.format(role.name))
        except:
            await self.bot.say('This role isn\'t in the list.')

    @buyroleset.command(pass_context=True, no_pm=True)
    async def toggle(self, ctx, toggle: bool):
        """Open or close the buyrole shop

        Use either True or False
        buyroleset toggle true"""
        server = ctx.message.server
        if toggle is True:
            if self.settings_dict[server.id]['toggle'] is True:
                await self.bot.say('The shop is already enabled')
            else:
                self.settings_dict[server.id]['toggle'] = True
                self.save_json()
                await self.bot.say('The shop has been enabled.')
        elif toggle is False:
            if self.settings_dict[server.id]['toggle'] is False:
                await self.bot.say('The shop is already disabled')
            else:
                self.settings_dict[server.id]['toggle'] = False
                self.save_json()
                await self.bot.say('The shop has been disabled')
        else:
            raise Exception('InvalidToggle')

    @buyroleset.command(pass_context=True, no_pm=True)
    async def uniquegroup(self, ctx, role: discord.Role, groupid: int):
        """Set a role to a unique group ID,
        This means that a user cannot have more then one role from the same group.

        Any role sharing the same ID will be considered a group.
        GroupID 0 will not be considered unique and can share other roles."""
        server = ctx.message.server
        if role.id not in self.settings_dict[server.id]['roles']:
            await self.bot.say('This role ins\'t in the buyrole list')
        elif groupid < 0:
            await self.bot.say('The group ID cannot be negative.')
        else:
            # Set the uniquegroup ID here, logic will remain in a subfunction of buyrole
            self.settings_dict[server.id]['roles'][role.id]['uniquegroup'] = groupid
            self.save_json()
            if groupid == 0:
                await self.bot.say('Unique Group ID set. {} isn\'t considered unique.'.format(role.name))
            else:
                await self.bot.say('Unique Group ID set. {} will now be unique in group ID {}'.format(role.name, groupid))

    @buyroleset.command(pass_context=True, no_pm=True, aliases=['color'])
    async def colour(self, ctx, colour: discord.Colour):
        """Set the sidebar colour in the buyrole list."""
        server = ctx.message.server
        self.settings_dict[server.id]['colour'] = colour.value
        self.save_json()
        await self.bot.say('The colour is now set to #{}'.format(hex(colour.value)[2:]))

    def save_json(self):
        dataIO.save_json(self.settings_loc, self.settings_dict)
        # What can I say... I got sick of writing this...

    # Helper Functions
    async def _create_list(self, server):  # A credit to calebj#7377 for helping me out here.
        """Creates the role list for a server"""
        if 'colour' not in self.settings_dict[server.id]:  # Backwards compatability. *Sigh*
            colour = 0x72198b
        else:
            colour = self.settings_dict[server.id]['colour']
        embed = discord.Embed(description='**Role list:**', colour=colour)
        for roleid, roledata in self.settings_dict[server.id]['roles'].items():
            role = discord.utils.get(server.roles, id=roleid)
            if not role:
                continue
            if roledata['uniquegroup'] > 0:
                embed.add_field(name='%s (Unique, ID #%s)' % (role.name, roledata['uniquegroup']), value=self._price_string(roledata['price'], True))
            else:
                embed.add_field(name=role.name, value=self._price_string(roledata['price'], True))
        return embed

    def _price_string(self, price, punctuation: bool):
        if price == 0 and punctuation is True:
            return "Free!"
        elif price == 0 and punctuation is False:
            return "free"
        else:
            return str(price)

    # Role managment (The easy part, lol)
    async def _process_role(self, server, user, role, paid: bool):
        """Process the role that the user is buying.

        For this we require the server, user, and the role the user is trying to buy.
        Server, User and Role should be the their objects.
        Paid is a Bool

        This function is meant as a integration for 3rd party cogs."""
        if server.id not in self.settings_dict:
            raise Exception('Shop is not setup')
        elif role.id not in self.settings_dict[server.id]['roles']:
            raise InvalidRole('This role cannot be bought.')
        else:
            role_dict = self.settings_dict[server.id]['roles'][role.id]
            role_list = []
            # START LOGIC UNIQUE ROLES
            if self.settings_dict[server.id]['roles'][role.id]['uniquegroup'] != 0:
                # Role is unique
                for role_loop, data_loop in self.settings_dict[server.id]['roles'].items():
                    # About this being easy, fuck loops
                    if role_loop != role.id and data_loop['uniquegroup'] == role_dict['uniquegroup']:
                        role_list.append(discord.utils.get(server.roles, id=role_loop))
            # END LOGIC UNIQUE ROLES
            if role_dict['price'] != 0 and paid is False:
                eco = self.bot.get_cog('Economy').bank
                if eco.can_spend(user, role_dict['price']) is True:
                    eco.withdraw_credits(user, role_dict['price'])
                else:
                    raise InsufficientBalance('The user has not enough balance')
            if role_list is not None:
                await self.bot.remove_roles(user, *role_list)
            await asyncio.sleep(0.3)
            await self.bot.add_roles(user, discord.utils.get(server.roles, id=role.id))
            return True


def check_folder():
    if not os.path.exists('data/buyrole'):
        os.makedirs('data/buyrole')


def check_file():
    f = 'data/buyrole/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})
    f = 'data/buyrole/settings.json'


def setup(bot):
    check_folder()
    check_file()
    n = Buyrole(bot)
    bot.add_cog(n)
