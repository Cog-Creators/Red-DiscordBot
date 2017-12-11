import pathlib
import asyncio  # noqa: F401
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from datetime import datetime

path = 'data/embedmaker'


class EmbedMaker:
    """
    Make embed objects. Recall them, remove them, reuse them (etc)
    """

    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "1.1.0"

    def __init__(self, bot):

        self.bot = bot
        self.settings = dataIO.load_json(path + '/settings.json')
        self.embeds = dataIO.load_json(path + '/embeds.json')

    def save_settings(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    def save_embeds(self):
        dataIO.save_json(path + '/embeds.json', self.embeds)

    async def initial_config(self, server=None):
        """adds default settings for all servers the bot is in
        when needed and on join"""

        if server:
            if server.id not in self.settings:
                self.settings[server.id] = {'inactive': True,
                                            'usercache': [],
                                            'roles': []
                                            }
                self.save_settings()

            if server.id not in self.embeds:
                self.embeds[server.id] = {'embeds': []}
                self.save_embeds()

        if 'global' not in self.embeds:
            self.embeds['global'] = {'embeds': []}
            self.save_embeds()
        if 'global' not in self.settings:
            self.settings['global'] = {'inactive': True,
                                       'usercache': [],
                                       'whitelist': []}  # Future Proofing
            self.save_settings()

    @commands.group(name="embedset", pass_context=True, no_pm=True)
    async def embedset(self, ctx):
        """configuration settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commands.group(name="embed", pass_context=True, no_pm=True)
    async def embed(self, ctx):
        """embed tools"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @embed.command(name="list", pass_context=True, no_pm=True)
    async def list_embeds(self, ctx):
        """lists the embeds on this server"""

        server = ctx.message.server
        if server.id not in self.embeds:
            return await self.bot.say("I couldn't find any embeds here")

        names = []
        for embed in self.embeds[server.id]["embeds"]:
            names.append(embed.get('name'))

        if len(names) > 0:
            await self.bot.say("The following embeds "
                               "exist here:\n {}".format(names))
        else:
            await self.bot.say("No embeds here.")

    @checks.admin_or_permissions(Manage_server=True)
    @embedset.command(name="toggleactive", pass_context=True, no_pm=True)
    async def embed_toggle(self, ctx):
        """Toggles whether embeds are enabled or not"""
        server = ctx.message.server
        if server.id not in self.settings:
            await self.initial_config(server)
        self.settings[server.id]['inactive'] = \
            not self.settings[server.id]['inactive']
        self.save_settings()
        if self.settings[server.id]['inactive']:
            await self.bot.say("Embeds disabled.")
        else:
            await self.bot.say("Embeds enabled.")

    @checks.is_owner()
    @embedset.command(name="toggleglobal")
    async def global_embed_toggle(self):
        """Toggles whether global embeds are enabled or not"""
        if "global" not in self.settings:
            self.initial_config()
        self.settings['global']['inactive'] = \
            not self.settings['global']['inactive']
        self.save_settings()
        if self.settings['global']['inactive']:
            await self.bot.say("Global Embeds disabled.")
        else:
            await self.bot.say("Global Embeds enabled.")

    @checks.admin_or_permissions(Manage_messages=True)
    @embed.command(name="remove", pass_context=True, no_pm=True)
    async def remove_embed(self, ctx, name: str):
        """removes an embed"""
        server = ctx.message.server
        name = name.lower()
        embeds = self.embeds[server.id]["embeds"]
        embeds[:] = [e for e in embeds if e.get('name') != name]
        self.embeds[server.id]["embeds"] = embeds
        self.save_embeds()
        await self.bot.say("If an embed of that name existed, it is gone now.")

    @checks.is_owner()
    @embed.command(name="removeglobal", pass_context=True)
    async def remove_g_embed(self, ctx, name: str):
        """removes a global embed"""
        name = name.lower()
        embeds = self.embeds["global"]["embeds"]
        embeds[:] = [e for e in embeds if e.get('name') != name]
        self.embeds['global']["embeds"] = embeds
        self.save_embeds()
        await self.bot.say("If an embed of that name existed, it is gone now.")

    @checks.admin_or_permissions(Manage_messages=True)
    @embed.command(name="make", pass_context=True, no_pm=True)
    async def make_embed(self, ctx, name: str):
        """Interactive prompt for making an embed"""
        author = ctx.message.author
        server = ctx.message.server

        if server.id not in self.embeds:
            await self.initial_config(server)
        if server.id not in self.settings:
            await self.initial_config(server)
        if self.settings[server.id]['inactive']:
            return await self.bot.say("Embed creation is not currently "
                                      "enabled on this server.")

        name = name.lower()
        for e in self.embeds[server.id]['embeds']:
            if e.get('name') == name:
                return await self.bot.say("An embed by that name exists ")

        if author.id in self.settings[server.id]['usercache']:
            return await self.bot.say("Finish making your prior embed "
                                      "before making an additional one")

        await self.bot.say("I will message you to continue.")
        await self.contact_for_embed(name, author, server)

    @checks.is_owner()
    @embed.command(name="makeglobal", pass_context=True)
    async def make_g_embed(self, ctx, name: str):
        """Interactive prompt for making a global embed"""
        author = ctx.message.author

        if "global" not in self.embeds:
            await self.initial_config()
        if "global" not in self.settings:
            await self.initial_config()

        name = name.lower()
        if name in self.embeds['global']['embeds']:
            return await self.bot.say("An embed by that name exists ")

        if author.id in self.settings["global"]['usercache']:
            return await self.bot.say("Finish making your prior embed "
                                      "before making an additional one")

        await self.bot.say("I will message you to continue.")
        await self.contact_for_embed(name, author)

    @embed.command(name="fetch", pass_context=True, no_pm=True)
    async def fetch(self, ctx, name: str):
        """fetches an embed"""
        server = ctx.message.server

        em = await self.get_embed(name.lower(), server.id)
        if em is None:
            return await self.bot.say("I couldn't find an embed by that name.")
        await self.bot.send_message(ctx.message.channel, embed=em)

    @embed.command(name="fetchglobal", pass_context=True, no_pm=True)
    async def fetch_global(self, ctx, name: str):
        """fetches a global embed"""

        em = await self.get_embed(name.lower())
        if em is None:
            return await self.bot.say("I couldn't find an embed by that name.")
        await self.bot.send_message(ctx.message.channel, embed=em)

    @checks.admin_or_permissions(Manage_messages=True)
    @embed.command(name="dm", pass_context=True, no_pm=True)
    async def fetch_dm(self, ctx, name: str, user_id: str):
        """fetches an embed, and DMs it to a user"""
        server = ctx.message.server

        em = await self.get_embed(name.lower(), server.id)
        if em is None:
            return await self.bot.say("I couldn't find an embed by that name.")
        who = await self.bot.get_user_info(user_id)
        if who is not None:
            await self.bot.send_message(who, embed=em)

    @checks.is_owner()
    @embed.command(name="dmglobal", pass_context=True, no_pm=True)
    async def fetch_global_dm(self, ctx, name: str, user_id: str):
        """fetches a global embed, and DMs it to a user"""

        em = await self.get_embed(name.lower())
        if em is None:
            return await self.bot.say("I couldn't find an embed by that name.")
        who = await self.bot.get_user_info(user_id)
        if who is not None:
            await self.bot.send_message(who, embed=em)

    async def contact_for_embed(self, name: str, author, server=None):
        if server is not None:
            self.settings[server.id]['usercache'].append(author.id)
        else:
            self.settings["global"]["usercache"].append(author.id)
        self.save_settings()

        dm = await self.bot.send_message(author,
                                         "Please respond to this message "
                                         "with the title of your embed. If "
                                         "you do not want a title, wait 30s")
        title = await self.bot.wait_for_message(channel=dm.channel,
                                                author=author, timeout=30)

        if title is None:
            await self.bot.send_message(author,
                                        "Okay, this one won't have a title.")

        dm = await self.bot.send_message(author,
                                         "Please respond to this message "
                                         "with the content of your embed")
        message = await self.bot.wait_for_message(channel=dm.channel,
                                                  author=author, timeout=120)

        if message is None:
            if server is not None:
                self.settings[server.id]['usercache'].remove(author.id)
            else:
                self.settings['global']['usercache'].remove(author.id)
            self.save_settings()
            return await self.bot.send_message(author,
                                               "I can't wait forever, "
                                               "try again when ready")
        else:
            await self.save_embed(name, title, message, server)
            await self.bot.send_message(author, "Your embed was created")

    async def get_embed(self, name: str, server_id=None):

        found = False
        if server_id is None:
            server_id = "global"
        if server_id in self.embeds:
            for embed in self.embeds[server_id]["embeds"]:
                if embed.get('name') == name:
                    title = embed.get('title')
                    content = embed.get('content')
                    timestring = embed.get('timestamp', None)
                    if timestring is None:
                        # old footer:
                        # message.timestamp.strftime('%Y-%m-%d %H:%M')
                        # footer = "created at {} UTC".format(timestamp)
                        # e.g. : "created at 2017-09-05 23:18 UTC"
                        timestring = embed.get('footer')[11:-4]
                    timestamp = datetime.strptime(timestring, '%Y-%m-%d %H:%M')
                    found = True

        if not found:
            return None

        em = discord.Embed(description=content, color=discord.Color.purple(),
                           timestamp=timestamp)
        if title is not None:
            em.set_author(name='{}'.format(title))
        return em

    async def save_embed(self, name, title, message, server=None):

        author = message.author
        content = message.clean_content
        if title is not None:
            title = title.clean_content
        timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
        name = name.lower()

        embed = {'name': name,
                 'title': title,
                 'content': content,
                 'timestamp': timestamp
                 }

        if server is not None:
            self.embeds[server.id]['embeds'].append(embed)
            self.settings[server.id]['usercache'].remove(author.id)
        else:
            self.embeds['global']['embeds'].append(embed)
            self.settings['global']['usercache'].remove(author.id)
        self.save_embeds()

        self.save_settings()


def check_file():
    f = path + '/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})
    f = path + '/embeds.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    check_file()
    n = EmbedMaker(bot)
    bot.add_cog(n)
