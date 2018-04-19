import asyncio
import contextlib
import types

import discord
from discord.ext import commands

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.core.config import Config

_ = CogI18n('Permissions', __file__)

# TODO: Block of stuff:
# 1. Commands for configuring this
# 2. Commands for displaying permissions (allowed / disallowed/ default)
# 3. Verification of all permission logic (This going wrong is bad)
# 4. Very strong user facing warnings if trying to widen access to
#    cog install / load
# 5. API for additional checks


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
        self._before = []
        self._after = []

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

        # never lock out an owner or co-owner
        if await self.bot.is_owner(ctx.author):
            return True

        # At this point, the person the override exists for should
        # just be a co-owner.
        if ctx.command.qualified_name in ('repl', 'debug', 'eval'):
            return None

        #  TODO: API for adding these additional checks
        for check in self._before:
            override = await self.val_if_check_is_valid(check)
            if override is not None:
                return override

        for model in self.resolution_order[level]:
            override_model = getattr(self, model + '_model', None)
            override = await override_model(ctx) if override_model else None
            if override is not None:
                return override

        for check in self._after:
            override = await self.val_if_check_is_valid(check)
            if override is not None:
                return override

        return None

    @staticmethod
    async def val_if_check_is_valid(
            *, ctx: RedContext, check: object, level: str) -> bool:
        """
        Returns the value from a check if it is valid
        """

        # Non staticmethods should not be run without their parent
        # class, even if the parent class did not deregister them
        if isinstance(check, types.FunctionType):
            if next(
                filter(
                    lambda x: check.__module__ == x.__module__,
                    ctx.bot.cogs
                    ), None) is None:
                return None

        # support both sync and async funcs, because why not
        # also, supress errors because we can't check know what
        # third party checks might raise if improperly made
        with contextlib.suppress(Exception):
            val = None
            if asyncio.iscoroutine(check) \
                    or asyncio.iscoroutinefunction(check):
                val = await check(ctx, level=level)
            else:
                val = check(ctx, level=level)

        return val

    def resolve_models(self, *, ctx: RedContext, models: dict) -> bool:

        cmd_name = ctx.command.qualified_name
        cog_name = ctx.cog.__module__

        blacklist = models.get('blacklist', [])
        whitelist = models.get('whitelist', [])
        resolved = self.resolve_lists(
            ctx=ctx, whitelist=whitelist, blacklist=blacklist
        )
        if resolved is not None:
            return resolved

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

        # default
        return None

    def resolve_lists(self, *, ctx: RedContext,
                      whitelist: list, blacklist: list) -> bool:

        voice_channel = None
        with contextlib.suppress(Exception):
            voice_channel = ctx.author.voice.voice_channel

        entries = [
            x for x in (ctx.author, voice_channel, ctx.channel) if x
        ]
        roles = sorted(ctx.author.roles, reverse=True) if ctx.guild else []
        entries.extend([x.id for x in roles])
        # entries now contains the following (in order) (if applicable)
        # author.id
        # author.voice.voice_channel.id
        # channel.id
        # role.id for each role (highest to lowest)
        # (implicitly) guild.id because
        #     the @everyone role shares an id with the guild

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

        async with self.config.owner_models() as models:
            return self.resolve_models(ctx=ctx, models=models)

    async def guildowner_model(self, ctx: RedContext) -> bool:
        """
        Handles guild level overrides
        """

        async with self.config.guild(ctx.guild).owner_models() as models:
            return self.resolve_models(ctx=ctx, models=models)
