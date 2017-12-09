import uuid
import os
from discord.ext import commands
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
from .utils import checks


class Coupon:
    """Creates redeemable coupons for credits"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/JumperCogs/coupon/coupons.json"
        self.system = dataIO.load_json(self.file_path)

    @commands.group(pass_context=True)
    async def coupon(self, ctx):
        """Coupon commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @coupon.command(name="create", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _create_coupon(self, ctx, credits: int):
        """Generates a unique coupon code"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        code = str(uuid.uuid4())
        self.coupon_add(settings, code, credits)
        await self.bot.whisper("I have created a coupon for {} credits.\nThe code is: "
                               "{}".format(credits, code))

    @coupon.command(name="clearall", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clearall_coupon(self, ctx):
        """Clears all unclaimed coupons"""
        server = ctx.message.server
        settings = self.check_server_settings(server)
        settings.clear()
        dataIO.save_json(self.file_path, self.system)
        await self.bot.say("All unclaimed coupon codes cleared from the list.")

    @coupon.command(name="redeem", pass_context=True, no_pm=True)
    async def _redeem_coupon(self, ctx, coupon):
        """Redeems a coupon code, can be done through PM with the bot"""
        server = ctx.message.server
        user = ctx.message.author
        settings = self.check_server_settings(server)
        if len(coupon) == 36:
            if coupon in settings:
                credits = settings[coupon]["Credits"]
                bank = self.bot.get_cog('Economy').bank
                bank.deposit_credits(user, credits)
                del settings[coupon]
                dataIO.save_json(self.file_path, self.system)
                await self.bot.say("I have added {} credits to your account".format(credits))
            else:
                await self.bot.say("This coupon either does not exist or has already been "
                                   "redeemed.")
        else:
            await self.bot.say("This is not a valid coupon code.")

    def check_server_settings(self, server):
        if server.id not in self.system["Servers"]:
            self.system["Servers"][server.id] = {}
            dataIO.save_json(self.file_path, self.system)
            print("Creating default coupon settings for Server: {}".format(server.name))
            path = self.system["Servers"][server.id]
            return path
        else:
            path = self.system["Servers"][server.id]
            return path

    def coupon_add(self, settings, coupon, credits):
        settings[coupon] = {"Credits": credits}
        dataIO.save_json(self.file_path, self.system)

    def coupon_redeem(self, settings, coupon):
        if coupon in settings:
            del settings[coupon]
            dataIO.save_json(self.file_path, self.system)
        else:
            return False


def check_folders():
    if not os.path.exists("data/JumperCogs/coupon"):
        print("Creating JumperCogs coupon folder...")
        os.makedirs("data/JumperCogs/coupon")


def check_files():
    default = {"Servers": {}}

    f = "data/JumperCogs/coupon/coupons.json"
    if not dataIO.is_valid_json(f):
        print("Creating default JumperCogs/coupons.json...")
        dataIO.save_json(f, default)


def setup(bot):
    check_folders()
    check_files()
    n = Coupon(bot)
    bot.add_cog(n)
