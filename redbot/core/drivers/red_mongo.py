import re
from typing import Match, Pattern, Tuple
from urllib.parse import quote_plus

import motor.core
import motor.motor_asyncio

from .red_base import BaseDriver, IdentifierData

__all__ = ["Mongo"]


_conn = None


def _initialize(**kwargs):
    uri = kwargs.get("URI", "mongodb")
    host = kwargs["HOST"]
    port = kwargs["PORT"]
    admin_user = kwargs["USERNAME"]
    admin_pass = kwargs["PASSWORD"]
    db_name = kwargs.get("DB_NAME", "default_db")

    if port is 0:
        ports = ""
    else:
        ports = ":{}".format(port)

    if admin_user is not None and admin_pass is not None:
        url = "{}://{}:{}@{}{}/{}".format(
            uri, quote_plus(admin_user), quote_plus(admin_pass), host, ports, db_name
        )
    else:
        url = "{}://{}{}/{}".format(uri, host, ports, db_name)

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

    def get_primary_key(self, identifier_data: IdentifierData) -> Tuple[str]:
        # noinspection PyTypeChecker
        return (identifier_data.category, *identifier_data.primary_key)

    async def get(self, identifier_data: IdentifierData):
        mongo_collection = self.get_collection()

        uuid = self._escape_key(identifier_data.uuid)
        primary_key = list(map(self._escape_key, self.get_primary_key(identifier_data)))
        dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))

        partial = await mongo_collection.find_one(
            filter={"RED_uuid": uuid, "RED_primary_key": primary_key},
            projection={dot_identifiers: True},
        )

        if partial is None:
            raise KeyError("No matching document was found and Config expects a KeyError.")

        for i in identifier_data.identifiers:
            partial = partial[i]
        if isinstance(partial, dict):
            return self._unescape_dict_keys(partial)
        return partial

    async def set(self, identifier_data: IdentifierData, value=None):
        uuid = self._escape_key(identifier_data.uuid)
        primary_key = list(map(self._escape_key, self.get_primary_key(identifier_data)))
        dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
        if isinstance(value, dict):
            value = self._escape_dict_keys(value)

        mongo_collection = self.get_collection()

        await mongo_collection.update_one(
            {"RED_uuid": uuid, "RED_primary_key": primary_key},
            update={"$set": {dot_identifiers: value}},
            upsert=True,
        )

    def generate_primary_key_filter(self, identifier_data: IdentifierData):
        uuid = self._escape_key(identifier_data.uuid)
        primary_key = list(map(self._escape_key, self.get_primary_key(identifier_data)))
        internal = [{"RED_uuid": uuid}]
        for key in primary_key:
            internal.append({"RED_primary_key": {"$in": [key]}})
        return {"$and": internal}

    async def clear(self, identifier_data: IdentifierData):
        # There are three cases here:
        # 1) We're clearing out a subset of identifiers (aka identifiers is NOT empty)
        # 2) We're clearing out full primary key and no identifiers
        # 3) We're clearing out partial primary key and no identifiers
        # 4) Primary key is empty, should wipe all documents in the collection
        mongo_collection = self.get_collection()
        pkey_filter = self.generate_primary_key_filter(identifier_data)
        if len(identifier_data.identifiers) == 0:
            # This covers cases 2-4
            await mongo_collection.delete_many(pkey_filter)
        else:
            dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
            await mongo_collection.update_one(pkey_filter, update={"$unset": {dot_identifiers: 1}})

    @staticmethod
    def _escape_key(key: str) -> str:
        return _SPECIAL_CHAR_PATTERN.sub(_replace_with_escaped, key)

    @staticmethod
    def _unescape_key(key: str) -> str:
        return _CHAR_ESCAPE_PATTERN.sub(_replace_with_unescaped, key)

    @classmethod
    def _escape_dict_keys(cls, data: dict) -> dict:
        """Recursively escape all keys in a dict."""
        ret = {}
        for key, value in data.items():
            key = cls._escape_key(key)
            if isinstance(value, dict):
                value = cls._escape_dict_keys(value)
            ret[key] = value
        return ret

    @classmethod
    def _unescape_dict_keys(cls, data: dict) -> dict:
        """Recursively unescape all keys in a dict."""
        ret = {}
        for key, value in data.items():
            key = cls._unescape_key(key)
            if isinstance(value, dict):
                value = cls._unescape_dict_keys(value)
            ret[key] = value
        return ret


_SPECIAL_CHAR_PATTERN: Pattern[str] = re.compile(r"([.$]|\\U0000002E|\\U00000024)")
_SPECIAL_CHARS = {
    ".": "\\U0000002E",
    "$": "\\U00000024",
    "\\U0000002E": "\\U&0000002E",
    "\\U00000024": "\\U&00000024",
}


def _replace_with_escaped(match: Match[str]) -> str:
    return _SPECIAL_CHARS[match[0]]


_CHAR_ESCAPE_PATTERN: Pattern[str] = re.compile(r"(\\U0000002E|\\U00000024)")
_CHAR_ESCAPES = {
    "\\U0000002E": ".",
    "\\U00000024": "$",
    "\\U&0000002E": "\\U0000002E",
    "\\U&00000024": "\\U00000024",
}


def _replace_with_unescaped(match: Match[str]) -> str:
    return _CHAR_ESCAPES[match[0]]


def get_config_details():
    uri = None
    while True:
        uri = input("Enter URI scheme (mongodb or mongodb+srv): ")
        if uri is "":
            uri = "mongodb"

        if uri in ["mongodb", "mongodb+srv"]:
            break
        else:
            print("Invalid URI scheme")

    host = input("Enter host address: ")
    if uri is "mongodb":
        port = int(input("Enter host port: "))
    else:
        port = 0

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
        "URI": uri,
    }
    return ret
