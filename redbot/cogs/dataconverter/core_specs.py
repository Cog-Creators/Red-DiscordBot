from itertools import chain, starmap
from pathlib import Path
from datetime import datetime

from redbot.core.bot import Red
from redbot.core.utils.data_converter import DataConverter as dc
from redbot.core.config import Config


class SpecResolver(object):
    """
    Resolves Certain things for DataConverter
    """

    def __init__(self, path: Path):
        self.v2path = path
        self.resolved = set()
        self.available_core_conversions = {
            "Bank Accounts": {
                "cfg": ("Bank", None, 384734293238749),
                "file": self.v2path / "data" / "economy" / "bank.json",
                "converter": self.bank_accounts_conv_spec,
            },
            "Economy Settings": {
                "cfg": ("Economy", "config", 1256844281),
                "file": self.v2path / "data" / "economy" / "settings.json",
                "converter": self.economy_conv_spec,
            },
            "Mod Log Cases": {
                "cfg": ("ModLog", None, 1354799444),
                "file": self.v2path / "data" / "mod" / "modlog.json",
                "converter": None,  # prevents from showing as available
            },
            "Filter": {
                "cfg": ("Filter", "settings", 4766951341),
                "file": self.v2path / "data" / "mod" / "filter.json",
                "converter": self.filter_conv_spec,
            },
            "Past Names": {
                "cfg": ("Mod", "settings", 4961522000),
                "file": self.v2path / "data" / "mod" / "past_names.json",
                "converter": self.past_names_conv_spec,
            },
            "Past Nicknames": {
                "cfg": ("Mod", "settings", 4961522000),
                "file": self.v2path / "data" / "mod" / "past_nicknames.json",
                "converter": self.past_nicknames_conv_spec,
            },
            "Custom Commands": {
                "cfg": ("CustomCommands", "config", 414589031223512),
                "file": self.v2path / "data" / "customcom" / "commands.json",
                "converter": self.customcom_conv_spec,
            },
        }

    @property
    def available(self):
        return sorted(
            k
            for k, v in self.available_core_conversions.items()
            if v["file"].is_file() and v["converter"] is not None and k not in self.resolved
        )

    def unpack(self, parent_key, parent_value):
        """Unpack one level of nesting in a dictionary"""
        try:
            items = parent_value.items()
        except AttributeError:
            yield (parent_key, parent_value)
        else:
            for key, value in items:
                yield (parent_key + (key,), value)

    def flatten_dict(self, dictionary: dict):
        """Flatten a nested dictionary structure"""
        dictionary = {(key,): value for key, value in dictionary.items()}
        while True:
            dictionary = dict(chain.from_iterable(starmap(self.unpack, dictionary.items())))
            if not any(isinstance(value, dict) for value in dictionary.values()):
                break
        return dictionary

    def apply_scope(self, scope: str, data: dict):
        return {(scope,) + k: v for k, v in data.items()}

    def bank_accounts_conv_spec(self, data: dict):
        flatscoped = self.apply_scope(Config.MEMBER, self.flatten_dict(data))
        ret = {}
        for k, v in flatscoped.items():
            outerkey, innerkey = tuple(k[:-1]), (k[-1],)
            if outerkey not in ret:
                ret[outerkey] = {}
            if innerkey[0] == "created_at":
                x = int(datetime.strptime(v, "%Y-%m-%d %H:%M:%S").timestamp())
                ret[outerkey].update({innerkey: x})
            else:
                ret[outerkey].update({innerkey: v})
        return ret

    def economy_conv_spec(self, data: dict):
        flatscoped = self.apply_scope(Config.GUILD, self.flatten_dict(data))
        ret = {}
        for k, v in flatscoped.items():
            outerkey, innerkey = (*k[:-1],), (k[-1],)
            if outerkey not in ret:
                ret[outerkey] = {}
            ret[outerkey].update({innerkey: v})
        return ret

    def mod_log_cases(self, data: dict):
        raise NotImplementedError("This one isn't ready yet")

    def filter_conv_spec(self, data: dict):
        return {(Config.GUILD, k): {("filter",): v} for k, v in data.items()}

    def past_names_conv_spec(self, data: dict):
        return {(Config.USER, k): {("past_names",): v} for k, v in data.items()}

    def past_nicknames_conv_spec(self, data: dict):
        flatscoped = self.apply_scope(Config.MEMBER, self.flatten_dict(data))
        ret = {}
        for k, v in flatscoped.items():
            outerkey, innerkey = (*k[:-1],), (k[-1],)
            if outerkey not in ret:
                ret[outerkey] = {}
            ret[outerkey].update({innerkey: v})
        return ret

    def customcom_conv_spec(self, data: dict):
        flatscoped = self.apply_scope(Config.GUILD, self.flatten_dict(data))
        ret = {}
        for k, v in flatscoped.items():
            outerkey, innerkey = (*k[:-1],), ("commands", k[-1])
            if outerkey not in ret:
                ret[outerkey] = {}

            ccinfo = {
                "author": {"id": 42, "name": "Converted from a v2 instance"},
                "command": k[-1],
                "created_at": "{:%d/%m/%Y %H:%M:%S}".format(datetime.utcnow()),
                "editors": [],
                "response": v,
            }
            ret[outerkey].update({innerkey: ccinfo})
        return ret

    async def convert(self, bot: Red, prettyname: str):
        if prettyname not in self.available:
            raise NotImplementedError("No Conversion Specs for this")

        info = self.available_core_conversions[prettyname]
        filepath, converter = info["file"], info["converter"]
        (cogname, attr, _id) = info["cfg"]
        try:
            config = getattr(bot.get_cog(cogname), attr)
        except (TypeError, AttributeError):
            config = Config.get_conf(None, _id, cog_name=cogname)

        try:
            items = converter(dc.json_load(filepath))
            await dc(config).dict_import(items)
        except Exception:
            raise
        else:
            self.resolved.add(prettyname)
