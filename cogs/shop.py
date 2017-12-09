# Shop System designed by Redjumpman
# This cog requires tabulate, and creates 1 json file and 2 folders
# Check out my wiki on my github page for more information
# https://github.com/Redjumpman/Jumper-Cogs

# Standard Library
import asyncio
import os
import random
import time
import uuid
from datetime import datetime
from operator import itemgetter

# Discord and Red Bot
import discord
from discord.ext import commands
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
from .utils import checks

# Thrid Party Library
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except ImportError:
    tabulateAvailable = False


class Shop:
    """Purchase server created items with credits."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/shop/system.json"
        self.system = dataIO.load_json(self.file_path)

    @commands.command(pass_context=True, no_pm=True)
    async def inventory(self, ctx):
        """Shows a list of items you have purchased"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        self.user_check(settings, user)
        title = "```{}```".format(self.bordered("{}'s\nI N V E N T O R Y".format(user.name)))
        if not settings["Users"][user.id]["Inventory"]:
            return await self.bot.say("Your inventory is empty.")

        column1 = ["[{}]".format(subdict["Item Name"].title())
                   if "Role" in subdict else subdict["Item Name"].title()
                   for subdict in settings["Users"][user.id]["Inventory"].values()
                   ]
        column2 = [subdict["Item Quantity"]
                   for subdict in settings["Users"][user.id]["Inventory"].values()
                   ]
        headers = ["Item Name", "Item Quantity"]
        data = sorted(list(zip(column1, column2)))
        method = settings["Config"]["Inventory Output Method"]
        msg = await self.inventory_split(user, title, headers, data, method)
        if method == "Chat":
            await self.bot.say(msg)
        else:
            await self.bot.whisper(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def shop(self, ctx):
        """Shop Commands. Use !help Shop for other command groups"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @shop.command(name="version", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _version_shop(self):
        """Shows the version of the shop cog you are running."""
        version = self.system["Version"]
        await self.bot.say("```Python\nYou are running Shop Cog version {}.```".format(version))

    @shop.command(name="redeem", pass_context=True, no_pm=True)
    async def _redeem_shop(self, ctx, *, itemname):
        """Sends a request to redeem an item"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        itemname = itemname.title()
        confirmation_number = str(uuid.uuid4())
        if itemname not in settings["Users"][user.id]["Inventory"]:
            await self.bot.say("You do not have that item to redeem")
        elif await self.redeem_handler(settings, ctx, user, itemname, confirmation_number):
            await self.notify_handler(settings, ctx, itemname, user, confirmation_number)
        else:
            await self.bot.say("You have too many items pending! You may only have 12 items "
                               "pending at one time.")

    @shop.command(name="addbulk", pass_context=True, no_pm=True, hidden=True, enabled=False)
    @checks.is_owner()
    async def _addbulk_shop(self, ctx, *, filename):
        """Adds a bulk list of items from a text file."""
        await self.bot.say("Coming soon!")

    @shop.command(name="add", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _add_shop(self, ctx, quantity: int, cost: int, *, itemname):
        """Adds items to the shop. Use 0 in quantity for infinite."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        itemname = itemname.title()
        item_count = len(settings["Shop List"].keys())
        self.shop_item_add(settings, itemname, cost, quantity)
        if quantity == 0:
            quantity = "An infinite quantity of"
        await self.bot.say("```{} {} have been added to {} shop.\n{} items available for purchase "
                           "in the store.```".format(quantity, itemname, shop_name, item_count))

    @shop.command(name="addrole", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _addrole_shop(self, ctx, quantity: int, cost: int, role: discord.Role):
        """Add a role token to shop list. Requires buyrole from refactored cogs"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        if 'Buyrole' not in self.bot.cogs:
            msg = ("This feature requires the buyrole cog from the Refactored Cogs repo.\n"
                   "Load buyrole to use this function.")
        else:
            self.shop_item_add(settings, role, cost, quantity, role=True)
            item_count = len(settings["Shop List"])
            msg = ("```{} {} have been added to {} shop.\n{} item(s) available for purchase in the "
                   "store.```".format(quantity, role.name, shop_name, item_count))
        await self.bot.say(msg)

    @shop.command(name="remove", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _remove_shop(self, ctx, *, itemname):
        """Removes an item from the shop."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        itemname = itemname.title()
        if itemname in settings["Shop List"]:
            del settings["Shop List"][itemname]
            dataIO.save_json(self.file_path, self.system)
            msg = "```{} has been removed from {} shop.```".format(itemname, shop_name)
        else:
            msg = ("There is no item with that name in the {} shop. "
                   "Please check your spelling.".format(shop_name))
        await self.bot.say(msg)

    @shop.command(name="clear", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clear_shop(self, ctx):
        """Wipes the entire shop list"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        shop_name = settings["Config"]["Shop Name"]
        await self.bot.say("Do you want to wipe the entire shop list? "
                           "You cannot undue this action.")
        choice = await self.bot.wait_for_message(timeout=15, author=user)
        if choice is None:
            msg = "Cancelling shop wipe."
        elif choice.content.title() == "No":
            msg = "Cancelling shop wipe."
        elif choice.content.title() == "Yes":
            settings["Shop List"] = {}
            dataIO.save_json(self.file_path, self.system)
            msg = "The shop list has been cleared from the {} Shop".format(shop_name)
        else:
            msg = "Improper response. Cancelling shop wipe."
        await self.bot.say(msg)

    @shop.command(name="buy", pass_context=True, no_pm=True)
    async def _buy_shop(self, ctx, quantity: int, *, itemname):
        """Purchase a shop item with credits."""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        shop_name = settings["Config"]["Shop Name"]
        itemname = itemname.title()
        self.user_check(settings, user)

        if quantity < 1:
            return await self.bot.say("You can't buy 0...")

        if not settings["Config"]["Shop Open"]:
            return await self.bot.say("The {} shop is currently closed.".format(shop_name))

        if await self.shop_check(user, settings, quantity, itemname):
            if settings["Config"]["Pending Type"] == "Manual":
                self.user_add_item(settings, user, quantity, itemname)
                cost = self.discount_calc(settings, itemname, quantity)
                self.shop_item_remove(settings, quantity, itemname)
                await self.bot.say("```You have purchased {} {}(s) for {} credits.\n"
                                   "{} has been added to your "
                                   "inventory.```".format(quantity, itemname, cost, itemname))
            else:
                msgs = settings["Shop List"][itemname]["Buy Msg"]
                if not msgs:
                    msg = ("Oops! The admin forgot to set enough msgs for this item. "
                           "Please contact them immediately.")
                    await self.bot.say(msg)
                else:
                    msg = random.choice(msgs)
                    msgs.remove(msg)
                    cost = self.discount_calc(settings, itemname, quantity)
                    self.shop_item_remove(settings, quantity, itemname)
                    await self.bot.whisper("You purchased {} {}(s) for {} credits. "
                                           "Details for this item are:\n"
                                           "```{}```".format(quantity, itemname, cost, msg))

    @shop.command(name="give", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _give_shop(self, ctx, user: discord.Member, *, itemname):
        """Adds an item to a users inventory. Item must be in the shop."""
        author = ctx.message.author
        settings = self.check_server_settings(author.server)
        itemname = itemname.title()
        self.user_check(settings, user)
        if itemname in settings["Shop List"]:
            quantity = 1
            self.user_give_item(settings, user, quantity, itemname)
            msg = "{} was given {} by {}".format(user.mention, itemname, author.mention)
        else:
            msg = "No such item in the shop."
        await self.bot.say(msg)

    @shop.command(name="trash", pass_context=True, no_pm=True)
    async def _trash_shop(self, ctx, *, itemname):
        """Throws away an item in your inventory."""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        self.user_check(settings, user)
        itemname = itemname.title()
        if itemname in settings["Users"][user.id]["Inventory"]:
            await self.bot.say("Are you sure you wish to trash {}?\nPlease think carefully as all "
                               "instances of this item will be gone forever.".format(itemname))
            choice = await self.bot.wait_for_message(timeout=15, author=user)
            if choice is None:
                msg = "No response. Cancelling the destruction of {}.".format(itemname)
            elif choice.content.title() == "Yes":
                self.user_remove_all(settings, user, itemname)
                msg = "Removed all {}s from your inventory".format(itemname)
            elif choice.content.title() == "No":
                msg = "Cancelling the destruction of {}.".format(itemname)
            else:
                msg = ("Improper response. Must choose Yes or No.\n"
                       "Cancelling the destruction of {}.".format(itemname))
            await self.bot.say(msg)
        else:
            await self.bot.say("You do not own this item.")

    @shop.command(name="gift", pass_context=True, no_pm=True)
    async def _gift_shop(self, ctx, user: discord.Member, quantity: int, *, itemname):
        """Send a number of items from your inventory to another user"""
        if quantity < 1:
            return await self.bot.say("Quantity must be higher than 0.")

        author = ctx.message.author
        itemname = itemname.title()
        settings = self.check_server_settings(author.server)
        self.user_check(settings, author)
        self.user_check(settings, user)
        if author == user:
            await self.bot.say("This is awkward. You can't do this action with yourself.")
        else:
            await self.user_gifting(settings, user, author, itemname, quantity)

    @shop.command(name="trade", pass_context=True, no_pm=True)
    async def _trade_shop(self, ctx, user: discord.Member, quantity: int, *, tradeoffer: str):
        """Request a trade with another user"""
        author = ctx.message.author
        tradeoffer = tradeoffer.title()
        settings = self.check_server_settings(author.server)
        self.user_check(settings, author)
        self.user_check(settings, user)
        result = self.trade_checks(settings, author, user, tradeoffer, quantity)
        if result != "OK":
            return await self.bot.say(result)
        await self.trade_handler(settings, user, author, tradeoffer, quantity)

    @shop.command(name="blocktrades", pass_context=True, no_pm=True)
    async def _blocktrades_shop(self, ctx):
        """Toggles blocking trade requests."""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        self.user_check(settings, user)
        if settings["Users"][user.id]["Block Trades"] is False:
            settings["Users"][user.id]["Block Trades"] = True
            msg = "You can no longer receive trade requests."
        else:
            settings["Users"][user.id]["Block Trades"] = False
            msg = "You can now accept trade requests."
        await self.bot.say(msg)
        dataIO.save_json(self.file_path, self.system)

    @shop.command(name="list", pass_context=True)
    async def _list_shop(self, ctx):
        """Shows a list of all the shop items. Roles are blue."""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        shop_name = settings["Config"]["Shop Name"]
        column1 = ["[{}]".format(subdict["Item Name"].title())
                   if "Role" in subdict else subdict["Item Name"].title()
                   for subdict in settings["Shop List"].values()]
        column2 = [subdict["Quantity"] for subdict in settings["Shop List"].values()]
        column3 = [subdict["Item Cost"] for subdict in settings["Shop List"].values()]
        column4_raw = [subdict["Discount"] for subdict in settings["Shop List"].values()]
        column4 = [x + "%" if x != "0" else "None" for x in list(map(str, column4_raw))]
        if not column1:
            await self.bot.say("There are no items for sale in the shop.")
        else:
            data, header = self.table_builder(settings, column1, column2,
                                              column3, column4, shop_name)
            msg = await self.shop_table_split(user, data)
            await self.shop_list_output(settings, msg, header)

    @commands.group(pass_context=True, no_pm=True)
    async def setshop(self, ctx):
        """Shop configuration settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setshop.command(name="ptype", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _ptype_setshop(self, ctx):
        """Change the pending method to automatic."""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        current_method = settings["Config"]["Pending Type"]
        if current_method == "Manual":
            await self.bot.say("Your current pending method is manual. Changing this to automatic "
                               "requires you to set a msg for each item in the shop.\nI am not "
                               "responsible for any lost information as a result of using this "
                               "method.\nIf you would still like to change your pending method, "
                               "type 'I Agree'.")
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                await self.bot.say("No response. Pending type will remain manual.")
            elif response.content.title() == "I Agree":
                settings["Config"]["Pending Type"] = "Automatic"
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("Pending type is now automatic. Please set a buy msg for your "
                                   "items with {}setshop buymsg.".format(ctx.prefix))
            else:
                await self.bot.say("Incorrect response. Pending type will stay manual.")
        elif current_method == "Automatic":
            settings["Config"]["Pending Type"] = "Manual"
            dataIO.save_json(self.file_path, self.system)
            await self.bot.say("Pending type changed to Manual")
        else:
            pass

    @setshop.command(name="buymsg", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _buymsg_setshop(self, ctx, *, item):
        """Set a msg for item redemption. """
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        item = item.title()
        quantity = settings["Shop List"][item]["Quantity"]
        if item not in settings["Shop List"]:
            msg = "That item is not in the shop."
        elif quantity == "∞" or len(settings["Shop List"][item]["Buy Msg"]) < int(quantity):
            await self.bot.whisper("What msg do you want users to receive when purchasing, "
                                   "{}?".format(item))
            response = await self.bot.wait_for_message(timeout=25, author=user)
            if response is None:
                msg = "No response. No msg will be set."
                await self.bot.whisper(msg)
            else:
                msg = "{} set a buy msg".format(user.name)
                settings["Shop List"][item]["Buy Msg"].append(response.content)
                dataIO.save_json(self.file_path, self.system)
                await self.bot.whisper("Setting {}'s, buy msg to:\n"
                                       "{}".format(item, response.content))
        else:
            quantity = settings["Shop List"][item]["Quantity"]
            msg = ("You can't set anymore buymsgs to {}, because there are only "
                   "{} left".format(item, quantity))
        await self.bot.say(msg)

    @setshop.command(name="notify", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _notify_setshop(self, ctx):
        """Turn on shop pending notifications."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if settings["Config"]["Shop Notify"]:
            settings["Config"]["Shop Notify"] = False
            msg = "Shop notifications are now OFF!"
        else:
            settings["Config"]["Shop Notify"] = True
            msg = "Shop notifcations are now ON!"
        await self.bot.say(msg)
        dataIO.save_json(self.file_path, self.system)

    @setshop.command(name="role", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _role_sethop(self, ctx, *, rolename: str):
        """Set the server role that will receive pending notifications"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        server_roles = [x.name for x in server.roles]
        if rolename in server_roles:
            settings["Config"]["Shop Role"] = rolename
            dataIO.save_json(self.file_path, self.system)
            msg = ("Notify role set to {}. Server users assigned this role will be notifed when "
                   "an item is redeemed.".format(rolename))
        else:
            role_output = ", ".join(server_roles).replace("@everyone,", "")
            msg = ("{} is not a role on your server. The current roles on your server are:\n"
                   "```{}```".format(rolename, role_output))
        await self.bot.say(msg)

    @setshop.command(name="discount", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _discount_setshop(self, ctx, discount: int, *, itemname):
        """Discounts an item in the shop by a percentage. 0-99"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        itemname = itemname.title()
        if itemname in settings["Shop List"]:
            if discount == 0:
                settings["Shop List"][itemname]["Discount"] = 0
                dataIO.save_json(self.file_path, self.system)
                msg = "Remove discount from {}".format(itemname)
            elif 0 < discount <= 99:
                settings["Shop List"][itemname]["Discount"] = discount
                dataIO.save_json(self.file_path, self.system)
                msg = "Adding {}% discount to item {}".format(discount, itemname)
            else:
                msg = "Discount must be 0 to 99."
        else:
            msg = "That item is not in the shop listing."
        await self.bot.say(msg)

    @setshop.command(name="output", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _output_setshop(self, ctx, listing: str, output: str):
        """Sets the output to chat/whisper for inventory or shop"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        listing = listing.title()
        output = output.title()
        if listing == "Shop":
            if output == "Chat":
                settings["Config"]["Store Output Method"] = "Chat"
                dataIO.save_json(self.file_path, self.system)
                msg = "Store listings will now display in chat."
            elif output == "Whisper" or output == "Pm" or output == "Dm":
                settings["Config"]["Store Output Method"] = "Whisper"
                dataIO.save_json(self.file_path, self.system)
                msg = "Store listings will now display in whisper."
            else:
                msg = "Output must be Chat or Whisper/DM/PM."
        elif listing == "Inventory":
            if output == "Chat":
                settings["Config"]["Inventory Output Method"] = "Chat"
                dataIO.save_json(self.file_path, self.system)
                msg = "Inventory will now display in chat."
            elif output == "Whisper" or output == "Pm" or output == "Dm":
                settings["Config"]["Inventory Output Method"] = "Whisper"
                dataIO.save_json(self.file_path, self.system)
                msg = "Inventory will now display in whisper."
            else:
                msg = "Output must be Chat or Whisper/DM/PM."
        else:
            msg = "Must be Shop or Inventory."
        await self.bot.say(msg)

    @setshop.command(name="tradecd", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _tcd_setshop(self, ctx, cooldown: int):
        """Sets the cooldown timer for trading, in seconds."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["Config"]["Trade Cooldown"] = cooldown
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("Trading cooldown set to {}".format(self.time_format(cooldown)))

    @setshop.command(name="toggle", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggle_setshop(self, ctx):
        """Opens and closes the shop"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        shop_name = settings["Config"]["Shop Name"]
        if settings["Config"]["Shop Open"]:
            settings["Config"]["Shop Open"] = False
            msg = "The {} shop is now closed.".format(shop_name)
        else:
            settings["Config"]["Shop Open"] = True
            msg = "{} shop is now open for business!".format(shop_name)
        await self.bot.say(msg)
        dataIO.save_json(self.file_path, self.system)

    @setshop.command(name="sorting", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _sort_setshop(self, ctx, choice: str):
        """Changes the sorting method for shop listings. Alphabetical, Lowest, Highest"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        choice = choice.title()
        if choice == "Alphabetical":
            settings["Config"]["Sort Method"] = "Alphabet"
            dataIO.save_json(self.file_path, self.system)
            msg = "Changing sorting method to Alphabetical."
        elif choice == "Lowest":
            settings["Config"]["Sort Method"] = "Lowest"
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting sorting method to Lowest."
        elif choice == "Highest":
            settings["Config"]["Sort Method"] = "Highest"
            dataIO.save_json(self.file_path, self.system)
            msg = "Setting sorting method to Highest."
        else:
            msg = "Please choose Alphabet, Lowest, or Highest."
        await self.bot.say(msg)

    @setshop.command(name="name", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _name_setshop(self, ctx, *, name):
        """Renames the shop"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings["Config"]["Shop Name"] = name
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("I have renamed the shop to {}.".format(name))

    @commands.group(pass_context=True, no_pm=True)
    async def pending(self, ctx):
        """Pending list commands"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @pending.command(name="showall", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _showall_pending(self, ctx):
        """Shows entire pending list"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        if settings["Pending"]:
            column1 = [subdict["Name"] for users in settings["Pending"]
                       for subdict in settings["Pending"][users].values()]
            column2 = [subdict["Time Stamp"] for users in settings["Pending"]
                       for subdict in settings["Pending"][users].values()]
            column3 = [subdict["Item"] for users in settings["Pending"]
                       for subdict in settings["Pending"][users].values()]
            column4 = [subdict["Confirmation Number"] for users in settings["Pending"]
                       for subdict in settings["Pending"][users].values()]
            column5 = [subdict["Status"] for users in settings["Pending"]
                       for subdict in settings["Pending"][users].values()]
            data = list(zip(column2, column1, column3, column4, column5))
            if len(data) > 12:
                msg = await self.table_split(user, data)
                await self.bot.say(msg)
            else:
                table = tabulate(data, headers=["Time Stamp", "Name", "Item",
                                                "Confirmation#", "Status"], numalign="left")
                await self.bot.say("```{}\n\n\nYou are viewing page 1 of 1. "
                                   "{} item(s) pending```".format(table, len(data)))
        else:
            await self.bot.say("There are no pending items to show.")

    @pending.command(name="search", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _search_pending(self, ctx, method, number):
        """Search by user and userid or code and confirmation#"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if method.title() == "User":
            mobj = server.get_member(number)
            await self.check_user_pending(settings, mobj)
        elif method.title() == "Code":
            await self.search_code(settings, number)
        else:
            await self.bot.say("Method of search needs to be specified as user or code.")

    @pending.command(name="user", pass_context=True, no_pm=True)
    async def _user_pending(self, ctx):
        """Shows all of your pending items"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        await self.check_user_pending(settings, user)

    @pending.command(name="code", pass_context=True, no_pm=True)
    async def _code_pending(self, ctx, code):
        """Searches for a pending item by your confirmation code"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        headers = ["Time Stamp", "Name", "Item", "Confirmation#", "Status"]
        if user.id in settings["Pending"]:
            if code in settings["Pending"][user.id]:
                col1 = settings["Pending"][user.id][code]["Name"]
                col2 = settings["Pending"][user.id][code]["Time Stamp"]
                col3 = settings["Pending"][user.id][code]["Item"]
                col4 = settings["Pending"][user.id][code]["Confirmation Number"]
                col5 = settings["Pending"][user.id][code]["Status"]
                data = [(col2, col1, col3, col4, col5)]
                table = tabulate(data, headers=headers, numalign="left")
                msg = "```{}```".format(table)
            else:
                msg = "Could not find that code in your pending items."
        else:
            msg = "You have no pending items."
        await self.bot.say(msg)

    @pending.command(name="clearall", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clearall_pending(self, ctx):
        """Clears entire pending list"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        await self.bot.say("This commmand will clear the **entire** pending list. If you "
                           "understand this, type Yes to continue or No to abort.")
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            msg = "No response. Aborting pending purge."
        elif response.content.title() == "No":
            msg = "Aborting pending purge."
        elif response.content.title() == "Yes":
            settings["Pending"] = {}
            dataIO.save_json(self.file_path, self.system)
            msg = "Pending list deleted"
        else:
            msg = "Unrecognized response. Aborting pending purge."
        await self.bot.say(msg)

    @pending.command(name="clear", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clear_pending(self, ctx, method, number):
        """Clear single item or entire user list. user/code and id/confirmation#"""
        user = ctx.message.author
        settings = self.check_server_settings(user.server)
        if method.title() == "User":
            await self.user_clear(settings, user.server, user, number)
        elif method.title() == "Code":
            await self.code_clear(settings, user.server, user, number)
        else:
            await self.bot.say("Method must be either user or code.")

    @pending.command(name="status", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _status_pending(self, ctx, code, status):
        """Changes the status of a pending item."""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        if len(status) <= 10:
            userli = [subdict for subdict in settings["Pending"]
                      if code in settings["Pending"][subdict]]
            userid = userli[0]
            if userid:
                settings["Pending"][userid][code]["Status"] = status
                msg = "The status for {}, has been changed to {}".format(code, status)
            else:
                msg = "The confirmation code you provided cannot be found."
        else:
            msg = "Status must be 10 characters or less."
        await self.bot.say(msg)

    async def inventory_split(self, user, title, headers, data, method):
        groups = [data[i:i + 10] for i in range(0, len(data), 10)]
        pages = len(groups)

        if pages == 1:
            page = 0
            table = tabulate(groups[page], headers=headers)
            msg = ("{}```ini\n{}\n\nYou are viewing page 1 of {}.```"
                   "".format(title, table, pages, len(data)))
            return msg
        if method == "Chat":
            await self.bot.say("There are {} pages of inventory items. "
                               "Which page would you like to display?".format(pages))
        else:
            await self.bot.whisper("There are {} pages of inventory items. "
                                   "Which page would you like to display?".format(pages))
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            page = 0
            table = tabulate(groups[page], headers=headers, numalign="left")
            msg = ("{}```ini\n{}\n\nYou are viewing page {} of {}.```"
                   "").format(title, table, page + 1, pages, len(data))
            return msg
        else:
            try:
                page = int(response.content) - 1
                table = tabulate(groups[page], headers=headers, numalign="left")
                msg = ("{}```ini\n{}\n\nYou are viewing page {} of {}.```"
                       "").format(title, table, page + 1, pages, len(data))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a number. Defaulting to page 1")
                page = 0
                table = tabulate(groups[page], headers=headers, numalign="left")
                msg = ("{}```ini\n{}\n\nYou are viewing page 1 of {}.```"
                       "".format(title, table, pages, len(data)))
                return msg

    async def code_clear(self, settings, server, user, number):
        userid = [subdict for subdict in settings["Pending"]
                  if number in settings["Pending"][subdict]]
        if userid:
            mobj = server.get_member(userid[0])
            await self.bot.say("Do you want to clear this pending item for {}?".format(mobj.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                msg = "Timeout response, cancelling clear command."
            elif response.content.title() == "No":
                msg = "Cancelling clear command."
            elif response.content.title() == "Yes":
                settings["Pending"][mobj.id].pop(number, None)
                msg = "Pending item {}, cleared for user {}".format(number, mobj.name)
            else:
                msg = "Incorrect response, cancelling clear command."
        else:
            msg = "The confirmation code provided could not be found."
        await self.bot.say(msg)

    async def user_clear(self, settings, server, user, number):
        if number in settings["Pending"]:
            mobj = server.get_member(number)
            await self.bot.say("Do you want to clear all pending items for {}".format(mobj.name))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                msg = "Timeout response, cancelling clear command."
            elif response.content.title() == "No":
                msg = "Cancelling clear command."
            elif response.content.title() == "Yes":
                settings["Pending"].pop(number)
                msg = "Pending list cleared for user {}".format(mobj.name)
            else:
                msg = "Incorrect response, cancelling clear command."
        else:
            msg = "Unable to find that userid in the pendingl list."
        await self.bot.say(msg)

    async def search_code(self, settings, code):
        userid = [subdict for subdict in settings["Pending"]
                  if code in settings["Pending"][subdict]]
        if userid:
            userid = userid[0]
            col1 = settings["Pending"][userid][code]["Name"]
            col2 = settings["Pending"][userid][code]["Time Stamp"]
            col3 = settings["Pending"][userid][code]["Item"]
            col4 = settings["Pending"][userid][code]["Confirmation Number"]
            col5 = settings["Pending"][userid][code]["Status"]
            data = [(col1, col2, col3, col4, col5)]
            table = tabulate(data, headers=["Name", "Time Stamp", "Item",
                                            "Confirmation#", "Status"], numalign="left")
            msg = "```{}```".format(table)
        else:
            msg = "Could not find that confirmation number in the pending list."
        await self.bot.say(msg)

    async def check_user_pending(self, settings, user):
        try:
            if user.id in settings["Pending"]:
                column1 = [subdict["Name"] for subdict in settings["Pending"][user.id].values()]
                column2 = [subdict["Time Stamp"] for subdict
                           in settings["Pending"][user.id].values()]
                column3 = [subdict["Item"] for subdict in settings["Pending"][user.id].values()]
                column4 = [subdict["Confirmation Number"] for subdict
                           in settings["Pending"][user.id].values()]
                column5 = [subdict["Status"] for subdict in settings["Pending"][user.id].values()]
                data = list(zip(column2, column1, column3, column4, column5))
                table = tabulate(data, headers=["Time Stamp", "Name", "Item",
                                                "Confirmation#", "Status"], numalign="left")
                msg = "```{}```".format(table)
            else:
                msg = "There are no pending items for this user."
        except AttributeError:
            msg = "You did not provide a valid user id."
        await self.bot.say(msg)

    async def shop_table_split(self, user, data):
        headers = ["Item Name", "Item Quantity", "Item Cost", "Discount"]
        groups = [data[i:i + 12] for i in range(0, len(data), 12)]
        pages = len(groups)
        if pages == 1:
            page = 0
            table = tabulate(groups[page], headers=headers, stralign="center", numalign="center")
            msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                   "There are {} items available.```".format(table, pages, len(data)))
            return msg
        else:
            await self.bot.say("There are {} pages of shop items. "
                               "Which page would you like to display?".format(pages))
            response = await self.bot.wait_for_message(timeout=15, author=user)
            if response is None:
                page = 0
            elif response.content.isdigit():
                page = int(response.content) - 1
            else:
                page = 0
            try:
                table = tabulate(groups[page], headers=headers, stralign="center",
                                 numalign="center")
                msg = ("```ini\n{}``````Python\nYou are viewing page {} of {}. "
                       "There are {} items available.```".format(table, page + 1, pages, len(data)))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a correct number. "
                                   "Defaulting to page 1")
                table = tabulate(groups[page], headers=headers, stralign="center",
                                 numalign="center")
                msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                       "There are {} items available.```".format(table, pages, len(data)))
                return msg

    async def shop_list_output(self, settings, message, header):
        if settings["Config"]["Store Output Method"] == "Whisper":
            await self.bot.whisper("{}\n{}".format(header, message))
        elif settings["Config"]["Store Output Method"] == "Chat":
            await self.bot.say("{}\n{}".format(header, message))
        else:
            await self.bot.whisper("{}\n{}".format(header, message))

    async def table_split(self, user, data):
        headers = ["Time Stamp", "Name", "Item", "Confirmation#", "Status"]
        groups = [data[i:i + 12] for i in range(0, len(data), 12)]
        pages = len(groups)
        await self.bot.say("There are {} pages of pending items. "
                           "Which page would you like to display?".format(pages))
        response = await self.bot.wait_for_message(timeout=15, author=user)
        if response is None:
            page = 0
            table = tabulate(groups[page], headers=headers, numalign="left")
            msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                   "{} pending items```".format(table, pages, len(data)))
            return msg
        else:
            try:
                page = int(response.content) - 1
                table = tabulate(groups[page], headers=headers, numalign="left")
                msg = ("```ini\n{}``````Python\nYou are viewing page {} of {}. "
                       "{} pending items```".format(table, page + 1, pages, len(data)))
                return msg
            except ValueError:
                await self.bot.say("Sorry your response was not a number. Defaulting to page 1")
                page = 0
                table = tabulate(groups[page], headers=headers, numalign="left")
                msg = ("```ini\n{}``````Python\nYou are viewing page 1 of {}. "
                       "{} pending items```".format(table, pages, len(data)))
                return msg

    def trade_checks(self, settings, author, user, itemname, quantity):
        cd = self.check_cooldowns(settings, author.id)
        if author == user:
            msg = "This is awkward. You can't do this action with yourself."
        elif settings["Users"][user.id]["Block Trades"]:
            msg = "This user is currently blocking trade requests."
        elif itemname not in settings["Users"][author.id]["Inventory"]:
            msg = "This item is not in your inventory."
        elif settings["Users"][author.id]["Inventory"][itemname]["Item Quantity"] < quantity:
            msg = "You don't have enough {}".format(itemname)
        elif cd != "OK":
            msg = cd
        else:
            msg = "OK"
        return msg

    def check_cooldowns(self, settings, userid):
        if abs(settings["Users"][userid]["Trade Cooldown"] - int(time.perf_counter())) \
                >= settings["Config"]["Trade Cooldown"]:
            settings["Users"][userid]["Trade Cooldown"] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return "OK"
        elif settings["Users"][userid]["Trade Cooldown"] == 0:
            settings["Users"][userid]["Trade Cooldown"] = int(time.perf_counter())
            dataIO.save_json(self.file_path, self.system)
            return "OK"
        else:
            s = abs(settings["Users"][userid]["Trade Cooldown"] - int(time.perf_counter()))
            seconds = abs(s - settings["Config"]["Trade Cooldown"])
            msg = ("You must wait before trading again. "
                   "You still have: {}".format(self.time_format(seconds)))
            return msg

    async def trade_handler(self, settings, user, author, itemname, quantity):
        cancel_msg = "No response. Cancelling trade."
        item_check = lambda m: m.content.title() in settings["Users"][user.id]["Inventory"]
        amount_check = lambda m: m.content.isdigit()

        await self.bot.say("{} requests a trade with {}. Do you wish to trade for {} "
                           "{}?".format(author.mention, user.mention, quantity, itemname))
        answer = await self.bot.wait_for_message(timeout=15, author=user)

        if answer is None:
            await self.bot.say(cancel_msg)
        elif answer.content.title() != "Yes":
            await self.bot.say("{} has rejected your trade.".format(user.name))
        else:

            await self.bot.say("Please say which item you would like to trade.")
            response = await self.bot.wait_for_message(timeout=20, author=user, check=item_check)

            if response is None:
                await self.bot.say(cancel_msg)
            else:

                await self.bot.say(
                    "How many {} do you wish to offer?".format(response.content.title()))
                amount = await self.bot.wait_for_message(timeout=20, author=user,
                                                         check=amount_check)

                inventory = settings["Users"][user.id]["Inventory"]

                if amount is None:
                    await self.bot.say(cancel_msg)
                elif inventory[response.content.title()]["Item Quantity"] < int(amount.content):
                    await self.bot.say(
                        "You don't have that many {}".format(response.content.title()))
                else:

                    await self.bot.say("{} has offered {}, do you wish to accept this trade, "
                                       "{}?".format(user.mention, response.content, author.mention))
                    reply = await self.bot.wait_for_message(timeout=15, author=author)

                    if reply is None:
                        await self.bot.say(cancel_msg)
                    elif reply.content.title() not in ["Yes", "Accept"]:
                        await self.bot.say("{} rejected the trade.".format(author.name))
                    else:

                        self.user_gt_item(settings, author, user, quantity, itemname)
                        self.user_gt_item(settings, user, author, quantity,
                                          response.content.title())
                        self.user_remove_item(settings, author, itemname, quantity)
                        self.user_remove_item(settings, user, response.content.title(),
                                              int(amount.content))

                        msg = await self.bot.say("Trading items.")
                        await asyncio.sleep(1)
                        await self.bot.edit_message(msg, "Trading items.")
                        await asyncio.sleep(1)
                        await self.bot.edit_message(msg, "Trading items..")
                        await asyncio.sleep(1)
                        await self.bot.edit_message(msg, "Trading items...")
                        await asyncio.sleep(1)
                        await self.bot.edit_message(msg, "Trade Complete!")
                        await asyncio.sleep(2)
                        new_msg = ("{} received {} {}, and {} received {} {}."
                                   "".format(author.mention, amount.content,
                                             response.content.title(),
                                             user.mention, quantity, itemname))
                        await self.bot.edit_message(msg, new_msg)

    async def notify_handler(self, settings, ctx, itemname, user, confirmation):
        role = settings["Config"]["Shop Role"]
        if "Role" not in settings["Users"][user.id]["Inventory"][itemname]:
            if settings["Config"]["Shop Notify"] and role is not None:
                msg = ("{} was added to the pending list by {}.\nConfirmation#: {}.\nUser ID: "
                       "{}".format(itemname, user.name, confirmation, user.id))
                names = self.role_check(role, ctx)
                destinations = [m for m in ctx.message.server.members if m.name in names]
                for destination in destinations:
                    await self.bot.send_message(destination, msg)
            await self.bot.say("```{} has been added to pending list. Your confirmation number is "
                               "{}.\nTo check the status of your pending items, use the command "
                               "{}pending check```".format(itemname, confirmation, ctx.prefix))
        else:
            await self.bot.say("{} just received the {} role!".format(user.name, itemname))
        quantity = 1
        self.user_remove_item(settings, user, itemname, quantity)

    async def user_gifting(self, settings, user, author, itemname, quantity):
        if itemname not in settings["Users"][author.id]["Inventory"]:
            await self.bot.say("This item is not in your inventory.")
        elif settings["Users"][author.id]["Inventory"][itemname]["Item Quantity"] < quantity:
            await self.bot.say("You have less than {} {}.".format(quantity, itemname))
        else:
            self.user_gt_item(settings, author, user, quantity, itemname)
            self.user_remove_item(settings, author, itemname, quantity)
            await self.bot.say("{} just sent a gift({} {}) "
                               "to {}.".format(author.mention, itemname, quantity, user.mention))

    async def shop_check(self, user, settings, quantity, itemname):
        if itemname in settings["Shop List"]:
            item_quantity = settings["Shop List"][itemname]["Quantity"]
            if item_quantity == "∞" or item_quantity >= quantity:
                cost = self.discount_calc(settings, itemname, quantity)
                if await self.subtract_credits(user, cost):
                    return True
                else:
                    return False
            else:
                await self.bot.say("There are not enough left in the shop to "
                                   "buy {}.".format(quantity))
        else:
            await self.bot.say("This item is not in the shop.")
            return False

    async def subtract_credits(self, user, number):
        bank = self.bot.get_cog("Economy").bank
        if bank.account_exists(user):
            if bank.can_spend(user, number):
                bank.withdraw_credits(user, number)
                return True
            else:
                await self.bot.say("You do not have enough credits in your account.")
                return False
        else:
            await self.bot.say("You do not have a bank account.")
            return False

    def role_check(self, role, ctx):
        return [m.name for m in ctx.message.server.members if role.lower() in [str(r).lower()
                for r in m.roles] and str(m.status) != "offline"]

    def bordered(self, text):
        lines = text.splitlines()
        width = max(len(s) + 9 for s in lines)
        res = ["+" + "-" * width + '+']
        for s in lines:
            res.append("│" + (s + " " * width)[:width] + "│")
        res.append("+" + "-" * width + "+")
        return "\n".join(res)

    def time_format(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            msg = "{} hours, {} minutes, {} seconds".format(h, m, s)
        elif h == 0 and m > 0:
            msg = "{} minutes, {} seconds".format(m, s)
        elif m == 0 and h == 0 and s > 0:
            msg = "{} seconds".format(s)
        elif m == 0 and h == 0 and s == 0:
            msg = "No cooldown"
        return msg

    async def redeem_handler(self, settings, ctx, user, itemname, confirmation):
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item_dict = {"Name": user.name, "Confirmation Number": confirmation, "Status": "Pending",
                     "Time Stamp": time_now, "Item": itemname}
        if "Role" in settings["Users"][user.id]["Inventory"][itemname]:
            if "Buyrole" in self.bot.cogs:
                roleid = settings["Users"][user.id]["Inventory"][itemname]["Role"]
                role = [role for role in ctx.message.server.roles if roleid == role.id][0]
                await self.bot.add_roles(user, role)
                return True
            else:
                raise RuntimeError('I need the buyrole cog to process this request.')
        elif user.id in settings["Pending"]:
                if len(settings["Pending"][user.id].keys()) <= 12:
                    settings["Pending"][user.id][confirmation] = item_dict
                    dataIO.save_json(self.file_path, self.system)
                    return True
                else:
                    return False
        else:
            settings["Pending"][user.id] = {}
            settings["Pending"][user.id][confirmation] = item_dict
            dataIO.save_json(self.file_path, self.system)
            return True

    def user_check(self, settings, user):
        if user.id in settings["Users"]:
            pass
        else:
            settings["Users"][user.id] = {"Inventory": {}, "Block Trades": False,
                                          "Trade Cooldown": 0, "Member": False}
            dataIO.save_json(self.file_path, self.system)

    def discount_calc(self, settings, itemname, quantity):
        base_cost = settings["Shop List"][itemname]["Item Cost"]
        discount = settings["Shop List"][itemname]["Discount"]
        if discount > 0:
            discount_amount = base_cost * discount / 100
            true_cost = round(base_cost - discount_amount)
            cost = true_cost * quantity
            return cost
        else:
            cost = base_cost * quantity
            return cost

    def table_builder(self, settings, column1, column2, column3, column4, shop_name):
        header = "```"
        header += self.bordered(shop_name + " Store Listings")
        header += "```"
        m = list(zip(column1, column2, column3, column4))
        if settings["Config"]["Sort Method"] == "Alphabet":
            m = sorted(m)
            return m, header
        elif settings["Config"]["Sort Method"] == "Highest":
            m = sorted(m, key=itemgetter(2), reverse=True)
            return m, header
        elif settings["Config"]["Sort Method"] == "Lowest":
            m = sorted(m, key=itemgetter(2))
            return m, header

    def shop_item_add(self, settings, itemname, cost, quantity, role=False):
        if role is False:
            item = itemname.title()
            settings["Shop List"][item] = {"Item Name": itemname, "Item Cost": cost,
                                           "Discount": 0, "Members Only": "No",
                                           "Buy Msg": []}
        else:
            item = str(itemname.name).title()
            settings["Shop List"][item] = {"Item Name": item, "Item Cost": cost,
                                           "Discount": 0, "Members Only": "No",
                                           "Role": itemname.id, "Buy Msg": []}
        if quantity == 0:
            settings["Shop List"][item]["Quantity"] = "∞"
        else:
            settings["Shop List"][item]["Quantity"] = quantity
        dataIO.save_json(self.file_path, self.system)

    def shop_item_remove(self, settings, quantity, itemname):
        if settings["Shop List"][itemname]["Quantity"] == "∞":
            pass
        elif settings["Shop List"][itemname]["Quantity"] > 1:
            settings["Shop List"][itemname]["Quantity"] -= quantity
            if settings["Shop List"][itemname]["Quantity"] < 1:
                settings["Shop List"].pop(itemname, None)
            dataIO.save_json(self.file_path, self.system)
        else:
            settings["Shop List"].pop(itemname, None)
            dataIO.save_json(self.file_path, self.system)

    def user_give_item(self, settings, user, quantity, itemname):
        if itemname in settings["Users"][user.id]["Inventory"]:
            settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] += quantity
        else:
            settings["Users"][user.id]["Inventory"][itemname] = {"Item Name": itemname,
                                                                 "Item Quantity": quantity}
        dataIO.save_json(self.file_path, self.system)

    def user_gt_item(self, settings, author, user, quantity, itemname):
        if itemname in settings["Users"][user.id]["Inventory"]:
            settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] += quantity
        else:
            item_copy = settings["Users"][author.id]["Inventory"][itemname].copy()
            item_copy["Item Quantity"] = 1
            settings["Users"][user.id]["Inventory"][itemname] = item_copy
        dataIO.save_json(self.file_path, self.system)

    def user_add_item(self, settings, user, quantity, itemname):
        user_path = settings["Users"][user.id]["Inventory"]
        if itemname in settings["Users"][user.id]["Inventory"]:
            user_path[itemname]["Item Quantity"] += quantity
        else:
            user_path[itemname] = {"Item Name": itemname, "Item Quantity": quantity}
        if "Role" in settings["Shop List"][itemname]:
            user_path[itemname]["Role"] = settings["Shop List"][itemname]["Role"]
        dataIO.save_json(self.file_path, self.system)

    def user_remove_all(self, settings, user, itemname):
        settings["Users"][user.id]["Inventory"].pop(itemname, None)
        dataIO.save_json(self.file_path, self.system)

    def user_remove_item(self, settings, user, itemname, quantity):
        if settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] > 1:
            settings["Users"][user.id]["Inventory"][itemname]["Item Quantity"] -= quantity
        else:
            settings["Users"][user.id]["Inventory"].pop(itemname, None)
        dataIO.save_json(self.file_path, self.system)

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = {"Shop List": {},
                                                 "Users": {},
                                                 "Pending": {},
                                                 "Config": {"Shop Name": "Jumpman's",
                                                            "Shop Open": True,
                                                            "Shop Notify": False,
                                                            "Shop Role": None,
                                                            "Trade Cooldown": 30,
                                                            "Store Output Method": "Chat",
                                                            "Inventory Output Method": "Chat",
                                                            "Sort Method": "Alphabet",
                                                            "Member Discount": None,
                                                            "Pending Type": "Manual"}
                                                 }
            dataIO.save_json(self.file_path, self.system)
            print("Creating default Shop settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            if "Shop Role" not in path["Config"]:
                path["Config"]["Shop Role"] = None
            return path


def check_folders():
    if not os.path.exists("data/JumperCogs"):   # Checks for parent directory for all Jumper cogs
        print("Creating JumperCogs default directory")
        os.makedirs("data/JumperCogs")

    if not os.path.exists("data/JumperCogs/shop"):
        print("Creating JumperCogs shop folder")
        os.makedirs("data/JumperCogs/shop")


def check_files():
    default = {"Servers": {},
               "Version": "2.2.9"
               }

    f = "data/JumperCogs/shop/system.json"
    if not dataIO.is_valid_json(f):
        print("Creating default shop system.json...")
        dataIO.save_json(f, default)
    else:
        current = dataIO.load_json(f)
        if current["Version"] != default["Version"]:
            print("Updating Shop Cog from version {} to version {}".format(current["Version"],
                                                                           default["Version"]))
            current["Version"] = default["Version"]
            dataIO.save_json(f, current)


def setup(bot):
    check_folders()
    check_files()
    if tabulateAvailable:
        bot.add_cog(Shop(bot))
    else:
        raise RuntimeError("You need to run 'pip3 install tabulate'")
