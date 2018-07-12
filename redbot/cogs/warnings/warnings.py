from collections import namedtuple

import discord
import asyncio

from redbot.cogs.warnings.helpers import (
    warning_points_add_check,
    get_command_for_exceeded_points,
    get_command_for_dropping_points,
    warning_points_remove_check,
)
from redbot.core import Config, modlog, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.mod import is_admin_or_superior
from redbot.core.utils.chat_formatting import warning, pagify

_ = Translator("Warnings", __file__)


@cog_i18n(_)
class Warnings:
    """A warning system for Red"""

    default_guild = {"actions": [], "reasons": {}, "allow_custom_reasons": False}

    default_member = {"total_points": 0, "status": "", "warnings": {}}

    def __init__(self, bot: Red):
        self.config = Config.get_conf(self, identifier=5757575755)
        self.config.register_guild(**self.default_guild)
        self.config.register_member(**self.default_member)
        self.bot = bot
        loop = asyncio.get_event_loop()
        loop.create_task(self.register_warningtype())

    @staticmethod
    async def register_warningtype():
        try:
            await modlog.register_casetype("warning", True, "\N{WARNING SIGN}", "Warning", None)
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warningset(self, ctx: commands.Context):
        """Warning settings"""
        pass

    @warningset.command()
    @commands.guild_only()
    async def allowcustomreasons(self, ctx: commands.Context, allowed: bool):
        """Enable or Disable custom reasons for a warning"""
        guild = ctx.guild
        await self.config.guild(guild).allow_custom_reasons.set(allowed)
        await ctx.send(
            _("Custom reasons have been {}.").format(_("enabled") if allowed else _("disabled"))
        )

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warnaction(self, ctx: commands.Context):
        """Action management"""
        pass

    @warnaction.command(name="add")
    @commands.guild_only()
    async def action_add(self, ctx: commands.Context, name: str, points: int):
        """Create an action to be taken at a specified point count

        Duplicate action names are not allowed
        """
        guild = ctx.guild

        await ctx.send("Would you like to enter commands to be run? (y/n)")

        def same_author_check(m):
            return m.author == ctx.author

        try:
            msg = await ctx.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("Ok then."))
            return

        if msg.content.lower() == "y":
            exceed_command = await get_command_for_exceeded_points(ctx)
            if exceed_command is None:
                return
            drop_command = await get_command_for_dropping_points(ctx)
            if drop_command is None:
                return
        else:
            exceed_command = None
            drop_command = None
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
                await ctx.tick()

    @warnaction.command(name="del")
    @commands.guild_only()
    async def action_del(self, ctx: commands.Context, action_name: str):
        """Delete the point count action with the specified name"""
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
                await ctx.send(_("No action named {} exists!").format(action_name))

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warnreason(self, ctx: commands.Context):
        """Add reasons for warnings"""
        pass

    @warnreason.command(name="add")
    @commands.guild_only()
    async def reason_add(self, ctx: commands.Context, name: str, points: int, *, description: str):
        """Add a reason to be available for warnings"""
        guild = ctx.guild

        if name.lower() == "custom":
            await ctx.send("That cannot be used as a reason name!")
            return
        to_add = {"points": points, "description": description}
        completed = {name.lower(): to_add}

        guild_settings = self.config.guild(guild)

        async with guild_settings.reasons() as registered_reasons:
            registered_reasons.update(completed)

        await ctx.send(_("That reason has been registered."))

    @warnreason.command(name="del")
    @commands.guild_only()
    async def reason_del(self, ctx: commands.Context, reason_name: str):
        """Delete the reason with the specified name"""
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
        """List all configured reasons for warnings"""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.reasons() as registered_reasons:
            for r, v in registered_reasons.items():
                msg_list.append(
                    "Name: {}\nPoints: {}\nDescription: {}".format(
                        r, v["points"], v["description"]
                    )
                )
        if msg_list:
            await ctx.send_interactive(msg_list)
        else:
            await ctx.send(_("There are no reasons configured!"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def actionlist(self, ctx: commands.Context):
        """List the actions to be taken at specific point values"""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.actions() as registered_actions:
            for r in registered_actions:
                msg_list.append(
                    "Name: {}\nPoints: {}\nExceed command: {}\n"
                    "Drop command: {}".format(
                        r["action_name"], r["points"], r["exceed_command"], r["drop_command"]
                    )
                )
        if msg_list:
            await ctx.send_interactive(msg_list)
        else:
            await ctx.send(_("There are no actions configured!"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def warn(self, ctx: commands.Context, user: discord.Member, reason: str):
        """Warn the user for the specified reason

        Reason must be a registered reason, or "custom" if custom reasons are allowed
        """
        if reason.lower() == "custom":
            custom_allowed = await self.config.guild(ctx.guild).allow_custom_reasons()
            if not custom_allowed:
                await ctx.send(
                    _(
                        "Custom reasons are not allowed! Please see {} for "
                        "a complete list of valid reasons."
                    ).format("`{}reasonlist`".format(ctx.prefix))
                )
                return
            reason_type = await self.custom_warning_reason(ctx)
        else:
            guild_settings = self.config.guild(ctx.guild)
            async with guild_settings.reasons() as registered_reasons:
                if reason.lower() not in registered_reasons:
                    await ctx.send(_("That is not a registered reason!"))
                    return
                else:
                    reason_type = registered_reasons[reason.lower()]

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
        await ctx.tick()

    @commands.command()
    @commands.guild_only()
    async def warnings(self, ctx: commands.Context, userid: int = None):
        """Show warnings for the specified user.

        If userid is None, show warnings for the person running the command
        Note that showing warnings for users other than yourself requires
        appropriate permissions
        """
        if userid is None:
            user = ctx.author
        else:
            if not await is_admin_or_superior(self.bot, ctx.author):
                await ctx.send(
                    warning(_("You are not allowed to check warnings for other users!"))
                )
                return
            else:
                user = ctx.guild.get_member(userid)
                if user is None:  # user not in guild
                    user = namedtuple("Member", "id guild")(userid, ctx.guild)
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
                            mod = await self.bot.get_user_info(user_warnings[key]["mod"])
                    msg += "{} point warning {} issued by {} for {}\n".format(
                        user_warnings[key]["points"], key, mod, user_warnings[key]["description"]
                    )
                await ctx.send_interactive(pagify(msg), box_lang="Warnings for {}".format(user))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def unwarn(self, ctx: commands.Context, user_id: int, warn_id: str):
        """Removes the specified warning from the user specified"""
        guild = ctx.guild
        member = guild.get_member(user_id)
        if member is None:  # no longer in guild, but need a "member" object
            member = namedtuple("Member", "guild id")(guild, user_id)
        member_settings = self.config.member(member)

        current_point_count = await member_settings.total_points()
        await warning_points_remove_check(self.config, ctx, member, current_point_count)
        async with member_settings.warnings() as user_warnings:
            if warn_id not in user_warnings.keys():
                await ctx.send("That warning doesn't exist!")
                return
            else:
                current_point_count -= user_warnings[warn_id]["points"]
                await member_settings.total_points.set(current_point_count)
                user_warnings.pop(warn_id)
        await ctx.tick()

    @staticmethod
    async def custom_warning_reason(ctx: commands.Context):
        """Handles getting description and points for custom reasons"""
        to_add = {"points": 0, "description": ""}

        def same_author_check(m):
            return m.author == ctx.author

        await ctx.send(_("How many points should be given for this reason?"))
        try:
            msg = await ctx.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("Ok then."))
            return
        try:
            int(msg.content)
        except ValueError:
            await ctx.send(_("That isn't a number!"))
            return
        else:
            if int(msg.content) <= 0:
                await ctx.send(_("The point value needs to be greater than 0!"))
                return
            to_add["points"] = int(msg.content)

        await ctx.send(_("Enter a description for this reason."))
        try:
            msg = await ctx.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("Ok then."))
            return
        to_add["description"] = msg.content
        return to_add
