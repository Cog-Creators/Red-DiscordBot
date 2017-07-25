from datetime import datetime
from typing import List

import discord
from discord.ext import commands

from cogs.bank.errors import AccountAlreadyExists, NoAccount, InsufficientBalance, \
    NegativeValue, SameSenderAndReceiver, BankIsGlobal, BankNotGlobal
from core import Config, checks
from core.bot import Red  # Only used for type hints


def check_global_setting():
    async def pred(ctx: commands.Context):
        bank = ctx.command.instance
        if not bank:
            return False
        elif bank.accounts.is_global():
            return checks.is_owner()
        elif not bank.accounts.is_global():
            return checks.guildowner_or_permissions(administrator=True)
    return commands.check(pred)


class Bank:
    """Bank"""

    default_global_settings = {
        "is_global": False,
        "BANK_NAME": "Twentysix bank",
        "CREDITS_NAME": "credits"
    }

    default_guild_settings = {
        "BANK_NAME": "Twentysix bank",
        "CREDITS_NAME": "credits"
    }

    default_member_settings = {
        "name": "",
        "balance": 0,
        "created_at": ""
    }

    default_user_settings = {
        "name": "",
        "balance": 0,
        "created_at": ""
    }

    def __init__(self, bot: Red):
        self.accounts = Config.get_conf(self, 1824486521, force_registration=True)
        self.accounts.register_member(**self.default_member_settings)
        self.accounts.register_guild(**self.default_guild_settings)
        self.accounts.register_global(**self.default_global_settings)
        self.accounts.register_user(**self.default_user_settings)
        self.bot = bot

    # SECTION commands

    @commands.group()
    @checks.guildowner_or_permissions(administrator=True)
    async def bankset(self, ctx: commands.Context):
        """Base command for bank settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @bankset.command(name="toggleglobal")
    @checks.is_owner()
    async def bankset_toggleglobal(self, ctx: commands.Context):
        """Toggles whether the bank is global or not
        If the bank is global, it will become per-guild
        If the bank is per-guild, it will become global"""
        cur_setting = self.accounts.is_global()
        if cur_setting:
            await self.accounts.set("is_global", False)
            await ctx.send("The bank is now per-guild")
        else:
            await self.accounts.set("is_global", True)
            await ctx.send("The bank is now global")

    @bankset.command(name="bankname")
    @check_global_setting()
    async def bankset_bankname(self, ctx: commands.Context, *, name: str):
        """Set the bank's name"""
        if self.accounts.is_global():
            await self.accounts.set("BANK_NAME", name)
        else:
            guild = ctx.guild
            await self.accounts.guild(guild).set("BANK_NAME", name)
        await ctx.send("Bank's name has been set to {}".format(name))

    @bankset.command(name="creditsname")
    @check_global_setting()
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency"""
        if self.accounts.is_global():
            await self.accounts.set("CREDITS_NAME", name)
        else:
            guild = ctx.guild
            await self.accounts.guild(guild).set("CREDITS_NAME", name)
        await ctx.send("Currency name has been set to {}".format(name))

    # ENDSECTION

    async def create_account(
            self, user: discord.Member, *, initial_balance: int=0) -> dict:
        balance = initial_balance
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        account = {
            "name": user.name,
            "balance": balance,
            "created_at": timestamp
        }
        if self.accounts.is_global():
            for key in list(account.keys()):
                await self.accounts.user(user).set(key, account[key])
            return account
        else:
            for key in list(account.keys()):
                await self.accounts.member(user).set(key, account[key])
            return account

    async def withdraw_credits(
            self, user: discord.Member, amount: int) -> bool:
        if amount < 0:
            raise NegativeValue()
        acc = await self.get_account(user)
        cur_balance = acc["balance"]
        if cur_balance >= amount:
            await self.accounts.member(user).set("balance", cur_balance - amount)
            return True
        else:
            raise InsufficientBalance()

    async def deposit_credits(
            self, user: discord.Member, amount: int) -> bool:
        if amount < 0:
            raise NegativeValue()
        account = await self.get_account(user)
        await self.set_credits(user, account["balance"] + amount)
        return True

    async def set_credits(self, user: discord.Member, amount: int) -> bool:
        if amount < 0:
            raise NegativeValue()
        await self.accounts.member(user).set("balance", amount)
        return True

    async def transfer_credits(
            self, sender: discord.Member,
            receiver: discord.Member, amount: int) -> bool:
        if amount < 0:
            raise NegativeValue()
        if sender is receiver:
            raise SameSenderAndReceiver()
        sender_acc = await self.get_account(sender)
        if sender_acc["balance"] < amount:
            raise InsufficientBalance()
        await self.withdraw_credits(sender, amount)
        await self.deposit_credits(receiver, amount)
        return True

    async def can_spend(self, user: discord.Member, amount: int) -> bool:
        account = await self.get_account(user)
        return True if account["balance"] >= amount else False

    async def wipe_bank(self, user: discord.Member) -> bool:
        if self.accounts.is_global():
            await self.accounts.user(user).clear_all()
        else:
            await self.accounts.member(user).clear_all()
        return True

    async def get_server_accounts(self, server: discord.Guild) -> List[tuple]:
        if self.accounts.is_global():
            raise BankIsGlobal()
        accounts = []
        for member in server.members:
            account = await self.get_account(member)
            accounts.append((member, account))
        return accounts

    async def get_accounts(self) -> List[tuple]:
        if not self.accounts.is_global():
            raise BankNotGlobal()
        accounts = []
        for user in self.bot.users:
            account = await self.get_account(user)
            accounts.append((user, account))
        return accounts

    async def get_balance(self, user: discord.Member) -> int:
        acc = await self.get_account(user)
        return acc["balance"]

    async def get_account(self, user: discord.Member) -> dict:
        if self.accounts.is_global():
            acc = {
                "balance": self.accounts.user(user).balance(),
                "created_at": self.accounts.user(user).created_at(),
                "name": self.accounts.user(user).name()
            }
            if not acc["balance"] and not acc["created_at"] and not acc["name"]:
                await self.create_account(user)
                acc = {
                    "balance": self.accounts.user(user).balance(),
                    "created_at": self.accounts.user(user).created_at(),
                    "name": self.accounts.user(user).name()
                }
        else:
            acc = {
                "balance": self.accounts.member(user).balance(),
                "created_at": self.accounts.member(user).created_at(),
                "name": self.accounts.member(user).name()
            }
            if not acc["balance"] and not acc["created_at"] and not acc["name"]:
                await self.create_account(user)
                acc = {
                    "balance": self.accounts.member(user).balance(),
                    "created_at": self.accounts.member(user).created_at(),
                    "name": self.accounts.member(user).name()
                }
        return acc
