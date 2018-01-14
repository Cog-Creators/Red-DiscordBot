from collections import namedtuple
from datetime import timedelta, datetime

from discord.ext import commands
import discord

from redbot.core import Config, modlog, checks
from redbot.core.bot import Red
from redbot.core.context import RedContext
from redbot.core.i18n import CogI18n
from redbot.core.utils.mod import is_admin_or_superior
from redbot.core.utils.chat_formatting import warning, pagify

_ = CogI18n("Warnings", __file__)


class Warnings:
    """A warning system for Red"""

    default_guild = {
        "actions": [],
        "reasons": {},
        "allow_custom_reasons": False
    }

    default_member = {
        "total_points": 0,
        "status": "",
        "warnings": {}
    }

    def __init__(self, bot: Red):
        self.config = Config.get_conf(self, identifier=5757575755)
        self.config.register_guild(**self.default_guild)
        self.config.register_member(**self.default_member)
        self.bot = bot
        self.bot.loop.create_task(self.register_warningtype())

    async def register_warningtype(self):
        try:
            await modlog.register_casetype(
                "warning", True, "\N{WARNING SIGN}", "Warning", None
            )
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warningset(self, ctx: RedContext):
        """Warning settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @warningset.command()
    @commands.guild_only()
    async def allowcustomreasons(self, ctx: RedContext, allowed: bool):
        """Allow or disallow custom reasons for a warning"""
        guild = ctx.guild
        await self.config.guild(guild).allow_custom_reasons.set(allowed)
        await ctx.send(
            _("Custom reasons have been {}".format("enabled" if allowed else "disabled"))
        )

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warnaction(self, ctx: RedContext):
        """Action management"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @warnaction.command(name="add")
    @commands.guild_only()
    async def action_add(self, ctx: RedContext, name: str, points: int, action: str):
        """Create an action to be taken at a specified point count
        Duplicate action names are not allowed"""
        guild = ctx.guild

        if action.lower() not in ("add_role", "kick", "softban", "tempban", "ban"):
            await ctx.send("Invalid action specified!")
            return
        to_add = {
            "point_count": points,
            "action": action.lower(),
            "action_name": name
        }

        def same_author_check(m):
            return m.author == ctx.author

        if action.lower() == "add_role":
            await ctx.send(_("Type the ID of the role that should be added"))
            msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
            if msg is None:
                await ctx.send(_("Ok then"))
                return
            try:
                int(msg.content)
            except ValueError:
                await ctx.send(_("That isn't an ID"))
                return
            else:
                role = discord.utils.get(guild.roles, id=int(msg.content))
                if role is None:
                    await ctx.send(_("That role doesn't exist!"))
                    return
                to_add["role_id"] = int(msg.content)
        elif action.lower() == "tempban":
            await ctx.send(_("Type the number of days the user should be banned for"))
            msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
            if msg is None:
                await ctx.send(_("Ok then"))
                return
            try:
                int(msg.content)
            except ValueError:
                await ctx.send("That isn't a number!")
                return
            else:
                to_add["tban_length"] = int(msg.content)

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
                registered_actions.sort(key=lambda a: a["point_count"], reverse=True)
                await ctx.tick()

    @warnaction.command(name="del")
    @commands.guild_only()
    async def action_del(self, ctx: RedContext, action_name: str):
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

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def warnreason(self, ctx: RedContext):
        """Add reasons for warnings"""
        if isinstance(ctx.invoked_subcommand, commands.Group):
            await ctx.send_help()

    @warnreason.command(name="add")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def reason_add(self, ctx: RedContext, name: str, points: int, *, description: str):
        """Add a reason to be available for warnings"""
        guild = ctx.guild

        if name.lower() == "custom":
            await ctx.send("That cannot be used as a reason name!")
            return
        to_add = {
            "points": points,
            "description": description
        }
        completed = {
            name.lower(): to_add
        }

        guild_settings = self.config.guild(guild)

        async with guild_settings.reasons() as registered_reasons:
            registered_reasons.update(completed)

        await ctx.send(_("That reason has been registered"))

    @warnreason.command(name="del")
    @commands.guild_only()
    async def reason_del(self, ctx: RedContext, reason_name: str):
        """Delete the reason with the specified name"""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        async with guild_settings.reasons() as registered_reasons:
            if registered_reasons.pop(reason_name.lower(), None):
                await ctx.send(_("Removed reason {}").format(reason_name))
            else:
                await ctx.send(_("That is not a registered reason name"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_member=True)
    async def reasonlist(self, ctx: RedContext):
        """List all configured reasons for warnings"""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.reasons() as registered_reasons:
            for r in registered_reasons.keys():
                msg_list.append(
                    "Name: {}\nPoints: {}\nAction: {}".format(
                        r, r["points"], r["action"]
                    )
                )
        await ctx.send_interactive(msg_list)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def actionlist(self, ctx: RedContext):
        """List the actions to be taken at specific point values"""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.actions() as registered_actions:
            for r in registered_actions.keys():
                msg_list.append(
                    "Name: {}\nPoints: {}\nDescription: {}".format(
                        r, r["points"], r["description"]
                    )
                )
        await ctx.send_interactive(msg_list)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def warn(self, ctx: RedContext, user: discord.Member, reason: str):
        """Warn the user for the specified reason
        Reason must be a registered reason, or custom if custom reasons are allowed"""
        reason_type = {}
        if reason.lower() == "custom":
            custom_allowed = await self.config.guild(ctx.guild).allow_custom_reasons()
            if not custom_allowed:
                await ctx.send(
                    _(
                        "Custom reasons are not allowed! Please see {} for "
                        "a complete list of valid reasons"
                    ).format(
                        "`{}reasonlist`".format(ctx.prefix)
                    )
                )
                return
            reason_type = await self.custom_warning_reason(ctx)
        else:
            guild_settings = self.config.guild(ctx.guild)
            async with guild_settings.reasons() as registered_reasons:
                if reason.lower() not in registered_reasons:
                    await ctx.send(_("That is not a registered reason!"))
                else:
                    reason_type = registered_reasons[reason.lower()]

        member_settings = self.config.member(user)
        current_point_count = await member_settings.total_points()
        warning_to_add = {
            str(ctx.message.id): {
                "points": reason_type["points"],
                "description": reason_type["description"],
                "mod": ctx.author.id
            }
        }
        async with member_settings.warnings() as user_warnings:
            user_warnings.update(warning_to_add)
        current_point_count += reason_type["points"]
        await member_settings.total_points.set(current_point_count)
        await self.warning_points_add_check(ctx, user, current_point_count)
        await ctx.tick()

    @commands.command()
    @commands.guild_only()
    async def warnings(self, ctx: RedContext, userid: int=None):
        """Show warnings for the specified user.
        If userid is None, show warnings for the person running the command
        Note that showing warnings for users other than yourself requires
        appropriate permissions"""
        if userid is None:
            user = ctx.author
        else:
            if not is_admin_or_superior(self.bot, ctx.author):
                await ctx.send(
                    warning(
                        _("You are not allowed to check "
                          "warnings for other users!")
                    )
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
                            self.bot.get_all_members(),
                            id=user_warnings[key]["mod"]
                        )
                        if mod is None:
                            mod = await self.bot.get_user_info(
                                user_warnings[key]["mod"]
                            )
                    msg += "{} point warning {} issued by {} for {}\n".format(
                        user_warnings[key]["points"],
                        key,
                        mod,
                        user_warnings[key]["description"]
                    )
                await ctx.send_interactive(
                    pagify(msg), box_lang="Warnings for {}".format(user)
                )

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def unwarn(self, ctx: RedContext, user_id: int, warn_id: str):
        """Removes the specified warning from the user specified"""
        guild = ctx.guild
        member = guild.get_member(user_id)
        if member is None:  # no longer in guild, but need a "member" object
            member = namedtuple("Member", "guild id")(guild, user_id)
        member_settings = self.config.member(member)

        current_point_count = await member_settings.total_points()
        async with member_settings.warnings() as user_warnings:
            if warn_id not in user_warnings.keys():
                await ctx.send("That warning doesn't exist!")
                return
            else:
                current_point_count -= user_warnings[warn_id]["points"]
                await member_settings.total_points.set(current_point_count)
                user_warnings.pop(warn_id)
        await ctx.tick()

    async def warning_points_add_check(self, ctx: RedContext, user: discord.Member, points: int):
        """Handles any action that needs to be taken or not based on the points"""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        act = {}
        async with guild_settings.actions() as registered_actions:
            for a in registered_actions.keys():
                if points >= registered_actions[a]["point_count"]:
                    act = registered_actions[a]
                else:
                    break
        mod_loaded = self.bot.get_cog("Mod")
        if points >= act["point_count"]:
            action_to_take = act["action"]
            if action_to_take == "add_role":
                role = discord.utils.get(guild.roles, id=act["role_id"])
                await user.add_roles(role)
                await modlog.create_case(
                    guild, ctx.message.created_at, "warning", user,
                    ctx.author, "Earned too many warning points"
                )
            elif action_to_take == "kick":
                if mod_loaded:
                    kick_cmd = self.bot.get_command("kick")
                    if kick_cmd:
                        await ctx.invoke(
                            kick_cmd, user, reason="Earned too many warning points"
                        )
            elif action_to_take == "softban":
                if mod_loaded:
                    softban_cmd = self.bot.get_command("softban")
                    if softban_cmd:
                        await ctx.invoke(
                            softban_cmd, user, reason="Earned too many warning points"
                        )
            elif action_to_take == "tempban":
                if mod_loaded:
                    tempban_cmd = self.bot.get_command("tempban")
                    tempban_length = act["tban_length"]
                    await ctx.invoke(
                        tempban_cmd, user, days=tempban_length,
                        reason="Earned too many warning points"
                    )
            elif action_to_take == "ban":
                if mod_loaded:
                    ban_cmd = self.bot.get_command("ban")
                    await ctx.invoke(
                        ban_cmd, user, 1, reason="Earned too many warning points"
                    )

    async def custom_warning_reason(self, ctx: RedContext):
        """Handles getting description and points for custom reasons"""
        to_add = {
            "points": 0,
            "description": ""
        }

        def same_author_check(m):
            return m.author == ctx.author

        await ctx.send(_("How many points should be given for this reason?"))
        msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
        if msg is None:
            await ctx.send(_("Ok then"))
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

        await ctx.send(_("Enter a description for this reason"))
        msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
        if msg is None:
            await ctx.send(_("Ok then"))
            return
        to_add["description"] = msg.content
        return to_add

    @staticmethod
    def get_expiry_time(expiredelta: str):
        units = expiredelta.split()
        weeks = 0
        days = 0
        hours = 0
        minutes = 0
        seconds = 0
        for unit in units:
            if unit[-1].lower() == "w":
                weeks = int(unit[:-1])
            elif unit[-1].lower() == "d":
                days = int(unit[:-1])
            elif unit[-1].lower() == "h":
                hours = int(unit[:-1])
            elif unit[-1].lower() == "m":
                minutes = int(unit[:-1])
            elif unit[-1].lower() == "s":
                seconds = int(unit[:-1])
            else:
                return None  # invalid unit passed in, so no idea how to interpret it
        return timedelta(
            weeks=weeks, days=days, hours=hours,
            minutes=minutes, seconds=seconds
        )
