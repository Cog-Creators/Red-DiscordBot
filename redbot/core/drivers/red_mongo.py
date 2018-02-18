from typing import Tuple

import motor.motor_asyncio
from .red_base import BaseDriver

__all__ = ["Mongo"]


class Mongo(BaseDriver):
    """
    Subclass of :py:class:`.red_base.BaseDriver`.
    """
    def __init__(self, cog_name, **kwargs):
        super().__init__(cog_name)
        self.host = kwargs['HOST']
        self.port = kwargs['PORT']
        admin_user = kwargs['USERNAME']
        admin_pass = kwargs['PASSWORD']

        from ..data_manager import instance_name

        self.instance_name = instance_name

        self.conn = None

        self.admin_user = admin_user
        self.admin_pass = admin_pass

    async def _authenticate(self):
        self.conn = motor.motor_asyncio.AsyncIOMotorClient(host=self.host, port=self.port)

        if None not in (self.admin_pass, self.admin_user):
            await self.db.authenticate(self.admin_user, self.admin_pass)

    async def _ensure_connected(self):
        if self.conn is None:
            await self._authenticate()

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
        db_name = "RED_{}".format(self.instance_name)
        return self.conn[db_name]

    def get_collection(self) -> motor.core.Collection:
        """
        Gets a specified collection within the PyMongo database for this cog.

        Unless you are doing custom stuff ``collection_name`` should be one of the class
        attributes of :py:class:`core.config.Config`.

        :param str collection_name:
        :return:
            PyMongo collection object.
        """
        return self.db[self.cog_name]

    @staticmethod
    def _parse_identifiers(identifiers):
        uuid, identifiers = identifiers[0], identifiers[1:]
        return uuid, identifiers

    async def get(self, *identifiers: Tuple[str]):
        await self._ensure_connected()

        mongo_collection = self.get_collection()

        dot_identifiers = '.'.join(identifiers)

        partial = await mongo_collection.find_one(
            filter={'_id': self.unique_cog_identifier},
            projection={dot_identifiers: True}
        )

        if partial is None:
            raise KeyError("No matching document was found and Config expects"
                           " a KeyError.")

        for i in identifiers:
            partial = partial[i]
        return partial

    async def set(self, *identifiers: str, value=None):
        await self._ensure_connected()

        dot_identifiers = '.'.join(identifiers)

        mongo_collection = self.get_collection()

        await mongo_collection.update_one(
            {'_id': self.unique_cog_identifier},
            update={"$set": {dot_identifiers: value}},
            upsert=True
        )


def get_config_details():
    host = input("Enter host address: ")
    port = int(input("Enter host port: "))

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
