from typing import Tuple

import asyncio

import motor.motor_asyncio
from .red_base import BaseDriver


class Mongo(BaseDriver):
    """
    Subclass of :py:class:`.red_base.BaseDriver`.
    """
    def __init__(self, cog_name, **kwargs):
        super().__init__(cog_name)
        host = kwargs['HOST']
        port = kwargs['PORT']
        admin_user = kwargs['USERNAME']
        admin_pass = kwargs['PASSWORD']

        self.conn = motor.motor_asyncio.AsyncIOMotorClient(host=host, port=port)

        self.admin_user = admin_user
        self.admin_pass = admin_pass

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._authenticate())

    async def _authenticate(self):
        if None not in (self.admin_pass, self.admin_user):
            await self.db.authenticate(self.admin_user, self.admin_pass)

    @property
    def db(self) -> motor.core.Database:
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

    def get_collection(self, collection_name) -> motor.core.Collection:
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

    async def get(self, identifiers: Tuple[str]):
        uuid, collection, identifiers = self._parse_identifiers(identifiers)

        mongo_collection = self.get_collection(collection)

        dot_identifiers = '.'.join(identifiers)

        partial = await mongo_collection.find_one(
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

        await mongo_collection.update_one(
            {'_id': uuid},
            update={"$set": {dot_identifiers: value}},
            upsert=True
        )

    def get_driver(self):
        return self

    def get_config_details(self):
        host = input("Enter host address: ")
        port = input("Enter host port: ")

        admin_uname = input("Enter login username: ")
        admin_password = input("Enter login password: ")

        if admin_uname == "":
            admin_uname = admin_password = None

        ret = {
            'HOST': host,
            'PORT': port,
            'USERNAME': admin_uname,
            'PASSWORD': admin_password
        }
        return ret
