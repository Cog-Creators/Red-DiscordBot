from typing import Tuple

import pymongo as m
from .red_base import BaseDriver


class Mongo(BaseDriver):
    def __init__(self, cog_name, host, port=27017, admin_user=None, admin_pass=None,
                 **kwargs):
        super().__init__(cog_name)
        self.conn = m.MongoClient(host=host, port=port, **kwargs)

        self.admin_user = admin_user
        self.admin_pass = admin_pass

        if self.admin_user is not None and self.admin_pass is not None:
            self.db.authenticate(self.admin_user, self.admin_pass)

    @property
    def db(self) -> m.database.Database:
        """
        Gets the mongo database for this cog's name.

        .. warning::

            Right now this will cause a new connection to be made every time the
            database is accessed. We will want to create a connection pool down the
            line to limit the number of connections.

        :return:
            PyMongo Database object.
        """
        return self.conn[self.cog_name]

    def get_collection(self, collection_name) -> m.collection.Collection:
        """
        Gets a specified collection within the PyMongo database for this cog.

        Unless you are doing custom stuff ``collection_name`` should be one of the class
        attributes of :py:class:`core.config.Config`.

        :param str collection_name:
        :return:
            PyMongo collection object.
        """
        return self.db[collection_name]

    @staticmethod
    def _parse_identifiers(identifiers):
        uuid, identifiers = identifiers[0], identifiers[1:]
        collection, identifiers = identifiers[0], identifiers[1:]
        return uuid, collection, identifiers

    def get(self, identifiers: Tuple[str]):
        uuid, collection, identifiers = self._parse_identifiers(identifiers)

        mongo_collection = self.get_collection(collection)

        dot_identifiers = '.'.join(identifiers)

        partial = mongo_collection.find_one(
            filter={'_id': uuid},
            projection={dot_identifiers: True}
        )

        for i in identifiers:
            partial = partial[i]
        return partial

    async def set(self, identifiers: Tuple[str], value):
        uuid, collection, identifiers = self._parse_identifiers(identifiers)

        dot_identifiers = '.'.join(identifiers)

        mongo_collection = self.get_collection(collection)

        mongo_collection.update_one(
            {'_id': uuid},
            update={"$set": {dot_identifiers: value}},
            upsert=True
        )

    def get_driver(self):
        return self
