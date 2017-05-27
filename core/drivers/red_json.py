from core.json_io import JsonIO
import os
from .red_base import BaseDriver

from pathlib import Path


class JSON(BaseDriver):
    def __init__(self, cog_name, *args, data_path_override: Path=None,
                 file_name_override: str="settings.json", **kwargs):
        self.cog_name = cog_name
        self.file_name = file_name_override
        if data_path_override:
            self.data_path = data_path_override
        else:
            self.data_path = Path.cwd() / 'cogs' / '.data' / self.cog_name

        self.data_path.mkdir(parents=True, exist_ok=True)

        self.data_path = self.data_path / self.file_name
        
        self.jsonIO = JsonIO(self.data_path)

        try:
            self.data = self.jsonIO._load_json()
        except FileNotFoundError:
            self.data = {}

    def maybe_add_ident(self, ident: str):
        if ident in self.data:
            return

        self.data[ident] = {}
        for k in ("GLOBAL", "GUILD", "CHANNEL", "ROLE", "MEMBER", "USER"):
            if k not in self.data[ident]:
                self.data[ident][k] = {}

        self.jsonIO._save_json(self.data)

    def get_global(self, cog_name, ident, _, key, *, default=None):
        return self.data[ident]["GLOBAL"].get(key, default)

    def get_guild(self, cog_name, ident, guild_id, key, *, default=None):
        guilddata = self.data[ident]["GUILD"].get(str(guild_id), {})
        return guilddata.get(key, default)

    def get_channel(self, cog_name, ident, channel_id, key, *, default=None):
        channeldata = self.data[ident]["CHANNEL"].get(str(channel_id), {})
        return channeldata.get(key, default)

    def get_role(self, cog_name, ident, role_id, key, *, default=None):
        roledata = self.data[ident]["ROLE"].get(str(role_id), {})
        return roledata.get(key, default)

    def get_member(self, cog_name, ident, user_id, guild_id, key, *,
                   default=None):
        userdata = self.data[ident]["MEMBER"].get(str(user_id), {})
        guilddata = userdata.get(str(guild_id), {})
        return guilddata.get(key, default)

    def get_user(self, cog_name, ident, user_id, key, *, default=None):
        userdata = self.data[ident]["USER"].get(str(user_id), {})
        return userdata.get(key, default)

    async def set_global(self, cog_name, ident, key, value, clear=False):
        if clear:
            self.data[ident]["GLOBAL"] = {}
        else:
            self.data[ident]["GLOBAL"][key] = value
        await self.jsonIO._threadsafe_save_json(self.data)

    async def set_guild(self, cog_name, ident, guild_id, key, value, clear=False):
        guild_id = str(guild_id)
        if clear:
            self.data[ident]["GUILD"][guild_id] = {}
        else:
            try:
                self.data[ident]["GUILD"][guild_id][key] = value
            except KeyError:
                self.data[ident]["GUILD"][guild_id] = {}
                self.data[ident]["GUILD"][guild_id][key] = value
        await self.jsonIO._threadsafe_save_json(self.data)

    async def set_channel(self, cog_name, ident, channel_id, key, value, clear=False):
        channel_id = str(channel_id)
        if clear:
            self.data[ident]["CHANNEL"][channel_id] = {}
        else:
            try:
                self.data[ident]["CHANNEL"][channel_id][key] = value
            except KeyError:
                self.data[ident]["CHANNEL"][channel_id] = {}
                self.data[ident]["CHANNEL"][channel_id][key] = value
        await self.jsonIO._threadsafe_save_json(self.data)

    async def set_role(self, cog_name, ident, role_id, key, value, clear=False):
        role_id = str(role_id)
        if clear:
            self.data[ident]["ROLE"][role_id] = {}
        else:
            try:
                self.data[ident]["ROLE"][role_id][key] = value
            except KeyError:
                self.data[ident]["ROLE"][role_id] = {}
                self.data[ident]["ROLE"][role_id][key] = value
        await self.jsonIO._threadsafe_save_json(self.data)

    async def set_member(self, cog_name, ident, user_id, guild_id, key, value, clear=False):
        user_id = str(user_id)
        guild_id = str(guild_id)
        if clear:
            self.data[ident]["MEMBER"][user_id] = {}
        else:
            try:
                self.data[ident]["MEMBER"][user_id][guild_id][key] = value
            except KeyError:
                if user_id not in self.data[ident]["MEMBER"]:
                    self.data[ident]["MEMBER"][user_id] = {}
                if guild_id not in self.data[ident]["MEMBER"][user_id]:
                    self.data[ident]["MEMBER"][user_id][guild_id] = {}

                self.data[ident]["MEMBER"][user_id][guild_id][key] = value
        await self.jsonIO._threadsafe_save_json(self.data)

    async def set_user(self, cog_name, ident, user_id, key, value, clear=False):
        user_id = str(user_id)
        if clear:
            self.data[ident]["USER"][user_id] = {}
        else:
            try:
                self.data[ident]["USER"][user_id][key] = value
            except KeyError:
                self.data[ident]["USER"][user_id] = {}
                self.data[ident]["USER"][user_id][key] = value
        await self.jsonIO._threadsafe_save_json(self.data)
