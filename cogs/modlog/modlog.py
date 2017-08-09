from collections import defaultdict
from datetime import datetime
from typing import List
import importlib
import asyncio

import discord
from discord.ext import commands

from cogs.mod.common import is_admin_or_superior
from core import Config, checks, modlog
from core.bot import Red
from .errors import UnauthorizedCaseEdit, CaseMessageNotFound, NoModLogChannel, \
    NoModLogAccess, CaseTypeNotEnabled, InvalidCaseType


class ModLog:
    """Log for mod actions"""
    default_server_settings = {
        "mod_log": None,
        "cases": {},
        "casetypes": {}
    }

    default_global_settings = {
        "casetypes": {}
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, 1354799444)
        self.settings.register_guild(**self.default_server_settings)
        self.settings.register_global(**self.default_global_settings)
        self.last_case = defaultdict(dict)

    # region modlog_commands
    @commands.group()
    @checks.guildowner_or_permissions(administrator=True)
    async def modlogset(self, ctx: commands.Context):
        """Settings for the mod log"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @modlogset.command()
    @commands.guild_only()
    async def modlog(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Sets a channel as mod log

        Leaving the channel parameter empty will deactivate it"""
        guild = ctx.guild
        if channel:
            if channel.permissions_for(guild.me).send_messages:
                await self.settings.guild(guild).set("mod_log", channel.id)
                await ctx.send("Mod events will be sent to {}"
                               "".format(channel.mention))
            else:
                await ctx.send(
                    "I do not have permissions to "
                    "send messages in {}!".format(channel.mention)
                )
        else:
            if self.settings.guild(guild).mod_log() is None:
                await self.bot.send_cmd_help(ctx)
                return
            await self.settings.guild(guild).set("mod_log", None)
            await ctx.send("Mod log deactivated.")

    @modlogset.command(name='cases')
    @commands.guild_only()
    async def set_cases(self, ctx: commands.Context, action: str = None, enabled: bool = None):
        """Enables or disables case creation for each type of mod action

        Enabled can be 'on' or 'off'"""
        guild = ctx.guild
        casetypes = self.settings.get("casetypes")
        if action == enabled:  # No args given
            await self.bot.send_cmd_help(ctx)
            msg = "Current settings:\n```\n"
            for key in list(casetypes.keys()):
                action = key[:key.find("Case")]
                enabled = self.settings.guild(guild).get(key)
                value = 'enabled' if enabled else 'disabled'
                msg += '%s : %s\n' % (action, value)

            msg += '```'
            await ctx.send(msg)

        elif action.upper() not in casetypes:
            msg = "That's not a valid action. Valid actions are: \n"
            msg += ', '.join(sorted(list(casetypes.keys())))
            await ctx.send(msg)

        elif not isinstance(enabled, bool):  # enabled not specified
            action = casetypes[action.upper()]["repr"][0]
            value = casetypes[action.upper()]["enabled"]
            await ctx.send('Case creation for %s is currently %s' %
                           (action, 'enabled' if value else 'disabled'))
        else:
            name = casetypes[action.upper()]["repr"][0]
            
            value = casetypes[action.upper()]["enabled"]
            if value != enabled:
                casetypes[action.upper()]["enabled"] = enabled
                await self.settings.guild().set("casetypes", casetypes)
            msg = ('Case creation for %s actions %s %s.' %
                   (name.lower(),
                    'was already' if enabled == value else 'is now',
                    'enabled' if enabled else 'disabled')
                   )
            await ctx.send(msg)

    @modlogset.command()
    @commands.guild_only()
    async def resetcases(self, ctx: commands.Context):
        """Resets modlog's cases"""
        guild = ctx.guild
        await self.settings.guild(guild).set("casetypes", self.default_server_settings["casetypes"])
        await ctx.send("Cases have been reset.")

    @commands.group()
    @commands.guild_only()
    async def case(self, ctx: commands.Context):
        """Commands for finding cases"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @case.command()
    async def number(self, ctx: commands.Context, case: int=None):
        """Shows the specified case"""
        cases = self.settings.guild(ctx.guild).get("cases")
        mod_channel = ctx.guild.get_channel(self.settings.guild(ctx.guild).get("mod_log"))
        if mod_channel is None:
            await ctx.send("No mod channel for this server")
            return
        if case is None:
            case = len(list(cases.keys()))
        if str(case) not in cases:
            await ctx.send("That case doesn't exist!")
            return
        case_data = cases[str(case)]
        case_message = case_data["message"]

        msg = await mod_channel.get_message(case_message)
        await ctx.send(msg.content)

    @case.command()
    async def target(self, ctx: commands.Context, target: int):
        """Shows cases where the specified user is the target
        Requires a user ID to work"""
        guild = ctx.guild
        mod_channel = guild.get_channel(self.settings.guild(guild).get("mod_log"))
        if mod_channel is None:
            await ctx.send("No mod channel for this server")
            return
        cases = self.settings.guild(guild).get("cases")
        case_messages = []
        for case_id in list(cases.keys()):
            if cases[case_id]["user"] == target and\
                    cases[case_id]["message"] is not None:
                case_messages.append(
                    mod_channel.get_message(cases[case_id]["message"])
                )
        if len(case_messages) == 0:
            await ctx.send("No cases found with that user as a target!")
            return
        for case in case_messages:
            await ctx.send(case.content)
            await asyncio.sleep(1)

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def reason(self, ctx: commands.Context, case: int=None, *, reason: str = ""):
        """Lets you specify a reason for mod-log's cases

        Defaults to last case assigned to yourself, if available."""
        author = ctx.author
        server = ctx.guild
        try:
            case = int(case)
            if not reason:
                await self.bot.send_cmd_help(ctx)
                return
        except ValueError:
            if reason:
                reason = "{} {}".format(case, reason)
            else:
                reason = case
            case = self.last_case[server.id].get(author.id)
            if case is None:
                await self.bot.send_cmd_help(ctx)
                return
        try:
            await self.update_case(server, case_id=case, mod=author,
                                   reason=reason)
        except UnauthorizedCaseEdit:
            await ctx.send("That case is not yours.")
        except KeyError:
            await ctx.send("That case doesn't exist.")
        except NoModLogChannel:
            await ctx.send("There's no mod-log channel set.")
        except CaseMessageNotFound:
            await ctx.send("I couldn't find the case's message.")
        except NoModLogAccess:
            await ctx.send("I'm not allowed to access the mod-log "
                           "channel (or its message history)")
        else:
            await ctx.send("Case #{} updated.".format(case))

    # endregion modlog_commands

    async def new_case(self, server: discord.Guild, action, *,
                       mod: discord.Member=None, user: discord.abc.User,
                       reason: str=None, until: datetime=None, channel: discord.TextChannel=None) -> bool:
        """Creates a new case in the mod log
        :param discord.Guild server: the server this case is to be associated with
        :param str action: The action taken for this case
        :param discord.Member mod: The moderator that took this action
        :param discord.abc.User user: The user the action was taken against
        :param str reason: The reason this action was taken
        :param datetime until: When this action expires
        :param discord.TextChannel channel: The channel this action applies to

        :return: True if creating the case was successful, otherwise False
        :rtype bool:

        :raises cogs.modlog.errors.InvalidCaseType: if the case type is invalid
        :raises cogs.modlog.errors.CaseTypeNotEnabled: if the case type is not enabled for this server
        :raises cogs.modlog.errors.NoModLogChannel: if no mod log channel has been set for this server
        :raises discord.Forbidden: if the bot does not have permissions to post the mod log message
        """
        # Check if case type has been registered; if it hasn't, raise an exception
        action_name = action.__name__
        if action_name not in self.settings.get("casetypes"):
            raise InvalidCaseType
        # Check if case type is enabled for the server; if not, raise exception
        if not self.settings.guild(server).get(action_name):
            raise CaseTypeNotEnabled

        mod_channel = server.get_channel(self.settings.guild(server).get("mod_log", None))

        if mod_channel is None:
            raise NoModLogChannel

        cases = self.settings.guild(server).get("cases", {})

        case_n = len(list(cases.keys())) + 1

        case = action(
            server=server, case=case_n, created_at=datetime.utcnow().timestamp(),
            modified_at=None, channel=channel, reason=reason, until=until, user=user,
            moderator=mod, amended_by=None
        )

        try:
            msg = await mod_channel.send(case)
            case_json = case.to_json(msg)
        except discord.Forbidden:
            raise

        cases[str(case_n)] = case_json[str(case_n)]

        if mod:
            self.last_case[server.id][mod.id] = case_n

        await self.settings.guild(server).set("cases", cases)
        return True

    async def update_case(self, server: discord.Guild, *, case_id: int,
                          mod: discord.Member=None, reason: str=None,
                          until: bool=False):
        channel = server.get_channel(self.settings.guild(server).mod_log())
        if channel is None:
            raise NoModLogChannel()
        case_id = str(case_id)
        cases = self.settings.guild(server).cases()
        case_data = cases[case_id]
        case_type = case_data["action"]
        registered_types = self.settings.get("casetypes")

        casetypes = importlib.import_module(registered_types[case_type])
        actual_type = getattr(casetypes, case_type)
        case = await actual_type.from_json(server=server, mod_channel=channel, data=case_data, bot=self.bot)

        if mod:
            if case.moderator is not None:
                if case.moderator.id != mod.id:
                    if is_admin_or_superior(self.bot, mod):
                        case.amended_by = mod
                    else:
                        raise UnauthorizedCaseEdit()
            else:
                case.moderator = mod

        if case.reason:  # Existing reason
            case.modified_at = datetime.utcnow().timestamp()
        case.reason = reason

        if until is not False:
            case.until = until

        if case.message is None:  # The case's message was never sent
            raise CaseMessageNotFound()

        cases[case_id] = case.to_json(case.message)[case_id]
        await self.settings.guild(server).set("cases", cases)
        await case.message.edit(content=str(case))

    async def register_new_casetype(self, action, default_setting: bool) -> bool:
        """Registers a new casetype for modlog cases
        :param action: the action's class
        :param default_setting: a bool representing whether the case type being registered
          should default to being on or off. If False, new cases will not be created by default
        It is recommended to trigger this in __init__ for the cog that needs a new casetype and
        to only register if it hasn't been registered previously.
        :return: True on success
        :raises: InvalidCaseType
        """
        action_module = action.__module__
        global_casetypes = self.settings.get("casetypes", {})
        if action not in global_casetypes:
            global_casetypes[action.__name__] = action_module
            await self.settings.set("casetypes", global_casetypes)
        else:
            raise InvalidCaseType
        for server in self.bot.guilds:
            casetypes = self.settings.guild(server).get("casetypes")
            if action not in casetypes:
                await self.settings.guild(server).set(action.__name__, default_setting)
        return True

    async def register_casetypes(self, types: List[tuple]) -> bool:
        """Helper function to register multiple case types at once by passing
        in a list containing tuples of the parameters for register_new_casetype
        :param types: a list containing tuples of the casetype's class and bool
          - the casetype's class
          - bool: whether the case type should be on (True) or off (False) by default
        :returns: bool"""
        for new_type in types:
            action = new_type[0]
            default_setting = new_type[1]
            try:
                await self.register_new_casetype(action, default_setting)
            except InvalidCaseType:
                break
        else:
            return True
        return False
