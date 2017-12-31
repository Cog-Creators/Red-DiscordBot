import asyncio
import importlib
import itertools
import logging
import sys
from collections import namedtuple
from random import SystemRandom
from string import ascii_letters, digits

import aiohttp
import datetime
import discord
from discord.ext import commands

from redbot.core import checks
from redbot.core import i18n
from redbot.core import rpc
from redbot.core import __version__
from redbot.core.context import RedContext

from .utils import TYPE_CHECKING
from .utils.chat_formatting import pagify, box

if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["Core"]

log = logging.getLogger("red")

OWNER_DISCLAIMER = ("⚠ **Only** the person who is hosting Red should be "
                    "owner. **This has SERIOUS security implications. The "
                    "owner can access any data that is present on the host "
                    "system.** ⚠")


_ = i18n.CogI18n("Core", __file__)


class Core:
    """Commands related to core functions"""
    def __init__(self, bot):
        self.bot = bot  # type: Red

        rpc.add_method('core', self.rpc_load)
        rpc.add_method('core', self.rpc_unload)
        rpc.add_method('core', self.rpc_reload)

    @commands.command()
    async def info(self, ctx: RedContext):
        """Shows info about Red"""
        author_repo = "https://github.com/Twentysix26"
        org_repo = "https://github.com/Cog-Creators"
        red_repo = org_repo + "/Red-DiscordBot"
        red_pypi = "https://pypi.python.org/pypi/Red-DiscordBot"
        support_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days
        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        python_version = "[{}.{}.{}]({})".format(
            *sys.version_info[:3], python_url
        )
        red_version = "[{}]({})".format(__version__, red_pypi)
        app_info = await self.bot.application_info()
        owner = app_info.owner

        about = (
            "This is an instance of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "".format(red_repo, author_repo, org_repo, support_server_url))

        embed = discord.Embed(color=discord.Color.red())
        embed.add_field(name="Instance owned by", value=str(owner))
        embed.add_field(name="Python", value=python_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name="Red version", value=red_version)
        embed.add_field(name="About Red", value=about, inline=False)
        embed.set_footer(text="Bringing joy since 02 Jan 2016 (over "
                         "{} days ago!)".format(days_since))
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("I need the `Embed links` permission to send this")

    @commands.command()
    @checks.is_owner()
    async def traceback(self, ctx, public: bool=False):
        """Sends to the owner the last command exception that has occurred

        If public (yes is specified), it will be sent to the chat instead"""
        if not public:
            destination = ctx.author
        else:
            destination = ctx.channel

        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception):
                await destination.send(box(page, lang="py"))
        else:
            await ctx.send("No exception has occurred yet")

    @commands.command()
    @checks.is_owner()
    async def invite(self, ctx):
        """Show's Red's invite url"""
        if self.bot.user.bot:
            await ctx.author.send(discord.utils.oauth_url(self.bot.user.id))
        else:
            await ctx.send("I'm not a bot account. I have no invite URL.")

    @commands.command()
    @commands.guild_only()
    @checks.is_owner()
    async def leave(self, ctx):
        """Leaves server"""
        author = ctx.author
        guild = ctx.guild

        await ctx.send("Are you sure you want me to leave this server?"
                       " Type yes to confirm.")

        def conf_check(m):
            return m.author == author

        response = await self.bot.wait_for("message", check=conf_check)

        if response.content.lower().strip() == "yes":
            await ctx.send("Alright. Bye :wave:")
            log.debug("Leaving '{}'".format(guild.name))
            await guild.leave()

    @commands.command()
    @checks.is_owner()
    async def servers(self, ctx):
        """Lists and allows to leave servers"""
        owner = ctx.author
        guilds = sorted(list(self.bot.guilds),
                        key=lambda s: s.name.lower())
        msg = ""
        for i, server in enumerate(guilds):
            msg += "{}: {}\n".format(i, server.name)

        msg += "\nTo leave a server, just type its number."

        for page in pagify(msg, ['\n']):
            await ctx.send(page)

        def msg_check(m):
            return m.author == owner

        while msg is not None:
            msg = await self.bot.wait_for("message", check=msg_check, timeout=15)
            try:
                msg = int(msg.content)
                await self.leave_confirmation(guilds[msg], owner, ctx)
                break
            except (IndexError, ValueError, AttributeError):
                pass

    async def leave_confirmation(self, server, owner, ctx):
        await ctx.send("Are you sure you want me to leave {}? (yes/no)".format(server.name))

        def conf_check(m):
            return m.author == owner

        msg = await self.bot.wait_for("message", check=conf_check, timeout=15)

        if msg is None:
            await ctx.send("I guess not.")
        elif msg.content.lower().strip() in ("yes", "y"):
            await server.leave()
            if server != ctx.guild:
                await ctx.send("Done.")
        else:
            await ctx.send("Alright then.")

    @commands.command()
    @checks.is_owner()
    async def load(self, ctx, *, cog_name: str):
        """Loads a package"""
        try:
            spec = await ctx.bot.cog_mgr.find_cog(cog_name)
        except RuntimeError:
            await ctx.send(_("No module by that name was found in any"
                             " cog path."))
            return

        try:
            ctx.bot.load_extension(spec)
        except Exception as e:
            log.exception("Package loading failed", exc_info=e)
            await ctx.send(_("Failed to load package. Check your console or "
                             "logs for details."))
        else:
            await ctx.bot.add_loaded_package(cog_name)
            await ctx.send(_("Done."))

    @commands.group()
    @checks.is_owner()
    async def unload(self, ctx, *, cog_name: str):
        """Unloads a package"""
        if cog_name in ctx.bot.extensions:
            ctx.bot.unload_extension(cog_name)
            await ctx.bot.remove_loaded_package(cog_name)
            await ctx.send(_("Done."))
        else:
            await ctx.send(_("That extension is not loaded."))

    @commands.command(name="reload")
    @checks.is_owner()
    async def _reload(self, ctx, *, cog_name: str):
        """Reloads a package"""
        ctx.bot.unload_extension(cog_name)

        try:
            spec = await ctx.bot.cog_mgr.find_cog(cog_name)
        except RuntimeError:
            await ctx.send(_("No module by that name was found in any"
                             " cog path."))
            return

        try:
            self.cleanup_and_refresh_modules(spec.name)
            ctx.bot.load_extension(spec)
        except Exception as e:
            log.exception("Package reloading failed", exc_info=e)
            await ctx.send(_("Failed to reload package. Check your console or "
                             "logs for details."))
        else:
            await ctx.send(_("Done."))

    @commands.command(name="shutdown")
    @checks.is_owner()
    async def _shutdown(self, ctx, silently: bool=False):
        """Shuts down the bot"""
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        try:  # We don't want missing perms to stop our shutdown
            if not silently:
                await ctx.send(_("Shutting down... ") + wave + skin)
        except:
            pass
        await ctx.bot.shutdown()

    def cleanup_and_refresh_modules(self, module_name: str):
        """Interally reloads modules so that changes are detected"""
        splitted = module_name.split('.')

        def maybe_reload(new_name):
            try:
                lib = sys.modules[new_name]
            except KeyError:
                pass
            else:
                importlib._bootstrap._exec(lib.__spec__, lib)

        modules = itertools.accumulate(splitted, "{}.{}".format)
        for m in modules:
            maybe_reload(m)

        children = {name: lib for name, lib in sys.modules.items() if name.startswith(module_name)}
        for child_name, lib in children.items():
            importlib._bootstrap._exec(lib.__spec__, lib)

    @commands.group(name="set")
    async def _set(self, ctx):
        """Changes Red's settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def adminrole(self, ctx, *, role: discord.Role):
        """Sets the admin role for this server"""
        await ctx.bot.db.guild(ctx.guild).admin_role.set(role.id)
        await ctx.send(_("The admin role for this guild has been set."))

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def modrole(self, ctx, *, role: discord.Role):
        """Sets the mod role for this server"""
        await ctx.bot.db.guild(ctx.guild).mod_role.set(role.id)
        await ctx.send(_("The mod role for this guild has been set."))

    @_set.command()
    @checks.is_owner()
    async def avatar(self, ctx, url: str):
        """Sets Red's avatar"""
        session = aiohttp.ClientSession()
        async with session.get(url) as r:
            data = await r.read()
        await session.close()

        try:
            await ctx.bot.user.edit(avatar=data)
        except discord.HTTPException:
            await ctx.send(_("Failed. Remember that you can edit my avatar "
                             "up to two times a hour. The URL must be a "
                             "direct link to a JPG / PNG."))
        except discord.InvalidArgument:
            await ctx.send(_("JPG / PNG format only."))
        else:
            await ctx.send(_("Done."))

    @_set.command(name="game")
    @checks.is_owner()
    @commands.guild_only()
    async def _game(self, ctx, *, game: str=None):
        """Sets Red's playing status"""
        status = ctx.me.status
        if game:
            game = discord.Game(name=game)
        else:
            game = None
        await ctx.bot.change_presence(status=status, game=game)
        await ctx.send(_("Game set."))

    @_set.command()
    @checks.is_owner()
    @commands.guild_only()
    async def status(self, ctx, *, status: str):
        """Sets Red's status
        Available statuses:
            online
            idle
            dnd
            invisible"""

        statuses = {
                    "online"    : discord.Status.online,
                    "idle"      : discord.Status.idle,
                    "dnd"       : discord.Status.dnd,
                    "invisible" : discord.Status.invisible
                   }

        game = ctx.me.game

        try:
            status = statuses[status.lower()]
        except KeyError:
            await ctx.send_help()
        else:
            await ctx.bot.change_presence(status=status,
                                          game=game)
            await ctx.send(_("Status changed to %s.") % status)

    @_set.command()
    @checks.is_owner()
    @commands.guild_only()
    async def stream(self, ctx, streamer=None, *, stream_title=None):
        """Sets Red's streaming status
        Leaving both streamer and stream_title empty will clear it."""

        status = ctx.me.status

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            game = discord.Game(type=1, url=streamer, name=stream_title)
            await ctx.bot.change_presence(game=game, status=status)
        elif streamer is not None:
            await ctx.send_help()
            return
        else:
            await ctx.bot.change_presence(game=None, status=status)
        await ctx.send(_("Done."))

    @_set.command(name="username", aliases=["name"])
    @checks.is_owner()
    async def _username(self, ctx, *, username: str):
        """Sets Red's username"""
        try:
            await ctx.bot.user.edit(username=username)
        except discord.HTTPException:
            await ctx.send(_("Failed to change name. Remember that you can "
                             "only do it up to 2 times an hour. Use "
                             "nicknames if you need frequent changes. "
                             "`{}set nickname`").format(ctx.prefix))
        else:
            await ctx.send(_("Done."))

    @_set.command(name="nickname")
    @checks.admin()
    @commands.guild_only()
    async def _nickname(self, ctx, *, nickname: str):
        """Sets Red's nickname"""
        try:
            await ctx.bot.user.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to change my own "
                             "nickname."))
        else:
            await ctx.send("Done.")

    @_set.command(aliases=["prefixes"])
    @checks.is_owner()
    async def prefix(self, ctx, *prefixes):
        """Sets Red's global prefix(es)"""
        if not prefixes:
            await ctx.send_help()
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.db.prefix.set(prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command(aliases=["serverprefixes"])
    @checks.admin()
    @commands.guild_only()
    async def serverprefix(self, ctx, *prefixes):
        """Sets Red's server prefix(es)"""
        if not prefixes:
            await ctx.bot.db.guild(ctx.guild).prefix.set([])
            await ctx.send(_("Guild prefixes have been reset."))
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.db.guild(ctx.guild).prefix.set(prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command()
    @commands.cooldown(1, 60 * 10, commands.BucketType.default)
    async def owner(self, ctx):
        """Sets Red's main owner"""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # According to the Python docs this is suitable for cryptographic use
        random = SystemRandom()
        length = random.randint(25, 35)
        chars = ascii_letters + digits
        token = ""

        for i in range(length):
            token += random.choice(chars)
        log.info("{0} ({0.id}) requested to be set as owner."
                 "".format(ctx.author))
        print(_("\nVerification token:"))
        print(token)

        await ctx.send(_("Remember:\n") + OWNER_DISCLAIMER)
        await asyncio.sleep(5)

        await ctx.send(_("I have printed a one-time token in the console. "
                         "Copy and paste it here to confirm you are the owner."))

        try:
            message = await ctx.bot.wait_for("message", check=check,
                                             timeout=60)
        except asyncio.TimeoutError:
            self.owner.reset_cooldown(ctx)
            await ctx.send(_("The set owner request has timed out."))
        else:
            if message.content.strip() == token:
                self.owner.reset_cooldown(ctx)
                await ctx.bot.db.owner.set(ctx.author.id)
                ctx.bot.owner_id = ctx.author.id
                await ctx.send(_("You have been set as owner."))
            else:
                await ctx.send(_("Invalid token."))

    @_set.command()
    @checks.is_owner()
    async def locale(self, ctx: commands.Context, locale_name: str):
        """
        Changes bot locale.
        """
        i18n.set_locale(locale_name)

        await ctx.bot.db.locale.set(locale_name)

        await ctx.send(_("Locale has been set."))

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx, *, message: str):
        """Sends a message to the owner"""
        guild = ctx.message.guild
        owner = discord.utils.get(ctx.bot.get_all_members(),
                                  id=ctx.bot.owner_id)
        author = ctx.message.author
        footer = _("User ID: %s") % author.id

        if ctx.guild is None:
            source = _("through DM")
        else:
            source = _("from {}").format(guild)
            footer += _(" | Server ID: %s") % guild.id

        # We need to grab the DM command prefix (global)
        # Since it can also be set through cli flags, bot.db is not a reliable
        # source. So we'll just mock a DM message instead.
        fake_message = namedtuple('Message', 'guild')
        prefixes = await ctx.bot.command_prefix(ctx.bot, fake_message(guild=None))
        prefix = prefixes[0]

        content = _("Use `{}dm {} <text>` to reply to this user"
                    "").format(prefix, author.id)

        if isinstance(author, discord.Member):
            colour = author.colour
        else:
            colour = discord.Colour.red()

        description = _("Sent by {} {}").format(author, source)

        e = discord.Embed(colour=colour, description=message)
        if author.avatar_url:
            e.set_author(name=description, icon_url=author.avatar_url)
        else:
            e.set_author(name=description)
        e.set_footer(text=footer)

        try:
            await owner.send(content, embed=e)
        except discord.InvalidArgument:
            await ctx.send(_("I cannot send your message, I'm unable to find "
                             "my owner... *sigh*"))
        except:
            await ctx.send(_("I'm unable to deliver your message. Sorry."))
        else:
            await ctx.send(_("Your message has been sent."))

    @commands.command()
    @checks.is_owner()
    async def dm(self, ctx, user_id: int, *, message: str):
        """Sends a DM to a user

        This command needs a user id to work.
        To get a user id enable 'developer mode' in Discord's
        settings, 'appearance' tab. Then right click a user
        and copy their id"""
        destination = discord.utils.get(ctx.bot.get_all_members(),
                                        id=user_id)
        if destination is None:
            await ctx.send(_("Invalid ID or user not found. You can only "
                             "send messages to people I share a server "
                             "with."))
            return

        e = discord.Embed(colour=discord.Colour.red(), description=message)
        description = _("Owner of %s") % ctx.bot.user
        fake_message = namedtuple('Message', 'guild')
        prefixes = await ctx.bot.command_prefix(ctx.bot, fake_message(guild=None))
        prefix = prefixes[0]
        e.set_footer(text=_("You can reply to this message with %scontact"
                            "") % prefix)
        if ctx.bot.user.avatar_url:
            e.set_author(name=description, icon_url=ctx.bot.user.avatar_url)
        else:
            e.set_author(name=description)

        try:
            await destination.send(embed=e)
        except:
            await ctx.send(_("Sorry, I couldn't deliver your message "
                             "to %s") % destination)
        else:
            await ctx.send(_("Message delivered to %s") % destination)

    @commands.group()
    @checks.is_owner()
    async def whitelist(self, ctx):
        """
        Whitelist management commands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @whitelist.command(name='add')
    async def whitelist_add(self, ctx, user: discord.User):
        """
        Adds a user to the whitelist.
        """
        async with ctx.bot.db.whitelist() as curr_list:
            if user.id not in curr_list:
                curr_list.append(user.id)

        await ctx.send(_("User added to whitelist."))

    @whitelist.command(name='list')
    async def whitelist_list(self, ctx):
        """
        Lists whitelisted users.
        """
        curr_list = await ctx.bot.db.whitelist()

        msg = _("Whitelisted Users:")
        for user in curr_list:
            msg.append("\n\t- {}".format(user))

        for page in pagify(msg):
            await ctx.send(box(page))

    @whitelist.command(name='remove')
    async def whitelist_remove(self, ctx, user: discord.User):
        """
        Removes user from whitelist.
        """
        removed = False

        async with ctx.bot.db.whitelist() as curr_list:
            if user.id in curr_list:
                removed = True
                curr_list.remove(user.id)

        if removed:
            await ctx.send(_("User has been removed from whitelist."))
        else:
            await ctx.send(_("User was not in the whitelist."))
            
    @whitelist.command(name='clear')
    async def whitelist_clear(self, ctx):
        """
        Clears the whitelist.
        """
        await ctx.bot.db.whitelist.set([])
        await ctx.send(_("Whitelist has been cleared."))

    @commands.group()
    @checks.is_owner()
    async def blacklist(self, ctx):
        """
        blacklist management commands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @blacklist.command(name='add')
    async def blacklist_add(self, ctx, user: discord.User):
        """
        Adds a user to the blacklist.
        """
        if await ctx.bot.is_owner(user):
            ctx.send(_("You cannot blacklist an owner!"))
            return

        async with ctx.bot.db.blacklist() as curr_list:
            if user.id not in curr_list:
                curr_list.append(user.id)

        await ctx.send(_("User added to blacklist."))

    @blacklist.command(name='list')
    async def blacklist_list(self, ctx):
        """
        Lists blacklisted users.
        """
        curr_list = await ctx.bot.db.blacklist()

        msg = _("blacklisted Users:")
        for user in curr_list:
            msg.append("\n\t- {}".format(user))

        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name='remove')
    async def blacklist_remove(self, ctx, user: discord.User):
        """
        Removes user from blacklist.
        """
        removed = False

        async with ctx.bot.db.blacklist() as curr_list:
            if user.id in curr_list:
                removed = True
                curr_list.remove(user.id)

        if removed:
            await ctx.send(_("User has been removed from blacklist."))
        else:
            await ctx.send(_("User was not in the blacklist."))

    @blacklist.command(name='clear')
    async def blacklist_clear(self, ctx):
        """
        Clears the blacklist.
        """
        await ctx.bot.db.blacklist.set([])
        await ctx.send(_("blacklist has been cleared."))

    # RPC handlers
    async def rpc_load(self, request):
        cog_name = request.params[0]

        spec = await self.bot.cog_mgr.find_cog(cog_name)
        if spec is None:
            raise LookupError("No such cog found.")

        self.cleanup_and_refresh_modules(spec.name)

        self.bot.load_extension(spec)

    async def rpc_unload(self, request):
        cog_name = request.params[0]

        self.bot.unload_extension(cog_name)

    async def rpc_reload(self, request):
        await self.rpc_unload(request)
        await self.rpc_load(request)

