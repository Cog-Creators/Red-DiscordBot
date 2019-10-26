from collections import namedtuple
from typing import Union, Optional

import discord

from redbot.cogs.warnings.helpers import (
    warning_points_add_check,
    get_command_for_exceeded_points,
    get_command_for_dropping_points,
    warning_points_remove_check,
)
from redbot.core import Config, checks, commands, modlog
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.mod import is_admin_or_superior, is_mod_or_superior
from redbot.core.utils.chat_formatting import warning, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS


_ = Translator("Warnings", __file__)


@cog_i18n(_)
class Warnings(commands.Cog):
    """Warn misbehaving users and take automated actions."""

    default_guild = {"actions": [], "reasons": {}, "allow_custom_reasons": False}

    default_member = {"total_points": 0, "status": "", "warnings": {}}

    def __init__(self, bot: Red):
        super().__init__()
        self.config = Config.get_conf(self, identifier=5757575755)
        self.config.register_guild(**self.default_guild)
        self.config.register_member(**self.default_member)
        self.bot = bot
        self.registration_task = self.bot.loop.create_task(self.register_warningtype())

    # We're not utilising modlog yet - no need to register a casetype
    @staticmethod
    async def register_warningtype():
        casetypes_to_register = [
            {
                "name": "warning",
                "default_setting": True,
                "image": "\N{WARNING SIGN}",
                "case_str": "Warning",
            },
            {
                "name": "unwarned",
                "default_setting": True,
                "image": "\N{WARNING SIGN}",
                "case_str": "Unwarned",
            },
        ]
        try:
            await modlog.register_casetypes(casetypes_to_register)
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warningset(self, ctx: commands.Context):
        """Manage settings for Warnings."""
        pass

    @warningset.command()
    @commands.guild_only()
    async def allowcustomreasons(self, ctx: commands.Context, allowed: bool):
        """Enable or disable custom reasons for a warning."""
        guild = ctx.guild
        await self.config.guild(guild).allow_custom_reasons.set(allowed)
        if allowed:
            await ctx.send(_("Custom reasons have been enabled."))
        else:
            await ctx.send(_("Custom reasons have been disabled."))

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warnaction(self, ctx: commands.Context):
        """Manage automated actions for Warnings.

        Actions are essentially command macros. Any command can be run
        when the action is initially triggered, and/or when the action
        is lifted.

        Actions must be given a name and a points threshold. When a
        user is warned enough so that their points go over this
        threshold, the action will be executed.
        """
        pass

    @warnaction.command(name="add")
    @commands.guild_only()
    async def action_add(self, ctx: commands.Context, name: str, points: int):
        """Create an automated action.

        Duplicate action names are not allowed.
        """
        guild = ctx.guild

        exceed_command = await get_command_for_exceeded_points(ctx)
        drop_command = await get_command_for_dropping_points(ctx)

        to_add = {
            "action_name": name,
            "points": points,
            "exceed_command": exceed_command,
            "drop_command": drop_command,
        }

        # Have all details for the action, now save the action
        guild_settings = self.config.guild(guild)
        async with guild_settings.actions() as registered_actions:
            for act in registered_actions:
                if act["action_name"] == to_add["action_name"]:
                    await ctx.send(_("Duplicate action name found!"))
                    break
            else:
                registered_actions.append(to_add)
                # Sort in descending order by point count for ease in
                # finding the highest possible action to take
                registered_actions.sort(key=lambda a: a["points"], reverse=True)
                await ctx.send(_("Action {name} has been added.").format(name=name))

    @warnaction.command(name="delete", aliases=["del", "remove"])
    @commands.guild_only()
    async def action_del(self, ctx: commands.Context, action_name: str):
        """Delete the action with the specified name."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        async with guild_settings.actions() as registered_actions:
            to_remove = None
            for act in registered_actions:
                if act["action_name"] == action_name:
                    to_remove = act
                    break
            if to_remove:
                registered_actions.remove(to_remove)
                await ctx.tick()
            else:
                await ctx.send(_("No action named {name} exists!").format(name=action_name))

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warnreason(self, ctx: commands.Context):
        """Manage warning reasons.

        Reasons must be given a name, description and points value. The
        name of the reason must be given when a user is warned.
        """
        pass

    @warnreason.command(name="create", aliases=["add"])
    @commands.guild_only()
    async def reason_create(
        self, ctx: commands.Context, name: str, points: int, *, description: str
    ):
        """Create a warning reason."""
        guild = ctx.guild

        if name.lower() == "custom":
            await ctx.send(_("*Custom* cannot be used as a reason name!"))
            return
        to_add = {"points": points, "description": description}
        completed = {name.lower(): to_add}

        guild_settings = self.config.guild(guild)

        async with guild_settings.reasons() as registered_reasons:
            registered_reasons.update(completed)

        await ctx.send(_("The new reason has been registered."))

    @warnreason.command(name="delete", aliases=["remove", "del"])
    @commands.guild_only()
    async def reason_del(self, ctx: commands.Context, reason_name: str):
        """Delete a warning reason."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        async with guild_settings.reasons() as registered_reasons:
            if registered_reasons.pop(reason_name.lower(), None):
                await ctx.tick()
            else:
                await ctx.send(_("That is not a registered reason name."))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def reasonlist(self, ctx: commands.Context):
        """List all configured reasons for Warnings."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.reasons() as registered_reasons:
            for r, v in registered_reasons.items():
                if await ctx.embed_requested():
                    em = discord.Embed(
                        title=_("Reason: {name}").format(name=r), description=v["description"]
                    )
                    em.add_field(name=_("Points"), value=str(v["points"]))
                    msg_list.append(em)
                else:
                    msg_list.append(
                        _(
                            "Name: {reason_name}\nPoints: {points}\nDescription: {description}"
                        ).format(reason_name=r, **v)
                    )
        if msg_list:
            await menu(ctx, msg_list, DEFAULT_CONTROLS)
        else:
            await ctx.send(_("There are no reasons configured!"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def actionlist(self, ctx: commands.Context):
        """List all configured automated actions for Warnings."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.actions() as registered_actions:
            for r in registered_actions:
                if await ctx.embed_requested():
                    em = discord.Embed(title=_("Action: {name}").format(name=r["action_name"]))
                    em.add_field(name=_("Points"), value="{}".format(r["points"]), inline=False)
                    em.add_field(name=_("Exceed command"), value=r["exceed_command"], inline=False)
                    em.add_field(name=_("Drop command"), value=r["drop_command"], inline=False)
                    msg_list.append(em)
                else:
                    msg_list.append(
                        _(
                            "Name: {action_name}\nPoints: {points}\n"
                            "Exceed command: {exceed_command}\nDrop command: {drop_command}"
                        ).format(**r)
                    )
        if msg_list:
            await menu(ctx, msg_list, DEFAULT_CONTROLS)
        else:
            await ctx.send(_("There are no actions configured!"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def warn(
        self,
        ctx: commands.Context,
        user: discord.Member,
        points: Optional[int] = 1,
        *,
        reason: str,
    ):
        """Warn the user for the specified reason.

        `<points>` number of points the warning should be for. If no number is supplied
        1 point will be given. Pre-set warnings disregard this.
        `<reason>` can be a registered reason if it exists or a custom one
        is created by default.
        """
        if user == ctx.author:
            await ctx.send(_("You cannot warn yourself."))
            return
        custom_allowed = await self.config.guild(ctx.guild).allow_custom_reasons()
        guild_settings = self.config.guild(ctx.guild)
        reason_type = None
        async with guild_settings.reasons() as registered_reasons:
            if reason.lower() not in registered_reasons:
                msg = _("That is not a registered reason!")
                if custom_allowed:
                    reason_type = {"description": reason, "points": points}
                elif (
                    ctx.guild.owner == ctx.author
                    or ctx.channel.permissions_for(ctx.author).administrator
                    or await ctx.bot.is_owner(ctx.author)
                ):
                    msg += " " + _(
                        "Do `{prefix}warningset allowcustomreasons true` to enable custom "
                        "reasons."
                    ).format(prefix=ctx.prefix)
                    return await ctx.send(msg)
            else:
                reason_type = registered_reasons[reason.lower()]
        if reason_type is None:
            return
        member_settings = self.config.member(user)
        current_point_count = await member_settings.total_points()
        warning_to_add = {
            str(ctx.message.id): {
                "points": reason_type["points"],
                "description": reason_type["description"],
                "mod": ctx.author.id,
            }
        }
        async with member_settings.warnings() as user_warnings:
            user_warnings.update(warning_to_add)
        current_point_count += reason_type["points"]
        await member_settings.total_points.set(current_point_count)

        await warning_points_add_check(self.config, ctx, user, current_point_count)
        try:
            em = discord.Embed(
                title=_("Warning from {user}").format(user=ctx.author),
                description=reason_type["description"],
            )
            em.add_field(name=_("Points"), value=str(reason_type["points"]))
            await user.send(
                _("You have received a warning in {guild_name}.").format(
                    guild_name=ctx.guild.name
                ),
                embed=em,
            )
        except discord.HTTPException:
            pass
        try:
            reason_msg = _(
                "{reason}\n\nUse `{prefix}unwarn {user} {message}` to remove this warning."
            ).format(
                reason=_("{description}\nPoints: {points}").format(
                    description=reason_type["description"], points=reason_type["points"]
                ),
                prefix=ctx.prefix,
                user=user.id,
                message=ctx.message.id,
            )
            await modlog.create_case(
                self.bot,
                ctx.guild,
                ctx.message.created_at,
                "warning",
                user,
                ctx.message.author,
                reason_msg,
                until=None,
                channel=None,
            )
        except RuntimeError:
            pass
        await ctx.send(_("User {user} has been warned.").format(user=user))

    @commands.command()
    @commands.guild_only()
    async def warnings(
        self, ctx: commands.Context, user: Optional[Union[discord.Member, int]] = None
    ):
        """List the warnings for the specified user.

        Omit `<user>` to see your own warnings.

        Note that showing warnings for users other than yourself requires
        appropriate permissions.
        """
        if user is None:
            user = ctx.author
        else:
            if not await is_mod_or_superior(self.bot, ctx.author):
                return await ctx.send(
                    warning(_("You are not allowed to check warnings for other users!"))
                )

            try:
                userid: int = user.id
            except AttributeError:
                userid: int = user
                user = ctx.guild.get_member(userid)
                user = user or namedtuple("Member", "id guild")(userid, ctx.guild)

        msg = ""
        member_settings = self.config.member(user)
        async with member_settings.warnings() as user_warnings:
            if not user_warnings.keys():  # no warnings for the user
                await ctx.send(_("That user has no warnings!"))
            else:
                for key in user_warnings.keys():
                    mod = ctx.guild.get_member(user_warnings[key]["mod"])
                    if mod is None:
                        mod = discord.utils.get(
                            self.bot.get_all_members(), id=user_warnings[key]["mod"]
                        )
                        if mod is None:
                            mod = await self.bot.fetch_user(user_warnings[key]["mod"])
                    msg += _(
                        "{num_points} point warning {reason_name} issued by {user} for "
                        "{description}\n"
                    ).format(
                        num_points=user_warnings[key]["points"],
                        reason_name=key,
                        user=mod,
                        description=user_warnings[key]["description"],
                    )
                await ctx.send_interactive(
                    pagify(msg, shorten_by=58), box_lang=_("Warnings for {user}").format(user=user)
                )

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def unwarn(self, ctx: commands.Context, user: Union[discord.Member, int], warn_id: str):
        """Remove a warning from a user."""

        guild = ctx.guild

        try:
            user_id = user.id
            member = user
        except AttributeError:
            user_id = user
            member = guild.get_member(user_id)
            member = member or namedtuple("Member", "guild id")(guild, user_id)

        if user_id == ctx.author.id:
            return await ctx.send(_("You cannot remove warnings from yourself."))

        member_settings = self.config.member(member)
        current_point_count = await member_settings.total_points()
        await warning_points_remove_check(self.config, ctx, member, current_point_count)
        async with member_settings.warnings() as user_warnings:
            if warn_id not in user_warnings.keys():
                return await ctx.send(_("That warning doesn't exist!"))
            else:
                current_point_count -= user_warnings[warn_id]["points"]
                await member_settings.total_points.set(current_point_count)
                user_warnings.pop(warn_id)
        try:
            await modlog.create_case(
                self.bot,
                ctx.guild,
                ctx.message.created_at,
                "unwarned",
                member,
                ctx.message.author,
                None,
                until=None,
                channel=None,
            )
        except RuntimeError:
            pass

        await ctx.tick()
