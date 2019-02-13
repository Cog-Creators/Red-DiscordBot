import asyncio
import io
import textwrap
from copy import copy
from typing import Union, Optional, Dict, List, Tuple, Any, Iterator, ItemsView, cast

import discord
import yaml
from schema import And, Or, Schema, SchemaError, Optional as UseOptional
from redbot.core import checks, commands, config
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate, MessagePredicate

from .converters import (
    CogOrCommand,
    RuleType,
    ClearableRuleType,
    GuildUniqueObjectFinder,
    GlobalUniqueObjectFinder,
)

_ = Translator("Permissions", __file__)

COG = "COG"
COMMAND = "COMMAND"
GLOBAL = 0

# The strings in the schema are constants and should get extracted, but not translated until
# runtime.
translate = _
_ = lambda s: s
YAML_SCHEMA = Schema(
    Or(
        {
            UseOptional(COMMAND): Or(
                {
                    str: And(
                        {
                            Or(int, "default"): And(
                                bool, error=_("Rules must be either `true` or `false`.")
                            )
                        },
                        error=_("Keys under command names must be IDs (numbers) or `default`."),
                    )
                },
                {},
                error=_("Keys under `COMMAND` must be command names (strings)."),
            ),
            UseOptional(COG): Or(
                {
                    str: Or(
                        {
                            Or(int, "default"): And(
                                bool, error=_("Rules must be either `true` or `false`.")
                            )
                        },
                        {},
                        error=_("Keys under cog names must be IDs or `default`."),
                    )
                },
                {},
                error=_("Keys under `COG` must be cog names (strings)."),
            ),
        },
        {},
        error=_("Top-level keys must be either `COG` or `COMMAND`."),
    )
)
_ = translate

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
        #     -> "default"
        #       -> True|False
        # "COMMAND"
        # -> Command names...
        #   -> Guild IDs...
        #     -> Model IDs...
        #       -> True|False
        #     -> "default"
        #       -> True|False

        # Note that GLOBAL rules are denoted by an ID of 0.
        self.config = config.Config.get_conf(self, identifier=78631113035100160)
        self.config.register_global(version="")
        self.config.register_custom(COG)
        self.config.register_custom(COMMAND)

    @commands.group(aliases=["p"])
    async def permissions(self, ctx: commands.Context):
        """Command permission management tools."""
        pass

    @permissions.command(name="explain")
    async def permissions_explain(self, ctx: commands.Context):
        """Explain how permissions works."""
        # Apologies in advance for the translators out there...

        message = _(
            "This cog extends the default permission model of the bot. By default, many commands "
            "are restricted based on what the command can do.\n"
            "This cog allows you to refine some of those restrictions. You can allow wider or "
            "narrower access to most commands using it. You cannot, however, change the "
            "restrictions on owner-only commands.\n\n"
            "When additional rules are set using this cog, those rules will be checked prior to "
            "checking for the default restrictions of the command.\n"
            "Global rules (set by the owner) are checked first, then rules set for servers. If "
            "multiple global or server rules apply to the case, the order they are checked is:\n"
            "  1. Rules about a user.\n"
            "  2. Rules about the voice channel a user is in.\n"
            "  3. Rules about the text channel a command was issued in.\n"
            "  4. Rules about a role the user has (The highest role they have with a rule will be "
            "used).\n"
            "  5. Rules about the server a user is in (Global rules only).\n\n"
            "For more details, please read the [official documentation]"
            "(https://red-discordbot.readthedocs.io/en/v3-develop/cog_permissions.html)."
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

        fake_message = copy(ctx.message)
        fake_message.author = user
        fake_message.content = "{}{}".format(ctx.prefix, command)

        com = ctx.bot.get_command(command)
        if com is None:
            out = _("No such command")
        else:
            fake_context = await ctx.bot.get_context(fake_message)
            try:
                can = await com.can_run(
                    fake_context, check_all_parents=True, change_permission_state=False
                )
            except commands.CommandError:
                can = False

            out = (
                _("That user can run the specified command.")
                if can
                else _("That user can not run the specified command.")
            )
        await ctx.send(out)

    @checks.guildowner_or_permissions(administrator=True)
    @permissions.group(name="acl", aliases=["yaml"])
    async def permissions_acl(self, ctx: commands.Context):
        """Manage permissions with YAML files."""
        if ctx.invoked_subcommand is None or ctx.invoked_subcommand == self.permissions_acl:
            # Send a little guide on YAML formatting
            await ctx.send(
                _("Example YAML for setting rules:\n")
                + box(
                    textwrap.dedent(
                        """\
                        COMMAND:
                            ping:
                                12345678901234567: true
                                56789012345671234: false
                        COG:
                            General:
                                56789012345671234: true
                                12345678901234567: false
                                default: false
                        """
                    ),
                    lang="yaml",
                )
            )

    @checks.is_owner()
    @permissions_acl.command(name="setglobal")
    async def permissions_acl_setglobal(self, ctx: commands.Context):
        """Set global rules with a YAML file.

        **WARNING**: This will override reset *all* global rules
        to the rules specified in the uploaded file.

        This does not validate the names of commands and cogs before
        setting the new rules.
        """
        await self._permissions_acl_set(ctx, guild_id=GLOBAL, update=False)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions_acl.command(name="setserver", aliases=["setguild"])
    async def permissions_acl_setguild(self, ctx: commands.Context):
        """Set rules for this server with a YAML file.

        **WARNING**: This will override reset *all* rules in this
        server to the rules specified in the uploaded file.
        """
        await self._permissions_acl_set(ctx, guild_id=ctx.guild.id, update=False)

    @checks.is_owner()
    @permissions_acl.command(name="getglobal")
    async def permissions_acl_getglobal(self, ctx: commands.Context):
        """Get a YAML file detailing all global rules."""
        file = await self._yaml_get_acl(guild_id=GLOBAL)
        try:
            await ctx.author.send(file=file)
        except discord.Forbidden:
            await ctx.send(_("I'm not allowed to DM you."))
        else:
            await ctx.send(_("I've just sent the file to you via DM."))
        finally:
            file.close()

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions_acl.command(name="getserver", aliases=["getguild"])
    async def permissions_acl_getguild(self, ctx: commands.Context):
        """Get a YAML file detailing all rules in this server."""
        file = await self._yaml_get_acl(guild_id=ctx.guild.id)
        try:
            await ctx.author.send(file=file)
        except discord.Forbidden:
            await ctx.send(_("I'm not allowed to DM you."))
        else:
            await ctx.send(_("I've just sent the file to you via DM."))
        finally:
            file.close()

    @checks.is_owner()
    @permissions_acl.command(name="updateglobal")
    async def permissions_acl_updateglobal(self, ctx: commands.Context):
        """Update global rules with a YAML file.

        This won't touch any rules not specified in the YAML
        file.
        """
        await self._permissions_acl_set(ctx, guild_id=GLOBAL, update=True)

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions_acl.command(name="updateserver", aliases=["updateguild"])
    async def permissions_acl_updateguild(self, ctx: commands.Context):
        """Update rules for this server with a YAML file.

        This won't touch any rules not specified in the YAML
        file.
        """
        await self._permissions_acl_set(ctx, guild_id=ctx.guild.id, update=True)

    @checks.is_owner()
    @permissions.command(name="addglobalrule")
    async def permissions_addglobalrule(
        self,
        ctx: commands.Context,
        allow_or_deny: RuleType,
        cog_or_command: CogOrCommand,
        who_or_what: commands.Greedy[GlobalUniqueObjectFinder],
    ):
        """Add a global rule to a command.

        `<allow_or_deny>` should be one of "allow" or "deny".

        `<cog_or_command>` is the cog or command to add the rule to.
        This is case sensitive.

        `<who_or_what>` is one or more users, channels or roles the rule is for.
        """
        for w in who_or_what:
            await self._add_rule(
                rule=cast(bool, allow_or_deny),
                cog_or_cmd=cog_or_command,
                model_id=w.id,
                guild_id=0,
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
        who_or_what: commands.Greedy[GuildUniqueObjectFinder],
    ):
        """Add a rule to a command in this server.

        `<allow_or_deny>` should be one of "allow" or "deny".

        `<cog_or_command>` is the cog or command to add the rule to.
        This is case sensitive.

        `<who_or_what>` is one or more users, channels or roles the rule is for.
        """
        for w in who_or_what:
            await self._add_rule(
                rule=cast(bool, allow_or_deny),
                cog_or_cmd=cog_or_command,
                model_id=w.id,
                guild_id=ctx.guild.id,
            )
        await ctx.send(_("Rule added."))

    @checks.is_owner()
    @permissions.command(name="removeglobalrule")
    async def permissions_removeglobalrule(
        self,
        ctx: commands.Context,
        cog_or_command: CogOrCommand,
        who_or_what: commands.Greedy[GlobalUniqueObjectFinder],
    ):
        """Remove a global rule from a command.

        `<cog_or_command>` is the cog or command to remove the rule
        from. This is case sensitive.

       `<who_or_what>` is one or more users, channels or roles the rule is for.
        """
        for w in who_or_what:
            await self._remove_rule(cog_or_cmd=cog_or_command, model_id=w.id, guild_id=GLOBAL)
        await ctx.send(_("Rule removed."))

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="removeserverrule", aliases=["removeguildrule"])
    async def permissions_removeguildrule(
        self,
        ctx: commands.Context,
        cog_or_command: CogOrCommand,
        who_or_what: commands.Greedy[GlobalUniqueObjectFinder],
    ):
        """Remove a server rule from a command.

        `<cog_or_command>` is the cog or command to remove the rule
        from. This is case sensitive.

        `<who_or_what>` is one or more users, channels or roles the rule is for.
        """
        for w in who_or_what:
            await self._remove_rule(
                cog_or_cmd=cog_or_command, model_id=w.id, guild_id=ctx.guild.id
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
        await self._set_default_rule(
            rule=cast(Optional[bool], allow_or_deny),
            cog_or_cmd=cog_or_command,
            guild_id=ctx.guild.id,
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
        await self._set_default_rule(
            rule=cast(Optional[bool], allow_or_deny), cog_or_cmd=cog_or_command, guild_id=GLOBAL
        )
        await ctx.send(_("Default set."))

    @checks.is_owner()
    @permissions.command(name="clearglobalrules")
    async def permissions_clearglobalrules(self, ctx: commands.Context):
        """Reset all global rules."""
        agreed = await self._confirm(ctx)
        if agreed:
            await self._clear_rules(guild_id=GLOBAL)
            await ctx.tick()

    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    @permissions.command(name="clearserverrules", aliases=["clearguildrules"])
    async def permissions_clearguildrules(self, ctx: commands.Context):
        """Reset all rules in this server."""
        agreed = await self._confirm(ctx)
        if agreed:
            await self._clear_rules(guild_id=ctx.guild.id)
            await ctx.tick()

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
        """Add a rule.

        Guild ID should be 0 for global rules.

        Handles config.
        """
        if rule is True:
            cog_or_cmd.obj.allow_for(model_id, guild_id=guild_id)
        else:
            cog_or_cmd.obj.deny_to(model_id, guild_id=guild_id)

        async with self.config.custom(cog_or_cmd.type, cog_or_cmd.name).all() as rules:
            rules.setdefault(str(guild_id), {})[str(model_id)] = rule

    async def _remove_rule(self, cog_or_cmd: CogOrCommand, model_id: int, guild_id: int) -> None:
        """Remove a rule.

        Guild ID should be 0 for global rules.

        Handles config.
        """
        cog_or_cmd.obj.clear_rule_for(model_id, guild_id=guild_id)
        guild_id, model_id = str(guild_id), str(model_id)
        async with self.config.custom(cog_or_cmd.type, cog_or_cmd.name).all() as rules:
            if guild_id in rules and rules[guild_id]:
                del rules[guild_id][model_id]

    async def _set_default_rule(
        self, rule: Optional[bool], cog_or_cmd: CogOrCommand, guild_id: int
    ) -> None:
        """Set the default rule.

        Guild ID should be 0 for the global default.

        Handles config.
        """
        cog_or_cmd.obj.set_default_rule(rule, guild_id)
        async with self.config.custom(cog_or_cmd.type, cog_or_cmd.name).all() as rules:
            rules.setdefault(str(guild_id), {})["default"] = rule

    async def _clear_rules(self, guild_id: int) -> None:
        """Clear all global rules or rules for a guild.

        Guild ID should be 0 for global rules.

        Handles config.
        """
        self.bot.clear_permission_rules(guild_id)
        for category in (COG, COMMAND):
            async with self.config.custom(category).all() as all_rules:
                for name, rules in all_rules.items():
                    rules.pop(str(guild_id), None)

    async def _permissions_acl_set(
        self, ctx: commands.Context, guild_id: int, update: bool
    ) -> None:
        """Set rules from a YAML file and handle response to users too."""
        if not ctx.message.attachments:
            await ctx.send(_("You must upload a file."))
            return

        try:
            await self._yaml_set_acl(ctx.message.attachments[0], guild_id=guild_id, update=update)
        except yaml.MarkedYAMLError as e:
            await ctx.send(_("Invalid syntax: ") + str(e))
        except SchemaError as e:
            await ctx.send(
                _("Your YAML file did not match the schema: ") + translate(e.errors[-1])
            )
        else:
            await ctx.send(_("Rules set."))

    async def _yaml_set_acl(self, source: discord.Attachment, guild_id: int, update: bool) -> None:
        """Set rules from a YAML file."""
        with io.BytesIO() as fp:
            await source.save(fp)
            rules = yaml.safe_load(fp)

        if rules is None:
            rules = {}
        YAML_SCHEMA.validate(rules)
        if update is False:
            await self._clear_rules(guild_id)

        for category, getter in ((COG, self.bot.get_cog), (COMMAND, self.bot.get_command)):
            rules_dict = rules.get(category)
            if not rules_dict:
                continue
            conf = self.config.custom(category)
            for cmd_name, cmd_rules in rules_dict.items():
                cmd_rules = {str(model_id): rule for model_id, rule in cmd_rules.items()}
                await conf.set_raw(cmd_name, str(guild_id), value=cmd_rules)
                cmd_obj = getter(cmd_name)
                if cmd_obj is not None:
                    self._load_rules_for(cmd_obj, {guild_id: cmd_rules})

    async def _yaml_get_acl(self, guild_id: int) -> discord.File:
        """Get a YAML file for all rules set in a guild."""
        guild_rules = {}
        for category in (COG, COMMAND):
            guild_rules.setdefault(category, {})
            rules_dict = await self.config.custom(category).all()
            for cmd_name, cmd_rules in rules_dict.items():
                model_rules = cmd_rules.get(str(guild_id))
                if model_rules is not None:
                    guild_rules[category][cmd_name] = dict(_int_key_map(model_rules.items()))

        fp = io.BytesIO(yaml.dump(guild_rules, default_flow_style=False).encode("utf-8"))
        return discord.File(fp, filename="acl.yaml")

    @staticmethod
    async def _confirm(ctx: commands.Context) -> bool:
        """Ask "Are you sure?" and get the response as a bool."""
        if ctx.guild is None or ctx.guild.me.permissions_in(ctx.channel).add_reactions:
            msg = await ctx.send(_("Are you sure?"))
            # noinspection PyAsyncCall
            task = start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS, ctx.bot.loop)
            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
                return False
            else:
                task.cancel()
                agreed = pred.result
            finally:
                await msg.delete()
        else:
            await ctx.send(_("Are you sure? (y/n)"))
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await ctx.bot.wait_for("message", check=pred, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
                return False
            else:
                agreed = pred.result

        if agreed is False:
            await ctx.send(_("Action cancelled."))
        return agreed

    async def initialize(self) -> None:
        """Initialize this cog.

        This will load all rules from config onto every currently
        loaded command.
        """
        await self._maybe_update_schema()
        await self._load_all_rules()

    async def _maybe_update_schema(self) -> None:
        """Maybe update rules set by config prior to permissions 1.0.0."""
        if await self.config.version():
            return
        old_config = await self.config.all_guilds()
        old_config[GLOBAL] = await self.config.all()
        new_cog_rules, new_cmd_rules = self._get_updated_schema(old_config)
        await self.config.custom(COG).set(new_cog_rules)
        await self.config.custom(COMMAND).set(new_cmd_rules)
        await self.config.version.set(__version__)

    _OldConfigSchema = Dict[int, Dict[str, Dict[str, Dict[str, Dict[str, List[int]]]]]]
    _NewConfigSchema = Dict[str, Dict[int, Dict[str, Dict[int, bool]]]]

    @staticmethod
    def _get_updated_schema(
        old_config: _OldConfigSchema
    ) -> Tuple[_NewConfigSchema, _NewConfigSchema]:
        # Prior to 1.0.0, the schema was in this form for both global
        # and guild-based rules:
        # "owner_models"
        # -> "cogs"
        #   -> Cog names...
        #     -> "allow"
        #       -> [Model IDs...]
        #     -> "deny"
        #       -> [Model IDs...]
        #     -> "default"
        #       -> "allow"|"deny"
        # -> "commands"
        #   -> Command names...
        #     -> "allow"
        #       -> [Model IDs...]
        #     -> "deny"
        #       -> [Model IDs...]
        #     -> "default"
        #       -> "allow"|"deny"

        new_cog_rules = {}
        new_cmd_rules = {}
        for guild_id, old_rules in old_config.items():
            if "owner_models" not in old_rules:
                continue
            old_rules = old_rules["owner_models"]
            for category, new_rules in zip(("cogs", "commands"), (new_cog_rules, new_cmd_rules)):
                if category in old_rules:
                    for name, rules in old_rules[category].items():
                        these_rules = new_rules.setdefault(name, {})
                        guild_rules = these_rules.setdefault(str(guild_id), {})
                        # Since allow rules would take precedence if the same model ID
                        # sat in both the allow and deny list, we add the deny entries
                        # first and let any conflicting allow entries overwrite.
                        for model_id in rules.get("deny", []):
                            guild_rules[str(model_id)] = False
                        for model_id in rules.get("allow", []):
                            guild_rules[str(model_id)] = True
                        if "default" in rules:
                            default = rules["default"]
                            if default == "allow":
                                guild_rules["default"] = True
                            elif default == "deny":
                                guild_rules["default"] = False
        return new_cog_rules, new_cmd_rules

    async def _load_all_rules(self):
        """Load all of this cog's rules into loaded commands and cogs."""
        for category, getter in ((COG, self.bot.get_cog), (COMMAND, self.bot.get_command)):
            all_rules = await self.config.custom(category).all()
            for name, rules in all_rules.items():
                obj = getter(name)
                if obj is None:
                    continue
                self._load_rules_for(obj, rules)

    @staticmethod
    def _load_rules_for(
        cog_or_command: Union[commands.Command, commands.Cog],
        rule_dict: Dict[Union[int, str], Dict[Union[int, str], bool]],
    ) -> None:
        """Load the rules into a command or cog object.

        rule_dict should be a dict mapping Guild IDs to Model IDs to
        rules.
        """
        for guild_id, guild_dict in _int_key_map(rule_dict.items()):
            for model_id, rule in _int_key_map(guild_dict.items()):
                if model_id == "default":
                    cog_or_command.set_default_rule(rule, guild_id=guild_id)
                elif rule is True:
                    cog_or_command.allow_for(model_id, guild_id=guild_id)
                elif rule is False:
                    cog_or_command.deny_to(model_id, guild_id=guild_id)

    def __unload(self) -> None:
        self.bot.remove_listener(self.cog_added, "on_cog_add")
        self.bot.remove_listener(self.command_added, "on_command_add")
        self.bot.loop.create_task(self._unload_all_rules())

    async def _unload_all_rules(self) -> None:
        """Unload all rules set by this cog.

        This is done instead of just clearing all rules, which could
        clear rules set by other cogs.
        """
        for category, getter in ((COG, self.bot.get_cog), (COMMAND, self.bot.get_command)):
            all_rules = await self.config.custom(category).all()
            for name, rules in all_rules.items():
                obj = getter(name)
                if obj is None:
                    continue
                self._unload_rules_for(obj, rules)

    @staticmethod
    def _unload_rules_for(
        cog_or_command: Union[commands.Command, commands.Cog],
        rule_dict: Dict[Union[int, str], Dict[Union[int, str], bool]],
    ) -> None:
        """Unload the rules from a command or cog object.

        rule_dict should be a dict mapping Guild IDs to Model IDs to
        rules.
        """
        for guild_id, guild_dict in _int_key_map(rule_dict.items()):
            for model_id in guild_dict.keys():
                if model_id == "default":
                    cog_or_command.set_default_rule(None, guild_id=guild_id)
                else:
                    cog_or_command.clear_rule_for(int(model_id), guild_id=guild_id)


def _int_key_map(items_view: ItemsView[str, Any]) -> Iterator[Tuple[Union[str, int], Any]]:
    for k, v in items_view:
        if k == "default":
            yield k, v
        else:
            yield int(k), v
