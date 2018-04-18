import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.converters import GlobalUser
from __main__ import set_cog
from .utils.dataIO import dataIO
from .utils.chat_formatting import pagify, box

import importlib
import traceback
import logging
import asyncio
import threading
import datetime
import glob
import os
import aiohttp
import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM

try:
    import psutil
    psutilAvailable = True
except ImportError:
    psutilAvailable = False

log = logging.getLogger("red.owner")


class CogNotFoundError(Exception):
    pass


class CogLoadError(Exception):
    pass


class NoSetupError(CogLoadError):
    pass


class CogUnloadError(Exception):
    pass


class OwnerUnloadWithoutReloadError(CogUnloadError):
    pass


class Owner:
    """All owner-only commands that relate to debug bot operations."""

    def __init__(self, bot):
        self.bot = bot
        self.setowner_lock = False
        self.disabled_commands = dataIO.load_json("data/red/disabled_commands.json")
        self.global_ignores = dataIO.load_json("data/red/global_ignores.json")
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def __unload(self):
        self.session.close()
    
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def load(self, ctx, *, cog_name: str):
        """Loads a cog

        Example: load mod"""
        author = ctx.message.author
        module = cog_name.strip()
        if "cogs." not in module:
            module = "cogs." + module
        try:
            self._load_cog(module)
        except CogNotFoundError:
            await self.bot.say("That cog could not be found.")
        except CogLoadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.add_reaction(ctx.message, '❌')
                               
        except Exception as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say('-~-\'')
        else:
            set_cog(module, True)
            await self.disable_commands()
            await self.bot.add_reaction(ctx.message, "✅")

    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.is_owner()
    async def unload(self, ctx, *, cog_name: str):
        """Unloads a cog

        Example: unload mod"""
        author = ctx.message.author
        module = cog_name.strip()
        if "cogs." not in module:
            module = "cogs." + module
        if not self._does_cogfile_exist(module):
            await self.bot.say("That cog file doesn't exist. I will not"
                               " turn off autoloading at start just in case"
                               " this isn't supposed to happen.")
        else:
            set_cog(module, False)
        try:  # No matter what we should try to unload it
            self._unload_cog(module)
        except OwnerUnloadWithoutReloadError:
            await self.bot.say("I cannot allow you to unload the Owner plugin"
                               " unless you are in the process of reloading.")
        except CogUnloadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say('Unable to safely unload that cog.')
        else:
            await self.bot.add_reaction(ctx.message, "👌")

    @unload.command(name="all")
    @checks.is_owner()
    async def unload_all(self):
        """Unloads all cogs"""
        cogs = self._list_cogs()
        still_loaded = []
        for cog in cogs:
            set_cog(cog, False)
            try:
                self._unload_cog(cog)
            except OwnerUnloadWithoutReloadError:
                pass
            except CogUnloadError as e:
                log.exception(e)
                traceback.print_exc()
                still_loaded.append(cog)
        if still_loaded:
            still_loaded = ", ".join(still_loaded)
            await self.bot.say("I was unable to unload some cogs: "
                "{}".format(still_loaded))
        else:
            await self.bot.say("All cogs are now unloaded.")

    @checks.is_owner()
    @commands.command(pass_context=True, name="reload", aliases=["re"])
    async def _reload(self, ctx, cog_name: str):
        """Reloads a cog

        Example: reload audio"""
        author = ctx.message.author
        module = cog_name.strip()
        if "cogs." not in module:
            module = "cogs." + module

        try:
            self._unload_cog(module, reloading=True)
        except:
            pass

        try:
            self._load_cog(module)
        except CogNotFoundError:
            await self.bot.say("What cog?")
        except NoSetupError:
            await self.bot.say("That cog does not have a setup function.")
        except CogLoadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.add_reaction(ctx.message, "❌")
        else:
            set_cog(module, True)
            await self.disable_commands()
            await self.bot.add_reaction(ctx.message, "👌")

    @commands.command(name="cogs")
    @checks.is_owner()
    async def _show_cogs(self):
        """Shows loaded/unloaded cogs"""
        # This function assumes that all cogs are in the cogs folder,
        # which is currently true.

        # Extracting filename from __module__ Example: cogs.owner
        loaded = [c.__module__.split(".")[1] for c in self.bot.cogs.values()]
        # What's in the folder but not loaded is unloaded
        unloaded = [c.split(".")[1] for c in self._list_cogs()
                    if c.split(".")[1] not in loaded]

        if not unloaded:
            unloaded = ["None"]

        msg = ("+ Loaded\n"
               "{}\n\n"
               "- Unloaded\n"
               "{}"
               "".format(", ".join(sorted(loaded)),
                         ", ".join(sorted(unloaded)))
               )
        for page in pagify(msg, [" "], shorten_by=16):
            await self.bot.say(box(page.lstrip(" "), lang="diff"))

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def debug(self, ctx, *, code):
        """Evaluates code"""
        def check(m):
            if m.content.strip().lower() == "more":
                return True

        author = ctx.message.author
        channel = ctx.message.channel

        code = code.strip('` ')
        result = None

        global_vars = globals().copy()
        global_vars['bot'] = self.bot
        global_vars['ctx'] = ctx
        global_vars['message'] = ctx.message
        global_vars['author'] = ctx.message.author
        global_vars['channel'] = ctx.message.channel
        global_vars['server'] = ctx.message.server

        try:
            result = eval(code, global_vars, locals())
        except Exception as e:
            lmao2 = discord.Embed(description="**omo:**\n" + box('{}: {}'.format(type(e).__name__, str(e)),
                                   lang="py"), color=0xef1111)
            await self.bot.say(embed=lmao2)
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = str(result)

        if not ctx.message.channel.is_private:
            censor = (self.bot.settings.email,
                      self.bot.settings.password,
                      self.bot.settings.token)
            r = "[EXPUNGED]"
            for w in censor:
                if w is None or w == "":
                    continue
                result = result.replace(w, r)
                result = result.replace(w.lower(), r)
                result = result.replace(w.upper(), r)

        result = list(pagify(result, shorten_by=16))

        for i, page in enumerate(result):
            if i != 0 and i % 4 == 0:
                last = await self.bot.say("There are still {} messages. "
                                          "Type `more` to continue."
                                          "".format(len(result) - (i+1)))
                msg = await self.bot.wait_for_message(author=author,
                                                      channel=channel,
                                                      check=check,
                                                      timeout=10)
                if msg is None:
                    try:
                        await self.bot.delete_message(last)
                    except:
                        pass
                    finally:
                        break
            lmao = discord.Embed(description="**Returned Evaluation:**\n" + box(page, lang="py"), color=0x4aaae8)
            await self.bot.say(embed=lmao)
    
         
     
    @commands.group(name="set", pass_context=True)
    @checks.is_owner()
    async def _set(self, ctx):
        """Changes my core settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return
 

    @_set.command()
    @checks.is_owner()
    async def defaultmodrole(self, *, role_name: str):
        """Sets the default mod role name

           This is used if a server-specific role is not set"""
        self.bot.settings.default_mod = role_name
        self.bot.settings.save_settings()
        await self.bot.say("The default mod role name has been set.")

    @_set.command()
    @checks.is_owner()
    async def defaultadminrole(self, *, role_name: str):
        """Sets the default admin role name

           This is used if a server-specific role is not set"""
        self.bot.settings.default_admin = role_name
        self.bot.settings.save_settings()
        await self.bot.say("The default admin role name has been set.")

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def prefix(self, ctx, *prefixes):
        """Sets owo's global prefixes

        Accepts multiple prefixes separated by a space. Enclose in double
        quotes if a prefix contains spaces.
        Example: set prefix ! $ ? "two words" """
        if prefixes == ():
            await self.bot.send_cmd_help(ctx)
            return

        self.bot.settings.prefixes = sorted(prefixes, reverse=True)
        self.bot.settings.save_settings()
        log.debug("Setting global prefixes to:\n\t{}"
                  "".format(self.bot.settings.prefixes))

        p = "prefixes" if len(prefixes) > 1 else "prefix"
        await self.bot.say("Global {} set".format(p))

    @_set.command(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(administrator=True)
    async def serverprefix(self, ctx, *prefixes):
        """Sets owo's prefixes for this server

        Accepts multiple prefixes separated by a space. Enclose in double
        quotes if a prefix contains spaces.
        Example: set serverprefix ! $ ? "two words"

        Issuing this command with no parameters will reset the server
        prefixes and the global ones will be used instead."""
        server = ctx.message.server

        if prefixes == ():
            self.bot.settings.set_server_prefixes(server, [])
            self.bot.settings.save_settings()
            current_p = ", ".join(self.bot.settings.prefixes)
            await self.bot.say("Server prefixes reset. Current prefixes: "
                               "`{}`".format(current_p))
            return

        prefixes = sorted(prefixes, reverse=True)
        self.bot.settings.set_server_prefixes(server, prefixes)
        self.bot.settings.save_settings()
        log.debug("Setting server's {} prefixes to:\n\t{}"
                  "".format(server.id, self.bot.settings.prefixes))

        p = "Prefixes" if len(prefixes) > 1 else "Prefix"
        await self.bot.say("{} set for this server.\n"
                           "To go back to the global prefixes, do"
                           " `{}set serverprefix` "
                           "".format(p, prefixes[0]))

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def name(self, ctx, *, name):
        """Sets the owo's name"""
        name = name.strip()
        if name != "":
            try:
                await self.bot.edit_profile(self.bot.settings.password,
                                            username=name)
            except:
                await self.bot.say("Failed to change name. Remember that you"
                                   " can only do it up to 2 times an hour."
                                   "Use nicknames if you need frequent "
                                   "changes. {}set nickname"
                                   "".format(ctx.prefix))
            else:
                await self.bot.say("Done.")
        else:
            await self.bot.send_cmd_help(ctx)

    @_set.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def nickname(self, ctx, *, nickname=""):
        """Sets owo's nickname

        Leaving this empty will remove it."""
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(ctx.message.server.me, nickname)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                "\"Change Nickname\" permission.")

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def game(self, ctx, *, game=None):
        """Sets owo's playing status

        Leaving this empty will clear it."""

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

        if game:
            game = game.strip()
            await self.bot.change_presence(game=discord.Game(name=game))
                                
            log.debug('Status set to "{}" by owner'.format(game))
        else:
            await self.bot.change_presence(game=None, status=current_status)
            log.debug('status cleared by owner')
        await self.bot.say("\*poof*")

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def status(self, ctx, *, status=None):
        """Sets my status

        Statuses:
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

        server = ctx.message.server

        current_game = server.me.game if server is not None else None

        if status is None:
            await self.bot.change_presence(game=current_game)
            await self.bot.say("Status reset.")
        else:
            status = statuses.get(status.lower(), None)
            if status:
                await self.bot.change_presence(status=status,
                                               game=current_game)
                await self.bot.say("Status changed.")
            else:
                await self.bot.send_cmd_help(ctx)

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def stream(self, ctx, streamer=None, *, stream_title=None):
        """Sets my streaming status

        Leaving both streamer and stream_title empty will clear it."""

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            game = discord.Game(type=1, url=streamer, name=stream_title)
            await self.bot.change_presence(game=game, status=current_status)
            log.debug('Owner has set streaming status and url to "{}" and {}'.format(stream_title, streamer))
        elif streamer is not None:
            await self.bot.send_cmd_help(ctx)
            return
        else:
            await self.bot.change_presence(game=None, status=current_status)
            log.debug('stream cleared by owner')
        await self.bot.say("Done.")

    @_set.command()
    @checks.is_owner()
    async def pfp(self, url):
        """Sets my pfp"""
        try:
            async with self.session.get(url) as r:
                data = await r.read()
            await self.bot.edit_profile(self.bot.settings.password, avatar=data)
            await self.bot.say("d-done.. how do i l-look..?")
            log.debug("changed pfp")
        except Exception as e:
            await self.bot.say("Error, check your console or logs for "
                               "more information.")
            log.exception(e)
            traceback.print_exc()

    @_set.command(name="token")
    @checks.is_owner()
    async def _token(self, token):
        """Sets my login token"""
        if len(token) < 50:
            await self.bot.say("Invalid token.")
        else:
            self.bot.settings.token = token
            self.bot.settings.save_settings()
            await self.bot.say("Token set. Restart me.")
            log.debug("Token changed.")

    @_set.command(name="adminrole", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _server_adminrole(self, ctx, *, role: discord.Role):
        """Sets the admin role for this server"""
        server = ctx.message.server
        if server.id not in self.bot.settings.servers:
            await self.bot.say("Remember to set modrole too.")
        self.bot.settings.set_server_admin(server, role.name)
        await self.bot.say("Admin role set to '{}'".format(role.name))

    @_set.command(name="modrole", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _server_modrole(self, ctx, *, role: discord.Role):
        """Sets the mod role for this server"""
        server = ctx.message.server
        if server.id not in self.bot.settings.servers:
            await self.bot.say("Remember to set adminrole too.")
        self.bot.settings.set_server_mod(server, role.name)
        await self.bot.say("Mod role set to '{}'".format(role.name))

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def blacklist(self, ctx):
        """Blacklist management commands

        Blacklisted users will be unable to issue commands"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @blacklist.command(name="add")
    async def _blacklist_add(self, user: GlobalUser):
        """Adds user to owo's global blacklist"""
        if user.id not in self.global_ignores["blacklist"]:
            self.global_ignores["blacklist"].append(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been blacklisted.")
        else:
            await self.bot.say("User is already blacklisted.")

    @blacklist.command(name="remove")
    async def _blacklist_remove(self, user: GlobalUser):
        """Removes user from owo's global blacklist"""
        if user.id in self.global_ignores["blacklist"]:
            self.global_ignores["blacklist"].remove(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been removed from the blacklist.")
        else:
            await self.bot.say("User is not blacklisted.")

    @blacklist.command(name="list")
    async def _blacklist_list(self):
        """Lists users on the blacklist"""
        blacklist = self._populate_list(self.global_ignores["blacklist"])

        if blacklist:
            for page in blacklist:
                await self.bot.say(box(page))
        else:
            await self.bot.say("The blacklist is empty.")

    @blacklist.command(name="clear")
    async def _blacklist_clear(self):
        """Clears the global blacklist"""
        self.global_ignores["blacklist"] = []
        self.save_global_ignores()
        await self.bot.say("Blacklist is now empty.")

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def whitelist(self, ctx):
        """Whitelist management commands

        If the whitelist is not empty, only whitelisted users will
        be able to use owo"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @whitelist.command(name="add")
    async def _whitelist_add(self, user: GlobalUser):
        """Adds user to owo's global whitelist"""
        if user.id not in self.global_ignores["whitelist"]:
            if not self.global_ignores["whitelist"]:
                msg = "\nNon-whitelisted users will be ignored."
            else:
                msg = ""
            self.global_ignores["whitelist"].append(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been whitelisted." + msg)
        else:
            await self.bot.say("User is already whitelisted.")

    @whitelist.command(name="remove")
    async def _whitelist_remove(self, user: GlobalUser):
        """Removes user from owo's global whitelist"""
        if user.id in self.global_ignores["whitelist"]:
            self.global_ignores["whitelist"].remove(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been removed from the whitelist.")
        else:
            await self.bot.say("User is not whitelisted.")

    @whitelist.command(name="list")
    async def _whitelist_list(self):
        """Lists users on the whitelist"""
        whitelist = self._populate_list(self.global_ignores["whitelist"])

        if whitelist:
            for page in whitelist:
                await self.bot.say(box(page))
        else:
            await self.bot.say("The whitelist is empty.")

    @whitelist.command(name="clear")
    async def _whitelist_clear(self):
        """Clears the global whitelist"""
        self.global_ignores["whitelist"] = []
        self.save_global_ignores()
        await self.bot.say("Whitelist is now empty.")

    @commands.command()
    @checks.is_owner()
    async def die(self, silently : bool=False):
        """Shuts down owo"""
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        try: # We don't want missing perms to stop our shutdown
            if not silently:
                await self.bot.say(":wave:XmX")
        except:
            pass
        await self.bot.shutdown()

    @commands.command()
    @checks.is_owner()
    async def restart(self, silently : bool=False):
        """Attempts to restart owo

        Makes birb quit with exit code 26
        The restart is not guaranteed: it must be dealt
        with by the process manager in use"""
        try:
            if not silently:
                await self.bot.say("I'll brb...")
        except:
            pass
        await self.bot.shutdown(restart=True)

    @commands.group(name="command", pass_context=True)
    @checks.is_owner()
    async def command_disabler(self, ctx):
        """Disables/enables commands

        With no subcommands returns the disabled commands list"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            if self.disabled_commands:
                msg = "Disabled commands:\n```xl\n"
                for cmd in self.disabled_commands:
                    msg += "{}, ".format(cmd)
                msg = msg.strip(", ")
                await self.bot.whisper("{}```".format(msg))

    @command_disabler.command()
    async def disable(self, *, command):
        """Disables commands/subcommands"""
        comm_obj = await self.get_command(command)
        if comm_obj is KeyError:
            await self.bot.say("That command doesn't seem to exist.")
        elif comm_obj is False:
            await self.bot.say("You cannot disable owner restricted commands.")
        else:
            comm_obj.enabled = False
            comm_obj.hidden = True
            self.disabled_commands.append(command)
            self.save_disabled_commands()
            await self.bot.say("Command has been disabled.")

    @command_disabler.command()
    async def enable(self, *, command):
        """Enables commands/subcommands"""
        if command in self.disabled_commands:
            self.disabled_commands.remove(command)
            self.save_disabled_commands()
            await self.bot.say("Command enabled.")
        else:
            await self.bot.say("That command is not disabled.")
            return
        try:
            comm_obj = await self.get_command(command)
            comm_obj.enabled = True
            comm_obj.hidden = False
        except:  # In case it was in the disabled list but not currently loaded
            pass # No point in even checking what returns

    async def get_command(self, command):
        command = command.split()
        try:
            comm_obj = self.bot.commands[command[0]]
            if len(command) > 1:
                command.pop(0)
                for cmd in command:
                    comm_obj = comm_obj.commands[cmd]
        except KeyError:
            return KeyError
        for check in comm_obj.checks:
            if hasattr(check, "__name__") and check.__name__ == "is_owner_check":
                return False
        return comm_obj

    async def disable_commands(self): # runs at boot
        for cmd in self.disabled_commands:
            cmd_obj = await self.get_command(cmd)
            try:
                cmd_obj.enabled = False
                cmd_obj.hidden = True
            except:
                pass

    @commands.command()
    async def invite(self):
        """Shows my invite URL"""
        if self.bot.user.bot:
            await self.bot.whisper("Invite URL: " + self.bot.oauth_url)
        else:
            await self.bot.say("I'm not a bot account. I have no invite URL.")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def servers(self, ctx):
        """Lists and allows to leave servers"""
        owner = ctx.message.author
        servers = sorted(list(self.bot.servers),
                         key=lambda s: s.name.lower())
        msg = ""
        for i, server in enumerate(servers):
            members = set(server.members)
            bots = filter(lambda m: m.bot, members)
            bots = set(bots)
            user = len(members) - len(bots)
            sketchy = len(bots) > len(members)
            if len(members) < 5:
                msg += "`{}`: {} `{} members, {} bots` <:blobglare:433415186012176395>\n".format(i, server.name, user, len(bots))
            elif sketchy:
                msg +"`{}`: {} `{} members, {} bots` **Might be a bot farm.** <:blobglare:433415186012176395>\n".format(i, server.name, user, len(bots))
            else:
                msg += "`{}`: {} `{} members, {} bots`\n".format(i, server.name, user, len(bots))
        msg += "```Total Servers: {}```\n".format(len(self.bot.servers))
        msg += "\nTo leave a server just type its number."

        for page in pagify(msg, ['\n']):
            await self.bot.say(page)

        while msg is not None:
            msg = await self.bot.wait_for_message(author=owner, timeout=15)
            
            try:
                msg = int(msg.content)
                await self.leave_confirmation(servers[msg], owner, ctx)
                break
            except (IndexError, ValueError, AttributeError):
                pass

    async def leave_confirmation(self, server, owner, ctx):
        await self.bot.say("Are you sure you want me "
                    "to leave {}? (yes/no)".format(server.name))

        msg = await self.bot.wait_for_message(author=owner, timeout=15)

        if msg is None:
            await self.bot.say("I guess not.")
        elif msg.content.lower().strip() in ("yes", "y"):
            await self.bot.leave_server(server)
            if server != ctx.message.server:
                await self.bot.say("Done.")
        else:
            await self.bot.say("Alright then.")

    @commands.command(pass_context=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx, *, message : str):
        """Sends a message to the owner"""
        if self.bot.settings.owner is None:
            await self.bot.say("I have no owner set.")
            return
        server = ctx.message.server
        owner = discord.utils.get(self.bot.get_all_members(),
                                  id=self.bot.settings.owner)
        author = ctx.message.author
        footer = "User ID: " + author.id

        if ctx.message.server is None:
            source = "through DM"
        else:
            source = "from {}".format(server)
            footer += " | Server ID: " + server.id

        if isinstance(author, discord.Member):
            colour = author.colour
        else:
            colour = discord.Colour.red()

        description = "Sent by {} {}".format(author, source)

        e = discord.Embed(colour=colour, description=message)
        if author.avatar_url:
            e.set_author(name=description, icon_url=author.avatar_url)
        else:
            e.set_author(name=description)
        e.set_footer(text=footer)

        try:
            await self.bot.send_message(owner, embed=e)
        except discord.InvalidArgument:
            await self.bot.say("I cannot send your message, I'm unable to find"
                               " my owner... *sigh*")
        except discord.HTTPException:
            await self.bot.say("Your message is too long.")
        except:
            await self.bot.say("I'm unable to deliver your message. Sorry.")
        else:
            await self.bot.say("Your message has been sent.")

    @commands.command()
    async def uptime(self):
        """Shows how long owo's been online"""
        since = self.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        passed = self.get_bot_uptime()
        await self.bot.say("Been up for: **{}** (since {} UTC)"
                           "".format(passed, since))

    @commands.command()
    async def info(self):
        """Info about owopup"""
        owner = discord.utils.get(self.bot.get_all_members(),
                                  id=self.bot.settings.owner)
        botto = discord.utils.get(self.bot.get_all_members(),
                                  id="365255872181567489")
        prefix_label = 'Prefix'
        if len(self.bot.settings.prefixes) > 1:
            prefix_label += 'es'
        prefix = self.bot.settings.prefixes
        
        binvite = "https://discordapp.com/api/oauth2/authorize?client_id=365255872181567489&permissions=8&scope=bot"
        sinvite = "https://discord.gg/2tXPN98"
        sinvite2 = 'https://discord.gg/c4vWDdd'
        info = discord.Embed(title="Hello i'm {}!".format(botto), description="A Discord Bot made with love and millions of owos!\n= **Written in Python 3.5.6 using discord.py**\n- `Messages Read:` **{}**\n- `Commands Processed:` **{}**\n- `Servers:` **{}**\n- `Users:` **{}**\n- `Total Commands:` **{}**\n- `{}:` {}\n+ [**Invite me to your server!**]({})\n+ [**Join Skull's server!**]({})\n+ [**Join the support server if you have any questions.**]({}) ".format(self.bot.counter["messages_read"], self.bot.counter["processed_commands"], len(self.bot.servers), len(set(self.bot.get_all_members())), len(self.bot.commands), prefix_label, ", ".join(prefix)[:], binvite, sinvite, sinvite2), color=0x356a21)
        info.set_footer(text="Owned by: {} ({})".format(owner, owner.id), icon_url=owner.avatar_url)
        info.set_thumbnail(url=botto.avatar_url)
        await self.bot.say(embed=info)

    @commands.command(pass_context=True)
    async def support(self, ctx):
        """Sends the support server invite if you need help"""
        sinvite = 'https://discord.gg/c4vWDdd'
        sup = discord.Embed(description="**Need help? [Join the support server]({})**".format(sinvite), color=0x356a21)
        await self.bot.say(embed=sup)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def traceback(self, ctx, public: bool=False):
        """Sends to the owner the last command exception that has occurred

        If public (yes is specified), it will be sent to the chat instead"""
        if not public:
            destination = ctx.message.author
        else:
            destination = ctx.message.channel

        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception):
                await self.bot.send_message(destination, box(page, lang="py"))
        else:
            await self.bot.say("No exception has occurred yet.")
                              
    def _populate_list(self, _list):
        """Used for both whitelist / blacklist

        Returns a paginated list"""
        users = []
        total = len(_list)

        for user_id in _list:
            user = discord.utils.get(self.bot.get_all_members(), id=user_id)
            if user:
                users.append("{} ({})".format(user, user.id))

        if users:
            not_found = total - len(users)
            users = ", ".join(users)
            if not_found:
                users += "\n\n ... and {} users I could not find".format(not_found)
            return list(pagify(users, delims=[" ", "\n"]))

        return []

    def _load_cog(self, cogname):
        if not self._does_cogfile_exist(cogname):
            raise CogNotFoundError(cogname)
        try:
            mod_obj = importlib.import_module(cogname)
            importlib.reload(mod_obj)
            self.bot.load_extension(mod_obj.__name__)
        except SyntaxError as e:
            raise CogLoadError(*e.args)
        except:
            raise

    def _unload_cog(self, cogname, reloading=False):
        if not reloading and cogname == "cogs.owner":
            raise OwnerUnloadWithoutReloadError(
                "Can't unload the owner plugin :P")
        try:
            self.bot.unload_extension(cogname)
        except:
            raise CogUnloadError

    def _list_cogs(self):
        cogs = [os.path.basename(f) for f in glob.glob("cogs/*.py")]
        return ["cogs." + os.path.splitext(f)[0] for f in cogs]

    def _does_cogfile_exist(self, module):
        if "cogs." not in module:
            module = "cogs." + module
        if module not in self._list_cogs():
            return False
        return True


    def get_bot_uptime(self, *, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h}h {m}m {s}s'
            if days:
                fmt = '{d}d ' + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    def save_global_ignores(self):
        dataIO.save_json("data/red/global_ignores.json", self.global_ignores)

    def save_disabled_commands(self):
        dataIO.save_json("data/red/disabled_commands.json", self.disabled_commands)


def _import_old_data(data):
    """Migration from mod.py"""
    try:
        data["blacklist"] = dataIO.load_json("data/mod/blacklist.json")
    except FileNotFoundError:
        pass

    try:
        data["whitelist"] = dataIO.load_json("data/mod/whitelist.json")
    except FileNotFoundError:
        pass

    return data


def check_files():
    if not os.path.isfile("data/red/disabled_commands.json"):
        print("Creating empty disabled_commands.json...")
        dataIO.save_json("data/red/disabled_commands.json", [])

    if not os.path.isfile("data/red/global_ignores.json"):
        print("Creating empty global_ignores.json...")
        data = {"blacklist": [], "whitelist": []}
        try:
            data = _import_old_data(data)
        except Exception as e:
            log.error("Failed to migrate blacklist / whitelist data from "
                      "mod.py: {}".format(e))

        dataIO.save_json("data/red/global_ignores.json", data)


def setup(bot):
    check_files()
    n = Owner(bot)
    bot.add_cog(n)
