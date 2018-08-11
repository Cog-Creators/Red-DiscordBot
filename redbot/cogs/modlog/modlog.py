import discord

from redbot.core import checks, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box

_ = Translator("ModLog", __file__)


@cog_i18n(_)
class ModLog:
    """Log for mod actions"""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.group()
    @checks.guildowner_or_permissions(administrator=True)
    async def modlogset(self, ctx: commands.Context):
        """Settings for the mod log"""
        pass

    @modlogset.command()
    @commands.guild_only()
    async def modlog(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Sets a channel as mod log

        Leaving the channel parameter empty will deactivate it"""
        guild = ctx.guild
        if channel:
            if channel.permissions_for(guild.me).send_messages:
                await modlog.set_modlog_channel(guild, channel)
                await ctx.send(_("Mod events will be sent to {}").format(channel.mention))
            else:
                await ctx.send(
                    _("I do not have permissions to send messages in {}!").format(channel.mention)
                )
        else:
            try:
                await modlog.get_modlog_channel(guild)
            except RuntimeError:
                await ctx.send_help()
            else:
                await modlog.set_modlog_channel(guild, None)
                await ctx.send(_("Mod log deactivated."))

    @modlogset.command(name="cases")
    @commands.guild_only()
    async def set_cases(self, ctx: commands.Context, action: str = None):
        """Enables or disables case creation for each type of mod action"""
        guild = ctx.guild

        if action is None:  # No args given
            casetypes = await modlog.get_all_casetypes(guild)
            await ctx.send_help()
            title = _("Current settings:")
            msg = ""
            for ct in casetypes:
                enabled = await ct.is_enabled()
                value = "enabled" if enabled else "disabled"
                msg += "%s : %s\n" % (ct.name, value)

            msg = title + "\n" + box(msg)
            await ctx.send(msg)
            return
        casetype = await modlog.get_casetype(action, guild)
        if not casetype:
            await ctx.send(_("That action is not registered"))
        else:

            enabled = await casetype.is_enabled()
            await casetype.set_enabled(True if not enabled else False)

            msg = _("Case creation for {} actions is now {}.").format(
                action, "enabled" if not enabled else "disabled"
            )
            await ctx.send(msg)

    @modlogset.command()
    @commands.guild_only()
    async def resetcases(self, ctx: commands.Context):
        """Resets modlog's cases"""
        guild = ctx.guild
        await modlog.reset_cases(guild)
        await ctx.send(_("Cases have been reset."))

    @commands.command()
    @commands.guild_only()
    async def case(self, ctx: commands.Context, number: int):
        """Shows the specified case"""
        try:
            case = await modlog.get_case(number, ctx.guild, self.bot)
        except RuntimeError:
            await ctx.send(_("That case does not exist for that server"))
            return
        else:
            await ctx.send(embed=await case.get_case_msg_content())

    @commands.command(usage="[case] <reason>")
    @commands.guild_only()
    async def reason(self, ctx: commands.Context, *, reason: str):
        """Lets you specify a reason for mod-log's cases
        
        Please note that you can only edit cases you are
        the owner of unless you are a mod/admin or the server owner.
        
        If no number is specified, the latest case will be used."""
        author = ctx.author
        guild = ctx.guild
        potential_case = reason.split()[0]
        if potential_case.isdigit():
            case = int(potential_case)
            reason = reason.replace(potential_case, "")
        else:
            case = str(int(await modlog.get_next_case_number(guild)) - 1)
            # latest case
        try:
            case_before = await modlog.get_case(case, guild, self.bot)
        except RuntimeError:
            await ctx.send(_("That case does not exist!"))
            return
        else:
            if case_before.moderator is None:
                # No mod set, so attempt to find out if the author
                # triggered the case creation with an action
                bot_perms = guild.me.guild_permissions
                if bot_perms.view_audit_log:
                    case_type = await modlog.get_casetype(case_before.action_type, guild)
                    if case_type is not None and case_type.audit_type is not None:
                        audit_type = getattr(discord.AuditLogAction, case_type.audit_type)
                        if audit_type:
                            audit_case = None
                            async for entry in guild.audit_logs(action=audit_type):
                                if (
                                    entry.target.id == case_before.user.id
                                    and entry.action == audit_type
                                ):
                                    audit_case = entry
                                    break
                            if audit_case:
                                case_before.moderator = audit_case.user
            is_guild_owner = author == guild.owner
            is_case_author = author == case_before.moderator
            author_is_mod = await ctx.bot.is_mod(author)
            if not (is_guild_owner or is_case_author or author_is_mod):
                await ctx.send(_("You are not authorized to modify that case!"))
                return
            to_modify = {"reason": reason}
            if case_before.moderator != author:
                to_modify["amended_by"] = author
            to_modify["modified_at"] = ctx.message.created_at.timestamp()
            await case_before.edit(to_modify)
            await ctx.send(_("Reason has been updated."))
