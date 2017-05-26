from core.json_io import JsonIO
import os
from .red_base import BaseDriver


dataIO = JsonIO()


class JSON(BaseDriver):
    def __init__(self, cog_name, *args, data_path_override=None, **kwargs):
        self.cog_name = cog_name
        if data_path_override:
            self.data_path = "{}/settings.json".format(data_path_override)
        else:
            self.data_path = "data/{}/settings.json".format(self.cog_name)

        try:
            self.data = dataIO._load_json(self.data_path)
        except FileNotFoundError:
            self.data = {}

        try:
            dataIO._save_json(self.data_path, self.data)
        except FileNotFoundError:
            os.makedirs("data/{}".format(self.cog_name))
            dataIO._save_json(self.data_path, self.data)

    def maybe_add_ident(self, ident: str):
        if ident in self.data:
            return

        self.data[ident] = {}
        for k in ("GLOBAL", "SERVER", "CHANNEL", "ROLE", "MEMBER", "USER",
                  "MISC"):
            if k not in self.data[ident]:
                self.data[ident][k] = {}

        dataIO._save_json(self.data_path, self.data)

    def get_global(self, cog_name, ident, _, key, *, default=None):
        return self.data[ident]["GLOBAL"].get(key, default)

    def get_guild(self, cog_name, ident, guild_id, key, *, default=None):
        guilddata = self.data[ident]["SERVER"].get(str(guild_id), {})
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

    def get_misc(self, cog_name, ident, *, default=None):
        miscdata = self.data[ident]["MISC"]
        return miscdata.get("MISC", default)

    async def set_global(self, cog_name, ident, key, value, clear=False):
        if clear:
            self.data[ident]["GLOBAL"] = {}
        else:
            self.data[ident]["GLOBAL"][key] = value
        dataIO._save_json(self.data_path, self.data)

    async def set_guild(self, cog_name, ident, guild_id, key, value, clear=False):
        guild_id = str(guild_id)
        if clear:
            self.data[ident]["SERVER"][guild_id] = {}
        else:
            try:
                self.data[ident]["SERVER"][guild_id][key] = value
            except KeyError:
                self.data[ident]["SERVER"][guild_id] = {}
                self.data[ident]["SERVER"][guild_id][key] = value
        await dataIO._threadsafe_save_json(self.data_path, self.data)

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
        await dataIO._threadsafe_save_json(self.data_path, self.data)

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
        await dataIO._threadsafe_save_json(self.data_path, self.data)

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
        await dataIO._threadsafe_save_json(self.data_path, self.data)

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
        await dataIO._threadsafe_save_json(self.data_path, self.data)

    async def set_misc(self, cog_name, ident, value, clear=False):
        if clear:
            self.data[ident]["MISC"] = {}
        else:
            self.data[ident]["MISC"]["MISC"] = value
        await dataIO._threadsafe_save_json(self.data_path, self.data)
