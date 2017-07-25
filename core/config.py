import logging
from pathlib import Path

from typing import Callable, NewType, Union, Tuple

import discord
from .drivers.red_json import JSON as JSONDriver

log = logging.getLogger("red.config")

CogInstance = NewType("CogInstance", object)


class Value:
    def __init__(self, identifiers: Tuple[str], default_value, spawner):
        self._identifiers = identifiers
        self.default = default_value

        self.spawner = spawner

    @property
    def identifiers(self):
        return tuple(str(i) for i in self._identifiers)

    def __call__(self, default=None):
        driver = self.spawner.get_driver()
        try:
            ret = driver.get(self.identifiers)
        except KeyError:
            return default or self.default
        return ret

    async def set(self, value):
        driver = self.spawner.get_driver()
        await driver.set(self.identifiers, value)


class Group(Value):
    def __init__(self, identifiers: Tuple[str],
                 defaults: dict,
                 spawner,
                 force_registration: bool=False):
        self.defaults = defaults
        self.force_registration = force_registration
        self.spawner = spawner

        super().__init__(identifiers, {}, self.spawner)

    # noinspection PyTypeChecker
    def __getattr__(self, item: str) -> Union["Group", Value]:
        """
        Takes in the next accessible item. If it's found to be a Group
            we return another Group object. If it's found to be a Value
            we return a Value object. If it is not found and
            force_registration is True then we raise AttributeException,
            otherwise return a Value object.
        :param item:
        :return:
        """
        is_group = self.is_group(item)
        is_value = not is_group and self.is_value(item)
        new_identifiers = self.identifiers + (item, )
        if is_group:
            return Group(
                identifiers=new_identifiers,
                defaults=self.defaults[item],
                spawner=self.spawner,
                force_registration=self.force_registration
            )
        elif is_value:
            return Value(
                identifiers=new_identifiers,
                default_value=self.defaults[item],
                spawner=self.spawner
            )
        elif self.force_registration:
            raise AttributeError(
                "'{}' is not a valid registered Group"
                "or value.".format(item)
            )
        else:
            return Value(
                identifiers=new_identifiers,
                default_value=None,
                spawner=self.spawner
            )

    def is_group(self, item: str) -> bool:
        """
        Determines if an attribute access is pointing at a registered group.
        :param item:
        :return:
        """
        default = self.defaults.get(item)
        return isinstance(default, dict)

    def is_value(self, item: str) -> bool:
        """
        Determines if an attribute access is pointing at a registered value.
        :param item:
        :return:
        """
        try:
            default = self.defaults[item]
        except KeyError:
            return False

        return not isinstance(default, dict)

    def get(self, item: str, default=None):
        """
        You should avoid this function whenever possible.
        :param item:
        :param default:
        :return:
        """
        value = getattr(self, item)
        return value(default=default)

    async def set(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "You may only set the value of a group to be a dict."
            )
        await super().set(value)

    async def set_attr(self, item: str, value):
        """
        You should avoid this function whenever possible.
        :param item:
        :param value:
        :return:
        """
        value_obj = getattr(self, item)
        await value_obj.set(value)


class MemberGroup(Group):
    def all_guilds(self) -> dict:
        """
        Gets a dict of all guilds and members.

        REMEMBER: ID's are stored in these dicts as STRINGS.
        :return:
        """
        new_identifiers = (self.identifiers[0], )
        value_obj = Value(
            identifiers=new_identifiers,
            default_value={},
            spawner=self.spawner
        )
        return value_obj()

    def all_members(self) -> dict:
        """
        Gets a dict of all members from the same guild as the
            given member.

        REMEMBER: ID's are stored in these dicts as STRINGS.
        :return:
        """
        new_identifiers = self.identifiers[:2]
        value_obj = Value(
            identifiers=new_identifiers,
            default_value={},
            spawner=self.spawner
        )
        return value_obj()


