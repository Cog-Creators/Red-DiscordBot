from .dataIO import fileIO
import discord

default_path = "data/red/settings.json"

class Settings:
    def __init__(self,path=default_path):
        self.path = path
        self.default_settings = {"EMAIL" : "EmailHere", "PASSWORD" : "PasswordHere", "OWNER" : "id_here", "PREFIXES" : [], "default":{"ADMIN_ROLE" : "Transistor", "MOD_ROLE" : "Process"}}
        if not fileIO(self.path,"check"):
            self.bot_settings = self.default_settings
            self.save_settings()
        else:
            self.bot_settings = fileIO(self.path,"load")
        if "default" not in self.bot_settings:
            self.update_old_settings()

    def save_settings(self):
        fileIO(self.path,"save",self.bot_settings)

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

    @property
    def password(self):
        return self.bot_settings["PASSWORD"]

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

    def get_server(self,server):
        assert isinstance(server,discord.Server)
        return self.bot_settings.get(server.id,self.bot_settings["default"]).copy()

    def get_server_admin(self,server):
        assert isinstance(server,discord.Server)
        if server is None:
            return
        if server.id not in self.bot_settings:
            return self.default_admin
        return self.bot_settings[server.id].get("ADMIN_ROLE","")

    def set_server_admin(self,server,value):
        assert isinstance(server,discord.Server)
        if server is None:
            return
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["ADMIN_ROLE"] = value
        self.save_settings()

    def get_server_mod(self,server):
        assert isinstance(server,discord.Server)
        if server is None:
            return
        if server.id not in self.bot_settings:
            return self.default_mod
        return self.bot_settings[server.id].get("MOD_ROLE","")

    def set_server_mod(self,server,value):
        assert isinstance(server,discord.Server)
        if server is None:
            return
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["MOD_ROLE"] = value
        self.save_settings()

    def add_server(self,sid):
        self.bot_settings[sid] = self.bot_settings["default"].copy()
        self.save_settings()
