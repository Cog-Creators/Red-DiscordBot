import discord
import os
import socket
import logging


# Copied from https://github.com/bb4242/sdnotify/
# Copyright (c) 2016 Brett Bethke
class SystemdNotifier:
    def __init__(self, debug=False):
        self.debug = debug
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            addr = os.getenv('NOTIFY_SOCKET')
            if addr[0] == '@':
                addr = '\0' + addr[1:]
            self.socket.connect(addr)
        except:
            self.socket = None
            if self.debug:
                raise

    def notify(self, state):
        try:
            self.socket.sendall(state)
        except:
            if self.debug:
                raise


class Watchdog:
    def __init__(self, bot):
        self.bot = bot
        self.sdnotify = SystemdNotifier()
        self.logger = logging.getLogger("marvin.sdwatchdog")

    def pet_watchdog(self):
        self.sdnotify.notify(b'WATCHDOG=1')
        self.logger.debug('Got HEARTBEAT_ACK; petting watchdog.')

    async def on_ready(self):
        self.pet_watchdog()

    async def on_socket_response(self, data):
            op = data.get('op')
            if op == discord.gateway.DiscordWebSocket.HEARTBEAT_ACK:
                self.pet_watchdog()


def setup(bot):
    w = Watchdog(bot)
    bot.add_cog(w)
