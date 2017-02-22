from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
import discord
import os
import asyncio
try:
    from mcstatus import MinecraftServer
    mcstatusInstalled = True
except:
    mcstatusInstalled = False


class Mcsvr():
    """Cog for getting info about a Minecraft server"""
    def __init__(self, bot):
        self.settings_file = "data/mcsvr/mcsvr.json"
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True, name="mcsvr")
    async def _mcsvr(self, ctx):
        """Commands for getting info about a Minecraft server"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_mcsvr.command(pass_context=True, no_pm=True, name="count")
    async def _count(self, ctx, server_ip: str):
        """Gets player count for the specified server"""
        server = MinecraftServer.lookup(server_ip).status()
        online_count = server.players.online
        max_count = server.players.max
        message = "Player count for " + server_ip + ":\n\n" + \
            str(online_count) + "/" + str(max_count)
        await self.bot.say("```{}```".format(message))

    @_mcsvr.command(pass_context=True, no_pm=True, name="version")
    async def _version(self, ctx, server_ip: str):
        """
        Gets information about the required Minecraft
        version for the specified server
        """
        server = MinecraftServer.lookup(server_ip).status()
        message = "Server version for " + server_ip + ":\n\n" + \
            str(server.version.name)
        await self.bot.say("```{}```".format(message))

    @checks.serverowner_or_permissions(administrator=True)
    @commands.command(pass_context=True, no_pm=True, name="mcsvrset")
    async def _mcsvrset(self, ctx, channel: discord.Channel, server_ip: str):
        """Settings for being notified of server issues"""
        if not channel and server_ip:
            await self.bot.say("Sorry, can't do that! Try specifying a channel and a server IP")
        else:
            server_list = dataIO.load_json(self.settings_file)
            chn_name = channel.name
            svr_id = ctx.message.server.id
            server_status = "down"
            try:
                mc_server = MinecraftServer.lookup(server_ip).status()
                server_status = "up"
                await self.bot.send_message(channel, "The server is up!")
            except ConnectionRefusedError:
                server_status = "down"
                await self.bot.send_message(channel, "The server is down!")
            svr_to_add = {"chn_name": chn_name, "server_ip": server_ip, "server_status": server_status}
            server_list[svr_id] = svr_to_add
            dataIO.save_json(self.settings_file, server_list)

    async def mc_servers_check(self):
        server_list = dataIO.load_json(self.settings_file)
        bot_servers = list(self.bot.servers)
        for server in bot_servers:
            print(server.id in server_list)
            if server.id in server_list:
                channel_name = server_list[server.id]["chn_name"]
                server_ip = server_list[server.id]["server_ip"]
                server_status = server_list[server.id]["server_status"]
                try:
                    mc_server = MinecraftServer.lookup(server_ip).status()
                    if server_status == "down":
                        await self.bot.send_message(discord.utils.get(self.bot.get_all_channels(), server__id=server.id, name=channel_name), "The server is up again!")
                    server_status = "up"
                except ConnectionRefusedError:
                    if server_status == "up":
                        await self.bot.send_message(discord.utils.get(self.bot.get_all_channels(), server__id=server.id, name=channel_name), "Oh no, the server went down!")
                    server_status = "down"
                server_list[server.id]["server_status"] = server_status
        dataIO.save_json(self.settings_file, server_list)
        asyncio.sleep(60)


def check_folders():
    if not os.path.exists("data/mcsvr"):
        print("Creating data/mcsvr folder...")
        os.makedirs("data/mcsvr")


def check_files():
    f = "data/mcsvr/mcsvr.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty mcsvr.json...")
        dataIO.save_json(f, {})


def setup(bot):
    if mcstatusInstalled:
        check_folders()
        check_files()
        n = Mcsvr(bot)
        loop = asyncio.get_event_loop()
        loop.create_task(n.mc_servers_check())
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to do 'pip3 install mcstatus'")
