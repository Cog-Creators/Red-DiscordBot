import discord
from discord.ext import commands
from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.core.config import Config

_ = CogI18n('Permissions', __file__)


class Permissions:
    """
    A high level permission model
    """

    _models = ['owner', 'guildowner', 'admin', 'mod']
    resolution_order = {
        k: _models[:i] for i, k in enumerate(_models, 1)
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )

    async def check_overrides(self, ctx: RedContext, *, level: str) -> bool:
        """
        This checks for any overrides in the permission model

        Parameters
        ----------
        ctx: `redbot.core.context.RedContext`
            The context of the command
        level: `str`
            One of 'owner', 'guildowner', 'admin', 'mod'

        Returns
        -------
        bool
            a trinary value using None + bool to resolve permissions for
            checks.py
        """

        for model in self.resolution_order[level]:
            override = await getattr(self, model + '_model')(ctx)
            if override is not None:
                return override

        return None

    def resolve_lists(self, *, ctx: RedContext,
                      whitelist: list, blacklist: list) -> bool:

        entries = [
            ctx.author.id,
            ctx.channel.id,
        ]
        roles = ctx.author.roles if ctx.guild else []
        entries.extend(
            [x.id for x in roles][::-1]
        )  # @everyone.id == guild.id and roles[0] == @everyone
        for entry in entries:
            if entry in whitelist:
                return True
            if entry in blacklist:
                return False
        else:
            return None

    async def owner_model(self, ctx: RedContext) -> bool:
        """
        Handles owner level overrides
        """

        author = ctx.author
        channel = ctx.channel
        guild = ctx.guild
        cmd_name = ctx.command.qualified_name
        cog_name = ctx.cog.__module__

        if await self.bot.is_owner(author):
            return True

        async with self.config.owner_models() as models:
            if any(
                x in models['blacklist']
                for x in (author.id, guild.id, channel.id)
            ):
                return False
                # corresponding whitelist would be equivalent to co-ownership

            if cmd_name in models['cmds']:
                blacklist = models['cmds'][cmd_name].get('blacklist', [])
                whitelist = models['cmds'][cmd_name].get('whitelist', [])
                resolved = self.resolve_lists(
                    ctx=ctx, whitelist=whitelist, blacklist=blacklist
                )
                if resolved is not None:
                    return resolved

            if cog_name in models['cogs']:
                blacklist = models['cogs'][cmd_name].get('blacklist', [])
                whitelist = models['cogs'][cmd_name].get('whitelist', [])
                resolved = self.resolve_lists(
                    ctx=ctx, whitelist=whitelist, blacklist=blacklist
                )
                if resolved is not None:
                    return resolved
