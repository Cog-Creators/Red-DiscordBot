from core.drivers.red_json import JSON as JSONDriver
from core.drivers.red_mongo import Mongo
import logging

from typing import Callable

log = logging.getLogger("red.config")

class BaseConfig:
    def __init__(self, cog_name, unique_identifier, driver_spawn, force_registration=False,
                 hash_uuid=True, collection="GLOBAL", collection_uuid=None,
                 defaults={}):
        self.cog_name = cog_name
        if hash_uuid:
            self.uuid = str(hash(unique_identifier))
        else:
            self.uuid = unique_identifier
        self.driver_spawn = driver_spawn
        self._driver = None
        self.collection = collection
        self.collection_uuid = collection_uuid

        self.force_registration = force_registration

        try:
            self.driver.maybe_add_ident(self.uuid)
        except AttributeError:
            pass

        self.driver_getmap = {
            "GLOBAL": self.driver.get_global,
            "GUILD": self.driver.get_guild,
            "CHANNEL": self.driver.get_channel,
            "ROLE": self.driver.get_role,
            "USER": self.driver.get_user,
            "MISC": self.driver.get_misc
        }

        self.driver_setmap = {
            "GLOBAL": self.driver.set_global,
            "GUILD": self.driver.set_guild,
            "CHANNEL": self.driver.set_channel,
            "ROLE": self.driver.set_role,
            "USER": self.driver.set_user,
            "MISC": self.driver.set_misc
        }

        self.curr_key = None

        self.restricted_keys = ("cog_name", "cog_identifier", "_id",
                                "guild_id", "channel_id", "role_id",
                                "user_id")

        self.defaults = defaults if defaults else {
            "GLOBAL": {}, "GUILD": {}, "CHANNEL": {}, "ROLE": {},
            "MEMBER": {}, "USER": {}, "MISC": {}}

    @classmethod
    def get_conf(cls, cog_name: str, unique_identifier: int=0):
        """
        Gets a config object that cog's can use to safely store data. The
            backend to this is totally modular and can easily switch between
            JSON and a DB. However, when changed, all data will likely be lost
            unless cogs write some converters for their data.
        
        Positional Arguments:
            cog_name - String representation of your cog name, normally something
                like `self.__class__.__name__`
        
        Keyword Arguments:
            unique_identifier - a random integer or string that is used to
                differentiate your cog from any other named the same. This way we
                can safely store data for multiple cogs that are named the same.
        """

        url = None  # TODO: get mongo url
        port = None  # TODO: get mongo port

        def spawn_mongo_driver():
            return Mongo(url, port)

        # TODO: Determine which backend users want, default to JSON

        driver_spawn = JSONDriver(cog_name)

        return cls(cog_name=cog_name, unique_identifier=unique_identifier,
                   driver_spawn=driver_spawn)

    @property
    def driver(self):
        if self._driver is None:
            try:
                self._driver = self.driver_spawn()
            except TypeError:
                return self.driver_spawn

        return self._driver

    def __getattr__(self, key):
        """This should be used to return config key data as determined by
            `self.collection` and `self.collection_uuid`."""
        raise NotImplemented

    def __setattr__(self, key, value):
        if 'defaults' in self.__dict__:  # Necessary to let the cog load
            restricted = list(self.defaults[self.collection].keys()) + \
                list(self.restricted_keys)
            if key in restricted:
                raise ValueError("Not allowed to dynamically set attributes of"
                                 " restricted_keys: {}".format(restricted))
            else:
                self.__dict__[key] = value
        else:
            self.__dict__[key] = value

    def clear(self):
        """Clears all values in the current context ONLY."""
        raise NotImplemented

    def set(self, key, value):
        """This should set config key with value `value` in the
            corresponding collection as defined by `self.collection` and
            `self.collection_uuid`."""
        raise NotImplemented

    def guild(self, guild):
        """This should return a `BaseConfig` instance with the corresponding
            `collection` and `collection_uuid`."""
        raise NotImplemented

    def channel(self, channel):
        """This should return a `BaseConfig` instance with the corresponding
            `collection` and `collection_uuid`."""
        raise NotImplemented

    def role(self, role):
        """This should return a `BaseConfig` instance with the corresponding
            `collection` and `collection_uuid`."""
        raise NotImplemented

    def member(self, member):
        """This should return a `BaseConfig` instance with the corresponding
            `collection` and `collection_uuid`."""
        raise NotImplemented

    def user(self, user):
        """This should return a `BaseConfig` instance with the corresponding
            `collection` and `collection_uuid`."""
        raise NotImplemented

    def register_global(self, **global_defaults):
        """
        Registers a new dict of global defaults. This function should
            be called EVERY TIME the cog loads (aka just do it in
            __init__)!

        :param global_defaults: Each key should be the key you want to
            access data by and the value is the default value of that
            key.
        :return: 
        """
        for k, v in global_defaults.items():
            try:
                self._register_global(k, v)
            except KeyError:
                log.exception("Bad default global key.")

    def _register_global(self, key, default=None):
        """Registers a global config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        elif not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")
        self.defaults["GLOBAL"][key] = default

    def register_guild(self, **guild_defaults):
        """
        Registers a new dict of guild defaults. This function should
            be called EVERY TIME the cog loads (aka just do it in
            __init__)!

        :param guild_defaults: Each key should be the key you want to
            access data by and the value is the default value of that
            key.
        :return: 
        """
        for k, v in guild_defaults.items():
            try:
                self._register_guild(k, v)
            except KeyError:
                log.exception("Bad default guild key.")

    def _register_guild(self, key, default=None):
        """Registers a guild config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        elif not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")
        self.defaults["GUILD"][key] = default

    def register_channel(self, **channel_defaults):
        """
        Registers a new dict of channel defaults. This function should
            be called EVERY TIME the cog loads (aka just do it in
            __init__)!

        :param channel_defaults: Each key should be the key you want to
            access data by and the value is the default value of that
            key.
        :return: 
        """
        for k, v in channel_defaults.items():
            try:
                self._register_channel(k, v)
            except KeyError:
                log.exception("Bad default channel key.")

    def _register_channel(self, key, default=None):
        """Registers a channel config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        elif not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")
        self.defaults["CHANNEL"][key] = default

    def register_role(self, **role_defaults):
        """
        Registers a new dict of role defaults. This function should
            be called EVERY TIME the cog loads (aka just do it in
            __init__)!

        :param role_defaults: Each key should be the key you want to
            access data by and the value is the default value of that
            key.
        :return: 
        """
        for k, v in role_defaults.items():
            try:
                self._register_role(k, v)
            except KeyError:
                log.exception("Bad default role key.")

    def _register_role(self, key, default=None):
        """Registers a role config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        elif not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")
        self.defaults["ROLE"][key] = default

    def register_member(self, **member_defaults):
        """
        Registers a new dict of member defaults. This function should
            be called EVERY TIME the cog loads (aka just do it in
            __init__)!

        :param member_defaults: Each key should be the key you want to
            access data by and the value is the default value of that
            key.
        :return: 
        """
        for k, v in member_defaults.items():
            try:
                self._register_member(k, v)
            except KeyError:
                log.exception("Bad default member key.")

    def _register_member(self, key, default=None):
        """Registers a member config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        elif not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")
        self.defaults["MEMBER"][key] = default

    def register_user(self, **user_defaults):
        """
        Registers a new dict of user defaults. This function should
            be called EVERY TIME the cog loads (aka just do it in
            __init__)!

        :param user_defaults: Each key should be the key you want to
            access data by and the value is the default value of that
            key.
        :return: 
        """
        for k, v in user_defaults.items():
            try:
                self._register_user(k, v)
            except KeyError:
                log.exception("Bad default user key.")

    def _register_user(self, key, default=None):
        """Registers a user config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        elif not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")
        self.defaults["USER"][key] = default


