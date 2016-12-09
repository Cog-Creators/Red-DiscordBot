from copy import deepcopy
from .red_mongo import MissingCollection


class BaseConfig:
    def __init__(self, cog_name, unique_identifier, driver, hash_uuid=True,
                 collection="GLOBAL", collection_uuid=None, defaults={}):
        self.cog_name = cog_name
        if hash_uuid:
            self.uuid = hash(unique_identifier)
        else:
            self.uuid = unique_identifier
        self.driver = driver
        self.collection = collection
        self.collection_uuid = collection_uuid

        self.curr_key = None

        self.defaults = defaults if defaults else {
            "GLOBAL": {}, "SERVER": {}, "CHANNEL": {}, "ROLE": {},
            "MEMBER": {}, "USER": {}}

    def __getattr__(self, key):
        """This should be used to return config key data as determined by
            `self.collection` and `self.collection_uuid`."""
        raise NotImplemented

    def clear(self):
        """Clears all values in the current context ONLY."""
        raise NotImplemented

    def set(self, value):
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

    def registerGlobal(self, key, default=None):
        """Registers a global config key `key`"""
        self.defaults["GLOBAL"][key] = default

    def registerServer(self, key, default=None):
        """Registers a server config key `key`"""
        self.defaults["SERVER"][key] = default

    def registerChannel(self, key, default=None):
        """Registers a channel config key `key`"""
        self.defaults["CHANNEL"][key] = default

    def registerRole(self, key, default=None):
        """Registers a role config key `key`"""
        self.defaults["ROLE"][key] = default

    def registerMember(self, key, default=None):
        """Registers a member config key `key`"""
        self.defaults["MEMBER"][key] = default

    def registerUser(self, key, default=None):
        """Registers a user config key `key`"""
        self.defaults["USER"][key] = default


class MongoConfig(BaseConfig):

    __slots__ = ("collection", "collection_uuid", "curr_key")

    def __getattr__(self, key):
        try:
            default = self.defaults[self.collection][key]
        except KeyError as e:
            raise AttributeError("Key '{}' not registered!".format(key)) from e

        self.curr_key = key

        collections = {
            "GLOBAL": self.driver.get_global,
            "SERVER": self.driver.get_server,
            "CHANNEL": self.driver.get_channel,
            "ROLE": self.driver.get_role,
            "USER": self.driver.get_user
        }

        if self.collection != "MEMBER":
            collections[self.collection](self.cog_name, self.uuid,
                                         self.collection_uuid, key,
                                         default=default)
        else:
            mid, sid = self.collection_uuid
            self.driver.get_member(self.cog_name, self.uuid,
                                   mid, sid, key, default=default)

    def set(self, value):
        if self.collection == "GLOBAL":
            self.driver.set_global(self.cog_name, self.uuid, self.curr_key,
                                   value)
        elif self.collection == "SERVER":
            self.driver.set_server(self.cog_name, self.uuid,
                                   self.collection_uuid, self.curr_key, value)
        elif self.collection == "CHANNEL":
            self.driver.set_channel(self.cog_name, self.uuid,
                                    self.collection_uuid, self.curr_key, value)
        elif self.collection == "ROLE":
            self.driver.set_channel(self.cog_name, self.uuid,
                                    self.collection_uuid, self.curr_key, value)
        elif self.collection == "MEMBER":
            mid, sid = self.collection_uuid
            self.driver.set_member(self.cog_name, self.uuid, mid, sid,
                                   self.curr_key, value)
        elif self.collection == "USER":
            self.driver.set_user(self.cog_name, self.uuid,
                                 self.collection_uuid, self.curr_key, value)
        else:
            raise MissingCollection("Can't find collection: {}".format(
                self.collection))

    def server(self, server):
        new = deepcopy(self)
        new.collection = "SERVER"
        new.collection_uuid = server.id
        return new

    def channel(self, channel):
        new = deepcopy(self)
        new.collection = "CHANNEL"
        new.collection_uuid = channel.id
        return new

    def role(self, role):
        new = deepcopy(self)
        new.collection = "ROLE"
        new.collection_uuid = role.id
        return new

    def member(self, member):
        new = deepcopy(self)
        new.collection = "MEMBER"
        new.collection_uuid = (member.id, server.id)
        return new

    def user(self, user):
        new = deepcopy(self)
        new.collection = "USER"
        new.collection_uuid = user.id
        return new
