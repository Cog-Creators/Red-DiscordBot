import discord
from discord.ext import commands

from redbot.core import checks, modlog
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import box

_ = CogI18n('ModLog', __file__)


class ModLog:
    """Log for mod actions"""

    def __init__(self, bot: Red):
        self.bot = bot

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
                await modlog.set_modlog_channel(guild, channel)
                await ctx.send(
                    _("Mod events will be sent to {}").format(
                        channel.mention
                    )
                )
            else:
                await ctx.send(
                    _("I do not have permissions to "
                      "send messages in {}!").format(channel.mention)
                )
        else:
            try:
                await modlog.get_modlog_channel(guild)
            except RuntimeError:
                await self.bot.send_cmd_help(ctx)
            else:
                await modlog.set_modlog_channel(guild, None)
                await ctx.send(_("Mod log deactivated."))

    @modlogset.command(name='cases')
    @commands.guild_only()
    async def set_cases(self, ctx: commands.Context, action: str = None):
        """Enables or disables case creation for each type of mod action

        Enabled can be 'on' or 'off'"""
        guild = ctx.guild

        if action is None:  # No args given
            casetypes = await modlog.get_all_casetypes()
            await self.bot.send_cmd_help(ctx)
            title = _("Current settings:")
            msg = ""
            for key in casetypes:
                enabled = await modlog.get_case_type_status(key, guild)
                value = 'enabled' if enabled else 'disabled'
                msg += '%s : %s\n' % (key, value)

            msg = title + "\n" + box(msg)
            await ctx.send(msg)

        elif not await modlog.is_casetype(action):
            await ctx.send(_("That action is not registered"))

        else:

            new_setting = await modlog.toggle_case_type(action, guild)

            msg = (
                _('Case creation for {} actions is now {}.').format(
                    action, 'enabled' if new_setting else 'disabled'
                )
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
            await ctx.send(_("That case does not exist for that guild"))
            return
        else:
            await ctx.send(embed=await case.get_case_msg_content())

    @commands.command()
    @commands.guild_only()
    async def reason(self, ctx: commands.Context, case: int, *, reason: str = ""):
        """Lets you specify a reason for mod-log's cases"""
        author = ctx.author
        guild = ctx.guild
        if not reason:
            await self.bot.send_cmd_help(ctx)
            return
        try:
            case_before = await modlog.get_case(case, guild, self.bot)
        except RuntimeError:
            await ctx.send(_("That case does not exist!"))
            return
        else:
            is_guild_owner = author == guild.owner
            is_case_author = author == case_before.moderator
            author_is_mod = await ctx.bot.is_mod(author)
            if not (is_guild_owner or is_case_author or author_is_mod):
                await ctx.send(_("You are not authorized to modify that case!"))
                return
            to_modify = {
                "reason": reason,
            }
            if case_before.moderator != author:
                to_modify["amended_by"] = author
                to_modify["modified_at"] = ctx.message.created_at.timestamp()
            case = await modlog.edit_case(case, guild, self.bot, to_modify)
            await ctx.send(_("Reason has been updated."))
