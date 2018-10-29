import re
from typing import Match, Pattern
from urllib.parse import quote_plus

import motor.core
import motor.motor_asyncio

from .red_base import BaseDriver

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

    @staticmethod
    def _parse_identifiers(identifiers):
        uuid, identifiers = identifiers[0], identifiers[1:]
        return uuid, identifiers

    async def get(self, *identifiers: str):
        mongo_collection = self.get_collection()

        identifiers = (*map(self._escape_key, identifiers),)
        dot_identifiers = ".".join(identifiers)

        partial = await mongo_collection.find_one(
            filter={"_id": self.unique_cog_identifier}, projection={dot_identifiers: True}
        )

        if partial is None:
            raise KeyError("No matching document was found and Config expects a KeyError.")

        for i in identifiers:
            partial = partial[i]
        if isinstance(partial, dict):
            return self._unescape_dict_keys(partial)
        return partial

    async def set(self, *identifiers: str, value=None):
        dot_identifiers = ".".join(map(self._escape_key, identifiers))
        if isinstance(value, dict):
            value = self._escape_dict_keys(value)

        mongo_collection = self.get_collection()

        await mongo_collection.update_one(
            {"_id": self.unique_cog_identifier},
            update={"$set": {dot_identifiers: value}},
            upsert=True,
        )

    async def clear(self, *identifiers: str):
        dot_identifiers = ".".join(map(self._escape_key, identifiers))
        mongo_collection = self.get_collection()

        if len(identifiers) > 0:
            await mongo_collection.update_one(
                {"_id": self.unique_cog_identifier}, update={"$unset": {dot_identifiers: 1}}
            )
        else:
            await mongo_collection.delete_one({"_id": self.unique_cog_identifier})

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
