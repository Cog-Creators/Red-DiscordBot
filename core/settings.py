from core.utils.helpers import JsonGuildDB
import discord
import argparse


class CoreDB(JsonGuildDB):
    """
    The central DB used by Red to store a variety
    of settings, both global and guild specific
    """

    def can_login(self):
        """Used on start to determine if Red is setup enough to login"""
        raise NotImplementedError

    def get_admin_role(self, guild):
        """Returns the guild's admin role

        Returns None if not set or if the role
        couldn't be retrieved"""
        _id = self.get_all(guild, {}).get("admin_role", None)
        return discord.utils.get(guild.roles, id=_id)

    def get_mod_role(self, guild):
        """Returns the guild's mod role

        Returns None if not set or if the role
        couldn't be retrieved"""
        _id = self.get_all(guild, {}).get("mod_role", None)
        return discord.utils.get(guild.roles, id=_id)

    async def set_admin_role(self, role):
        """Sets the admin role for the guild"""
        if not isinstance(role, discord.Role):
            raise TypeError("A valid Discord role must be passed.")
        await self.set(role.guild, "admin_role", role.id)

    async def set_mod_role(self, role):
        """Sets the mod role for the guild"""
        if not isinstance(role, discord.Role):
            raise TypeError("A valid Discord role must be passed.")
        await self.set(role.guild, "mod_role", role.id)

    def get_global_whitelist(self):
        """Returns the global whitelist"""
        return self.get_global("whitelist", [])

    def get_global_blacklist(self):
        """Returns the global whitelist"""
        return self.get_global("blacklist", [])

    async def set_global_whitelist(self, whitelist):
        """Sets the global whitelist"""
        if not isinstance(list, whitelist):
            raise TypeError("A list of IDs must be passed.")
        await self.set_global("whitelist", whitelist)

    async def set_global_blacklist(self, blacklist):
        """Sets the global blacklist"""
        if not isinstance(list, blacklist):
            raise TypeError("A list of IDs must be passed.")
        await self.set_global("blacklist", blacklist)

    def get_guild_whitelist(self, guild):
        """Returns the guild's whitelist"""
        return self.get(guild, "whitelist", [])

    def get_guild_blacklist(self, guild):
        """Returns the guild's blacklist"""
        return self.get(guild, "blacklist", [])

    async def set_guild_whitelist(self, guild, whitelist):
        """Sets the guild's whitelist"""
        if not isinstance(guild, discord.Guild) or not isinstance(whitelist, list):
            raise TypeError("A valid Discord guild and a list of IDs "
                            "must be passed.")
        await self.set(guild, "whitelist", whitelist)

    async def set_guild_blacklist(self, guild, blacklist):
        """Sets the guild's blacklist"""
        if not isinstance(guild, discord.Guild) or not isinstance(blacklist, list):
            raise TypeError("A valid Discord guild and a list of IDs "
                            "must be passed.")
        await self.set(guild, "blacklist", blacklist)


def parse_cli_flags():
    parser = argparse.ArgumentParser(description="Red - Discord Bot")
    parser.add_argument("--owner", help="ID of the owner. Only who hosts "
                                        "Red should be owner, this has "
                                        "security implications")
    parser.add_argument("--prefix", "-p", action="append",
                        help="Global prefix. Can be multiple")
    parser.add_argument("--no-prompt",
                        action="store_true",
                        help="Disables console inputs. Features requiring "
                             "console interaction could be disabled as a "
                             "result")
    parser.add_argument("--no-cogs",
                        action="store_true",
                        help="Starts Red with no cogs loaded, only core")
    parser.add_argument("--self-bot",
                        action='store_true',
                        help="Specifies if Red should log in as selfbot")
    parser.add_argument("--not-bot",
                        action='store_true',
                        help="Specifies if the token used belongs to a bot "
                             "account.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Makes Red quit with code 0 just before the "
                             "login. This is useful for testing the boot "
                             "process.")
    parser.add_argument("--debug",
                        action="store_true",
                        help="Sets the loggers level as debug")
    parser.add_argument("--dev",
                        action="store_true",
                        help="Enables developer mode")

    args = parser.parse_args()

    if args.prefix:
        args.prefix = sorted(args.prefix, reverse=True)
    else:
        args.prefix = []

    return args
