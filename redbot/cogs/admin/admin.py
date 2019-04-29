import logging
from typing import Tuple

import discord

from redbot.core import Config, checks, commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box
from .announcer import Announcer
from .rpchelpers import FakeContextAnnouncer
from .converters import MemberDefaultAuthor, SelfRole

log = logging.getLogger("red.admin")

T_ = Translator("Admin", __file__)

_ = lambda s: s
GENERIC_FORBIDDEN = _(
    "I attempted to do something that Discord denied me permissions for."
    " Your command failed to successfully complete."
)

HIERARCHY_ISSUE = _(
    "I tried to {verb} {role.name} to {member.display_name} but that role"
    " is higher than my highest role in the Discord hierarchy so I was"
    " unable to successfully add it. Please give me a higher role and "
    "try again."
)

USER_HIERARCHY_ISSUE = _(
    "I tried to {verb} {role.name} to {member.display_name} but that role"
    " is higher than your highest role in the Discord hierarchy so I was"
    " unable to successfully add it. Please get a higher role and "
    "try again."
)

ROLE_USER_HIERARCHY_ISSUE = _(
    "I tried to edit {role.name} but that role"
    " is higher than your highest role in the Discord hierarchy so I was"
    " unable to successfully add it. Please get a higher role and "
    "try again."
)

RUNNING_ANNOUNCEMENT = _(
    "I am already announcing something. If you would like to make a"
    " different announcement please use `{prefix}announce cancel`"
    " first."
)
_ = T_


