from ..dataIO import dataIO
import os
from .red_base import BaseDriver


class JSON(BaseDriver):
    def __init__(self, cog_name, *args, **kwargs):
        self.cog_name = cog_name
        self.data_path = "data/{}/settings.json".format(self.cog_name)

        try:
            self.data = dataIO.load_json(self.data_path)
        except FileNotFoundError:
            self.data = {}

        for k in ("GLOBAL", "SERVER", "CHANNEL", "ROLE", "MEMBER", "USER"):
            if k not in self.data:
                self.data[k] = {}
        try:
            dataIO.save_json(self.data_path, self.data)
        except FileNotFoundError:
            os.makedirs("data/{}".format(self.cog_name))
            dataIO.save_json(self.data_path, self.data)

    def get_global(self, cog_name, ident, _, key, *, default=None):
        return self.data["GLOBAL"].get(key, default)

    def get_server(self, cog_name, ident, server_id, key, *, default=None):
        serverdata = self.data["SERVER"].get(str(server_id), {})
        return serverdata.get(key, default)

    def get_channel(self, cog_name, ident, channel_id, key, *, default=None):
        channeldata = self.data["CHANNEL"].get(str(channel_id), {})
        return channeldata.get(key, default)

    def get_role(self, cog_name, ident, role_id, key, *, default=None):
        roledata = self.data["ROLE"].get(str(role_id), {})
        return roledata.get(key, default)

    def get_member(self, cog_name, ident, user_id, server_id, key, *,
                   default=None):
        userdata = self.data["MEMBER"].get(str(user_id), {})
        serverdata = userdata.get(str(server_id), {})
        return serverdata.get(key, default)

    def get_user(self, cog_name, ident, user_id, key, *, default=None):
        userdata = self.data["USER"].get(str(user_id), {})
        return userdata.get(key, default)

    def set_global(self, cog_name, ident, _, key, value, *, clear=False):
        if clear:
            self.data["GLOBAL"] = {}
        else:
            self.data["GLOBAL"][key] = value
        dataIO.save_json(self.data_path, self.data)

    def set_server(self, cog_name, ident, server_id, key, value, *,
                   clear=False):
        server_id = str(server_id)
        if clear:
            self.data["SERVER"][server_id] = {}
        else:
            try:
                self.data["SERVER"][server_id][key] = value
            except KeyError:
                self.data["SERVER"][server_id] = {}
                self.data["SERVER"][server_id][key] = value
        dataIO.save_json(self.data_path, self.data)

    def set_channel(self, cog_name, ident, channel_id, key, value, *,
                    clear=False):
        channel_id = str(channel_id)
        if clear:
            self.data["CHANNEL"][channel_id] = {}
        else:
            try:
                self.data["CHANNEL"][channel_id][key] = value
            except KeyError:
                self.data["CHANNEL"][channel_id] = {}
                self.data["CHANNEL"][channel_id][key] = value
        dataIO.save_json(self.data_path, self.data)

    def set_role(self, cog_name, ident, role_id, key, value, *, clear=False):
        role_id = str(role_id)
        if clear:
            self.data["ROLE"][role_id] = {}
        else:
            try:
                self.data["ROLE"][role_id][key] = value
            except KeyError:
                self.data["ROLE"][role_id] = {}
                self.data["ROLE"][role_id][key] = value
        dataIO.save_json(self.data_path, self.data)

    def set_member(self, cog_name, ident, user_id, server_id, key, value, *,
                   clear=False):
        user_id = str(user_id)
        server_id = str(server_id)
        if clear:
            self.data["MEMBER"][user_id] = {}
        else:
            try:
                self.data["MEMBER"][user_id][server_id][key] = value
            except KeyError:
                if user_id not in self.data["MEMBER"]:
                    self.data["MEMBER"][user_id] = {}
                if server_id not in self.data["MEMBER"][user_id]:
                    self.data["MEMBER"][user_id][server_id] = {}

                self.data["MEMBER"][user_id][server_id][key] = value
        dataIO.save_json(self.data_path, self.data)

    def set_user(self, cog_name, ident, user_id, key, value, *, clear=False):
        user_id = str(user_id)
        if clear:
            self.data["USER"][user_id] = {}
        else:
            try:
                self.data["USER"][user_id][key] = value
            except KeyError:
                self.data["USER"][user_id] = {}
                self.data["USER"][user_id][key] = value
        dataIO.save_json(self.data_path, self.data)
