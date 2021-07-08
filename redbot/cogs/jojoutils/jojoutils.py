"""
This doesn't have a license just because I own this code and I don't care to put one in here.
This kinda only works for me soo yeah
"""

import discord

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box

import json
from datetime import datetime
from .converters import BotUser


_config = {
    "denyed_bots": {}
}


class JojoUtils(commands.Cog):
    """Various utilities for Jojo"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 544974305445019651, True)
        self.config.register_global(**_config)

    async def red_delete_data_for_user(self, *args):
        return

    @commands.command()
    @commands.is_owner()
    @commands.check(lambda c: c.guild.id == 696461072101539961)
    async def unwait(self, ctx: commands.Context, user: discord.Member):
        """Unwait a member"""
        waiting_role = ctx.guild.get_role(832798336036896829)
        if waiting_role.id not in user._roles:
            return await ctx.send("That user is not waiting.")

        roles = [ctx.guild.get_role(id) for id in (719645857716240465, 785279135953453077)]
        try:
            await user.remove_roles(waiting_role, reason="Unwaited by Jojo")
        except discord.Forbidden:
            await ctx.send("I could not remove that user's waiting role.")
        try:
            await user.add_roles(*roles, reason="Unwaited by Jojo")
        except discord.Forbidden:
            await ctx.send("I could not add that user's sky blue and safe people roles.")
        await ctx.tick()

    @commands.command()
    async def getrawembedtext(self, ctx: commands.Context, message: discord.Message):
        """Get the raw data of an embed from a message"""

        if not message.embeds:
            return await ctx.send("That message does not have any embeds")
        embed = message.embeds[0]
        data = json.dumps(embed.to_dict(), indent=4, sort_keys=True)
        await ctx.send(f"Here is your raw embed data: {box(data, 'json')}")

    @commands.command()
    async def getescapedtext(self, ctx: commands.Context, message: discord.Message):
        """Get the raw text of a message"""

        await ctx.send(discord.utils.escape_markdown(message.content))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if any([message.author.bot, not message.guild, message.guild.id != 696461072101539961]):
            return
        log_channel = message.guild.get_channel(827255649171013632)
        embed = discord.Embed(
            title=f"Deleted message by {message.author.name} ({message.author.id})",
            description=message.content,
            colour=0x00ffff,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
        embed.set_thumbnail(url=message.author.avatar_url)
        await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.check(lambda c: c.guild.id == 744572173137477692)
    @commands.admin_or_permissions(administrator=True)
    async def removebotperms(self, ctx: commands.Context, bot: BotUser):
        """Remove the bots role and add the removed perms bot role"""

        perms_denyed_role = ctx.guild.get_role(810845790532403201)

        if perms_denyed_role.id in bot._roles:
            return await ctx.send("That bot already has restricted permissions.")
        bot_role = ctx.guild.get_role(759697876342276117)
        staff_bot_role = ctx.guild.get_role(760519519109120040)
        has_staffbot_role = staff_bot_role in bot._roles

        reason = f"Requested by {ctx.author.name} ({ctx.author.id})"
        try:
            await bot.remove_roles(bot_role, reason=reason)
        except discord.Forbidden:
            await ctx.tick(cross=True)
            return await ctx.send("I lack permissions to remove roles")
        if has_staffbot_role:
            await bot.remove_roles(bot_role, reason=reason)
        await bot.add_roles(perms_denyed_role, reason=reason)
        await ctx.tick()
        await ctx.send(f"Done. {bot.name} now has permissions denyed.")
        async with self.config.denyed_bots() as db:
            db[bot.id] = has_staffbot_role # Store true or false

    @commands.command()
    @commands.guild_only()
    @commands.check(lambda c: c.guild.id == 744572173137477692)
    @commands.admin_or_permissions(administrator=True)
    async def addbotperms(self, ctx: commands.Context, bot: BotUser):
        """Add a bot's permissions again"""

        denyed_bot_role = ctx.guild.get_role(810845790532403201)
        async with self.config.denyed_bots() as db:
            found = db.pop(bot.id, None) # remove it from the database
        if found is None and denyed_bot_role not in bot._roles:
            return await ctx.send("That bot does not have the denyed permissions role.")

        reason = f"Requested by {ctx.author.name} ({ctx.author.id})"
        bot_role = ctx.guild.get_role(759697876342276117)
        if found:
            staff_bot_role = ctx.guild.get_role(760519519109120040)

        try:
            await bot.remove_roles(denyed_bot_role, reason=reason)
        except discord.Forbidden:
            await ctx.tick(cross=True)
            return await ctx.send("I lack permissions to remove roles.")

        roles = [bot_role] + ([staff_bot_role] if found else [])
        await bot.add_roles(*roles, reason=reason)
        await ctx.tick()
        await ctx.send(f"Done. {bot.name} now has its permissions back.")
