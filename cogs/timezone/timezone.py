from discord.ext import commands
import discord
from core.utils.helpers import JsonDB
from core import checks
import pytz
from pytz import country_timezones
from datetime import datetime as dt


class TimeZone:
    """Per-user time handling"""

    def __init__(self, bot):
        self.bot = bot
        self.data = JsonDB("data/settings.json")

    @commands.group()
    async def settime(self, ctx):
        """Commands for setting time"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @settime.command(name="server")
    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def settime_server(self, ctx, timezone: str):
        """Sets the server's default timezone. Timezone must either
        be a timezone name from the IANA timezone database
        or a ISO-3166-1 country code (which will be used to
        help you choose your timezone from a list of timezones
        for the country code you provide)"""
        server = ctx.guild
        if len(timezone) == 2:
            # An ISO-3166-1 country code was provided so get timezone from that
            if timezone not in country_timezones.keys():
                await ctx.send("That country code is invalid!")
                return
            zones_for_country = country_timezones[timezone]
            cur_idx = 1
            msg = "Possible options:\n"
            for zone in zones_for_country:
                msg += "{}. {}\n".format(cur_idx, zone)
                cur_idx += 1
            msg += "\nPlease enter your selection (followed by a period):"
            def check(m):
                if m.author == ctx.author:
                    ints = range(1, cur_idx + 1)
                    period_pos = m.content.find(".")
                    for i in ints:
                        if period_pos == -1:
                            if int(m.content) == i:
                                return True
                        else:
                            if int(m.content[: period_pos]) == i:
                                return True
                    return False
            await ctx.send(msg)
            resp = await self.bot.wait_for('message', check=check)
            dot_pos = resp.content.find(".")
            if dot_pos == -1:
                server_zone = zones_for_country[int(resp.content)-1]
            else:
                server_zone = zones_for_country[int(resp.content[:dot_pos] - 1)]
            server_data = self.data.get("servers")
            server_data[str(server.id)] = server_zone
            await self.data.set("servers", server_data)
            await ctx.send("Set the timezone successfully!")
        else:
            server_data = self.data.get("servers")
            try:
                pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                await ctx.send("The specified timezone is invalid!")
                return
            else:
                server_data[str(server.id)] = timezone
                await self.data.set("servers", server_data)
                await ctx.send("Set the timezone successfully!")

    @settime.command(name="user")
    async def settime_user(self, ctx, timezone: str):
        """Sets your default timezone. Timezone must either
        be a timezone name from the IANA timezone database
        or a ISO-3166-1 country code (which will be used to
        help you choose your timezone from a list of timezones
        for the country code you provide)."""
        user = ctx.author
        if len(timezone) == 2:
            # An ISO-3166-1 country code was provided so get timezone from that
            if timezone not in country_timezones.keys():
                await ctx.send("That country code is invalid!")
                return
            zones_for_country = country_timezones[timezone]
            cur_idx = 1
            msg = "Possible options:\n"
            for zone in zones_for_country:
                msg += "{}. {}\n".format(cur_idx, zone)
                cur_idx += 1
            msg += "\nPlease enter your selection (followed by a period):"
            def check(m):
                if m.author == user:
                    ints = range(1, cur_idx + 1)
                    period_pos = m.content.find(".")
                    for i in ints:
                        if period_pos == -1:
                            if int(m.content) == i:
                                return True
                        else:
                            if int(m.content[: period_pos]) == i:
                                return True
                return False
            await ctx.send(msg)
            resp = await self.bot.wait_for('message', check=check)
            dot_pos = resp.content.find(".")
            if dot_pos == -1:
                user_zone = zones_for_country[int(resp.content)-1]
            else:
                user_zone = zones_for_country[int(resp.content[:dot_pos] - 1)]
            user_data = self.data.get("users")
            user_data[str(user.id)] = user_zone
            await self.data.set("users", user_data)
            await ctx.send("Set the timezone successfully!")
        else:
            user_data = self.data.get("users")
            try:
                pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                await ctx.send("The specified timezone is invalid!")
                return
            else:
                user_data[str(user.id)] = timezone
                await self.data.set("users", user_data)
                await ctx.send("Set the timezone successfully!")

    @commands.command()
    async def mytime(self, ctx):
        author = ctx.author
        fmt = "%Y-%m-%d %H:%M:%S %Z%z"
        cur_utc = dt.utcnow()
        converted = await self.get_user_time(author, cur_utc)
        await ctx.send(converted.strftime(fmt))

    @commands.command()
    async def servertime(self, ctx):
        server = ctx.guild
        fmt = "%Y-%m-%d %H:%M:%S %Z%z"
        cur_utc = dt.utcnow()
        converted = await self.get_server_time(server, cur_utc)
        await ctx.send(converted.strftime(fmt))

    async def get_server_time(self, guild: discord.Guild, utctime):
        """Gets the time for the specified server based on the
        provided utc time.
        Args:
          - guild - a Discord guild object
          - utctime - a datetime object

        Returns:
          - the localized time for the server if a timezone has been set
          - otherwise, the utctime arg as provided by the calling method
        """
        if guild.id in self.data.get("servers"):
            localized_utc = pytz.utc.localize(utctime)
            server_tz = pytz.timezone(self.data.get("servers")[str(guild.id)])
            return localized_utc.astimezone(server_tz)
        else:
            return utctime

    async def get_user_time(self, user: discord.Member, utctime):
        """Gets the time for the specified user based on the
        provided utc time.
        Args:
          - user - a Discord member object
          - utctime - a datetime object

        Returns:
          - the localized time for the member if a timezone has been set
          - otherwise, the utctime arg as provided by the calling method
        """
        if user.id in self.data.get("users"):
            localized_utc = pytz.utc.localize(utctime)
            user_tz = pytz.timezone(self.data.get("users")[str(user.id)])
            return localized_utc.astimezone(user_tz)
        else:
            return utctime

    async def setup_data(self):
        """Data setup function. Shouldn't need to be called manually"""
        if not self.data.get("servers"):
            await self.data.set("servers", {})
        if not self.data.get("users"):
            await self.data.set("users", {})
