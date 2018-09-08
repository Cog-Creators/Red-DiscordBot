import motor.motor_asyncio
from .red_base import BaseDriver
from urllib.parse import quote

__all__ = ["Mongo"]


_conn = None


def _initialize(**kwargs):
    host = kwargs["HOST"]
    port = kwargs["PORT"]
    admin_user = kwargs["USERNAME"]
    admin_pass = kwargs["PASSWORD"]
    db_name = kwargs.get("DB_NAME", "default_db")

    if admin_user is not None and admin_pass is not None:
        url = "mongodb://{}:{}@{}:{}/{}".format(quote(admin_user), quote(admin_pass), host, port, db_name)
    else:
        url = "mongodb://{}:{}/{}".format(host, port, db_name)

    global _conn
    _conn = motor.motor_asyncio.AsyncIOMotorClient(url)


class Mongo(BaseDriver):
    """
    Subclass of :py:class:`.red_base.BaseDriver`.
    """

    def __init__(self, cog_name, identifier, **kwargs):
        super().__init__(cog_name, identifier)

        if _conn is None:
            _initialize(**kwargs)

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
        return _conn.get_database()

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

    async def get(self, *identifiers: str):
        mongo_collection = self.get_collection()

        dot_identifiers = ".".join(identifiers)

        partial = await mongo_collection.find_one(
            filter={"_id": self.unique_cog_identifier}, projection={dot_identifiers: True}
        )

        if partial is None:
            raise KeyError("No matching document was found and Config expects a KeyError.")

        for i in identifiers:
            partial = partial[i]
        return partial

    async def set(self, *identifiers: str, value=None):
        dot_identifiers = ".".join(identifiers)

        mongo_collection = self.get_collection()

        await mongo_collection.update_one(
            {"_id": self.unique_cog_identifier},
            update={"$set": {dot_identifiers: value}},
            upsert=True,
        )

    async def clear(self, *identifiers: str):
        dot_identifiers = ".".join(identifiers)
        mongo_collection = self.get_collection()

        if len(identifiers) > 0:
            await mongo_collection.update_one(
                {"_id": self.unique_cog_identifier}, update={"$unset": {dot_identifiers: 1}}
            )
        else:
            await mongo_collection.delete_one({"_id": self.unique_cog_identifier})


def get_config_details():
    host = input("Enter host address: ")
    port = int(input("Enter host port: "))

    admin_uname = input("Enter login username: ")
    admin_password = input("Enter login password: ")

    db_name = input("Enter mongodb database name: ")

    if admin_uname == "":
        admin_uname = admin_password = None

    ret = {
        "HOST": host,
        "PORT": port,
        "USERNAME": admin_uname,
        "PASSWORD": admin_password,
        "DB_NAME": db_name,
    }
    return ret
