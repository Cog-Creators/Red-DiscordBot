import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify
from copy import deepcopy
import asyncio
import logging
import os


log = logging.getLogger("red.admin")


class Admin:
    """Admin tools, more to come."""

    def __init__(self, bot):
        self.bot = bot
        self._announce_msg = None
        self._announce_server = None
        self._settings = dataIO.load_json('data/admin/settings.json')
        self._settable_roles = self._settings.get("ROLES", {})

    async def _confirm_invite(self, server, owner, ctx):
        answers = ("yes", "y")
        invite = await self.bot.create_invite(server)
        if ctx.message.channel.is_private:
            await self.bot.say(invite)
        else:
            await self.bot.say("Are you sure you want to post an invite to {} "
                               "here? (yes/no)".format(server.name))
            msg = await self.bot.wait_for_message(author=owner, timeout=15)
            if msg is None:
                await self.bot.say("I guess not.")
            elif msg.content.lower().strip() in answers:
                await self.bot.say(invite)
            else:
                await self.bot.say("Alright then.")

    def _get_selfrole_names(self, server):
        if server.id not in self._settable_roles:
            return None
        else:
            return self._settable_roles[server.id]

    def _is_server_locked(self):
        return self._settings.get("SERVER_LOCK", False)

    def _role_from_string(self, server, rolename, roles=None):
        if roles is None:
            roles = server.roles

        roles = [r for r in roles if r is not None]
        role = discord.utils.find(lambda r: r.name.lower() == rolename.lower(),
                                  roles)
        try:
            log.debug("Role {} found from rolename {}".format(
                role.name, rolename))
        except:
            log.debug("Role not found for rolename {}".format(rolename))
        return role

    def _save_settings(self):
        dataIO.save_json('data/admin/settings.json', self._settings)

    def _set_selfroles(self, server, rolelist):
        self._settable_roles[server.id] = rolelist
        self._settings["ROLES"] = self._settable_roles
        self._save_settings()

    def _set_serverlock(self, lock=True):
        self._settings["SERVER_LOCK"] = lock
        self._save_settings()

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def addrole(self, ctx, rolename, user: discord.Member=None):
        """Adds a role to a user, defaults to author

        Role name must be in quotes if there are spaces."""
        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server

        if user is None:
            user = author

        role = self._role_from_string(server, rolename)

        if role is None:
            await self.bot.say('That role cannot be found.')
            return

        if not channel.permissions_for(server.me).manage_roles:
            await self.bot.say('I don\'t have manage_roles.')
            return

        await self.bot.add_roles(user, role)
        await self.bot.say('Added role {} to {}'.format(role.name, user.name))

    @commands.group(pass_context=True, no_pm=True)
    async def adminset(self, ctx):
        """Manage Admin settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @adminset.command(pass_context=True, name="selfroles")
    @checks.admin_or_permissions(manage_roles=True)
    async def adminset_selfroles(self, ctx, *, rolelist=None):
        """Set which roles users can set themselves.

        COMMA SEPARATED LIST (e.g. Admin,Staff,Mod)"""
        server = ctx.message.server
        if rolelist is None:
            await self.bot.say("selfrole list cleared.")
            self._set_selfroles(server, [])
            return
        unparsed_roles = list(map(lambda r: r.strip(), rolelist.split(',')))
        parsed_roles = list(map(lambda r: self._role_from_string(server, r),
                                unparsed_roles))
        if len(unparsed_roles) != len(parsed_roles):
            not_found = set(unparsed_roles) - {r.name for r in parsed_roles}
            await self.bot.say(
                "These roles were not found: {}\n\nPlease"
                " try again.".format(not_found))
        parsed_role_set = list({r.name for r in parsed_roles})
        self._set_selfroles(server, parsed_role_set)
        await self.bot.say(
            "Self roles successfully set to: {}".format(parsed_role_set))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def announce(self, ctx, *, msg):
        """Announces a message to all servers that a bot is in."""
        if self._announce_msg is not None:
            await self.bot.say("Already announcing, wait until complete to"
                               " issue a new announcement.")
        else:
            self._announce_msg = msg
            self._announce_server = ctx.message.server

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def serverlock(self, ctx):
        """Toggles locking the current server list, will not join others"""
        if self._is_server_locked():
            self._set_serverlock(False)
            await self.bot.say("Server list unlocked")
        else:
            self._set_serverlock()
            await self.bot.say("Server list locked.")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def partycrash(self, ctx, idnum=None):
        """Lists servers and generates invites for them"""
        owner = ctx.message.author
        if idnum:
            server = discord.utils.get(self.bot.servers, id=idnum)
            if server:
                await self._confirm_invite(server, owner, ctx)
            else:
                await self.bot.say("I'm not in that server")
        else:
            msg = ""
            servers = sorted(self.bot.servers, key=lambda s: s.name)
            for i, server in enumerate(servers, 1):
                msg += "{}: {}\n".format(i, server.name)
            msg += "\nTo post an invite for a server just type its number."
            for page in pagify(msg, delims=["\n"]):
                await self.bot.say(box(page))
                await asyncio.sleep(1.5)  # Just in case for rate limits
            msg = await self.bot.wait_for_message(author=owner, timeout=15)
            if msg is not None:
                try:
                    msg = int(msg.content.strip())
                    server = servers[msg - 1]
                except ValueError:
                    await self.bot.say("You must enter a number.")
                except IndexError:
                    await self.bot.say("Index out of range.")
                else:
                    try:
                        await self._confirm_invite(server, owner, ctx)
                    except discord.Forbidden:
                        await self.bot.say("I'm not allowed to make an invite"
                                           " for {}".format(server.name))
            else:
                await self.bot.say("Response timed out.")

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def removerole(self, ctx, rolename, user: discord.Member=None):
        """Removes a role from user, defaults to author

        Role name must be in quotes if there are spaces."""
        server = ctx.message.server
        author = ctx.message.author

        role = self._role_from_string(server, rolename)
        if role is None:
            await self.bot.say("Role not found.")
            return

        if user is None:
            user = author

        if role in user.roles:
            try:
                await self.bot.remove_roles(user, role)
                await self.bot.say("Role successfully removed.")
            except discord.Forbidden:
                await self.bot.say("I don't have permissions to manage roles!")
        else:
            await self.bot.say("User does not have that role.")

    @commands.command(pass_context=True, no_pm=True)
    async def say(self, ctx, *, text):
        """Bot repeats what you tell it to, utility for scheduler."""
        channel = ctx.message.channel
        await self.bot.send_message(channel, text)

    @commands.command(pass_context=True, no_pm=True)
    async def saychan(self, ctx, chan, *, text):
        """Bot said a messages to the channel specified"""
        try:
            server = ctx.message.server
            channel = server.get_channel(chan)
            await self.bot.send_message(channel, text)
        except:
            print(chan)
            print(channel)

    def is_mm():
        def predicate(ctx):
            return ctx.message.channel.id == "260141615971041281"
        return commands.check(predicate)
    
    @commands.command(pass_context=True)
    @is_mm()
    async def mm(self, ctx):
        role = self._role_from_string(ctx.message.server, "mm", roles=ctx.message.author.roles) 
        if(role):
            try:
                await self.bot.remove_roles(ctx.message.author, role)
                await self.bot.say("No longer receiving match requests.")
            except BaseException as e:
                print(e)
        else:
            try:
                role = self._role_from_string(ctx.message.server, "mm", roles=None) 
                await self.bot.add_roles(ctx.message.author, role)
                await self.bot.say("You will now be notified.")
            except BaseException as e:
                print(e)

    @commands.group(no_pm=True, pass_context=True, invoke_without_command=True, aliases=["region", "main"])
    async def selfrole(self, ctx, *, rolename):
        """Allows users to set their own role.

        Configurable using `adminset`"""
        server = ctx.message.server
        author = ctx.message.author
        role_names = self._get_selfrole_names(server)
        if role_names is None:
            await self.bot.say("I have no user settable roles for this"
                               " server.")
            return

        f = self._role_from_string
        roles = [f(server, r) for r in role_names if r is not None]

        role_to_add = self._role_from_string(server, rolename, roles=roles)

        try:
            await self.bot.add_roles(author, role_to_add)
        except discord.errors.Forbidden:
            log.debug("{} just tried to add a role but I was forbidden".format(
                author.name))
            await self.bot.say("I don't have permissions to do that.")
        except AttributeError:  # role_to_add is NoneType
            log.debug("{} not found as settable on {}".format(rolename,
                                                              server.id))
            await self.bot.say("That role isn't user settable.")
        else:
            log.debug("Role {} added to {} on {}".format(rolename, author.name,
                                                         server.id))
            await self.bot.say("Role added.")

    @selfrole.command(no_pm=True, pass_context=True, name="remove")
    async def selfrole_remove(self, ctx, *, rolename):
        """Allows users to remove their own roles

        Configurable using `adminset`"""
        server = ctx.message.server
        author = ctx.message.author
        role_names = self._get_selfrole_names(server)
        if role_names is None:
            await self.bot.say("I have no user settable roles for this"
                               " server.")
            return

        f = self._role_from_string
        roles = [f(server, r) for r in role_names if r is not None]

        role_to_remove = self._role_from_string(server, rolename, roles=roles)

        try:
            await self.bot.remove_roles(author, role_to_remove)
        except discord.errors.Forbidden:
            log.debug("{} just tried to remove a role but I was"
                      " forbidden".format(author.name))
            await self.bot.say("I don't have permissions to do that.")
        except AttributeError:  # role_to_remove is NoneType
            log.debug("{} not found as removeable on {}".format(rolename,
                                                                server.id))
            await self.bot.say("That role isn't user removeable.")
        else:
            log.debug("Role {} removed from {} on {}".format(rolename,
                                                             author.name,
                                                             server.id))
            await self.bot.say("Role removed.")

    @selfrole.command(no_pm=True, pass_context=True, name="list")
    async def selfrole_list(self, ctx):
        """Views all current roles you can assign to yourself.

        Configurable using `adminset`"""
        server = ctx.message.server
        if self._get_selfrole_names(ctx.message.server) is None:
            await self.bot.say("There are no selfroles set.")
        else:
            selfroles = self._settable_roles[server.id]
            if len(selfroles) == 2:
                await self.bot.say("You can currently"
                                   " give yourself\n{}."
                                   "".format(" and ".join(selfroles)))
            else:
                await self.bot.say("You can currently"
                                   "give yourself\n{}."
                                   "".format(", ".join(selfroles)))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def sudo(self, ctx, user: discord.Member, *, command):
        """Runs the [command] as if [user] had run it. DON'T ADD A PREFIX
        """
        new_msg = deepcopy(ctx.message)
        new_msg.author = user
        new_msg.content = self.bot.settings.get_prefixes(new_msg.server)[0] \
            + command
        await self.bot.process_commands(new_msg)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()  # I don't know how permissive this should be yet
    async def whisper(self, ctx, id, *, text):
        author = ctx.message.author

        target = discord.utils.get(self.bot.get_all_members(), id=id)
        if target is None:
            target = self.bot.get_channel(id)
            if target is None:
                target = self.bot.get_server(id)

        prefix = "Hello, you're getting a message from {} ({})".format(
            author.name, author.id)
        payload = "{}\n\n{}".format(prefix, text)

        try:
            for page in pagify(payload, delims=[" ", "\n"], shorten_by=10):
                await self.bot.send_message(target, box(page))
        except discord.errors.Forbidden:
            log.debug("Forbidden to send message to {}".format(id))
        except (discord.errors.NotFound, discord.errors.InvalidArgument):
            log.debug("{} not found!".format(id))
        else:
            await self.bot.say("Done.")

    async def announcer(self, msg):
        server_ids = map(lambda s: s.id, self.bot.servers)
        for server_id in server_ids:
            if self != self.bot.get_cog('Admin'):
                break
            server = self.bot.get_server(server_id)
            if server is None:
                continue
            if server == self._announce_server:
                continue
            chan = server.default_channel
            log.debug("Looking to announce to {} on {}".format(chan.name,
                                                               server.name))
            me = server.me
            if chan.permissions_for(me).send_messages:
                log.debug("I can send messages to {} on {}, sending".format(
                    server.name, chan.name))
                await self.bot.send_message(chan, msg)
            await asyncio.sleep(1)

    async def announce_manager(self):
        while self == self.bot.get_cog('Admin'):
            if self._announce_msg is not None:
                log.debug("Found new announce message, announcing")
                await self.announcer(self._announce_msg)
                self._announce_msg = None
            await asyncio.sleep(1)

    async def server_locker(self, server):
        if self._is_server_locked():
            await self.bot.leave_server(server)


def check_files():
    if not os.path.exists('data/admin/settings.json'):
        try:
            os.mkdir('data/admin')
        except FileExistsError:
            pass
        else:
            dataIO.save_json('data/admin/settings.json', {})


def setup(bot):
    check_files()
    n = Admin(bot)
    bot.add_cog(n)
    bot.add_listener(n.server_locker, "on_server_join")
    bot.loop.create_task(n.announce_manager())