class Config:
    GLOBAL = "GLOBAL"
    GUILD = "GUILD"
    CHANNEL = "TEXTCHANNEL"
    ROLE = "ROLE"
    USER = "USER"
    MEMBER = "MEMBER"

    def __init__(self, cog_name: str, unique_identifier: str,
                 driver_spawn: Callable,
                 force_registration: bool=False,
                 defaults: dict=None):
        self.cog_name = cog_name
        self.unique_identifier = unique_identifier

        self.spawner = driver_spawn
        self.force_registration = force_registration
        self.defaults = defaults or {}

    @classmethod
    def get_conf(cls, cog_instance: CogInstance, identifier: int,
                 force_registration=False):
        """
        Returns a Config instance based on a simplified set of initial
            variables.
        :param cog_instance:
        :param identifier: Any random integer, used to keep your data
            distinct from any other cog with the same name.
        :param force_registration: Should config require registration
            of data keys before allowing you to get/set values?
        :return:
        """
        cog_name = cog_instance.__class__.__name__
        uuid = str(hash(identifier))

        spawner = JSONDriver(cog_name)
        return cls(cog_name=cog_name, unique_identifier=uuid,
                   force_registration=force_registration,
                   driver_spawn=spawner)

    @classmethod
    def get_core_conf(cls, force_registration: bool=False):
        core_data_path = Path.cwd() / 'core' / '.data'
        driver_spawn = JSONDriver("Core", data_path_override=core_data_path)
        return cls(cog_name="Core", driver_spawn=driver_spawn,
                   unique_identifier='0',
                   force_registration=force_registration)

    def __getattr__(self, item: str) -> Union[Group, Value]:
        """
        This is used to generate Value or Group objects for global
            values.
        :param item:
        :return:
        """
        global_group = self._get_base_group(self.GLOBAL)
        return getattr(global_group, item)

    @staticmethod
    def _get_defaults_dict(key: str, value) -> dict:
        """
        Since we're allowing nested config stuff now, not storing the
            defaults as a flat dict sounds like a good idea. May turn
            out to be an awful one but we'll see.
        :param key:
        :param value:
        :return:
        """
        ret = {}
        partial = ret
        splitted = key.split('__')
        for i, k in enumerate(splitted, start=1):
            if not k.isidentifier():
                raise RuntimeError("'{}' is an invalid config key.".format(k))
            if i == len(splitted):
                partial[k] = value
            else:
                partial[k] = {}
                partial = partial[k]
        return ret

    @staticmethod
    def _update_defaults(to_add: dict, _partial: dict):
        """
        This tries to update the defaults dictionary with the nested
            partial dict generated by _get_defaults_dict. This WILL
            throw an error if you try to have both a value and a group
            registered under the same name.
        :param to_add:
        :param _partial:
        :return:
        """
        for k, v in to_add.items():
            val_is_dict = isinstance(v, dict)
            if k in _partial:
                existing_is_dict = isinstance(_partial[k], dict)
                if not (val_is_dict and existing_is_dict):
                    raise KeyError("You cannot register a Group and a Value under"
                                   " the same name.")
                if val_is_dict:
                    Config._update_defaults(v, _partial=_partial[k])
            else:
                _partial[k] = v

    def _register_default(self, key: str, **kwargs):
        if key not in self.defaults:
            self.defaults[key] = {}

        for k, v in kwargs.items():
            to_add = self._get_defaults_dict(k, v)
            self._update_defaults(to_add, self.defaults[key])

    def register_global(self, **kwargs):
        self._register_default(self.GLOBAL, **kwargs)

    def register_guild(self, **kwargs):
        self._register_default(self.GUILD, **kwargs)

    def register_channel(self, **kwargs):
        # We may need to add a voice channel category later
        self._register_default(self.CHANNEL, **kwargs)

    def register_role(self, **kwargs):
        self._register_default(self.ROLE, **kwargs)

    def register_user(self, **kwargs):
        self._register_default(self.USER, **kwargs)

    def register_member(self, **kwargs):
        self._register_default(self.MEMBER, **kwargs)

    def _get_base_group(self, key: str, *identifiers: str,
                        group_class=Group) -> Group:
        # noinspection PyTypeChecker
        return group_class(
            identifiers=(key, ) + identifiers,
            defaults=self.defaults.get(key, {}),
            spawner=self.spawner,
            force_registration=self.force_registration
        )

    def guild(self, guild: discord.Guild) -> Group:
        return self._get_base_group(self.GUILD, guild.id)

    def channel(self, channel: discord.TextChannel) -> Group:
        return self._get_base_group(self.CHANNEL, channel.id)

    def role(self, role: discord.Role) -> Group:
        return self._get_base_group(self.ROLE, role.id)

    def user(self, user: discord.User) -> Group:
        return self._get_base_group(self.USER, user.id)

    def member(self, member: discord.Member) -> MemberGroup:
        return self._get_base_group(self.MEMBER, member.guild.id, member.id,
                                    group_class=MemberGroup)

