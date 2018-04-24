import copy
import contextlib

import discord
from discord.ext import commands

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.utils import checks
from redbot.core.i18n import CogI18n
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify

from .resolvers import val_if_check_is_valid, resolve_models
from .ux import build_tables, send

_ = CogI18n('Permissions', __file__)

# TODO: Block of stuff:
# 1. Commands for configuring this
# 2. Commands for displaying permissions (allowed / disallowed/ default)
# 3. Verification of all permission logic (This going wrong is bad)
# 4. API for additional checks


class Permissions:
    """
    A high level permission model
    """

    _models = ['owner', 'guildowner', 'admin', 'mod']
    # Not sure if we will use admin or mod models in core red
    # but they are explicitly supported
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
        self._internal_cache = {}

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

        voice_channel = None
        with contextlib.suppress(Exception):
            voice_channel = ctx.author.voice.voice_channel
        entries = [
            x for x in (ctx.author, voice_channel, ctx.channel) if x
        ]
        roles = sorted(ctx.author.roles, reverse=True) if ctx.guild else []
        entries.extend([x.id for x in roles])
        id_tuple = tuple(entries)

        # never lock out an owner or co-owner
        if await self.bot.is_owner(ctx.author):
            return True

        #  TODO: API for adding these additional checks
        for check in self._before:
            override = await val_if_check_is_valid(check)
            # before overrides should never return True
            if override is False:
                return False

        if self._internal_cache.get(id_tuple, None) is not None:
            return self._internal_cache[id_tuple]

        for model in self.resolution_order[level]:
            override_model = getattr(self, model + '_model', None)
            override = await override_model(ctx) if override_model else None
            self._internal_cache[id_tuple] = override
            if override is not None:
                return override

        for check in self._after:
            override = await val_if_check_is_valid(check)
            if override is not None:
                return override

        return None

    async def owner_model(self, ctx: RedContext) -> bool:
        """
        Handles owner level overrides
        """

        async with self.config.owner_models() as models:
            return resolve_models(ctx=ctx, models=models)

    async def guildowner_model(self, ctx: RedContext) -> bool:
        """
        Handles guild level overrides
        """

        async with self.config.guild(ctx.guild).owner_models() as models:
            return resolve_models(ctx=ctx, models=models)

#   Either of the below function signatures could be used
#   without any other modifications required at a later date
#
#   async def admin_model(self, ctx: RedContext) -> bool:
#   async def mod_model(self, ctx: RedContext) -> bool:

    @commands.group()
    async def permissions(self, ctx: RedContext):
        """
        Permission management tools
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @permissions.command()
    async def explain(self, ctx: RedContext):
        """
        Provides a detailed explanation of how the permission model functions
        """
        # Apologies in advance for the translators out there...

        message = _(
            "This cog extends the default permission model of the bot. "
            "By default, many commands are restricted based on what "
            "the command can do."
            "\n"
            "Any command that could impact the host machine, "
            "is generally owner only."
            "\n"
            "Commands that take administrative or moderator "
            "actions in servers generally require a mod or an admin."
            "\n"
            "This cog allows you to refine some of those settings. "
            "You can allow wider or narrower "
            "access to most commands using it."
            "\n\n"
            "When additional rules are set using this cog, "
            "those rules will be checked prior to "
            "checking for the default restrictions of the command. "
            "\n"
            "Rules set globally (by the owner) are checked first, "
            "then rules set for guilds. If multiple global or guild "
            "rules apply to the case, the order they are checked is:"
            "\n"
            "1. Rules about a user.\n"
            "2. Rules about the voice channel a user is in.\n"
            "3. Rules about the text channel a command was issued in\n"
            "4. Rules about a role the user has "
            "(The highest role they have with a rule will be used)\n"
            "5. Rules about the guild a user is in (Owner level only)"
        )

        await send(ctx, message)

    @permissions.command(name='canrun')
    async def _test_permission_model(
            self, ctx: RedContext, user: discord.User, *, command: str):
        """
        This checks if someone can run a command in the current location
        """

        if not command:
            return await ctx.send_help()

        message = copy(ctx.message)
        message.author = user

        com = self.bot.get_command(command.strip())
        if com is None:
            message = _('No such command')
        else:
            testcontext = await self.bot.get_context(message, cls=RedContext)

            if await com.can_run(testcontext):
                message = _('That user can run the specified command.')
            else:
                message = _('That user can not run the specified command.')

            message += _(
                '\n\nIf this is not what you expected, '
                'you can find what rules apply '
                'to a given situation with the interactive '
                'explorer using `{commandstring}`'
            ).format(commandstring='{0}permissions explore'.format(ctx.prefix))

        await send(ctx, message)

    def object_finder(
            self, ctx: RedContext, info: str, *, _all: bool=False):
        """
        Attempt to uniquely identify an object the bot can see from a str
        """

        objects = []

        if _all or ctx.guild is None:
            _guilds = self.bot.guilds
        else:
            _guilds = [ctx.guild]
        for guild in _guilds:
            objects.extend(
                guild.members
                + guild.channels
                + guild.roles
            )

        try:
            _id = int(info)
        except ValueError:
            obj = None
            _id = -1

        # actual unique stuff first
        obj = discord.utils.find(
            lambda x: x.mention == info or x.id == _id,
            objects
        )

        if obj:
            return obj

        # This should catch User#1234 format
        temp = list(filter(lambda x: str(x) == info, objects))
        if len(temp) == 1:
            return temp[0]

        temp = list(filter(lambda x: x.name == info, objects))
        if len(temp) == 1:
            return temp[0]

        # last ditch effort on unique after case sensitivity removal
        temp = list(filter(
            lambda x: x.name.lower() == info.lower(), objects
        ))
        if len(temp) == 1:
            return temp[0]
        return None

    @permissions.command()
    async def explore(self, ctx: RedContext, command: str, *things: str):
        """
        Permission explorer

        If your command includes spaces, enclose it in quotations

        Things can be a list of mentions or ids to check
        """

        com = self.bot.get_command(command)
        if com is None:
            return await send(
                ctx, _('No such command')
            )

        m = copy(ctx.message)
        m.content = com
        fctx = await self.bot.get_context(m, cls=RedContext)

        _objs = [
            self.object_finder(v) for v in things
        ]
        try:
            ids = [o.id for o in _objs]
        except AttributeError:
            return await send(
                ctx,
                _("I could not find one or more of those, "
                  "please try again with ids")
            )

        async with self.config.owner_models() as models:
            o_val, o_info = resolve_models(
                ctx=fctx, models=models, debug=True, debug_ids=ids
            )

        if ctx.guild:
            async with self.config.guild(ctx.guild).owner_models() as models:
                g_val, g_res = resolve_models(
                    ctx=fctx, models=models, debug=True, debug_ids=ids
                )
        else:
            g_val, g_info = None, []

        allowance = o_val if o_val is not None else g_val
        if allowance is None:
            return await send(
                send,
                _("This command's allowed usage is not modified "
                  "for any of these ids by the core permission cog")
            )

        msg = build_tables(_objs, o_info, guild=g_info)

        for page in pagify(msg):
            await send(ctx, msg)
