import discord
from discord.ext import commands

from core import Config, checks

from .converters import MemberDefaultAuthor


GENERIC_FORBIDDEN = (
    "I attempted to do something that Discord denied me permissions for."
    " Your command failed to successfully complete."
)


HEIRARCHY_ISSUE = (
    "I tried to add {role.name} to {member.display_name} but that role"
    " is higher than my highest role in the Discord heirarchy so I was"
    " unable to successfully add it. Please give me a higher role and "
    "try again."
)


class Admin:
    def __init__(self):
        self.conf = Config.get_conf(self, 8237492837454039)

    async def complain(self, ctx: commands.Context, message: str,
                       **kwargs):
        await ctx.send(message.format(**kwargs))

    def pass_heirarchy_check(self, ctx: commands.Context,
                             role: discord.Role) -> bool:
        """
        Determines if the bot has a higher role than the given one.
        :param ctx:
        :param role: Role object.
        :return:
        """
        return ctx.guild.me.top_role > role

    @commands.command()
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
                await self.complain(ctx, HEIRARCHY_ISSUE, role=rolename,
                                    member=user)
            else:
                await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            await ctx.send("I successfully added {role.name} to"
                           " {member.display_name}".format(
                               role=rolename, member=user
                           ))

    @commands.command()
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
            if not self.pass_heirarchy_check(ctx, rolename)
                await self.complain(ctx, HEIRARCHY_ISSUE, role=rolename,
                                    member=user)
            else:
                await self.complain(ctx, GENERIC_FORBIDDEN)
        else:
            await ctx.send("I successfully removed {role.name} from"
                           " {member.display_name}".format(
                               role=rolename, member=user
                           ))

