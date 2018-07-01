from typing import Tuple

import discord

from redbot.core import Config, checks, commands

import logging

from redbot.core.utils.chat_formatting import box
from .announcer import Announcer
from .converters import MemberDefaultAuthor, SelfRole

log = logging.getLogger("red.admin")

GENERIC_FORBIDDEN = (
    "I attempted to do something that Discord denied me permissions for."
    " Your command failed to successfully complete."
)

HIERARCHY_ISSUE = (
    "I tried to add {role.name} to {member.display_name} but that role"
    " is higher than my highest role in the Discord hierarchy so I was"
    " unable to successfully add it. Please give me a higher role and "
    "try again."
)

USER_HIERARCHY_ISSUE = (
    "I tried to add {role.name} to {member.display_name} but that role"
    " is higher than your highest role in the Discord hierarchy so I was"
    " unable to successfully add it. Please get a higher role and "
    "try again."
)

RUNNING_ANNOUNCEMENT = (
    "I am already announcing something. If you would like to make a"
    " different announcement please use `{prefix}announce cancel`"
    " first."
)


class Admin:
    def __init__(self, config=Config):
        self.conf = config.get_conf(self, 8237492837454039, force_registration=True)

        self.conf.register_global(serverlocked=False)

        self.conf.register_guild(
            announce_ignore=False,
            announce_channel=None,  # Integer ID
            selfroles=[],  # List of integer ID's
        )

        self.__current_announcer = None

    def __unload(self):
        try:
            self.__current_announcer.cancel()
        except AttributeError:
            pass

    @staticmethod
    async def complain(ctx: commands.Context, message: str, **kwargs):
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
    def pass_hierarchy_check(ctx: commands.Context, role: discord.Role) -> bool:
        """
        Determines if the bot has a higher role than the given one.
        :param ctx:
        :param role: Role object.
        :return:
        """
        return ctx.guild.me.top_role > role

    @staticmethod
    def pass_user_hierarchy_check(ctx: commands.Context, role: discord.Role) -> bool:
        """
        Determines if a user is allowed to add/remove/edit the given role.
        :param ctx:
        :param role:
        :return:
        """
        return ctx.author.top_role > role

    async def _addrole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            if not self.pass_hierarchy_check(ctx, role):
                await self.complain(ctx, HIERARCHY_ISSUE, role=role, member=member)
            else:
                await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            await ctx.send(
                "I successfully added {role.name} to"
                " {member.display_name}".format(role=role, member=member)
            )

    async def _removerole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            if not self.pass_hierarchy_check(ctx, role):
                await self.complain(ctx, HIERARCHY_ISSUE, role=role, member=member)
            else:
                await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            await ctx.send(
                "I successfully removed {role.name} from"
                " {member.display_name}".format(role=role, member=member)
            )

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def addrole(
        self, ctx: commands.Context, rolename: discord.Role, *, user: MemberDefaultAuthor = None
    ):
        """
        Adds a role to a user.
        If user is left blank it defaults to the author of the command.
        """
        if user is None:
            user = ctx.author
        if self.pass_user_hierarchy_check(ctx, rolename):
            # noinspection PyTypeChecker
            await self._addrole(ctx, user, rolename)
        else:
            await self.complain(ctx, USER_HIERARCHY_ISSUE, member=ctx.author)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def removerole(
        self, ctx: commands.Context, rolename: discord.Role, *, user: MemberDefaultAuthor = None
    ):
        """
        Removes a role from a user.
        If user is left blank it defaults to the author of the command.
        """
        if user is None:
            user = ctx.author
        if self.pass_user_hierarchy_check(ctx, rolename):
            # noinspection PyTypeChecker
            await self._removerole(ctx, user, rolename)
        else:
            await self.complain(ctx, USER_HIERARCHY_ISSUE)

    @commands.group(autohelp=True)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx: commands.Context):
        """Edits roles settings"""
        pass

    @editrole.command(name="colour", aliases=["color"])
    async def editrole_colour(
        self, ctx: commands.Context, role: discord.Role, value: discord.Colour
    ):
        """Edits a role's colour

        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        \"http://www.w3schools.com/colors/colors_picker.asp\"
        Examples:
        !editrole colour \"The Transistor\" #ff0000
        !editrole colour Test #ff9900"""
        author = ctx.author
        reason = "{}({}) changed the colour of role '{}'".format(author.name, author.id, role.name)

        if not self.pass_user_hierarchy_check(ctx, role):
            await self.complain(ctx, USER_HIERARCHY_ISSUE)
            return

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
            author.name, author.id, old_name, name
        )

        if not self.pass_user_hierarchy_check(ctx, role):
            await self.complain(ctx, USER_HIERARCHY_ISSUE)
            return

        try:
            await role.edit(reason=reason, name=name)
        except discord.Forbidden:
            await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            log.info(reason)
            await ctx.send("Done.")

    @commands.group(invoke_without_command=True)
    @checks.is_owner()
    async def announce(self, ctx: commands.Context, *, message: str):
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
            await self.complain(ctx, RUNNING_ANNOUNCEMENT, prefix=prefix)

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

    @announce.command(name="channel")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def announce_channel(self, ctx, *, channel: discord.TextChannel = None):
        """
        Changes the channel on which the bot makes announcements.
        """
        if channel is None:
            channel = ctx.channel
        await self.conf.guild(ctx.guild).announce_channel.set(channel.id)

        await ctx.send("The announcement channel has been set to {}".format(channel.mention))

    @announce.command(name="ignore")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def announce_ignore(self, ctx):
        """
        Toggles whether the announcements will ignore the current server.
        """
        ignored = await self.conf.guild(ctx.guild).announce_ignore()
        await self.conf.guild(ctx.guild).announce_ignore.set(not ignored)

        verb = "will" if ignored else "will not"

        await ctx.send(f"The server {ctx.guild.name} {verb} receive announcements.")

    async def _valid_selfroles(self, guild: discord.Guild) -> Tuple[discord.Role]:
        """
        Returns a list of valid selfroles
        :param guild:
        :return:
        """
        selfrole_ids = set(await self.conf.guild(guild).selfroles())
        guild_roles = guild.roles

        valid_roles = tuple(r for r in guild_roles if r.id in selfrole_ids)
        valid_role_ids = set(r.id for r in valid_roles)

        if selfrole_ids != valid_role_ids:
            await self.conf.guild(guild).selfroles.set(valid_role_ids)

        # noinspection PyTypeChecker
        return valid_roles

    @commands.group(invoke_without_command=True)
    async def selfrole(self, ctx: commands.Context, *, selfrole: SelfRole):
        """
        Add a role to yourself that server admins have configured as user settable.

        NOTE: The role is case sensitive!
        """
        # noinspection PyTypeChecker
        await self._addrole(ctx, ctx.author, selfrole)

    @selfrole.command(name="remove")
    async def selfrole_remove(self, ctx: commands.Context, *, selfrole: SelfRole):
        """
        Removes a selfrole from yourself.

        NOTE: The role is case sensitive!
        """
        # noinspection PyTypeChecker
        await self._removerole(ctx, ctx.author, selfrole)

    @selfrole.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def selfrole_add(self, ctx: commands.Context, *, role: discord.Role):
        """
        Add a role to the list of available selfroles.

        NOTE: The role is case sensitive!
        """
        async with self.conf.guild(ctx.guild).selfroles() as curr_selfroles:
            if role.id not in curr_selfroles:
                curr_selfroles.append(role.id)

        await ctx.send("The selfroles list has been successfully modified.")

    @selfrole.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    async def selfrole_delete(self, ctx: commands.Context, *, role: SelfRole):
        """
        Removes a role from the list of available selfroles.

        NOTE: The role is case sensitive!
        """
        async with self.conf.guild(ctx.guild).selfroles() as curr_selfroles:
            curr_selfroles.remove(role.id)

        await ctx.send("The selfroles list has been successfully modified.")

    @selfrole.command(name="list")
    async def selfrole_list(self, ctx: commands.Context):
        """
        Lists all available selfroles.
        """
        selfroles = await self._valid_selfroles(ctx.guild)
        fmt_selfroles = "\n".join(["+ " + r.name for r in selfroles])

        msg = "Available Selfroles:\n{}".format(fmt_selfroles)
        await ctx.send(box(msg, "diff"))

    async def _serverlock_check(self, guild: discord.Guild) -> bool:
        """
        Checks if serverlocked is enabled.
        :param guild:
        :return: True if locked and left server
        """
        if await self.conf.serverlocked():
            await guild.leave()
            return True
        return False

    @commands.command()
    @checks.is_owner()
    async def serverlock(self, ctx: commands.Context):
        """
        Locks a bot to its current servers only.
        """
        serverlocked = await self.conf.serverlocked()
        await self.conf.serverlocked.set(not serverlocked)

        verb = "is now" if not serverlocked else "is no longer"

        await ctx.send("The bot {} serverlocked.".format(verb))

    # region Event Handlers
    async def on_guild_join(self, guild: discord.Guild):
        if await self._serverlock_check(guild):
            return


# endregion
