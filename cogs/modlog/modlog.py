import discord
from discord.ext import commands

from core import checks, modlog
from core.bot import Red


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
                await modlog.set_modlog_channel(channel)
                await ctx.send("Mod events will be sent to {}"
                               "".format(channel.mention))
            else:
                await ctx.send(
                    "I do not have permissions to "
                    "send messages in {}!".format(channel.mention)
                )
        else:
            if await modlog.get_modlog_channel(guild) is None:
                await self.bot.send_cmd_help(ctx)
                return
            await modlog.set_modlog_channel(None)
            await ctx.send("Mod log deactivated.")

    @modlogset.command(name='cases')
    @commands.guild_only()
    async def set_cases(self, ctx: commands.Context, action: str = None):
        """Enables or disables case creation for each type of mod action

        Enabled can be 'on' or 'off'"""
        guild = ctx.guild

        if action is None:  # No args given
            casetypes = await modlog.get_all_casetypes()
            await self.bot.send_cmd_help(ctx)
            msg = "Current settings:\n```\n"
            for key in casetypes:
                enabled = await modlog.get_case_type_status(key, guild)
                value = 'enabled' if enabled else 'disabled'
                msg += '%s : %s\n' % (key, value)

            msg += '```'
            await ctx.send(msg)

        elif not await modlog.is_casetype(action):
            await ctx.send("That action is not registered")

        else:

            new_setting = await modlog.toggle_case_type(action, guild)

            msg = (
                'Case creation for %s actions %s %s.' %
                (action, 'is now', 'enabled' if new_setting else 'disabled')
            )
            await ctx.send(msg)

    @modlogset.command()
    @commands.guild_only()
    async def resetcases(self, ctx: commands.Context):
        """Resets modlog's cases"""
        guild = ctx.guild
        await modlog.reset_cases(guild)
        await ctx.send("Cases have been reset.")

    @commands.command()
    @commands.guild_only()
    async def case(self, ctx: commands.Context, number: int):
        """Shows the specified case"""
        try:
            case = await modlog.get_case(number, ctx.guild, self.bot)
        except RuntimeError:
            await ctx.send("That case does not exist for that guild")
        else:
            await ctx.send(embed=await case.get_case_msg_content())

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
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
            await ctx.send("That case does not exist!")
            return
        to_modify = {
            "reason": reason,
        }
        if case_before.moderator != author:
            to_modify["amended_by"] = author
            to_modify["modified_at"] = ctx.message.created_at.timestamp()
        case = await modlog.edit_case(case, guild, self.bot, to_modify)
