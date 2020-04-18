# Warning: The implementation below touches several private attributes.
# While this implementation will be updated, and public interfaces maintained, derived classes
# should not assume these private attributes are version safe, and use the provided HelpSettings
# class for these settings.

# This is a full replacement of discord.py's help command
#
# At a later date, there should be things added to support extra formatter
# registration from 3rd party cogs.
#
# This exists due to deficiencies in discord.py which conflict
# with our needs for per-context help settings
# see https://github.com/Rapptz/discord.py/issues/2123
#
# While the issue above discusses this as theoretical, merely interacting with config within
# the help command preparation was enough to cause
# demonstrable breakage in 150 help invokes in a 2 minute window.
# This is not an unreasonable volume on some already existing Red instances,
# especially since help is invoked for command groups
# automatically when subcommands are not provided correctly as user feedback.
#
# The implemented fix is in
# https://github.com/Rapptz/discord.py/commit/ad5beed8dd75c00bd87492cac17fe877033a3ea1
#
# While this fix would handle our immediate specific issues, it's less appropriate to use
# Where we do not have a downstream consumer to consider.
# Simply modifying the design to not be susceptible to the issue,
# rather than adding copy and deepcopy use in multiple places is better for us
#
# Additionally, this gives our users a bit more customization options including by
# 3rd party cogs down the road.

# Note: 3rd party help must not remove the copyright notice

import asyncio
from collections import namedtuple
from dataclasses import dataclass
from typing import Union, List, AsyncIterator, Iterable, cast

import discord
from discord.ext import commands as dpy_commands

from . import commands
from .context import Context
from ..i18n import Translator
from ..utils import menus
from ..utils.mod import mass_purge
from ..utils._internal_utils import fuzzy_command_search, format_fuzzy_results
from ..utils.chat_formatting import box, pagify

__all__ = ["red_help", "RedHelpFormatter", "HelpSettings"]

T_ = Translator("Help", __file__)

HelpTarget = Union[commands.Command, commands.Group, commands.Cog, dpy_commands.bot.BotBase, str]

# The below could be a protocol if we pulled in typing_extensions from mypy.
SupportsCanSee = Union[commands.Command, commands.Group, dpy_commands.bot.BotBase, commands.Cog]

EmbedField = namedtuple("EmbedField", "name value inline")
EMPTY_STRING = "\N{ZERO WIDTH SPACE}"


@dataclass(frozen=True)
class HelpSettings:
    """
    A representation of help settings.
    """

    page_char_limit: int = 1000
    max_pages_in_guild: int = 2
    use_menus: bool = False
    show_hidden: bool = False
    verify_checks: bool = True
    verify_exists: bool = False
    tagline: str = ""

    # Contrib Note: This is intentional to not accept the bot object
    # There are plans to allow guild and user specific help settings
    # Adding a non-context based method now would involve a breaking change later.
    # At a later date, more methods should be exposed for non-context based creation.
    #
    # This is also why we aren't just caching the
    # current state of these settings on the bot object.
    @classmethod
    async def from_context(cls, context: Context):
        """
        Get the HelpSettings for the current context
        """
        settings = await context.bot._config.help.all()
        return cls(**settings)


class NoCommand(Exception):
    pass


class NoSubCommand(Exception):
    def __init__(self, *, last, not_found):
        self.last = last
        self.not_found = not_found


