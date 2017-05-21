from core.drivers.red_json import JSON as JSONDriver
from core.drivers.red_mongo import Mongo

class BaseConfig:
    def __init__(self, cog_name, unique_identifier, driver_spawn,
                 hash_uuid=True, collection="GLOBAL", collection_uuid=None,
                 defaults={}):
        self.cog_name = cog_name
        if hash_uuid:
            self.uuid = hash(unique_identifier)
        else:
            self.uuid = unique_identifier
        self.driver_spawn = driver_spawn
        self._driver = None
        self.collection = collection
        self.collection_uuid = collection_uuid

        self.driver_getmap = {
            "GLOBAL": self.driver.get_global,
            "SERVER": self.driver.get_server,
            "CHANNEL": self.driver.get_channel,
            "ROLE": self.driver.get_role,
            "USER": self.driver.get_user,
            "MISC": self.driver.get_misc
        }

        self.driver_setmap = {
            "GLOBAL": self.driver.set_global,
            "SERVER": self.driver.set_server,
            "CHANNEL": self.driver.set_channel,
            "ROLE": self.driver.set_role,
            "USER": self.driver.set_user,
            "MISC": self.driver.set_misc
        }

        self.curr_key = None

        self.restricted_keys = ("cog_name", "cog_identifier", "_id",
                                "server_id", "channel_id", "role_id",
                                "user_id")

        self.defaults = defaults if defaults else {
            "GLOBAL": {}, "SERVER": {}, "CHANNEL": {}, "ROLE": {},
            "MEMBER": {}, "USER": {}, "MISC": {}}

    @classmethod
    def get_conf(cls, cog_name, unique_identifier):
        """
        Gets a config object that cog's can use to safely store data. The
            backend to this is totally modular and can easily switch between
            JSON and a DB. However, when changed, all data will likely be lost
            unless cogs write some converters for their data.
        
        Positional Arguments:
            cog_name - String representation of your cog name, normally something
                like `self.__class__.__name__`
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

    def server(self, server):
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

    def register_global(self, key, default=None):
        """Registers a global config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        self.defaults["GLOBAL"][key] = default

    def register_server(self, key, default=None):
        """Registers a server config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        self.defaults["SERVER"][key] = default

    def register_channel(self, key, default=None):
        """Registers a channel config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        self.defaults["CHANNEL"][key] = default

    def register_role(self, key, default=None):
        """Registers a role config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        self.defaults["ROLE"][key] = default

    def register_member(self, key, default=None):
        """Registers a member config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        self.defaults["MEMBER"][key] = default

    def register_user(self, key, default=None):
        """Registers a user config key `key`"""
        if key in self.restricted_keys:
            raise KeyError("Attempt to use restricted key: '{}'".format(key))
        self.defaults["USER"][key] = default


class Config(BaseConfig):
    """
    Config object created by `Bot.get_conf()`

    Use the `set()` function to save data at a certain level
        e.g.:
            Global level: `conf.set("key1", "value1")`
            Server level: `conf.server(server_id).set("key2", "value2")

    Misc data is special, use `conf.misc()` and `conf.set_misc(value)`
        respectively.
    """

    def __getattr__(self, key):
        try:
            default = self.defaults[self.collection][key]
        except KeyError as e:
            raise AttributeError("Key '{}' not registered!".format(key)) from e

        self.curr_key = key

        if self.collection != "MEMBER":
            ret = self.driver_getmap[self.collection](
                self.cog_name, self.uuid, self.collection_uuid, key,
                default=default)
        else:
            mid, sid = self.collection_uuid
            ret = self.driver.get_member(
                self.cog_name, self.uuid, mid, sid, key,
                default=default)

        return ret

    def set(self, key, value):
        if key not in self.defaults[self.collection]:
            raise AttributeError("Key '{}' not registered!".format(key))

        if self.collection == "MEMBER":
            mid, sid = self.collection_uuid
            self.driver.set_member(self.cog_name, self.uuid, mid, sid,
                                   key, value)
        elif self.collection in self.driver_setmap:
            func = self.driver_setmap[self.collection]
            func(self.cog_name, self.uuid, self.collection_uuid, key, value)

    def set_misc(self, value):
        self.driver.set_misc(self.cog_name, self.uuid, value)

    def clear(self):
        self.driver_setmap[self.collection](
            self.cog_name, self.uuid, self.collection_uuid, None, None,
            clear=True)

    def clear_misc(self):
        self.driver.set_misc(self.cog_name, self.uuid, None, clear=True)

    def server(self, server):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "SERVER"
        new.collection_uuid = server.id
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
        server = member.server
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "MEMBER"
        new.collection_uuid = (member.id, server.id)
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
