from copy import copy
import contextlib
import asyncio
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core import checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n

from .resolvers import val_if_check_is_valid, resolve_models
from .yaml_handler import yamlset_acl, yamlget_acl
from .converters import CogOrCommand, RuleType

_models = ["owner", "guildowner", "admin", "mod"]

_ = Translator("Permissions", __file__)

REACTS = {"\N{WHITE HEAVY CHECK MARK}": True, "\N{NEGATIVE SQUARED CROSS MARK}": False}


@cog_i18n(_)
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

    def add_check(self, check_obj: object, before_or_after: str):
        """
        adds a check to the check ordering

        checks should be a function taking 2 arguments:
        ctx: commands.Context
        level: str

        and returning:
        None: do not interfere
        True: command should be allowed even if they dont
            have role or perm requirements for the check
        False: command should be blocked

        before_or_after:
        Should literally be a str equaling 'before' or 'after'
        This should be based on if this should take priority
        over set rules or not

        3rd party cogs adding checks using this should only allow
        the owner to add checks before, and ensure only the owner
        can add checks recieving the level 'owner'

        3rd party cogs should keep a copy of of any checks they registered
        and deregister then on unload
        """

        if before_or_after == "before":
            self._before.append(check_obj)
        elif before_or_after == "after":
            self._after.append(check_obj)
        else:
            raise TypeError("RTFM")

    def remove_check(self, check_obj: object, before_or_after: str):
        """
        removes a previously registered check object

        3rd party cogs should keep a copy of of any checks they registered
        and deregister then on unload
        """

        if before_or_after == "before":
            self._before.remove(check_obj)
        elif before_or_after == "after":
            self._after.remove(check_obj)
        else:
            raise TypeError("RTFM")

    async def __global_check(self, ctx):
        """
        Yes, this is needed on top of hooking into checks.py
        to ensure that unchecked commands can still be managed by permissions
        This should return True in the case of no overrides
        defering to check logic
        This works since all checks must be True to run
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

        for check in self._before:
            override = await val_if_check_is_valid(check=check, ctx=ctx, level=level)
            if override is not None:
                return override

        for model in self.resolution_order[level]:
            override_model = getattr(self, model + "_model", None)
            override = await override_model(ctx) if override_model else None
            if override is not None:
                return override

        for check in self._after:
            override = await val_if_check_is_valid(check=check, ctx=ctx, level=level)
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

    @commands.group(aliases=["p"])
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
        await ctx.send(out)

    @checks.is_owner()
    @permissions.command(name="setglobalacl")
    async def owner_set_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to set permissions from
        """
        if not ctx.message.attachments:
            return await ctx.send(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.owner_models, update=False)
        except Exception as e:
            print(e)
            return await ctx.send(_("Inalid syntax"))
        else:
            await ctx.send(_("Rules set."))

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
            return await ctx.send(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.guild(ctx.guild).owner_models, update=False)
        except Exception as e:
            print(e)
            return await ctx.send(_("Inalid syntax"))
        else:
            await ctx.send(_("Rules set."))

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
            return await ctx.send(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.guild(ctx.guild).owner_models, update=True)
        except Exception as e:
            print(e)
            return await ctx.send(_("Inalid syntax"))
        else:
            await ctx.send(_("Rules set."))

    @checks.is_owner()
    @permissions.command(name="updateglobalacl")
    async def owner_update_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to update permissions from

        Use this to not lose existing rules
        """
        if not ctx.message.attachments:
            return await ctx.send(_("You must upload a file"))

        try:
            await yamlset_acl(ctx, config=self.config.owner_models, update=True)
        except Exception as e:
            print(e)
            return await ctx.send(_("Inalid syntax"))
        else:
            await ctx.send(_("Rules set."))

    @checks.is_owner()
    @permissions.command(name="addglobalrule")
    async def add_to_global_rule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: str,
    ):
        """
        adds something to the rules

        allow_or_deny: "allow" or "deny", depending on the rule to modify

        cog_or_command: case sensitive cog or command name
        nested commands should be space seperated, but enclosed in quotes

        who_or_what: what to add to the rule list.
        For best results, use an ID or mention
        The bot will try to uniquely match even without,
        but a failure to do so will raise an error
        This can be a user, role, channel, or guild
        """
        obj = self.find_object_uniquely(who_or_what)
        if not obj:
            return await ctx.send(_("No unique matches. Try using an ID or mention"))
        model_type, type_name = cog_or_command
        async with self.config.owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}
            if allow_or_deny not in data[model_type][type_name]:
                data[model_type][type_name][allow_or_deny] = []

            if obj in data[model_type][type_name][allow_or_deny]:
                return await ctx.send(_("That rule already exists."))

            data[model_type][type_name][allow_or_deny].append(obj)
            models.update(data)
        await ctx.send(_("Rule added."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="addguildrule")
    async def add_to_guild_rule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: str,
    ):
        """
        adds something to the rules

        allow_or_deny: "allow" or "deny", depending on the rule to modify

        cog_or_command: case sensitive cog or command name
        nested commands should be space seperated, but enclosed in quotes

        who_or_what: what to add to the rule list.
        For best results, use an ID or mention
        The bot will try to uniquely match even without,
        but a failure to do so will raise an error
        This can be a user, role, channel, or guild
        """
        obj = self.find_object_uniquely(who_or_what)
        if not obj:
            return await ctx.send(_("No unique matches. Try using an ID or mention"))
        model_type, type_name = cog_or_command
        async with self.config.guild(ctx.guild).owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}
            if allow_or_deny not in data[model_type][type_name]:
                data[model_type][type_name][allow_or_deny] = []

            if obj in data[model_type][type_name][allow_or_deny]:
                return await ctx.send(_("That rule already exists."))

            data[model_type][type_name][allow_or_deny].append(obj)
            models.update(data)
        await ctx.send(_("Rule added."))

    @checks.is_owner()
    @permissions.command(name="removeglobalrule")
    async def rem_from_global_rule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: str,
    ):
        """
        removes something from the rules

        allow_or_deny: "allow" or "deny", depending on the rule to modify

        cog_or_command: case sensitive cog or command name
        nested commands should be space seperated, but enclosed in quotes

        who_or_what: what to add to the rule list.
        For best results, use an ID or mention
        The bot will try to uniquely match even without,
        but a failure to do so will raise an error
        This can be a user, role, channel, or guild
        """
        obj = self.find_object_uniquely(who_or_what)
        if not obj:
            return await ctx.send(_("No unique matches. Try using an ID or mention"))
        model_type, type_name = cog_or_command
        async with self.config.owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}
            if allow_or_deny not in data[model_type][type_name]:
                data[model_type][type_name][allow_or_deny] = []

            if obj not in data[model_type][type_name][allow_or_deny]:
                return await ctx.send(_("That rule doesn't exist."))

            data[model_type][type_name][allow_or_deny].remove(obj)
            models.update(data)
        await ctx.send(_("Rule removed."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="removeguildrule")
    async def rem_from_guild_rule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: str,
    ):
        """
        removes something from the rules

        allow_or_deny: "allow" or "deny", depending on the rule to modify

        cog_or_command: case sensitive cog or command name
        nested commands should be space seperated, but enclosed in quotes

        who_or_what: what to add to the rule list.
        For best results, use an ID or mention
        The bot will try to uniquely match even without,
        but a failure to do so will raise an error
        This can be a user, role, channel, or guild
        """
        obj = self.find_object_uniquely(who_or_what)
        if not obj:
            return await ctx.send(_("No unique matches. Try using an ID or mention"))
        model_type, type_name = cog_or_command
        async with self.config.guild(ctx.guild).owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}
            if allow_or_deny not in data[model_type][type_name]:
                data[model_type][type_name][allow_or_deny] = []

            if obj not in data[model_type][type_name][allow_or_deny]:
                return await ctx.send(_("That rule doesn't exist."))

            data[model_type][type_name][allow_or_deny].remove(obj)
            models.update(data)
        await ctx.send(_("Rule removed."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="setdefaultguildrule")
    async def set_default_guild_rule(
        self, ctx: commands.Context, cog_or_command: CogOrCommand, allow_or_deny: RuleType = None
    ):
        """
        Sets the default behavior for a cog or command if no rule is set

        Use with a cog or command and no setting to clear the default and defer to
        normal check logic
        """
        if allow_or_deny:
            val_to_set = {"allow": True, "deny": False}.get(allow_or_deny)
        else:
            val_to_set = None

        model_type, type_name = cog_or_command
        async with self.config.guild(ctx.guild).owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}

            data[model_type][type_name]["default"] = val_to_set

            models.update(data)
        await ctx.send(_("Defualt set."))

    @checks.is_owner()
    @permissions.command(name="setdefaultglobalrule")
    async def set_default_global_rule(
        self, ctx: commands.Context, cog_or_command: CogOrCommand, allow_or_deny: RuleType = None
    ):
        """
        Sets the default behavior for a cog or command if no rule is set

        Use with a cog or command and no setting to clear the default and defer to
        normal check logic
        """

        if allow_or_deny:
            val_to_set = {"allow": True, "deny": False}.get(allow_or_deny)
        else:
            val_to_set = None

        model_type, type_name = cog_or_command
        async with self.config.owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}

            data[model_type][type_name]["default"] = val_to_set

            models.update(data)
        await ctx.send(_("Defualt set."))

    @commands.bot_has_permissions(add_reactions=True)
    @checks.is_owner()
    @permissions.command(name="clearglobalsettings")
    async def clear_globals(self, ctx: commands.Context):
        """
        Clears all global rules.
        """

        m = await ctx.send("Are you sure?")
        for r in REACTS.keys():
            await m.add_reaction(r)
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", check=lambda r, u: u == ctx.author and str(r) in REACTS, timeout=30
            )
        except asyncio.TimeoutError:
            return await ctx.send(_("Ok, try responding with an emoji next time."))

        if REACTS.get(str(reaction)):
            await self.config.owner_models.clear()
            await ctx.send(_("Global settings cleared"))
        else:
            await ctx.send(_("Okay."))

    @commands.bot_has_permissions(add_reactions=True)
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="clearguildsettings")
    async def clear_guild_settings(self, ctx: commands.Context):
        """
        Clears all guild rules.
        """

        m = await ctx.send("Are you sure?")
        for r in REACTS.keys():
            await m.add_reaction(r)
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", check=lambda r, u: u == ctx.author and str(r) in REACTS, timeout=30
            )
        except asyncio.TimeoutError:
            return await ctx.send(_("Ok, try responding with an emoji next time."))

        if REACTS.get(str(reaction)):
            await self.config.guild(ctx.guild).owner_models.clear()
            await ctx.send(_("Guild settings cleared"))
        else:
            await ctx.send(_("Okay."))

    def find_object_uniquely(self, info: str) -> int:
        """
        Finds an object uniquely, returns it's id or returns None
        """
        if info is None:
            return None
        objs = []

        objs.extend(self.bot.users)
        for guild in self.bot.guilds:
            objs.extend(guild.roles)

        try:
            _id = int(info)
        except ValueError:
            _id = None

        for function in (
            lambda x: x.id == _id,
            lambda x: x.mention == info,
            lambda x: str(x) == info,
            lambda x: x.name == info,
            lambda x: (x.nick if hasattr(x, "nick") else None) == info,
        ):
            canidates = list(filter(function, objs))
            if len(canidates) == 1:
                return canidates[0].id

        return None
