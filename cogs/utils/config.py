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

        self.driver_getmap = {
            "GLOBAL": self.driver.get_global,
            "SERVER": self.driver.get_server,
            "CHANNEL": self.driver.get_channel,
            "ROLE": self.driver.get_role,
            "USER": self.driver.get_user
        }

        self.driver_setmap = {
            "GLOBAL": self.driver.set_global,
            "SERVER": self.driver.set_server,
            "CHANNEL": self.driver.set_channel,
            "ROLE": self.driver.set_role,
            "USER": self.driver.set_user
        }

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


class Config(BaseConfig):

    __slots__ = ("collection", "collection_uuid", "curr_key")

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

        if self.collection == "GLOBAL":
            self.driver.set_global(self.cog_name, self.uuid, key,
                                   value)
        elif self.collection == "SERVER":
            self.driver.set_server(self.cog_name, self.uuid,
                                   self.collection_uuid, key, value)
        elif self.collection == "CHANNEL":
            self.driver.set_channel(self.cog_name, self.uuid,
                                    self.collection_uuid, key, value)
        elif self.collection == "ROLE":
            self.driver.set_channel(self.cog_name, self.uuid,
                                    self.collection_uuid, key, value)
        elif self.collection == "MEMBER":
            mid, sid = self.collection_uuid
            self.driver.set_member(self.cog_name, self.uuid, mid, sid,
                                   key, value)
        elif self.collection == "USER":
            self.driver.set_user(self.cog_name, self.uuid,
                                 self.collection_uuid, key, value)
        else:
            raise MissingCollection("Can't find collection: {}".format(
                self.collection))

    def clear(self):
        self.driver_setmap[self.collection](
            self.cog_name, self.uuid, self.collection_uuid, None, None,
            clear=True)

    def server(self, server):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "SERVER"
        new.collection_uuid = server.id
        return new

    def channel(self, channel):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "CHANNEL"
        new.collection_uuid = channel.id
        return new

    def role(self, role):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "ROLE"
        new.collection_uuid = role.id
        return new

    def member(self, member):
        server = member.server
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "MEMBER"
        new.collection_uuid = (member.id, server.id)
        return new

    def user(self, user):
        new = type(self)(self.cog_name, self.uuid, self.driver,
                         hash_uuid=False, defaults=self.defaults)
        new.collection = "USER"
        new.collection_uuid = user.id
        return new
