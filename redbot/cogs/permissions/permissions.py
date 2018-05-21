from copy import copy
import contextlib

import discord
from redbot.core import commands

from redbot.core.bot import Red
from redbot.core import checks
from redbot.core.config import Config

from .resolvers import val_if_check_is_valid, resolve_models
from .yaml_handler import yamlset_acl, yamlget_acl

_models = ["owner", "guildowner", "admin", "mod"]

_ = lambda x: x


class Permissions:
    """
    A high level permission model
    """

    # Not sure if we will use admin or mod models in core red
    # but they are explicitly supported
    resolution_order = {k: _models[:i] for i, k in enumerate(_models, 1)}

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631113035100160, force_registration=True)
        self._before = []
        self._after = []
        self.config.register_global(owner_models={})
        self.config.register_guild(owner_models={})

    async def __global_check(self, ctx):
        """
        Yes, this is needed on top of hooking into checks.py
        to ensure that unchecked commands can still be managed by permissions
        This should return True in the case of no overrides
        defering to check logic
        This works since all checks must be True to run
        It's also part of why the caching layer is needed
        """
        v = await self.check_overrides(ctx, "mod")

        if v is False:
            return False
        return True

    async def check_overrides(self, ctx: commands.Context, level: str) -> bool:
        """
        This checks for any overrides in the permission model

        Parameters
        ----------
        ctx: `redbot.core.context.commands.Context`
            The context of the command
        level: `str`
            One of 'owner', 'guildowner', 'admin', 'mod'

        Returns
        -------
        bool
            a trinary value using None + bool to resolve permissions for
            checks.py
        """
        if await ctx.bot.is_owner(ctx.author):
            return True
        voice_channel = None
        with contextlib.suppress(Exception):
            voice_channel = ctx.author.voice.voice_channel
        entries = [x for x in (ctx.author, voice_channel, ctx.channel) if x]
        roles = sorted(ctx.author.roles, reverse=True) if ctx.guild else []
        entries.extend([x.id for x in roles])

        #  TODO: API for adding these additional checks
        for check in self._before:
            override = await val_if_check_is_valid(check)
            # before overrides should never return True
            if override is False:
                return False

        for model in self.resolution_order[level]:
            override_model = getattr(self, model + "_model", None)
            override = await override_model(ctx) if override_model else None
            if override is not None:
                return override

        for check in self._after:
            override = await val_if_check_is_valid(check)
            if override is not None:
                return override

        return None

    async def owner_model(self, ctx: commands.Context) -> bool:
        """
        Handles owner level overrides
        """

        async with self.config.owner_models() as models:
            return resolve_models(ctx=ctx, models=models)

    async def guildowner_model(self, ctx: commands.Context) -> bool:
        """
        Handles guild level overrides
        """

        async with self.config.guild(ctx.guild).owner_models() as models:
            return resolve_models(ctx=ctx, models=models)

    #   Either of the below function signatures could be used
    #   without any other modifications required at a later date
    #
    #   async def admin_model(self, ctx: commands.Context) -> bool:
    #   async def mod_model(self, ctx: commands.Context) -> bool:

    @commands.group()
    async def permissions(self, ctx: commands.Context):
        """
        Permission management tools
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @permissions.command()
    async def explain(self, ctx: commands.Context):
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
            "\n\nFor more details, please read the official documentation."
        )

        await ctx.maybe_send_embed(message)

    @permissions.command(name="canrun")
    async def _test_permission_model(
        self, ctx: commands.Context, user: discord.Member, *, command: str
    ):
        """
        This checks if someone can run a command in the current location
        """

        if not command:
            return await ctx.send_help()

        message = copy(ctx.message)
        message.author = user
        message.content = "{}{}".format(ctx.prefix, command)

        com = self.bot.get_command(command)
        if com is None:
            out = _("No such command")
        else:
            try:
                testcontext = await self.bot.get_context(message, cls=commands.Context)
                can = await com.can_run(testcontext)
            except commands.CheckFailure:
                can = False

            out = (
                _("That user can run the specified command.")
                if can
                else _("That user can not run the specified command.")
            )
        await ctx.maybe_send_embed(out)

    @checks.is_owner()
    @permissions.command(name="setglobalacl")
    async def owner_set_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to set permissions from
        """
        if not ctx.message.attachments:
            return await ctx.maybe_send_embed(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.owner_models, update=False)
        except Exception as e:
            print(e)
            return await ctx.maybe_send_embed(_("Inalid syntax"))
        else:
            await ctx.tick()

    @checks.is_owner()
    @permissions.command(name="getglobalacl")
    async def owner_get_acl(self, ctx: commands.Context):
        """
        Dumps a YAML file with the current owner level permissions
        """
        await yamlget_acl(ctx, config=self.config.owner_models)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="setguildacl")
    async def guild_set_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to set permissions from
        """
        if not ctx.message.attachments:
            return await ctx.maybe_send_embed(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.guild(ctx.guild).owner_models, update=False)
        except Exception as e:
            print(e)
            return await ctx.maybe_send_embed(_("Inalid syntax"))
        else:
            await ctx.tick()

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="getguildacl")
    async def guild_get_acl(self, ctx: commands.Context):
        """
        Dumps a YAML file with the current owner level permissions
        """
        await yamlget_acl(ctx, config=self.config.guild(ctx.guild).owner_models)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="updateguildacl")
    async def guild_update_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to update permissions from
        
        Use this to not lose existing rules
        """
        if not ctx.message.attachments:
            return await ctx.maybe_send_embed(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.guild(ctx.guild).owner_models, update=True)
        except Exception as e:
            print(e)
            return await ctx.maybe_send_embed(_("Inalid syntax"))
        else:
            await ctx.tick()

    @checks.is_owner()
    @permissions.command(name="updateglobalacl")
    async def owner_update_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to set permissions from

        Use this to not lose existing rules
        """
        if not ctx.message.attachments:
            return await ctx.maybe_send_embed(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.owner_models, update=True)
        except Exception as e:
            print(e)
            return await ctx.maybe_send_embed(_("Inalid syntax"))
        else:
            await ctx.tick()
