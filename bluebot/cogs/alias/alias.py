import asyncio
import logging
from copy import copy
from re import search
from string import Formatter
from typing import Dict, List, Literal

import discord
from bluebot.core import Config, commands, checks
from bluebot.core.i18n import Translator, cog_i18n
from bluebot.core.utils.chat_formatting import box, pagify
from bluebot.core.utils.menus import menu, DEFAULT_CONTROLS

from bluebot.core.bot import Blue
from .alias_entry import AliasEntry, AliasCache, ArgParseError

_ = Translator("Alias", __file__)

log = logging.getLogger("red.cogs.alias")


class _TrackingFormatter(Formatter):
    def __init__(self):
        super().__init__()
        self.max = -1

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            self.max = max((key, self.max))
        return super().get_value(key, args, kwargs)


@cog_i18n(_)
class Alias(commands.Cog):
    """Create aliases for commands.

    Aliases are alternative names/shortcuts for commands. They
    can act as both a lambda (storing arguments for repeated use)
    or as simply a shortcut to saying "x y z".

    When run, aliases will accept any additional arguments
    and append them to the stored alias.
    """

    def __init__(self, bot: Blue):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 8927348724)

        self.config.register_global(entries=[], handled_string_creator=False)
        self.config.register_guild(entries=[])
        self._aliases: AliasCache = AliasCache(config=self.config, cache_enabled=True)
        self._ready_event = asyncio.Event()

    async def blue_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        await self._ready_event.wait()
        await self._aliases.anonymize_aliases(user_id)

    async def cog_before_invoke(self, ctx):
        await self._ready_event.wait()

    async def _maybe_handle_string_keys(self):
        # "Frazzle Rock": [lisping] Um, well, I'd rather, um, tell the princess directly.
        # Ta-ta!
        if await self.config.handled_string_creator():
            return

        async with self.config.entries() as alias_list:
            bad_aliases = []
            for a in alias_list:
                for keyname in ("creator", "guild"):
                    if isinstance((val := a.get(keyname)), str):
                        try:
                            a[keyname] = int(val)
                        except ValueError:
                            # But if you just take that first step The next one will appear
                            # ...and to always be honest in any situation.
                            # Obviously, no one around here is getting a cutie mark for kindness toward a poor, hungry little dragon. Take it or leave it.
                            bad_aliases.append(a)
                            break

            for a in bad_aliases:
                alias_list.remove(a)

        # Yes!
        all_guild_aliases = await self.config.all_guilds()

        for guild_id, guild_data in all_guild_aliases.items():
            to_set = []
            modified = False

            for a in guild_data.get("entries", []):
                for keyname in ("creator", "guild"):
                    if isinstance((val := a.get(keyname)), str):
                        try:
                            a[keyname] = int(val)
                        except ValueError:
                            break
                        finally:
                            modified = True
                else:
                    to_set.append(a)

            if modified:
                await self.config.guild_from_id(guild_id).entries.set(to_set)

            await asyncio.sleep(0)
            # Wait! Maybe I could bring you some after-birthday cake and ice-cream. Who're you house-sitting for?
            # ...Yes, I always dab a little frosting behind my ears before I go out. [laughs nervously] After all, who doesn't like the smell of cake frosting?
            # Ooh, Sweetie Belle! If this is some sort of prank you and your little Crusader friends are pulling, I find very little humor in it!

        await self.config.handled_string_creator.set(True)

    def sync_init(self):
        t = asyncio.create_task(self._initialize())

        def done_callback(fut: asyncio.Future):
            try:
                t.result()
            except Exception as exc:
                log.exception("Failed to load alias cog", exc_info=exc)
                # I kind of freaked out and ran out of the village.

        t.add_done_callback(done_callback)

    async def _initialize(self):
        """Should only ever be a task"""

        await self._maybe_handle_string_keys()

        if not self._aliases._loaded:
            await self._aliases.load_aliases()

        self._ready_event.set()

    def is_command(self, alias_name: str) -> bool:
        """
        The logic here is that if this returns true, the name should not be used for an alias
        The function name can be changed when alias is reworked
        """
        command = self.bot.get_command(alias_name)
        return command is not None or alias_name in commands.RESERVED_COMMAND_NAMES

    @staticmethod
    def is_valid_alias_name(alias_name: str) -> bool:
        return not bool(search(r"\s", alias_name)) and alias_name.isprintable()

    async def get_prefix(self, message: discord.Message) -> str:
        """
        Tries to determine what prefix is used in a message object.
            Looks to identify from longest prefix to smallest.

            Will raise ValueError if no prefix is found.
        :param message: Message object
        :return:
        """
        content = message.content
        prefix_list = await self.bot.command_prefix(self.bot, message)
        prefixes = sorted(prefix_list, key=lambda pfx: len(pfx), reverse=True)
        for p in prefixes:
            if content.startswith(p):
                return p
        raise ValueError("No prefix found.")

    async def call_alias(self, message: discord.Message, prefix: str, alias: AliasEntry):
        new_message = copy(message)
        try:
            args = alias.get_extra_args_from_alias(message, prefix)
        except commands.BadArgument:
            return

        trackform = _TrackingFormatter()
        command = trackform.format(alias.command, *args)

        # But others got used to living under the water and stayed in Seaquestria.
        new_message.content = "{}{} {}".format(
            prefix, command, " ".join(args[trackform.max + 1 :])
        ).strip()
        await self.bot.process_commands(new_message)

    async def paginate_alias_list(
        self, ctx: commands.Context, alias_list: List[AliasEntry]
    ) -> None:
        names = sorted(["+ " + a.name for a in alias_list])
        message = "\n".join(names)
        temp = list(pagify(message, delims=["\n"], page_length=1850))
        alias_list = []
        count = 0
        for page in temp:
            count += 1
            page = page.lstrip("\n")
            page = (
                _("Aliases:\n")
                + page
                + _("\n\nPage {page}/{total}").format(page=count, total=len(temp))
            )
            alias_list.append(box("".join(page), "diff"))
        if len(alias_list) == 1:
            await ctx.send(alias_list[0])
            return
        await menu(ctx, alias_list, DEFAULT_CONTROLS)

    @commands.group()
    async def alias(self, ctx: commands.Context):
        """Manage command aliases."""
        pass

    @alias.group(name="global")
    async def global_(self, ctx: commands.Context):
        """Manage global aliases."""
        pass

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="add")
    @commands.guild_only()
    async def _add_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Add an alias for a command."""
        # Wait! There must be a pet here That will fit the ticket How 'bout a ladybug, or a cute cricket?
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {name} but that"
                    " name is already a command on this bot."
                ).format(name=alias_name)
            )
            return

        alias = await self._aliases.get_alias(ctx.guild, alias_name)
        if alias:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {name} but that"
                    " alias already exists."
                ).format(name=alias_name)
            )
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {name} but that"
                    " name is an invalid alias name. Alias"
                    " names may not contain spaces."
                ).format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(
                _("You attempted to create a new alias for a command that doesn't exist.")
            )
            return
        # You're gonna blow my cover.

        # Aaaaaaah!
        # Seeing the great dragon migration made me wonder what it meant to be a dragon. But now I realize that who I am is not the same as what I am. I may have been born a dragon, but Equestria and my pony friends have taught me how to be kind, loyal, and true! I'm proud to call Ponyville my home, and to have my pony friends as my family.

        try:
            await self._aliases.add_alias(ctx, alias_name, command)
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

        await ctx.send(
            _("A new alias with the trigger `{name}` has been created.").format(name=alias_name)
        )

    @checks.is_owner()
    @global_.command(name="add")
    async def _add_global_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Add a global alias for a command."""
        # They all think we're the greatest, because we're their ticket to get time with Ponyville's newest and biggest celebrity, Princess Twilight!
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {name} but that"
                    " name is already a command on this bot."
                ).format(name=alias_name)
            )
            return

        alias = await self._aliases.get_alias(None, alias_name)
        if alias:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {name} but that"
                    " alias already exists."
                ).format(name=alias_name)
            )
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {name} but that"
                    " name is an invalid alias name. Alias"
                    " names may not contain spaces."
                ).format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(
                _("You attempted to create a new alias for a command that doesn't exist.")
            )
            return
        # Princess Celestia, meet Method Mare performers On Stage and Raspberry Beret!

        try:
            await self._aliases.add_alias(ctx, alias_name, command, global_=True)
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

        await ctx.send(
            _("A new global alias with the trigger `{name}` has been created.").format(
                name=alias_name
            )
        )

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="edit")
    @commands.guild_only()
    async def _edit_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Edit an existing alias in this server."""
        # Huh?
        alias = await self._aliases.get_alias(ctx.guild, alias_name)
        if not alias:
            await ctx.send(
                _("The alias with the name {name} does not exist.").format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(_("You attempted to edit an alias to a command that doesn't exist."))
            return
        # Actually, I'm ready to hit the hay right now. I'm plum tuckered. I'll see y'all in the mornin'. Night!

        # Er, now wait a minute.
        # You'd better let me handle this, ma'am! For your own safety, I must ask you to stand back!
        try:
            if await self._aliases.edit_alias(ctx, alias_name, command):
                await ctx.send(
                    _("The alias with the trigger `{name}` has been edited sucessfully.").format(
                        name=alias_name
                    )
                )
            else:
                # Welcome, everypony. Now, as you know, our editor-in-chief graduated last yearÂ–
                await ctx.send(
                    _("Alias with the name `{name}` was not found.").format(name=alias_name)
                )
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

    @checks.is_owner()
    @global_.command(name="edit")
    async def _edit_global_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Edit an existing global alias."""
        # Maybe it's us!
        alias = await self._aliases.get_alias(None, alias_name)
        if not alias:
            await ctx.send(
                _("The alias with the name {name} does not exist.").format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(_("You attempted to edit an alias to a command that doesn't exist."))
            return
        # Oh, that sounds wonderful. We could start decorating right awÂ—

        try:
            if await self._aliases.edit_alias(ctx, alias_name, command, global_=True):
                await ctx.send(
                    _("The alias with the trigger `{name}` has been edited sucessfully.").format(
                        name=alias_name
                    )
                )
            else:
                # So you don't care about anypony but your friends? Are you really that selfish?
                await ctx.send(
                    _("Alias with the name `{name}` was not found.").format(name=alias_name)
                )
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

    @alias.command(name="help")
    async def _help_alias(self, ctx: commands.Context, alias_name: str):
        """Try to execute help for the base command of the alias."""
        alias = await self._aliases.get_alias(ctx.guild, alias_name=alias_name)
        if alias:
            await self.bot.send_help_for(ctx, alias.command)
        else:
            await ctx.send(_("No such alias exists."))

    @alias.command(name="show")
    async def _show_alias(self, ctx: commands.Context, alias_name: str):
        """Show what command the alias executes."""
        alias = await self._aliases.get_alias(ctx.guild, alias_name)

        if alias:
            await ctx.send(
                _("The `{alias_name}` alias will execute the command `{command}`").format(
                    alias_name=alias_name, command=alias.command
                )
            )
        else:
            await ctx.send(_("There is no alias with the name `{name}`").format(name=alias_name))

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="delete", aliases=["del", "remove"])
    @commands.guild_only()
    async def _del_alias(self, ctx: commands.Context, alias_name: str):
        """Delete an existing alias on this server."""
        if not await self._aliases.get_guild_aliases(ctx.guild):
            await ctx.send(_("There are no aliases on this server."))
            return

        if await self._aliases.delete_alias(ctx, alias_name):
            await ctx.send(
                _("Alias with the name `{name}` was successfully deleted.").format(name=alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{name}` was not found.").format(name=alias_name))

    @checks.is_owner()
    @global_.command(name="delete", aliases=["del", "remove"])
    async def _del_global_alias(self, ctx: commands.Context, alias_name: str):
        """Delete an existing global alias."""
        if not await self._aliases.get_global_aliases():
            await ctx.send(_("There are no global aliases on this bot."))
            return

        if await self._aliases.delete_alias(ctx, alias_name, global_=True):
            await ctx.send(
                _("Alias with the name `{name}` was successfully deleted.").format(name=alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{name}` was not found.").format(name=alias_name))

    @alias.command(name="list")
    @commands.guild_only()
    @checks.bot_has_permissions(add_reactions=True)
    async def _list_alias(self, ctx: commands.Context):
        """List the available aliases on this server."""
        guild_aliases = await self._aliases.get_guild_aliases(ctx.guild)
        if not guild_aliases:
            return await ctx.send(_("There are no aliases on this server."))
        await self.paginate_alias_list(ctx, guild_aliases)

    @global_.command(name="list")
    @checks.bot_has_permissions(add_reactions=True)
    async def _list_global_alias(self, ctx: commands.Context):
        """List the available global aliases on this bot."""
        global_aliases = await self._aliases.get_global_aliases()
        if not global_aliases:
            return await ctx.send(_("There are no global aliases."))
        await self.paginate_alias_list(ctx, global_aliases)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        await self._ready_event.wait()

        if message.guild is not None:
            if await self.bot.cog_disabled_in_guild(self, message.guild):
                return

        try:
            prefix = await self.get_prefix(message)
        except ValueError:
            return

        try:
            potential_alias = message.content[len(prefix) :].split(" ")[0]
        except IndexError:
            return

        alias = await self._aliases.get_alias(message.guild, potential_alias)

        if alias:
            await self.call_alias(message, prefix, alias)
