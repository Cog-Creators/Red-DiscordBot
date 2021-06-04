import logging
import sys
from http.client import HTTPException

import discord
from discord import GatewayNotFound
from discord.gateway import DiscordWebSocket
from discord.http import HTTPClient, Route

log_ws = logging.getLogger("discord.gateway")


class _DiscordWebSocket(DiscordWebSocket):
    async def identify(self):
        """Sends the IDENTIFY packet."""
        payload = {
            "op": self.IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {
                    "$os": sys.platform,
                    "$browser": "discord.py",
                    "$device": "discord.py",
                    "$referrer": "",
                    "$referring_domain": "",
                },
                "compress": False,
                "large_threshold": 250,
                "guild_subscriptions": self._connection.guild_subscriptions,
                "v": 3,
            },
        }

        if not self._connection.is_bot:
            payload["d"]["synced_guilds"] = []

        if self.shard_id is not None and self.shard_count is not None:
            payload["d"]["shard"] = [self.shard_id, self.shard_count]

        state = self._connection
        if state._activity is not None or state._status is not None:
            payload["d"]["presence"] = {
                "status": state._status,
                "game": state._activity,
                "since": 0,
                "afk": False,
            }

        if state._intents is not None:
            payload["d"]["intents"] = state._intents.value

        await self.call_hooks("before_identify", self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
        log_ws.info("Shard ID %s has sent the IDENTIFY payload.", self.shard_id)


class _HTTPClient(HTTPClient):
    async def get_gateway(self, *, encoding="json", v=6, zlib=False):
        try:
            data = await self.request(Route("GET", "/gateway"))
        except HTTPException as exc:
            raise GatewayNotFound() from exc
        if zlib:
            value = "{0}?encoding={1}&v={2}&compress=zlib-stream"
        else:
            value = "{0}?encoding={1}&v={2}"
        return value.format(data["url"], encoding, v)

    async def get_bot_gateway(self, *, encoding="json", v=6, zlib=False):
        try:
            data = await self.request(Route("GET", "/gateway/bot"))
        except HTTPException as exc:
            raise GatewayNotFound() from exc

        if zlib:
            value = "{0}?encoding={1}&v={2}&compress=zlib-stream"
        else:
            value = "{0}?encoding={1}&v={2}"
        return data["shards"], value.format(data["url"], encoding, v)


discord.voice_client.DiscordWebSocket = _DiscordWebSocket
discord.client.DiscordWebSocket = _DiscordWebSocket
discord.shard.DiscordWebSocket = _DiscordWebSocket
discord.gateway.DiscordWebSocket = _DiscordWebSocket

discord.http.HTTPClient = _HTTPClient
discord.client.HTTPClient = _HTTPClient
