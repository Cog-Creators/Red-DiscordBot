from copy import copy
import contextlib
import asyncio
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core import checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.caching import LRUDict

from .resolvers import val_if_check_is_valid, resolve_models, entries_from_ctx
from .yaml_handler import yamlset_acl, yamlget_acl
from .converters import CogOrCommand, RuleType, ClearableRuleType
from .mass_resolution import mass_resolve

_models = ["owner", "guildowner", "admin", "mod", "all"]

_ = Translator("Permissions", __file__)

REACTS = {"\N{WHITE HEAVY CHECK MARK}": True, "\N{NEGATIVE SQUARED CROSS MARK}": False}
Y_OR_N = {"y": True, "yes": True, "n": False, "no": False}


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
        self.config.register_global(owner_models={})
        self.config.register_guild(owner_models={})
        self.cache = LRUDict(size=25000)  # This can be tuned later

    async def get_user_ctx_overrides(self, ctx: commands.Context) -> dict:
        """
        This takes a context object, and returns a dict of

        allowed: list of commands
        denied: list of commands
        default: list of commands

        representing how permissions interacts with the
        user, channel, guild, and (possibly) voice channel
        for all commands on the bot (not just the one in the context object)

        This mainly exists for use by the help formatter,
        but others may find it useful

        Unlike the rest of the permission system, if other models are added later,
        due to optimizations made for this, this needs to be adjusted accordingly

        This does not account for before and after permission hooks,
        these need to be checked seperately
        """
        return await mass_resolve(ctx=ctx, config=self.config)

    async def __global_check(self, ctx: commands.Context) -> bool:
        """
        Yes, this is needed on top of hooking into checks.py
        to ensure that unchecked commands can still be managed by permissions
        This should return True in the case of no overrides
        defering to check logic
        This works since all checks must be True to run
        """
        v = await self.check_overrides(ctx, "all")

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
            One of 'owner', 'guildowner', 'admin', 'mod', 'all'

        Returns
        -------
        bool
            a trinary value using None + bool to resolve permissions for
            checks.py
        """
        if await ctx.bot.is_owner(ctx.author):
            return True

        # This block below is a work around for d.py behavior
        # The help formatter needs a work around as well as our checks
        # rely on things not guaranteed to be in commands.Context
        # at the time of check.
        if ctx._internal_view_use is None:
            # discord.py doesn't give checks access to the actual command
            # a user attempted to invoke, This sidesteps that somewhat.
            view = ctx.view
            previous = view.index
            ctx._internal_view_use = ctx.command

            while True:
                view.skip_ws()
                check_next = view.get_word()
                try:
                    possible_command = next(
                        filter(
                            lambda c: check_next in c.aliases or c.name == check_next,
                            ctx._internal_view_use.all_commands.values(),
                        )
                    )
                except (AttributeError, StopIteration):
                    break
                else:
                    ctx._internal_view_use = possible_command

            # restore the view object's state
            view.index = previous
            view.previous = previous

        before = [
            getattr(cog, "_{0.__class__.__name__}__red_permissions_before".format(cog), None)
            for cog in ctx.bot.cogs.values()
        ]
        for check in before:
            if check is None:
                continue
            override = await val_if_check_is_valid(check=check, ctx=ctx, level=level)
            if override is not None:
                return override

        # checked ids + configureable to be checked against
        cache_tup = entries_from_ctx(ctx) + (
            ctx.cog.__class__.__name__,
            ctx._internal_view_use.qualified_name,
        )
        if cache_tup in self.cache:
            override = self.cache[cache_tup]
            if override is not None:
                return override
        else:
            for model in self.resolution_order[level]:
                if ctx.guild is None and model != "owner":
                    break
                override_model = getattr(self, model + "_model", None)
                override = await override_model(ctx) if override_model else None
                if override is not None:
                    self.cache[cache_tup] = override
                    return override
            # This is intentional not being in an else block
            self.cache[cache_tup] = None

        after = [
            getattr(cog, "_{0.__class__.__name__}__red_permissions_after".format(cog), None)
            for cog in ctx.bot.cogs.values()
        ]
        for check in after:
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
        if ctx.guild is None:
            return None
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
        pass

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
            "3. Rules about the text channel a command was issued in.\n"
            "4. Rules about a role the user has "
            "(The highest role they have with a rule will be used).\n"
            "5. Rules about the guild a user is in (Owner level only)."
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
                can = await com.can_run(testcontext) and all(
                    [await p.can_run(testcontext) for p in com.parents]
                )
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
            return await ctx.send(_("You must upload a file."))

        try:
            await yamlset_acl(ctx, config=self.config.owner_models, update=False)
        except Exception as e:
            print(e)
            return await ctx.send(_("Invalid syntax."))
        else:
            await ctx.send(_("Rules set."))
            self.invalidate_cache()

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
            return await ctx.send(_("You must upload a file."))

        try:
            await yamlset_acl(ctx, config=self.config.guild(ctx.guild).owner_models, update=False)
        except Exception as e:
            print(e)
            return await ctx.send(_("Invalid syntax."))
        else:
            await ctx.send(_("Rules set."))
            self.invalidate_cache(ctx.guild.id)

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
            return await ctx.send(_("You must upload a file."))

        try:
            await yamlset_acl(ctx, config=self.config.guild(ctx.guild).owner_models, update=True)
        except Exception as e:
            print(e)
            return await ctx.send(_("Invalid syntax."))
        else:
            await ctx.send(_("Rules set."))
            self.invalidate_cache(ctx.guild.id)

    @checks.is_owner()
    @permissions.command(name="updateglobalacl")
    async def owner_update_acl(self, ctx: commands.Context):
        """
        Take a YAML file upload to update permissions from

        Use this to not lose existing rules
        """
        if not ctx.message.attachments:
            return await ctx.send(_("You must upload a file."))

        try:
            await yamlset_acl(ctx, config=self.config.owner_models, update=True)
        except Exception as e:
            print(e)
            return await ctx.send(_("Invalid syntax."))
        else:
            await ctx.send(_("Rules set."))
            self.invalidate_cache()

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
        Adds something to the rules

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
            return await ctx.send(_("No unique matches. Try using an ID or mention."))
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
        self.invalidate_cache(type_name, obj)

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
        Adds something to the rules

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
            return await ctx.send(_("No unique matches. Try using an ID or mention."))
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
        self.invalidate_cache(type_name, obj)

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
            return await ctx.send(_("No unique matches. Try using an ID or mention."))
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
        self.invalidate_cache(obj, type_name)

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
            return await ctx.send(_("No unique matches. Try using an ID or mention."))
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
        self.invalidate_cache(obj, type_name)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="setdefaultguildrule")
    async def set_default_guild_rule(
        self, ctx: commands.Context, allow_or_deny: ClearableRuleType, cog_or_command: CogOrCommand
    ):
        """
        Sets the default behavior for a cog or command if no rule is set
        """
        val_to_set = {"allow": True, "deny": False, "clear": None}.get(allow_or_deny)

        model_type, type_name = cog_or_command
        async with self.config.guild(ctx.guild).owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}

            data[model_type][type_name]["default"] = val_to_set

            models.update(data)
        await ctx.send(_("Default set."))
        self.invalidate_cache(type_name)

    @checks.is_owner()
    @permissions.command(name="setdefaultglobalrule")
    async def set_default_global_rule(
        self, ctx: commands.Context, allow_or_deny: ClearableRuleType, cog_or_command: CogOrCommand
    ):
        """
        Sets the default behavior for a cog or command if no rule is set
        """
        val_to_set = {"allow": True, "deny": False, "clear": None}.get(allow_or_deny)

        model_type, type_name = cog_or_command
        async with self.config.owner_models() as models:
            data = {k: v for k, v in models.items()}
            if model_type not in data:
                data[model_type] = {}
            if type_name not in data[model_type]:
                data[model_type][type_name] = {}

            data[model_type][type_name]["default"] = val_to_set

            models.update(data)
        await ctx.send(_("Default set."))
        self.invalidate_cache(type_name)

    @checks.is_owner()
    @permissions.command(name="clearglobalsettings")
    async def clear_globals(self, ctx: commands.Context):
        """
        Clears all global rules.
        """
        await self._confirm_then_clear_rules(ctx, is_guild=False)
        self.invalidate_cache()

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="clearguildsettings")
    async def clear_guild_settings(self, ctx: commands.Context):
        """
        Clears all guild rules.
        """
        await self._confirm_then_clear_rules(ctx, is_guild=True)
        self.invalidate_cache(ctx.guild.id)

    async def _confirm_then_clear_rules(self, ctx: commands.Context, is_guild: bool):
        if ctx.guild.me.permissions_in(ctx.channel).add_reactions:
            m = await ctx.send(_("Are you sure?"))
            for r in REACTS.keys():
                await m.add_reaction(r)
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: u == ctx.author and str(r) in REACTS,
                    timeout=30,
                )
            except asyncio.TimeoutError:
                return await ctx.send(_("Ok, try responding with an emoji next time."))

            agreed = REACTS.get(str(reaction))
        else:
            await ctx.send(_("Are you sure? (y/n)"))
            try:
                message = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.content in Y_OR_N,
                    timeout=30,
                )
            except asyncio.TimeoutError:
                return await ctx.send(_("Ok, try responding with yes or no next time."))

            agreed = Y_OR_N.get(message.content.lower())

        if agreed:
            if is_guild:
                await self.config.guild(ctx.guild).owner_models.clear()
                await ctx.send(_("Guild settings cleared."))
            else:
                await self.config.owner_models.clear()
                await ctx.send(_("Global settings cleared."))
        else:
            await ctx.send(_("Okay."))

    def invalidate_cache(self, *to_invalidate):
        """
        Either invalidates the entire cache (if given no objects)
        or does a partial invalidation based on passed objects
        """
        if len(to_invalidate) == 0:
            self.cache.clear()
            return
        # LRUDict inherits from ordered dict, hence the syntax below
        stil_valid = [
            (k, v) for k, v in self.cache.items() if not any(obj in k for obj in to_invalidate)
        ]
        self.cache = LRUDict(stil_valid, size=self.cache.size)

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
            objs.extend(guild.channels)

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