@cog_i18n(_)
class Admin(commands.Cog):
    """A collection of server administration utilities."""

    def __init__(self, bot, config=Config):
        super().__init__()
        self.conf = config.get_conf(self, 8237492837454039, force_registration=True)

        self.conf.register_global(serverlocked=False)

        self.conf.register_guild(
            announce_ignore=False,
            announce_channel=None,  # Integer ID
            selfroles=[],  # List of integer ID's
        )

        self.__current_announcer = None

        # Bot and RPC initialization
        self.bot = bot
        self.bot.register_rpc_handler(self._announce)
        self.bot.register_rpc_handler(self._serverlock)

    def cog_unload(self):
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
                await self.complain(
                    ctx, T_(HIERARCHY_ISSUE), role=role, member=member, verb=_("add")
                )
            else:
                await self.complain(ctx, T_(GENERIC_FORBIDDEN))
        else:
            await ctx.send(
                _("I successfully added {role.name} to {member.display_name}").format(
                    role=role, member=member
                )
            )

    async def _removerole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            if not self.pass_hierarchy_check(ctx, role):
                await self.complain(
                    ctx, T_(HIERARCHY_ISSUE), role=role, member=member, verb=_("remove")
                )
            else:
                await self.complain(ctx, T_(GENERIC_FORBIDDEN))
        else:
            await ctx.send(
                _("I successfully removed {role.name} from {member.display_name}").format(
                    role=role, member=member
                )
            )

    # RPC Functions
    async def _announce(self, message) -> bool:
        """Starts an announcement through the bot.
        Paramaters
        ----------
        message: str

        Returns
        ----------
        bool
            Indicating whether or not starting the announcement worked.  True if succeeded, False otherwise.
        """
        if not self.is_announcing():
            announcer = Announcer(FakeContextAnnouncer(self.bot), message, config=self.conf)
            announcer.start()
            self.__current_announcer = announcer
            return True
        else:
            return False

    async def _serverlock(self):
        """Serverlocks the bot, preventing the bot from joining new guilds.

        Returns
        ----------
        bool
            Indicating whether or not the bot is serverlocked now.  True if the bot is now serverlocked, False if now it is not.
        """
        serverlocked = await self.conf.serverlocked()
        await self.conf.serverlocked.set(not serverlocked)
        return not serverlocked

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def addrole(
        self, ctx: commands.Context, rolename: discord.Role, *, user: MemberDefaultAuthor = None
    ):
        """Add a role to a user.

        If user is left blank it defaults to the author of the command.
        """
        if user is None:
            user = ctx.author
        if self.pass_user_hierarchy_check(ctx, rolename):
            # noinspection PyTypeChecker
            await self._addrole(ctx, user, rolename)
        else:
            await self.complain(
                ctx, T_(USER_HIERARCHY_ISSUE), member=user, role=rolename, verb=_("add")
            )

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def removerole(
        self, ctx: commands.Context, rolename: discord.Role, *, user: MemberDefaultAuthor = None
    ):
        """Remove a role from a user.

        If user is left blank it defaults to the author of the command.
        """
        if user is None:
            user = ctx.author
        if self.pass_user_hierarchy_check(ctx, rolename):
            # noinspection PyTypeChecker
            await self._removerole(ctx, user, rolename)
        else:
            await self.complain(
                ctx, T_(USER_HIERARCHY_ISSUE), member=user, role=rolename, verb=_("remove")
            )

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx: commands.Context):
        """Edit role settings."""
        pass

    @editrole.command(name="colour", aliases=["color"])
    async def editrole_colour(
        self, ctx: commands.Context, role: discord.Role, value: discord.Colour
    ):
        """Edit a role's colour.

        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        [Online colour picker](http://www.w3schools.com/colors/colors_picker.asp)

        Examples:
            `[p]editrole colour "The Transistor" #ff0000`
            `[p]editrole colour Test #ff9900`
        """
        author = ctx.author
        reason = "{}({}) changed the colour of role '{}'".format(author.name, author.id, role.name)

        if not self.pass_user_hierarchy_check(ctx, role):
            await self.complain(ctx, T_(ROLE_USER_HIERARCHY_ISSUE), role=role)
            return

        try:
            await role.edit(reason=reason, color=value)
        except discord.Forbidden:
            await self.complain(ctx, T_(GENERIC_FORBIDDEN))
        else:
            log.info(reason)
            await ctx.send(_("Done."))

    @editrole.command(name="name")
    @checks.admin_or_permissions(administrator=True)
    async def edit_role_name(self, ctx: commands.Context, role: discord.Role, *, name: str):
        """Edit a role's name.

        Use double quotes if the role or the name contain spaces.

        Examples:
            `[p]editrole name \"The Transistor\" Test`
        """
        author = ctx.message.author
        old_name = role.name
        reason = "{}({}) changed the name of role '{}' to '{}'".format(
            author.name, author.id, old_name, name
        )

        if not self.pass_user_hierarchy_check(ctx, role):
            await self.complain(ctx, T_(ROLE_USER_HIERARCHY_ISSUE), role=role)
            return

        try:
            await role.edit(reason=reason, name=name)
        except discord.Forbidden:
            await self.complain(ctx, T_(GENERIC_FORBIDDEN))
        else:
            log.info(reason)
            await ctx.send(_("Done."))

    @commands.group(invoke_without_command=True)
    @checks.is_owner()
    async def announce(self, ctx: commands.Context, *, message: str):
        """Announce a message to all servers the bot is in."""
        success = await self._announce(message)
        if success:
            await ctx.send(_("The announcement has begun."))
        else:
            prefix = ctx.prefix
            await self.complain(ctx, T_(RUNNING_ANNOUNCEMENT), prefix=prefix)

    @announce.command(name="cancel")
    @checks.is_owner()
    async def announce_cancel(self, ctx):
        """Cancel a running announce."""
        try:
            self.__current_announcer.cancel()
        except AttributeError:
            pass

        await ctx.send(_("The current announcement has been cancelled."))

    @announce.command(name="channel")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def announce_channel(self, ctx, *, channel: discord.TextChannel = None):
        """Change the channel to which the bot makes announcements."""
        if channel is None:
            channel = ctx.channel
        await self.conf.guild(ctx.guild).announce_channel.set(channel.id)

        await ctx.send(
            _("The announcement channel has been set to {channel.mention}").format(channel=channel)
        )

    @announce.command(name="ignore")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def announce_ignore(self, ctx):
        """Toggle announcements being enabled this server."""
        ignored = await self.conf.guild(ctx.guild).announce_ignore()
        await self.conf.guild(ctx.guild).announce_ignore.set(not ignored)

        if ignored:  # Keeping original logic....
            await ctx.send(
                _("The server {guild.name} will receive announcements.").format(guild=ctx.guild)
            )
        else:
            await ctx.send(
                _("The server {guild.name} will not receive announcements.").format(
                    guild=ctx.guild
                )
            )

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

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def selfrole(self, ctx: commands.Context, *, selfrole: SelfRole):
        """Add a role to yourself.

        Server admins must have configured the role as user settable.

        NOTE: The role is case sensitive!
        """
        # noinspection PyTypeChecker
        await self._addrole(ctx, ctx.author, selfrole)

    @selfrole.command(name="remove")
    async def selfrole_remove(self, ctx: commands.Context, *, selfrole: SelfRole):
        """Remove a selfrole from yourself.

        NOTE: The role is case sensitive!
        """
        # noinspection PyTypeChecker
        await self._removerole(ctx, ctx.author, selfrole)

    @selfrole.command(name="add")
    @checks.admin_or_permissions(manage_roles=True)
    async def selfrole_add(self, ctx: commands.Context, *, role: discord.Role):
        """Add a role to the list of available selfroles.

        NOTE: The role is case sensitive!
        """
        async with self.conf.guild(ctx.guild).selfroles() as curr_selfroles:
            if role.id not in curr_selfroles:
                curr_selfroles.append(role.id)

        await ctx.send(_("The selfroles list has been successfully modified."))

    @selfrole.command(name="delete")
    @checks.admin_or_permissions(manage_roles=True)
    async def selfrole_delete(self, ctx: commands.Context, *, role: SelfRole):
        """Remove a role from the list of available selfroles.

        NOTE: The role is case sensitive!
        """
        async with self.conf.guild(ctx.guild).selfroles() as curr_selfroles:
            curr_selfroles.remove(role.id)

        await ctx.send(_("The selfroles list has been successfully modified."))

    @selfrole.command(name="list")
    async def selfrole_list(self, ctx: commands.Context):
        """
        Lists all available selfroles.
        """
        selfroles = await self._valid_selfroles(ctx.guild)
        fmt_selfroles = "\n".join(["+ " + r.name for r in selfroles])

        msg = _("Available Selfroles:\n{selfroles}").format(selfroles=fmt_selfroles)
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
        """Lock a bot to its current servers only."""
        serverlocked = await self._serverlock()
        if serverlocked:
            await ctx.send(_("The bot is now serverlocked."))
        else:
            await ctx.send(_("The bot is no longer serverlocked."))

    # region Event Handlers
    async def on_guild_join(self, guild: discord.Guild):
        if await self._serverlock_check(guild):
            return


# endregion
