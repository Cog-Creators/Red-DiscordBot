import pymongo as m


class RedMongoException(Exception):
    """Base Red Mongo Exception class"""
    pass


class MultipleMatches(RedMongoException):
    """Raised when multiple documents match a single cog_name and
        cog_identifier pair."""
    pass


class MissingCollection(RedMongoException):
    """Raised when a collection is missing from the mongo db"""
    pass


class Mongo:
    def __init__(self, host, port=27017, **kwargs):
        self.conn = m.MongoClient(host=host, port=port, **kwargs)

        self._db = self.conn.red
        self._global = self._db.GLOBAL
        self._server = self._db.SERVER
        self._channel = self._db.CHANNEL
        self._role = self._db.ROLE
        self._member = self._db.MEMBER
        self._user = self._db.USER

    def get_global(self, cog_name, cog_identifier, key, *, default=None):
        doc = self._global.find(
            {"cog_name": cog_name, "cog_identifier": cog_identifier},
            projection=[key, ], batch_size=2)
        if doc.count() == 2:
            raise MultipleMatches("Too many matching documents at the GLOBAL"
                                  " level: ({}, {})".format(cog_name,
                                                            cog_identifier))
        elif doc.count() == 1:
            return doc[0].get(key, default)
        return default

    def get_server(self, cog_name, cog_identifier, server_id, key, *,
                   default=None):
        doc = self._server.find(
            {"cog_name": cog_name, "cog_identifier": cog_identifier,
             "server_id": server_id},
            projection=[key, ], batch_size=2)
        if doc.count() == 2:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, {})".format(
                                      cog_name, cog_identifier, server_id))
        elif doc.count() == 1:
            return doc[0].get(key, default)
        return default

    def get_channel(self, cog_name, cog_identifier, channel_id, key, *,
                    default=None):
        doc = self._channel.find(
            {"cog_name": cog_name, "cog_identifier": cog_identifier,
             "channel_id": channel_id},
            projection=[key, ], batch_size=2)
        if doc.count() == 2:
            raise MultipleMatches("Too many matching documents at the CHANNEL"
                                  " level: ({}, {}, {})".format(
                                      cog_name, cog_identifier, channel_id))
        elif doc.count() == 1:
            return doc[0].get(key, default)
        return default

    def get_role(self, cog_name, cog_identifier, role_id, key, *,
                 default=None):
        doc = self._role.find(
            {"cog_name": cog_name, "cog_identifier": cog_identifier,
             "role_id": role_id},
            projection=[key, ], batch_size=2)
        if doc.count() == 2:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, {})".format(
                                      cog_name, cog_identifier, role_id))
        elif doc.count() == 1:
            return doc[0].get(key, default)
        return default

    def get_member(self, cog_name, cog_identifier, user_id, server_id, key, *,
                   default=None):
        doc = self._member.find(
            {"cog_name": cog_name, "cog_identifier": cog_identifier,
             "user_id": user_id, "server_id": server_id},
            projection=[key, ], batch_size=2)
        if doc.count() == 2:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, mid {}, sid {})".format(
                                      cog_name, cog_identifier, user_id,
                                      server_id))
        elif doc.count() == 1:
            return doc[0].get(key, default)
        return default

    def get_user(self, cog_name, cog_identifier, user_id, key, *,
                 default=None):
        doc = self._user.find(
            {"cog_name": cog_name, "cog_identifier": cog_identifier,
             "user_id": user_id},
            projection=[key, ], batch_size=2)
        if doc.count() == 2:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, mid {})".format(
                                      cog_name, cog_identifier, user_id))
        elif doc.count() == 1:
            return doc[0].get(key, default)
        else:
            return default

    def set_global(self, cog_name, cog_identifier, key, value, clear=False):
        filter = {"cog_name": cog_name, "cog_identifier": cog_identifier}
        data = {"$set": {key: value}}
        if self._global.count(filter) > 1:
            raise MultipleMatches("Too many matching documents at the GLOBAL"
                                  " level: ({}, {})".format(cog_name,
                                                            cog_identifier))
        else:
            if clear:
                self._global.delete_one(filter)
            else:
                self._global.update_one(filter, data, upsert=True)

    def set_server(self, cog_name, cog_identifier, server_id, key, value,
                   clear=False):
        filter = {"cog_name": cog_name, "cog_identifier": cog_identifier,
                  "server_id": server_id}
        data = {"$set": {key: value}}
        if self._server.count(filter) > 1:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, {})".format(
                                      cog_name, cog_identifier, server_id))
        else:
            if clear:
                self._server.delete_one(filter)
            else:
                self._server.update_one(filter, data, upsert=True)

    def set_channel(self, cog_name, cog_identifier, channel_id, key, value,
                    clear=False):
        filter = {"cog_name": cog_name, "cog_identifier": cog_identifier,
                  "channel_id": channel_id}
        data = {"$set": {key: value}}
        if self._channel.count(filter) > 1:
            raise MultipleMatches("Too many matching documents at the CHANNEL"
                                  " level: ({}, {}, {})".format(
                                      cog_name, cog_identifier, channel_id))
        else:
            if clear:
                self._channel.delete_one(filter)
            else:
                self._channel.update_one(filter, data, upsert=True)

    def set_role(self, cog_name, cog_identifier, role_id, key, value,
                 clear=False):
        filter = {"cog_name": cog_name, "cog_identifier": cog_identifier,
                  "role_id": role_id}
        data = {"$set": {key: value}}
        if self._role.count(filter) > 1:
            raise MultipleMatches("Too many matching documents at the ROLE"
                                  " level: ({}, {}, {})".format(
                                      cog_name, cog_identifier, role_id))
        else:
            if clear:
                self._role.delete_one(filter)
            else:
                self._role.update_one(filter, data, upsert=True)

    def set_member(self, cog_name, cog_identifier, user_id, server_id, key,
                   value, clear=False):
        filter = {"cog_name": cog_name, "cog_identifier": cog_identifier,
                  "server_id": server_id, "user_id": user_id}
        data = {"$set": {key: value}}
        if self._member.count(filter) > 1:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, mid {}, sid {})".format(
                                      cog_name, cog_identifier, user_id,
                                      server_id))
        else:
            if clear:
                self._member.delete_one(filter)
            else:
                self._member.update_one(filter, data, upsert=True)

    def set_user(self, cog_name, cog_identifier, user_id, key, value,
                 clear=False):
        filter = {"cog_name": cog_name, "cog_identifier": cog_identifier,
                  "user_id": user_id}
        data = {"$set": {key: value}}
        if self._user.count(filter) > 1:
            raise MultipleMatches("Too many matching documents at the SERVER"
                                  " level: ({}, {}, mid {})".format(
                                      cog_name, cog_identifier, user_id))
        else:
            if clear:
                self._user.delete_one(filter)
            else:
                self._user.update_one(filter, data, upsert=True)
