import re
from getpass import getpass
from typing import Match, Pattern, Tuple, Optional, AsyncIterator
from urllib.parse import quote_plus

try:
    import pymongo.errors
    import motor.core
    import motor.motor_asyncio
except ModuleNotFoundError:
    motor = None
    pymongo = None

from .. import errors
from .base import BaseDriver, IdentifierData

__all__ = ["MongoDriver"]


class MongoDriver(BaseDriver):
    """
    Subclass of :py:class:`.BaseDriver`.
    """

    _conn: Optional["motor.motor_asyncio.AsyncIOMotorClient"] = None

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        if motor is None:
            raise errors.MissingExtraRequirements(
                "Red must be installed with the [mongo] extra to use the MongoDB driver"
            )
        uri = storage_details.get("URI", "mongodb")
        host = storage_details["HOST"]
        port = storage_details["PORT"]
        user = storage_details["USERNAME"]
        password = storage_details["PASSWORD"]
        database = storage_details.get("DB_NAME", "default_db")

        if port is 0:
            ports = ""
        else:
            ports = ":{}".format(port)

        if user is not None and password is not None:
            url = "{}://{}:{}@{}{}/{}".format(
                uri, quote_plus(user), quote_plus(password), host, ports, database
            )
        else:
            url = "{}://{}{}/{}".format(uri, host, ports, database)

        cls._conn = motor.motor_asyncio.AsyncIOMotorClient(url)

    @classmethod
    async def teardown(cls) -> None:
        if cls._conn is not None:
            cls._conn.close()

    @staticmethod
    def get_config_details():
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

    @property
    def db(self) -> "motor.core.Database":
        """
        Gets the mongo database for this cog's name.

        :return:
            PyMongo Database object.
        """
        return self._conn.get_database()

    def get_collection(self, category: str) -> "motor.core.Collection":
        """
        Gets a specified collection within the PyMongo database for this cog.

        Unless you are doing custom stuff ``category`` should be one of the class
        attributes of :py:class:`core.config.Config`.

        :param str category:
        :return:
            PyMongo collection object.
        """
        return self.db[self.cog_name][category]

    @staticmethod
    def get_primary_key(identifier_data: IdentifierData) -> Tuple[str, ...]:
        # noinspection PyTypeChecker
        return identifier_data.primary_key

    @staticmethod
    async def rebuild_dataset(
        identifier_data: IdentifierData, cursor: "motor.motor_asyncio.AsyncIOMotorCursor"
    ):
        ret = {}
        async for doc in cursor:
            pkeys = doc["_id"]["RED_primary_key"]
            del doc["_id"]
            doc = self._unescape_dict_keys(doc)
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

        try:
            await mongo_collection.update_one(
                {"_id": {"RED_uuid": uuid, "RED_primary_key": primary_key}},
                update=update_stmt,
                upsert=True,
            )
        except pymongo.errors.WriteError as exc:
            if exc.args and exc.args[0].startswith("Cannot create field"):
                # There's a bit of a failing edge case here...
                # If we accidentally set the sub-field of an array, and the key happens to be a
                # digit, it will successfully set the value in the array, and not raise an error.
                # This is different to how other drivers would behave, and could lead to unexpected
                # behaviour.
                raise errors.CannotSetSubfield
            else:
                # Unhandled driver exception, should expose.
                raise

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
        # There are four cases here:
        # 1) We're clearing out a subset of identifiers (aka identifiers is NOT empty)
        # 2) We're clearing out full primary key and no identifiers (single document)
        # 3) We're clearing out partial primary key and no identifiers
        # 4) Primary key is empty, should wipe all documents in the collection
        # 5) Category is empty, should wipe out documents in many collections
        pkey_filter = self.generate_primary_key_filter(identifier_data)
        if identifier_data.identifiers:
            # This covers case 1
            mongo_collection = self.get_collection(identifier_data.category)
            dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
            await mongo_collection.update_one(pkey_filter, update={"$unset": {dot_identifiers: 1}})
        elif identifier_data.category:
            # This covers cases 2-4
            mongo_collection = self.get_collection(identifier_data.category)
            await mongo_collection.delete_many(pkey_filter)
        else:
            # This covers case 5
            db = self.db
            super_collection = db[self.cog_name]
            results = await db.list_collections(
                filter={"name": {"$regex": rf"^{super_collection.name}\."}}
            )
            for result in results:
                await db[result["name"]].delete_many(pkey_filter)

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        db = cls._conn.get_database()
        for collection_name in await db.list_collection_names():
            parts = collection_name.split(".")
            if not len(parts) == 2:
                continue
            cog_name = parts[0]
            for cog_id in await db[collection_name].distinct("_id.RED_uuid"):
                yield cog_name, cog_id

    @classmethod
    async def delete_all_data(
        cls, *, interactive: bool = False, drop_db: Optional[bool] = None, **kwargs
    ) -> None:
        """Delete all data being stored by this driver.

        Parameters
        ----------
        interactive : bool
            Set to ``True`` to allow the method to ask the user for
            input from the console, regarding the other unset parameters
            for this method.
        drop_db : Optional[bool]
            Set to ``True`` to drop the entire database for the current
            bot's instance. Otherwise, collections which appear to be
            storing bot data will be dropped.

        """
        if interactive is True and drop_db is None:
            print(
                "Please choose from one of the following options:\n"
                " 1. Drop the entire MongoDB database for this instance, or\n"
                " 2. Delete all of Red's data within this database, without dropping the database "
                "itself."
            )
            options = ("1", "2")
            while True:
                resp = input("> ")
                try:
                    drop_db = bool(options.index(resp))
                except ValueError:
                    print("Please type a number corresponding to one of the options.")
                else:
                    break
        db = cls._conn.get_database()
        if drop_db is True:
            await cls._conn.drop_database(db)
        else:
            async with await cls._conn.start_session() as session:
                async for cog_name, cog_id in cls.aiter_cogs():
                    await db.drop_collection(db[cog_name], session=session)

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