class RedHelpFormatter:
    """
    Red's help implementation

    This is intended to be overridable in parts to only change some behavior.

    While currently, there is a global formatter, later plans include a context specific
    formatter selector as well as an API for cogs to register/un-register a formatter with the bot.

    When implementing your own formatter, at minimum you must provide an implementation of
    `send_help` with identical signature.

    While this exists as a class for easy partial overriding, most implementations
    should not need or want a shared state.
    """

    async def send_help(self, ctx: Context, help_for: HelpTarget = None):
        """
        This delegates to other functions.

        For most cases, you should use this and only this directly.
        """

        help_config = await HelpSettings.from_context(ctx)

        if help_for is None or isinstance(help_for, dpy_commands.bot.BotBase):
            await self.format_bot_help(ctx, help_config=help_config)
            return

        if isinstance(help_for, str):
            try:
                help_for = self.parse_command(ctx, help_for)
            except NoCommand:
                await self.command_not_found(ctx, help_for, help_config=help_config)
                return
            except NoSubCommand as exc:
                if help_config.verify_exists:
                    await self.subcommand_not_found(
                        ctx, exc.last, exc.not_found, help_config=help_config
                    )
                    return
                help_for = exc.last

        if isinstance(help_for, commands.Cog):
            await self.format_cog_help(ctx, help_for, help_config=help_config)
        else:
            await self.format_command_help(ctx, help_for, help_config=help_config)

    async def get_cog_help_mapping(
        self, ctx: Context, obj: commands.Cog, help_config: HelpSettings
    ):
        iterator = filter(lambda c: c.parent is None and c.cog is obj, ctx.bot.commands)
        return {
            com.name: com
            async for com in self.help_filter_func(ctx, iterator, help_config=help_config)
        }

    async def get_group_help_mapping(
        self, ctx: Context, obj: commands.Group, help_config: HelpSettings
    ):
        return {
            com.name: com
            async for com in self.help_filter_func(
                ctx, obj.all_commands.values(), help_config=help_config
            )
        }

    async def get_bot_help_mapping(self, ctx, help_config: HelpSettings):
        sorted_iterable = []
        for cogname, cog in (*sorted(ctx.bot.cogs.items()), (None, None)):
            cm = await self.get_cog_help_mapping(ctx, cog, help_config=help_config)
            if cm:
                sorted_iterable.append((cogname, cm))
        return sorted_iterable

    @staticmethod
    def get_default_tagline(ctx: Context):
        return T_(
            "Type {ctx.clean_prefix}help <command> for more info on a command. "
            "You can also type {ctx.clean_prefix}help <category> for more info on a category."
        ).format(ctx=ctx)

    async def format_command_help(
        self, ctx: Context, obj: commands.Command, help_config: HelpSettings
    ):

        send = help_config.verify_exists
        if not send:
            async for _ in self.help_filter_func(
                ctx, (obj,), bypass_hidden=True, help_config=help_config
            ):
                # This is a really lazy option for not
                # creating a separate single case version.
                # It is efficient though
                #
                # We do still want to bypass the hidden requirement on
                # a specific command explicitly invoked here.
                send = True

        if not send:
            return

        command = obj

        description = command.description or ""

        tagline = (help_config.tagline) or self.get_default_tagline(ctx)
        signature = (
            f"`{T_('Syntax')}: {ctx.clean_prefix}{command.qualified_name} {command.signature}`"
        )
        subcommands = None

        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(ctx, grp, help_config=help_config)

        if await ctx.embed_requested():
            emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

            if description:
                emb["embed"]["title"] = f"*{description[:250]}*"

            emb["footer"]["text"] = tagline
            emb["embed"]["description"] = signature

            command_help = command.format_help_for_context(ctx)
            if command_help:
                splitted = command_help.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(name[:250], value[:1024], False)
                emb["fields"].append(field)

            if subcommands:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                subtext = "\n".join(
                    shorten_line(f"**{name}** {command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(subcommands.items())
                )
                for i, page in enumerate(pagify(subtext, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = T_("**__Subcommands:__**")
                    else:
                        title = T_("**__Subcommands:__** (continued)")
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_config=help_config)

        else:  # Code blocks:

            subtext = None
            subtext_header = None
            if subcommands:
                subtext_header = T_("Subcommands:")
                max_width = max(discord.utils._string_width(name) for name in subcommands.keys())

                def width_maker(cmds):
                    doc_max_width = 80 - max_width
                    for nm, com in sorted(cmds):
                        width_gap = discord.utils._string_width(nm) - len(nm)
                        doc = com.format_shortdoc_for_context(ctx)
                        if len(doc) > doc_max_width:
                            doc = doc[: doc_max_width - 3] + "..."
                        yield nm, doc, max_width - width_gap

                subtext = "\n".join(
                    f"  {name:<{width}} {doc}"
                    for name, doc, width in width_maker(subcommands.items())
                )

            to_page = "\n\n".join(
                filter(
                    None,
                    (
                        description,
                        signature[1:-1],
                        command.format_help_for_context(ctx),
                        subtext_header,
                        subtext,
                    ),
                )
            )
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False)

    @staticmethod
    def group_embed_fields(fields: List[EmbedField], max_chars=1000):

        curr_group = []
        ret = []
        current_count = 0

        for i, f in enumerate(fields):
            f_len = len(f.value) + len(f.name)

            # Commands start at the 1st index of fields, i < 2 is a hacky workaround for now
            if not current_count or f_len + current_count < max_chars or i < 2:
                current_count += f_len
                curr_group.append(f)
            elif curr_group:
                ret.append(curr_group)
                current_count = f_len
                curr_group = [f]
        else:
            if curr_group:
                ret.append(curr_group)

        return ret

    async def make_and_send_embeds(self, ctx, embed_dict: dict, help_config: HelpSettings):

        pages = []

        page_char_limit = help_config.page_char_limit
        page_char_limit = min(page_char_limit, 5500)  # Just in case someone was manually...

        author_info = {
            "name": f"{ctx.me.display_name} {T_('Help Menu')}",
            "icon_url": ctx.me.avatar_url,
        }

        # Offset calculation here is for total embed size limit
        # 20 accounts for# *Page {i} of {page_count}*
        offset = len(author_info["name"]) + 20
        foot_text = embed_dict["footer"]["text"]
        if foot_text:
            offset += len(foot_text)
        offset += len(embed_dict["embed"]["description"])
        offset += len(embed_dict["embed"]["title"])

        # In order to only change the size of embeds when neccessary for this rather
        # than change the existing behavior for people uneffected by this
        # we're only modifying the page char limit should they be impacted.
        # We could consider changing this to always just subtract the offset,
        # But based on when this is being handled (very end of 3.2 release)
        # I'd rather not stick a major visual behavior change in at the last moment.
        if page_char_limit + offset > 5500:
            # This is still neccessary with the max interaction above
            # While we could subtract 100% of the time the offset from page_char_limit
            # the intent here is to shorten again
            # *only* when neccessary, by the exact neccessary amount
            # To retain a visual match with prior behavior.
            page_char_limit = 5500 - offset
        elif page_char_limit < 250:
            # Prevents an edge case where a combination of long cog help and low limit
            # Could prevent anything from ever showing up.
            # This lower bound is safe based on parts of embed in use.
            page_char_limit = 250

        field_groups = self.group_embed_fields(embed_dict["fields"], page_char_limit)

        color = await ctx.embed_color()
        page_count = len(field_groups)

        if not field_groups:  # This can happen on single command without a docstring
            embed = discord.Embed(color=color, **embed_dict["embed"])
            embed.set_author(**author_info)
            embed.set_footer(**embed_dict["footer"])
            pages.append(embed)

        for i, group in enumerate(field_groups, 1):
            embed = discord.Embed(color=color, **embed_dict["embed"])

            if page_count > 1:
                description = T_(
                    "*Page {page_num} of {page_count}*\n{content_description}"
                ).format(content_description=embed.description, page_num=i, page_count=page_count)
                embed.description = description

            embed.set_author(**author_info)

            for field in group:
                embed.add_field(**field._asdict())

            embed.set_footer(**embed_dict["footer"])

            pages.append(embed)

        await self.send_pages(ctx, pages, embed=True)

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_config: HelpSettings):

        coms = await self.get_cog_help_mapping(ctx, obj, help_config=help_config)
        if not (coms or help_config.verify_exists):
            return

        description = obj.format_help_for_context(ctx)
        tagline = (help_config.tagline) or self.get_default_tagline(ctx)

        if await ctx.embed_requested():
            emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

            emb["footer"]["text"] = tagline
            if description:
                splitted = description.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(name[:252], value[:1024], False)
                emb["fields"].append(field)

            if coms:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                command_text = "\n".join(
                    shorten_line(f"**{name}** {command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(coms.items())
                )
                for i, page in enumerate(pagify(command_text, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = T_("**__Commands:__**")
                    else:
                        title = T_("**__Commands:__** (continued)")
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_config=help_config)

        else:
            subtext = None
            subtext_header = None
            if coms:
                subtext_header = T_("Commands:")
                max_width = max(discord.utils._string_width(name) for name in coms.keys())

                def width_maker(cmds):
                    doc_max_width = 80 - max_width
                    for nm, com in sorted(cmds):
                        width_gap = discord.utils._string_width(nm) - len(nm)
                        doc = com.format_shortdoc_for_context(ctx)
                        if len(doc) > doc_max_width:
                            doc = doc[: doc_max_width - 3] + "..."
                        yield nm, doc, max_width - width_gap

                subtext = "\n".join(
                    f"  {name:<{width}} {doc}" for name, doc, width in width_maker(coms.items())
                )

            to_page = "\n\n".join(filter(None, (description, subtext_header, subtext)))
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False)

    async def format_bot_help(self, ctx: Context, help_config: HelpSettings):

        coms = await self.get_bot_help_mapping(ctx, help_config=help_config)
        if not coms:
            return

        description = ctx.bot.description or ""
        tagline = (help_config.tagline) or self.get_default_tagline(ctx)

        if await ctx.embed_requested():

            emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

            emb["footer"]["text"] = tagline
            if description:
                emb["embed"]["title"] = f"*{description[:250]}*"

            for cog_name, data in coms:

                if cog_name:
                    title = f"**__{cog_name}:__**"
                else:
                    title = f"**__{T_('No Category')}:__**"

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                cog_text = "\n".join(
                    shorten_line(f"**{name}** {command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(data.items())
                )

                for i, page in enumerate(pagify(cog_text, page_length=1000, shorten_by=0)):
                    title = title if i < 1 else f"{title} {T_('(continued)')}"
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_config=help_config)

        else:
            to_join = []
            if description:
                to_join.append(f"{description}\n")

            names = []
            for k, v in coms:
                names.extend(list(v.name for v in v.values()))

            max_width = max(
                discord.utils._string_width((name or T_("No Category:"))) for name in names
            )

            def width_maker(cmds):
                doc_max_width = 80 - max_width
                for nm, com in cmds:
                    width_gap = discord.utils._string_width(nm) - len(nm)
                    doc = com.format_shortdoc_for_context(ctx)
                    if len(doc) > doc_max_width:
                        doc = doc[: doc_max_width - 3] + "..."
                    yield nm, doc, max_width - width_gap

            for cog_name, data in coms:

                title = f"{cog_name}:" if cog_name else T_("No Category:")
                to_join.append(title)

                for name, doc, width in width_maker(sorted(data.items())):
                    to_join.append(f"  {name:<{width}} {doc}")

            to_join.append(f"\n{tagline}")
            to_page = "\n".join(to_join)
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False)

    @staticmethod
    async def help_filter_func(
        ctx, objects: Iterable[SupportsCanSee], help_config: HelpSettings, bypass_hidden=False,
    ) -> AsyncIterator[SupportsCanSee]:
        """
        This does most of actual filtering.
        """
        show_hidden = bypass_hidden or help_config.show_hidden
        verify_checks = help_config.verify_checks

        # TODO: Settings for this in core bot db
        for obj in objects:
            if verify_checks and not show_hidden:
                # Default Red behavior, can_see includes a can_run check.
                if await obj.can_see(ctx) and getattr(obj, "enabled", True):
                    yield obj
            elif verify_checks:
                try:
                    can_run = await obj.can_run(ctx)
                except discord.DiscordException:
                    can_run = False
                if can_run and getattr(obj, "enabled", True):
                    yield obj
            elif not show_hidden:
                if not getattr(obj, "hidden", False):  # Cog compatibility
                    yield obj
            else:
                yield obj

    async def command_not_found(self, ctx, help_for, help_config: HelpSettings):
        """
        Sends an error, fuzzy help, or stays quiet based on settings
        """
        coms = {
            c
            async for c in self.help_filter_func(
                ctx, ctx.bot.walk_commands(), help_config=help_config
            )
        }
        fuzzy_commands = await fuzzy_command_search(ctx, help_for, commands=coms, min_score=75)
        use_embeds = await ctx.embed_requested()
        if fuzzy_commands:
            ret = await format_fuzzy_results(ctx, fuzzy_commands, embed=use_embeds)
            if use_embeds:
                ret.set_author(
                    name=f"{ctx.me.display_name} {T_('Help Menu')}", icon_url=ctx.me.avatar_url
                )
                tagline = help_config.tagline or self.get_default_tagline(ctx)
                ret.set_footer(text=tagline)
                await ctx.send(embed=ret)
            else:
                await ctx.send(ret)
        elif help_config.verify_exists:
            ret = T_("Help topic for *{command_name}* not found.").format(command_name=help_for)
            if use_embeds:
                ret = discord.Embed(color=(await ctx.embed_color()), description=ret)
                ret.set_author(
                    name=f"{ctx.me.display_name} {T_('Help Menu')}", icon_url=ctx.me.avatar_url
                )
                tagline = help_config.tagline or self.get_default_tagline(ctx)
                ret.set_footer(text=tagline)
                await ctx.send(embed=ret)
            else:
                await ctx.send(ret)

    async def subcommand_not_found(self, ctx, command, not_found, help_config: HelpSettings):
        """
        Sends an error
        """
        ret = T_("Command *{command_name}* has no subcommand named *{not_found}*.").format(
            command_name=command.qualified_name, not_found=not_found[0]
        )
        if await ctx.embed_requested():
            ret = discord.Embed(color=(await ctx.embed_color()), description=ret)
            ret.set_author(
                name=f"{ctx.me.display_name} {T_('Help Menu')}", icon_url=ctx.me.avatar_url
            )
            tagline = help_config.tagline or self.get_default_tagline(ctx)
            ret.set_footer(text=tagline)
            await ctx.send(embed=ret)
        else:
            await ctx.send(ret)

    @staticmethod
    def parse_command(ctx, help_for: str):
        """
        Handles parsing
        """

        maybe_cog = ctx.bot.get_cog(help_for)
        if maybe_cog:
            return maybe_cog

        com = ctx.bot
        last = None

        clist = help_for.split()

        for index, item in enumerate(clist):
            try:
                com = com.all_commands[item]
                # TODO: This doesn't handle valid command aliases.
                # swap parsing method to use get_command.
            except (KeyError, AttributeError):
                if last:
                    raise NoSubCommand(last=last, not_found=clist[index:]) from None
                else:
                    raise NoCommand() from None
            else:
                last = com

        return com

    async def send_pages(
        self, ctx: Context, pages: List[Union[str, discord.Embed]], embed: bool = True
    ):
        """
        Sends pages based on settings.
        """

        # save on config calls
        config_help = await ctx.bot._config.help()
        channel_permissions = ctx.channel.permissions_for(ctx.me)

        if not (channel_permissions.add_reactions and config_help["use_menus"]):

            max_pages_in_guild = config_help["max_pages_in_guild"]
            use_DMs = len(pages) > max_pages_in_guild
            destination = ctx.author if use_DMs else ctx.channel
            delete_delay = config_help["delete_delay"]

            messages: List[discord.Message] = []
            for page in pages:
                try:
                    if embed:
                        msg = await destination.send(embed=page)
                    else:
                        msg = await destination.send(page)
                except discord.Forbidden:
                    return await ctx.send(
                        T_(
                            "I couldn't send the help message to you in DM. "
                            "Either you blocked me or you disabled DMs in this server."
                        )
                    )
                else:
                    messages.append(msg)

            # The if statement takes into account that 'destination' will be
            # the context channel in non-DM context, reusing 'channel_permissions' to avoid
            # computing the permissions twice.
            if (
                not use_DMs  # we're not in DMs
                and delete_delay > 0  # delete delay is enabled
                and channel_permissions.manage_messages  # we can manage messages here
            ):

                # We need to wrap this in a task to not block after-sending-help interactions.
                # The channel has to be TextChannel as we can't bulk-delete from DMs
                async def _delete_delay_help(
                    channel: discord.TextChannel, messages: List[discord.Message], delay: int
                ):
                    await asyncio.sleep(delay)
                    await mass_purge(messages, channel)

                asyncio.create_task(_delete_delay_help(destination, messages, delete_delay))
        else:
            # Specifically ensuring the menu's message is sent prior to returning
            m = await (ctx.send(embed=pages[0]) if embed else ctx.send(pages[0]))
            c = menus.DEFAULT_CONTROLS if len(pages) > 1 else {"\N{CROSS MARK}": menus.close_menu}
            # Allow other things to happen during menu timeout/interaction.
            asyncio.create_task(menus.menu(ctx, pages, c, message=m))
            # menu needs reactions added manually since we fed it a messsage
            menus.start_adding_reactions(m, c.keys())


@commands.command(name="help", hidden=True, i18n=T_)
async def red_help(ctx: Context, *, thing_to_get_help_for: str = None):
    """
    I need somebody
    (Help) not just anybody
    (Help) you know I need someone
    (Help!)
    """
    await ctx.bot.send_help_for(ctx, thing_to_get_help_for)
