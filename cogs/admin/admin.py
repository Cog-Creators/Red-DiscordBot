import discord
from discord.ext import commands

from core import Config, checks

import logging

from .announcer import Announcer
from .converters import MemberDefaultAuthor

log = logging.getLogger("red.admin")

GENERIC_FORBIDDEN = (
    "I attempted to do something that Discord denied me permissions for."
    " Your command failed to successfully complete."
)

HIERARCHY_ISSUE = (
    "I tried to add {role.name} to {member.display_name} but that role"
    " is higher than my highest role in the Discord heirarchy so I was"
    " unable to successfully add it. Please give me a higher role and "
    "try again."
)

RUNNING_ANNOUNCEMENT = (
    "I am already announcing something. If you would like to make a"
    " different announcement please use `{prefix}announce cancel`"
    " first."
)


class Admin:
    def __init__(self):
        self.conf = Config.get_conf(self, 8237492837454039)

        self.conf.register_guild(
            announce_channel=None
        )

        self.__current_announcer = None

    def __unload(self):
        try:
            self.__current_announcer.cancel()
        except AttributeError:
            pass

    @staticmethod
    async def complain(ctx: commands.Context, message: str,
                       **kwargs):
        await ctx.send(message.format(**kwargs))

    def is_announcing(self) -> bool:
        """
        Is the bot currently announcing something?
        :return:
        """
        if self.__current_announcer is None:
            return False

        return self.__current_announcer.active or False

    @staticmethod
    def pass_heirarchy_check(ctx: commands.Context,
                             role: discord.Role) -> bool:
        """
        Determines if the bot has a higher role than the given one.
        :param ctx:
        :param role: Role object.
        :return:
        """
        return ctx.guild.me.top_role > role

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def addrole(self, ctx: commands.Context, rolename: discord.Role,
                      user: MemberDefaultAuthor=None):
        """
        Adds a role to a user. If user is left blank it defaults to the
            author of the command.
        """
        # So I'm an idiot.

        try:
            # noinspection PyUnresolvedReferences
            user.add_roles(rolename)
        except discord.Forbidden:
            if not self.pass_heirarchy_check(ctx, rolename):
                await self.complain(ctx, HIERARCHY_ISSUE, role=rolename,
                                    member=user)
            else:
                await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            await ctx.send("I successfully added {role.name} to"
                           " {member.display_name}".format(
                               role=rolename, member=user
                           ))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def removerole(self, ctx: commands.Context, rolename: discord.Role,
                         user: MemberDefaultAuthor=None):
        """
        Removes a role from a user. If user is left blank it defaults to the
            author of the command.
        """
        try:
            user.remove_roles(rolename)
        except discord.Forbidden:
            if not self.pass_heirarchy_check(ctx, rolename):
                await self.complain(ctx, HIERARCHY_ISSUE, role=rolename,
                                    member=user)
            else:
                await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            await ctx.send("I successfully removed {role.name} from"
                           " {member.display_name}".format(
                               role=rolename, member=user
                           ))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx: commands.Context):
        """Edits roles settings"""
        if ctx.invoked_subcommand is None:
            await ctx.bot.send_cmd_help(ctx)

    @editrole.command(name="colour", aliases=["color", ])
    async def editrole_colour(self, ctx: commands.Context, role: discord.Role,
                              value: discord.Colour):
        """Edits a role's colour

        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        \"http://www.w3schools.com/colors/colors_picker.asp\"
        Examples:
        !editrole colour \"The Transistor\" #ff0000
        !editrole colour Test #ff9900"""
        author = ctx.author
        reason = "{}({}) changed the colour of role '{}'".format(
            author.name, author.id, role.name)
        try:
            await role.edit(reason=reason, color=value)
        except discord.Forbidden:
            await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            log.info(reason)
            await ctx.send("Done.")

    @editrole.command(name="name")
    @checks.admin_or_permissions(administrator=True)
    async def edit_role_name(self, ctx: commands.Context, role: discord.Role, *, name: str):
        """Edits a role's name

        Use double quotes if the role or the name contain spaces.
        Examples:
        !editrole name \"The Transistor\" Test"""
        author = ctx.message.author
        old_name = role.name
        reason = "{}({}) changed the name of role '{}' to '{}'".format(
            author.name, author.id, old_name, name)
        try:
            await role.edit(reason=reason, name=name)
        except discord.Forbidden:
            await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            log.info(reason)
            await ctx.send("Done.")

    @commands.group()
    @checks.is_owner()
    async def announce(self, ctx: commands.Context, message: str):
        """
        Announces a message to all servers the bot is in.
        """
        if not self.is_announcing():
            announcer = Announcer(ctx, message, config=self.conf)
            announcer.start()

            self.__current_announcer = announcer

            await ctx.send("The announcement has begun.")
        else:
            prefix = ctx.prefix
            await self.complain(ctx, RUNNING_ANNOUNCEMENT,
                                prefix=prefix)

    @announce.command(name="cancel")
    @checks.is_owner()
    async def announce_cancel(self, ctx):
        """
        Cancels a running announce.
        """
        try:
            self.__current_announcer.cancel()
        except AttributeError:
            pass

        await ctx.send("The current announcement has been cancelled.")
