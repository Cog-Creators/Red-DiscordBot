from typing import Optional, Union

import discord

from redbot.core import checks, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import PagedMenu

_ = Translator("ModLog", __file__)


@cog_i18n(_)
class ModLog(commands.Cog):
    """Manage log channels for moderation actions."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    @commands.group()
    @checks.guildowner_or_permissions(administrator=True)
    async def modlogset(self, ctx: commands.Context):
        """Manage modlog settings."""
        pass

    @modlogset.command()
    @commands.guild_only()
    async def modlog(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set a channel as the modlog.

        Omit `<channel>` to disable the modlog.
        """
        guild = ctx.guild
        if channel:
            if channel.permissions_for(guild.me).send_messages:
                await modlog.set_modlog_channel(guild, channel)
                await ctx.send(
                    _("Mod events will be sent to {channel}").format(channel=channel.mention)
                )
            else:
                await ctx.send(
                    _("I do not have permissions to send messages in {channel}!").format(
                        channel=channel.mention
                    )
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
        """Enable or disable case creation for a mod action."""
        guild = ctx.guild

        if action is None:  # No args given
            casetypes = await modlog.get_all_casetypes(guild)
            await ctx.send_help()
            lines = []
            for ct in casetypes:
                enabled = _("enabled") if await ct.is_enabled() else _("disabled")
                lines.append(f"{ct.name} : {enabled}")

            await ctx.send(_("Current settings:\n") + box("\n".join(lines)))
            return

        casetype = await modlog.get_casetype(action, guild)
        if not casetype:
            await ctx.send(_("That action is not registered"))
        else:
            enabled = await casetype.is_enabled()
            await casetype.set_enabled(not enabled)
            await ctx.send(
                _("Case creation for {action_name} actions is now {enabled}.").format(
                    action_name=action, enabled=_("enabled") if not enabled else _("disabled")
                )
            )

    @modlogset.command()
    @commands.guild_only()
    async def resetcases(self, ctx: commands.Context):
        """Reset all modlog cases in this server."""
        guild = ctx.guild
        await modlog.reset_cases(guild)
        await ctx.send(_("Cases have been reset."))

    @commands.command()
    @commands.guild_only()
    async def case(self, ctx: commands.Context, number: int):
        """Show the specified case."""
        try:
            case = await modlog.get_case(number, ctx.guild, self.bot)
        except RuntimeError:
            await ctx.send(_("That case does not exist for that server"))
            return
        else:
            if await ctx.embed_requested():
                await ctx.send(embed=await case.message_content(embed=True))
            else:
                await ctx.send(await case.message_content(embed=False))

    @commands.command()
    @commands.guild_only()
    async def casesfor(self, ctx: commands.Context, *, member: Union[discord.Member, int]):
        """Display cases for the specified member."""
        try:
            if isinstance(member, int):
                cases = await modlog.get_cases_for_member(
                    bot=ctx.bot, guild=ctx.guild, member_id=member
                )
            else:
                cases = await modlog.get_cases_for_member(
                    bot=ctx.bot, guild=ctx.guild, member=member
                )
        except discord.NotFound:
            return await ctx.send(_("That user does not exist."))
        except discord.HTTPException:
            return await ctx.send(
                _("Something unexpected went wrong while fetching that user by ID.")
            )

        if not cases:
            return await ctx.send(_("That user does not have any cases."))

        embed_requested = await ctx.embed_requested()

        rendered_cases = [await case.message_content(embed=embed_requested) for case in cases]

        await PagedMenu.send_and_wait(ctx, pages=rendered_cases)

    @commands.command()
    @commands.guild_only()
    async def reason(self, ctx: commands.Context, case: Optional[int], *, reason: str):
        """Specify a reason for a modlog case.

        Please note that you can only edit cases you are
        the owner of unless you are a mod, admin or server owner.

        If no case number is specified, the latest case will be used.
        """
        author = ctx.author
        guild = ctx.guild
        if case is None:
            # get the latest case
            case = int(await modlog.get_next_case_number(guild)) - 1
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
