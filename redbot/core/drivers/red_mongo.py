import re
from getpass import getpass
from typing import Match, Pattern, Tuple, Union
from urllib.parse import quote_plus

import motor.core
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorCursor

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

    async def has_valid_connection(self) -> bool:
        # Maybe fix this?
        return True

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

    def get_collection(self, category: str) -> motor.core.Collection:
        """
        Gets a specified collection within the PyMongo database for this cog.

        Unless you are doing custom stuff ``category`` should be one of the class
        attributes of :py:class:`core.config.Config`.

        :param str category:
        :return:
            PyMongo collection object.
        """
        return self.db[self.cog_name][category]

    def get_primary_key(self, identifier_data: IdentifierData) -> Tuple[str]:
        # noinspection PyTypeChecker
        return identifier_data.primary_key

    async def rebuild_dataset(self, identifier_data: IdentifierData, cursor: AsyncIOMotorCursor):
        ret = {}
        async for doc in cursor:
            pkeys = doc["_id"]["RED_primary_key"]
            del doc["_id"]
            if len(pkeys) == 0:
                # Global data
                ret.update(**doc)
            elif len(pkeys) > 0:
                # All other data
                partial = ret
                for key in pkeys[:-1]:
                    if key in identifier_data.primary_key:
                        continue
                    if key not in partial:
                        partial[key] = {}
                    partial = partial[key]
                if pkeys[-1] in identifier_data.primary_key:
                    partial.update(**doc)
                else:
                    partial[pkeys[-1]] = doc
        return ret

    async def get(self, identifier_data: IdentifierData):
        mongo_collection = self.get_collection(identifier_data.category)

        pkey_filter = self.generate_primary_key_filter(identifier_data)
        if len(identifier_data.identifiers) > 0:
            dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
            proj = {"_id": False, dot_identifiers: True}

            partial = await mongo_collection.find_one(filter=pkey_filter, projection=proj)
        else:
            # The case here is for partial primary keys like all_members()
            cursor = mongo_collection.find(filter=pkey_filter)
            partial = await self.rebuild_dataset(identifier_data, cursor)

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
            if len(value) == 0:
                await self.clear(identifier_data)
                return
            value = self._escape_dict_keys(value)

        mongo_collection = self.get_collection(identifier_data.category)
        if len(dot_identifiers) > 0:
            update_stmt = {"$set": {dot_identifiers: value}}
        else:
            update_stmt = {"$set": value}

        await mongo_collection.update_one(
            {"_id": {"RED_uuid": uuid, "RED_primary_key": primary_key}},
            update=update_stmt,
            upsert=True,
        )

    def generate_primary_key_filter(self, identifier_data: IdentifierData):
        uuid = self._escape_key(identifier_data.uuid)
        primary_key = list(map(self._escape_key, self.get_primary_key(identifier_data)))
        ret = {"_id.RED_uuid": uuid}
        if len(identifier_data.identifiers) > 0:
            ret["_id.RED_primary_key"] = primary_key
        elif len(identifier_data.primary_key) > 0:
            for i, key in enumerate(primary_key):
                keyname = f"_id.RED_primary_key.{i}"
                ret[keyname] = key
        else:
            ret["_id.RED_primary_key"] = {"$exists": True}
        return ret

    async def clear(self, identifier_data: IdentifierData):
        # There are three cases here:
        # 1) We're clearing out a subset of identifiers (aka identifiers is NOT empty)
        # 2) We're clearing out full primary key and no identifiers
        # 3) We're clearing out partial primary key and no identifiers
        # 4) Primary key is empty, should wipe all documents in the collection
        mongo_collection = self.get_collection(identifier_data.category)
        pkey_filter = self.generate_primary_key_filter(identifier_data)
        if len(identifier_data.identifiers) == 0:
            # This covers cases 2-4
            await mongo_collection.delete_many(pkey_filter)
        else:
            dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
            await mongo_collection.update_one(pkey_filter, update={"$unset": {dot_identifiers: 1}})

    async def inc(self, identifier_data: IdentifierData, value: Union[int, float], default):
        if len(identifier_data.identifiers) == 0:
            raise ValueError("Cannot call incr on a group!")

        if default != 0:
            try:
                # If this does not error the data is already in the DB and we can safely
                # make an $inc call.
                await self.get(identifier_data)
            except KeyError:
                curr_value = default
                await self.set(identifier_data, curr_value + value)
                return curr_value + value

        # If default is 0 we can do an atomic incr
        uuid = self._escape_key(identifier_data.uuid)
        primary_key = list(map(self._escape_key, self.get_primary_key(identifier_data)))
        dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))

        mongo_collection = self.get_collection(identifier_data.category)
        update_stmt = {"$inc": {dot_identifiers: value}}
        await mongo_collection.update_one(
            {"_id": {"RED_uuid": uuid, "RED_primary_key": primary_key}},
            update=update_stmt,
            upsert=True,
        )
        return await self.get(identifier_data)

    async def toggle(self, identifier_data: IdentifierData, default) -> bool:
        try:
            curr_val = await self.get(identifier_data)
        except KeyError:
            curr_val = default

        await self.set(identifier_data, not curr_val)
        return not curr_val

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
    admin_password = getpass("Enter login password: ")

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