class Config(BaseConfig):
    """
    Config object created by `Config.get_conf()`

    This configuration object is designed to make backend data
        storage mechanisms pluggable. It also is designed to
        help a cog developer make fewer mistakes (such as
        typos) when dealing with cog data and to make those mistakes
        apparent much faster in the design process.
        
        It also has the capability to safely store data between cogs
        that share the same name.
        
    There are two main components to this config object. First,
        you have the ability to get data on a level specific basis.
        The seven levels available are: global, guild, channel, role,
        member, user, and misc.
        
        The second main component is registering default values for
        data in each of the levels. This functionality is OPTIONAL
        and must be explicitly enabled when creating the Config object
        using the kwarg `force_registration=True`.

    Basic Usage:
        Creating a Config object:
            Use the `Config.get_conf()` class method to create new
                Config objects.
                
                See the `Config.get_conf()` documentation for more
                information.

        Registering Default Values (optional):
            You can register default values for data at all levels
                EXCEPT misc.
            
            Simply pass in the key/value pairs as keyword arguments to
                the respective function.
                
                e.g.: conf_obj.register_global(enabled=True)
                      conf_obj.register_guild(likes_red=True)
        
        Retrieving data by attributes:
            Since I registered the "enabled" key in the previous example
                at the global level I can now do:
                
                conf_obj.enabled()
                
                which will retrieve the current value of the "enabled"
                key, making use of the default of "True". I can also do
                the same for the guild key "likes_red":
                
                conf_obj.guild(guild_obj).likes_red()
            
            If I elected to not register default values, you can provide them
                when you try to access the key:
            
                conf_obj.no_default(default=True)
                
                However if you do not provide a default and you do not register
                defaults, accessing the attribute will return "None".
        
        Saving data:
            This is accomplished by using the `set` function available at
                every level.
                
                e.g.: conf_obj.set("enabled", False)
                      conf_obj.guild(guild_obj).set("likes_red", False)
                      
                If `force_registration` was enabled when the config object
                was created you will only be allowed to save keys that you
                have registered.

    Misc data is special, use `conf.misc()` and `conf.set_misc(value)`
        respectively.
    """

    def __getattr__(self, key) -> Callable:
        """
        Until I've got a better way to do this I'm just gonna fake __call__
        
        :param key: 
        :return: lambda function with kwarg 
        """
        return self._get_value_from_key(key)

    def _get_value_from_key(self, key) -> Callable:
        try:
            default = self.defaults[self.collection][key]
        except KeyError as e:
            if self.force_registration:
                raise AttributeError("Key '{}' not registered!".format(key)) from e
            default = None

        self.curr_key = key

        if self.collection != "MEMBER":
            ret = lambda default=default: self.driver_getmap[self.collection](
                self.cog_name, self.uuid, self.collection_uuid, key,
                default=default)
        else:
            mid, sid = self.collection_uuid
            ret = lambda default=default: self.driver.get_member(
                self.cog_name, self.uuid, mid, sid, key,
                default=default)
        return ret

    def get(self, key, default=None):
        """
        Included as an alternative to registering defaults.
        
        :param key: 
        :param default: 
        :return: 
        """

        try:
            return getattr(self, key)(default=default)
        except AttributeError:
            return

    async def set(self, key, value):
        # Notice to future developers:
        #   This code was commented to allow users to set keys without having to register them.
        #       That being said, if they try to get keys without registering them
        #       things will blow up. I do highly recommend enforcing the key registration.

        if self.force_registration and key not in self.defaults[self.collection]:
            raise AttributeError("Key '{}' not registered!".format(key))

        if not key.isidentifier():
            raise RuntimeError("Invalid key name, must be a valid python variable"
                               " name.")

        if self.collection == "GLOBAL":
            await self.driver.set_global(self.cog_name, self.uuid, key, value)
        elif self.collection == "MEMBER":
            mid, sid = self.collection_uuid
            await self.driver.set_member(self.cog_name, self.uuid, mid, sid,
                                         key, value)
        elif self.collection in self.driver_setmap:
            func = self.driver_setmap[self.collection]
            await func(self.cog_name, self.uuid, self.collection_uuid, key, value)

    async def set_misc(self, value):
        await self.driver.set_misc(self.cog_name, self.uuid, value)

    async def clear(self):
        await self.driver_setmap[self.collection](
            self.cog_name, self.uuid, self.collection_uuid, None, None,
            clear=True)

    async def clear_misc(self):
        await self.driver.set_misc(self.cog_name, self.uuid, None, clear=True)

    def guild(self, guild):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "GUILD"
        new.collection_uuid = guild.id
        new._driver = None
        return new

    def channel(self, channel):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "CHANNEL"
        new.collection_uuid = channel.id
        new._driver = None
        return new

    def role(self, role):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "ROLE"
        new.collection_uuid = role.id
        new._driver = None
        return new

    def member(self, member):
        guild = member.guild
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "MEMBER"
        new.collection_uuid = (member.id, guild.id)
        new._driver = None
        return new

    def user(self, user):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "USER"
        new.collection_uuid = user.id
        new._driver = None
        return new

    def misc(self):
        try:
            default = self.defaults["MISC"]
        except KeyError as e:
            default = {}

        return self.driver_getmap["MISC"](
            self.cog_name, self.uuid,
            default=default)
