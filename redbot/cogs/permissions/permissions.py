import asyncio
from copy import copy
from typing import Union, Optional, Dict, List, Tuple, Any, Iterator, ItemsView

import discord
from redbot.core import checks, commands, config
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n

from .yaml_handler import yamlset_acl, yamlget_acl
from .converters import CogOrCommand, RuleType, ClearableRuleType

_ = Translator("Permissions", __file__)

COG = "COG"
COMMAND = "COMMAND"
GLOBAL = 0

REACTS = {"\N{WHITE HEAVY CHECK MARK}": True, "\N{NEGATIVE SQUARED CROSS MARK}": False}
Y_OR_N = {"y": True, "yes": True, "n": False, "no": False}

__version__ = "1.0.0"


@cog_i18n(_)
class Permissions(commands.Cog):
    """Customise permissions for commands and cogs."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        # Config Schema:
        # "COG"
        # -> Cog names...
        #   -> Guild IDs...
        #     -> Model IDs...
        #       -> True|False
        #   -> "global"
        #     -> Model IDs...
        #       -> True|False
        # "COMMAND"
        # -> Command names...
        #   -> Guild IDs...
        #     -> Model IDs...
        #       -> True|False
        #   -> "global"
        #     -> Model IDs...
        #       -> True|False
        self.config = config.Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(version="")
        self.config.register_custom(COG)
        self.config.register_custom(COMMAND)

    async def initialize(self) -> None:
        """Initialize this cog.

        This will load all rules from config onto every currently
        loaded command.
        """
        await self._maybe_update_schema()

        for category, getter in ((COG, self.bot.get_cog), (COMMAND, self.bot.get_command)):
            all_rules = await self.config.custom(category).all()
            for name, rules in all_rules.items():
                obj = getter(name)
                if obj is None:
                    continue
                self._load_rules_for(obj, rules)

    @commands.group(aliases=["p"])
    async def permissions(self, ctx: commands.Context):
        """Command permission management tools."""
        pass

    @permissions.command(name="explain")
    async def permissions_explain(self, ctx: commands.Context):
        """Explain how permissions works. """
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
    async def permissions_canrun(
        self, ctx: commands.Context, user: discord.Member, *, command: str
    ):
        """Check if a user can run a command.

        This will take the current context into account, such as the
        server and text channel.
        """

        if not command:
            return await ctx.send_help()

        message = copy(ctx.message)
        message.author = user
        message.content = "{}{}".format(ctx.prefix, command)

        com = ctx.bot.get_command(command)
        if com is None:
            out = _("No such command")
        else:
            try:
                testcontext = await ctx.bot.get_context(message, cls=commands.Context)
                to_check = [*reversed(com.parents)] + [com]
                can = False
                for cmd in to_check:
                    can = await cmd.can_run(testcontext)
                    if can is False:
                        break
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
    async def permissions_setglobalacl(self, ctx: commands.Context):
        """Set global rules with a YAML file.

        **WARNING**: This will override reset *all* global rules
        to the rules specified in the uploaded file.
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
    async def permissions_getglobalacl(self, ctx: commands.Context):
        """Get a YAML file detailing all global rules."""
        await yamlget_acl(ctx, config=self.config.owner_models)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="setserveracl", aliases=["setguildacl"])
    async def permissions_setguildacl(self, ctx: commands.Context):
        """Set rules for this server with a YAML file.

        **WARNING**: This will override reset *all* rules in this
        server to the rules specified in the uploaded file.
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
    @permissions.command(name="getserveracl", aliases=["getguildacl"])
    async def permissions_getguildacl(self, ctx: commands.Context):
        """Get a YAML file detailing all rules in this server."""
        await yamlget_acl(ctx, config=self.config.guild(ctx.guild).owner_models)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="updateserveracl", aliases=["updateguildacl"])
    async def permissions_updateguildacl(self, ctx: commands.Context):
        """Update rules for this server with a YAML file.

        This won't touch any rules not specified in the YAML
        file.
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
    async def permissions_updateglobalacl(self, ctx: commands.Context):
        """Update global rules with a YAML file.

        This won't touch any rules not specified in the YAML
        file.
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
    async def permissions_addglobalrule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: commands.GlobalPermissionModel,
    ):
        """Add a global rule to a command.

        `<allow_or_deny>` should be one of "allow" or "deny".

        `<cog_or_command>` is the cog or command to add the rule to.
        This is case sensitive.

        `<who_or_what>` is the user, channel, role or server the rule
        is for.
        """
        # noinspection PyTypeChecker
        await self._add_rule(
            rule=allow_or_deny, cog_or_cmd=cog_or_command, model_id=who_or_what.id, guild_id=0
        )
        await ctx.send(_("Rule added."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="addserverrule", aliases=["addguildrule"])
    async def permissions_addguildrule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: commands.GuildPermissionModel,
    ):
        """Add a rule to a command in this server.

        `<allow_or_deny>` should be one of "allow" or "deny".

        `<cog_or_command>` is the cog or command to add the rule to.
        This is case sensitive.

        `<who_or_what>` is the user, channel or role the rule is for.
        """
        # noinspection PyTypeChecker
        await self._add_rule(
            rule=allow_or_deny,
            cog_or_cmd=cog_or_command,
            model_id=who_or_what.id,
            guild_id=ctx.guild.id,
        )
        await ctx.send(_("Rule added."))

    @checks.is_owner()
    @permissions.command(name="removeglobalrule")
    async def permissions_removeglobalrule(
        self,
        ctx: commands.Context,
        cog_or_command: CogOrCommand,
        who_or_what: commands.GlobalPermissionModel,
    ):
        """Remove a global rule from a command.

        `<cog_or_command>` is the cog or command to remove the rule
        from. This is case sensitive.

        `<who_or_what>` is the user, channel, role or server the rule
        is for.
        """
        await self._remove_rule(
            cog_or_cmd=cog_or_command, model_id=who_or_what.id, guild_id=GLOBAL
        )
        await ctx.send(_("Rule removed."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="removeserverrule", aliases=["removeguildrule"])
    async def permissions_removeguildrule(
        self,
        ctx: commands.Context,
        cog_or_command: CogOrCommand,
        *,
        who_or_what: commands.GuildPermissionModel,
    ):
        """Remove a server rule from a command.

        `<cog_or_command>` is the cog or command to remove the rule
        from. This is case sensitive.

        `<who_or_what>` is the user, channel or role the rule is for.
        """
        await self._remove_rule(
            cog_or_cmd=cog_or_command, model_id=who_or_what.id, guild_id=ctx.guild.id
        )
        await ctx.send(_("Rule removed."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="setdefaultserverrule", aliases=["setdefaultguildrule"])
    async def permissions_setdefaultguildrule(
        self, ctx: commands.Context, allow_or_deny: ClearableRuleType, cog_or_command: CogOrCommand
    ):
        """Set the default rule for a command in this server.

        This is the rule a command will default to when no other rule
        is found.

        `<allow_or_deny>` should be one of "allow", "deny" or "clear".
        "clear" will reset the default rule.

        `<cog_or_command>` is the cog or command to set the default
        rule for. This is case sensitive.
        """
        # noinspection PyTypeChecker
        await self._set_default_rule(
            rule=allow_or_deny, cog_or_cmd=cog_or_command, guild_id=ctx.guild.id
        )
        await ctx.send(_("Default set."))

    @checks.is_owner()
    @permissions.command(name="setdefaultglobalrule")
    async def permissions_setdefaultglobalrule(
        self, ctx: commands.Context, allow_or_deny: ClearableRuleType, cog_or_command: CogOrCommand
    ):
        """Set the default global rule for a command.

        This is the rule a command will default to when no other rule
        is found.

        `<allow_or_deny>` should be one of "allow", "deny" or "clear".
        "clear" will reset the default rule.

        `<cog_or_command>` is the cog or command to set the default
        rule for. This is case sensitive.
        """
        # noinspection PyTypeChecker
        await self._set_default_rule(
            rule=allow_or_deny, cog_or_cmd=cog_or_command, guild_id=GLOBAL
        )
        await ctx.send(_("Default set."))

    @checks.is_owner()
    @permissions.command(name="clearglobalrules")
    async def permissions_clearglobalrules(self, ctx: commands.Context):
        """Reset all global rules."""
        agreed = await self._confirm(ctx)
        if agreed:
            await self._clear_rules(bot=ctx.bot, guild_id=GLOBAL)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="clearserverrules", aliases=["clearguildrules"])
    async def permissions_clearguildrules(self, ctx: commands.Context):
        """Reset all rules in this server."""
        agreed = await self._confirm(ctx)
        if agreed:
            await self._clear_rules(bot=ctx.bot, guild_id=ctx.guild.id)

    async def cog_added(self, cog: commands.Cog) -> None:
        """Event listener for `cog_add`.

        This loads rules whenever a new cog is added.
        """
        self._load_rules_for(
            cog_or_command=cog,
            rule_dict=await self.config.custom(COMMAND, cog.__class__.__name__).all(),
        )

    async def command_added(self, command: commands.Command) -> None:
        """Event listener for `command_add`.

        This loads rules whenever a new command is added.
        """
        self._load_rules_for(
            cog_or_command=command,
            rule_dict=await self.config.custom(COMMAND, command.qualified_name).all(),
        )

    async def _add_rule(
        self, rule: bool, cog_or_cmd: CogOrCommand, model_id: int, guild_id: int
    ) -> None:
        if rule is True:
            cog_or_cmd.obj.allow_for(model_id, guild_id=guild_id)
        else:
            cog_or_cmd.obj.deny_to(model_id, guild_id=guild_id)

        async with self.config.custom(cog_or_cmd.type, cog_or_cmd.name).all() as rules:
            rules.setdefault(str(guild_id), {})[str(model_id)] = rule

    async def _remove_rule(self, cog_or_cmd: CogOrCommand, model_id: int, guild_id: int) -> None:
        cog_or_cmd.obj.clear_rule_for(model_id, guild_id=guild_id)
        guild_id, model_id = str(guild_id), str(model_id)
        async with self.config.custom(cog_or_cmd.type, cog_or_cmd.name).all() as rules:
            if guild_id in rules and rules[guild_id]:
                del rules[guild_id][model_id]

    async def _set_default_rule(
        self, rule: Optional[bool], cog_or_cmd: CogOrCommand, guild_id: int
    ):
        cog_or_cmd.obj.set_default_rule(rule, guild_id)
        async with self.config.custom(cog_or_cmd.type, cog_or_cmd.name).all() as rules:
            rules.setdefault(str(guild_id), {})["default"] = rule

    async def _clear_rules(self, bot: Red, guild_id: int):
        bot.clear_permission_rules(guild_id)
        for category in (COG, COMMAND):
            async with self.config.custom(category).all() as all_rules:
                for name, rules in all_rules.items():
                    rules.pop(str(guild_id), None)

    @staticmethod
    async def _confirm(ctx: commands.Context) -> bool:
        if ctx.guild is None or ctx.guild.me.permissions_in(ctx.channel).add_reactions:
            msg = await ctx.send(_("Are you sure?"))
            for emoji in REACTS.keys():
                await msg.add_reaction(emoji)
            try:
                reaction, user = await ctx.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: r.message == msg and u == ctx.author and str(r) in REACTS,
                    timeout=30,
                )
            except asyncio.TimeoutError:
                agreed = False
            else:
                agreed = REACTS.get(str(reaction))
        else:
            await ctx.send(_("Are you sure? (y/n)"))
            try:
                message = await ctx.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content in Y_OR_N,
                    timeout=30,
                )
            except asyncio.TimeoutError:
                agreed = False
            else:
                agreed = Y_OR_N.get(message.content.lower())

        if agreed is False:
            await ctx.send(_("Action cancelled."))
        return agreed

    @staticmethod
    def _load_rules_for(
        cog_or_command: Union[commands.Command, commands.Cog],
        rule_dict: Dict[str, Dict[str, bool]],
    ) -> None:
        for guild_id, guild_dict in _int_key_map(rule_dict.items()):
            for model_id, rule in _int_key_map(guild_dict.items()):
                if rule is True:
                    cog_or_command.allow_for(model_id, guild_id=guild_id)
                elif rule is False:
                    cog_or_command.deny_to(model_id, guild_id=guild_id)

    async def _maybe_update_schema(self) -> None:
        if await self.config.version():
            return
        old_config = await self.config.all_guilds()
        old_config[GLOBAL] = await self.config.all()
        new_cog_rules, new_cmd_rules = self._get_updated_schema(old_config)
        await self.config.custom(COG).set(new_cog_rules)
        await self.config.custom(COMMAND).set(new_cmd_rules)
        await self.config.version.set(__version__)

    _OldConfigSchema = Dict[Optional[int], Dict[str, Dict[str, Dict[str, Dict[str, List[int]]]]]]
    _NewConfigSchema = Dict[str, Dict[int, Dict[str, Dict[int, bool]]]]

    @staticmethod
    def _get_updated_schema(
        old_config: _OldConfigSchema
    ) -> Tuple[_NewConfigSchema, _NewConfigSchema]:
        # Prior to 1.0.0, the schema was in this form for both global
        # and guild-based rules:
        # "cogs"
        # -> Cog names...
        #   -> "allow"
        #     -> [Model IDs...]
        #   -> "deny"
        #     -> [Model IDs...]
        # "commands"
        # -> Command names...
        #   -> "allow"
        #     -> [Model IDs...]
        #   -> "deny"
        #     -> [Model IDs...]

        new_cog_rules = {}
        new_cmd_rules = {}
        ret = (new_cog_rules, new_cmd_rules)
        for guild_id, old_rules in old_config.items():
            if "owner_models" not in old_config:
                continue
            if guild_id is None:
                guild_id = GLOBAL
            old_rules = old_rules["owner_models"]
            for category, new_rules in zip(("cogs", "commands"), ret):
                if "category" in old_rules:
                    for name, rules in old_rules[category].items():
                        these_rules = new_rules.setdefault(name, {})
                        guild_rules = these_rules.setdefault(guild_id, {})
                        # Since allow rules would take precedence if the same model ID
                        # sat in both the allow and deny list, we add the deny entries
                        # first and let any conflicting allow entries overwrite.
                        for model_id in rules.get("deny", []):
                            guild_rules[model_id] = False
                        for model_id in rules.get("allow", []):
                            guild_rules[model_id] = True
        return ret

    def __unload(self) -> None:
        self.bot.remove_listener(self.cog_added, "on_cog_add")
        self.bot.remove_listener(self.command_added, "on_command_add")


def _int_key_map(items_view: ItemsView[str, Any]) -> Iterator[Tuple[int, Any]]:
    return map(lambda tup: (int(tup[0]), tup[1]), items_view)
