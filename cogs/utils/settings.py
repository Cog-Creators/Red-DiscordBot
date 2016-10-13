from .dataIO import dataIO
import discord
import os

default_path = "data/red/settings.json"

class Settings:
    def __init__(self,path=default_path):
        self.path = path
        self.check_folders()
        self.default_settings = {"EMAIL" : "EmailHere", "PASSWORD" : "", "OWNER" : "id_here", "PREFIXES" : [], "default":{"ADMIN_ROLE" : "Transistor", "MOD_ROLE" : "Process"}, "LOGIN_TYPE" : "email"}
        if not dataIO.is_valid_json(self.path):
            self.bot_settings = self.default_settings
            self.save_settings()
        else:
            current = dataIO.load_json(self.path)
            if current.keys() != self.default_settings.keys():
                for key in self.default_settings.keys():
                    if key not in current.keys():
                        current[key] = self.default_settings[key]
                        print("Adding " + str(key) + " field to red settings.json")
                dataIO.save_json(self.path, current)
            self.bot_settings = dataIO.load_json(self.path)
        if "default" not in self.bot_settings:
            self.update_old_settings()

    def check_folders(self):
        folders = ("data", os.path.dirname(self.path), "cogs", "cogs/utils")
        for folder in folders:
            if not os.path.exists(folder):
                print("Creating " + folder + " folder...")
                os.makedirs(folder)

    def save_settings(self):
        dataIO.save_json(self.path,self.bot_settings)

    def update_old_settings(self):
        mod = self.bot_settings["MOD_ROLE"]
        admin = self.bot_settings["ADMIN_ROLE"]
        del self.bot_settings["MOD_ROLE"]
        del self.bot_settings["ADMIN_ROLE"]
        self.bot_settings["default"] = {"MOD_ROLE":mod,"ADMIN_ROLE":admin}
        self.save_settings()

    @property
    def owner(self):
        return self.bot_settings["OWNER"]

    @owner.setter
    def owner(self,value):
        self.bot_settings["OWNER"] = value
        self.save_settings()

    @property
    def email(self):
        return self.bot_settings["EMAIL"]

    @email.setter
    def email(self,value):
        self.bot_settings["EMAIL"] = value
        self.save_settings()

    @property
    def password(self):
        return self.bot_settings["PASSWORD"]

    @password.setter
    def password(self,value):
        self.bot_settings["PASSWORD"] = value
        self.save_settings()

    @property
    def prefixes(self):
        return self.bot_settings["PREFIXES"]

    @prefixes.setter
    def prefixes(self,value):
        assert isinstance(value,list)
        self.bot_settings["PREFIXES"] = value
        self.save_settings()

    @property
    def default_admin(self):
        if "default" not in self.bot_settings:
            self.update_old_settings()
        return self.bot_settings["default"].get("ADMIN_ROLE","")

    @default_admin.setter
    def default_admin(self,value):
        if "default" not in self.bot_settings:
            self.update_old_settings()
        self.bot_settings["default"]["ADMIN_ROLE"] = value
        self.save_settings()

    @property
    def default_mod(self):
        if "default" not in self.bot_settings:
            self.update_old_settings()
        return self.bot_settings["default"].get("MOD_ROLE","")

    @default_mod.setter
    def default_mod(self,value):
        if "default" not in self.bot_settings:
            self.update_old_settings()
        self.bot_settings["default"]["MOD_ROLE"] = value
        self.save_settings()

    @property
    def servers(self):
        ret = {}
        server_ids = list(filter(lambda x: str(x).isdigit(),self.bot_settings))
        for server in server_ids:
            ret.update({server:self.bot_settings[server]})
        return ret

    @property
    def login_type(self):
                return self.bot_settings["LOGIN_TYPE"]

    @login_type.setter
    def login_type(self,value):
                self.bot_settings["LOGIN_TYPE"] = value
                self.save_settings()

    def get_server(self,server):
        if server is None:
            return self.bot_settings["default"].copy()
        assert isinstance(server,discord.Server)
        return self.bot_settings.get(server.id,self.bot_settings["default"]).copy()

    def get_server_admin(self,server):
        if server is None:
            return self.default_admin
        assert isinstance(server,discord.Server)
        if server.id not in self.bot_settings:
            return self.default_admin
        return self.bot_settings[server.id].get("ADMIN_ROLE","")

    def set_server_admin(self,server,value):
        if server is None:
            return
        assert isinstance(server,discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["ADMIN_ROLE"] = value
        self.save_settings()

    def get_server_mod(self,server):
        if server is None:
            return self.default_mod
        assert isinstance(server,discord.Server)
        if server.id not in self.bot_settings:
            return self.default_mod
        return self.bot_settings[server.id].get("MOD_ROLE","")

    def set_server_mod(self,server,value):
        if server is None:
            return
        assert isinstance(server,discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["MOD_ROLE"] = value
        self.save_settings()

    def add_server(self,sid):
        self.bot_settings[sid] = self.bot_settings["default"].copy()
        self.save_settings()
