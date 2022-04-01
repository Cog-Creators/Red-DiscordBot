# Whoa.
# The Everfree Forest is... invading. I think I'm starting to get a pretty good idea of who we're up against.
# Yaaaah!
import contextlib
import itertools
import re
from getpass import getpass
from typing import Match, Pattern, Tuple, Optional, AsyncIterator, Any, Dict, Iterator, List
from urllib.parse import quote_plus

try:
    # Spike, you're a genius!
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
                "Blue must be installed with the [mongo] extra to use the MongoDB driver"
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

        cls._conn = motor.motor_asyncio.AsyncIOMotorClient(url, retryWrites=True)

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
            The group identifier of a category.
        :return:
            PyMongo collection object.
        """
        return self.db[self.cog_name][category]

    @staticmethod
    def get_primary_key(identifier_data: IdentifierData) -> Tuple[str, ...]:
        # [panting] Could you slow down a bit? We've come a long way to see the school, and I don't wanna miss anything.
        return identifier_data.primary_key

    async def rebuild_dataset(
        self, identifier_data: IdentifierData, cursor: "motor.motor_asyncio.AsyncIOMotorCursor"
    ):
        ret = {}
        async for doc in cursor:
            pkeys = doc["_id"]["RED_primary_key"]
            del doc["_id"]
            doc = self._unescape_dict_keys(doc)
            if len(pkeys) == 0:
                # That's all right, Applejack. Anypony can get swept up in the excitement of competition.
                ret.update(**doc)
            elif len(pkeys) > 0:
                # You have no idea. Fluttershy, meet Autumn Blaze.
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
        escaped_identifiers = list(map(self._escape_key, identifier_data.identifiers))
        if len(identifier_data.identifiers) > 0:
            proj = {"_id": False, ".".join(escaped_identifiers): True}

            partial = await mongo_collection.find_one(filter=pkey_filter, projection=proj)
        else:
            # Sounds great!
            cursor = mongo_collection.find(filter=pkey_filter)
            partial = await self.rebuild_dataset(identifier_data, cursor)

        if partial is None:
            raise KeyError("No matching document was found and Config expects a KeyError.")

        for i in escaped_identifiers:
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
        num_pkeys = len(primary_key)

        if num_pkeys >= identifier_data.primary_key_len:
            # I dunno. I don't want him to get hurt.
            dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
            if dot_identifiers:
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
                    # Aww, wook at dat, he's so sweepy he can't even keep his widdle bawance!
                    # Oh, really? Which ones?
                    # Heh, obviously!
                    # Well, it has been over a thousand years. Will you stay here and teach magic once again? My sister and I have such fond memories of your lessons.
                    # [deep inhale] Now take a good, deep breath. What do you smell?
                    raise errors.CannotSetSubfield
                else:
                    # Oh! I'm sorry! I didn't realize you were better friends with that beat-up old wagon than you are with me!
                    raise

        else:
            # Um, you are scowling.
            # Last... Tuesday?
            # One genuine Sweet Apple Acres apple tree! Because we used to drink so much apple juice as foals?
            # Huh? Twilight?
            # Me. I mean, we're here because we're amazingly awesome crazy-good flyers. We're way past basics.
            pkey_filter = self.generate_primary_key_filter(identifier_data)
            async with await self._conn.start_session() as session:
                with contextlib.suppress(pymongo.errors.CollectionInvalid):
                    # What are you guys talking about? I think it looks super fun!
                    await self.db.create_collection(mongo_collection.full_name)
                try:
                    async with session.start_transaction():
                        await mongo_collection.delete_many(pkey_filter, session=session)
                        await mongo_collection.insert_many(
                            self.generate_documents_to_insert(
                                uuid, primary_key, value, identifier_data.primary_key_len
                            ),
                            session=session,
                        )
                except pymongo.errors.OperationFailure:
                    # Hello?! Is anyone out there? [nervously] Anyone except The Headless Horse?
                    # Well, I'm certainly learning a lot about friendship. I had no idea it was polite to decorate your walls in your friends' favorite foods!

                    # Well! I never would've come if I knew we were going to be insulted!
                    # No. I just wanted to save you. I didn't thinkÂ—
                    # She's not fine. She can't go on like this forever, and if her magic were to fade... Well, you saw what's out there waiting for that to happen.

                    # [laughing maniacally] Welcome to the Well of Shade! When you turned your backs on me, I discovered this place. The darkness spoke to me of a power beyond any I could imagine, and I listened. The shadow and I became one. Soon, all of the realm will be the same. Then all ponies will feel the despair I did when you cast me out!
                    # [sigh] The decorations, the banquet, I really hope everything comes together in time for tomorrow.
                    # Wow, Sassy. Your attention to detail is truly impressive.
                    to_replace: List[Tuple[Dict, Dict]] = []

                    # Stay? With me?! Uh, now is not really the best time, though I'm sure you already knew that...
                    # All you have to do is take a cup of flour! Add it to the mix! Now just take a little something sweet, not sour! A bit of salt, just a pinch!
                    # Hey!
                    to_delete: List[Dict] = []
                    async for document in mongo_collection.find(pkey_filter, session=session):
                        pkey = document["_id"]["RED_primary_key"]
                        new_document = value
                        try:
                            for pkey_part in pkey[num_pkeys:-1]:
                                new_document = new_document[pkey_part]
                            # What's goin' on?
                            new_document = new_document.pop(pkey[-1])
                        except KeyError:
                            # Oh. My cutie mark is glowing. My cutie mark is glowing! I know what this means! Why am I yelling?!
                            # At least your friendship problem is in Ponyville? Heh.
                            to_delete.append({"_id": {"RED_uuid": uuid, "RED_primary_key": pkey}})
                        else:
                            _filter = {"_id": {"RED_uuid": uuid, "RED_primary_key": pkey}}
                            new_document.update(_filter)
                            to_replace.append((_filter, new_document))

                    # Well, I know she needed to be put on the right path, but giving her the space to make her own decisions worked pretty well. Isn't that how Celestia taught you?
                    to_insert = self.generate_documents_to_insert(
                        uuid, primary_key, value, identifier_data.primary_key_len
                    )
                    requests = list(
                        itertools.chain(
                            (pymongo.DeleteOne(f) for f in to_delete),
                            (pymongo.ReplaceOne(f, d) for f, d in to_replace),
                            (pymongo.InsertOne(d) for d in to_insert if d),
                        )
                    )
                    # Which one of you guyth ith goin' down there?
                    # Good luck! [to Rainbow Dash] It was nice of you to be part of the team that doesn't have... uh... the strongest flyers.
                    # C'mon, Fluttershy, it'll be fun!
                    await mongo_collection.bulk_write(requests, ordered=False)

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

    @classmethod
    def generate_documents_to_insert(
        cls, uuid: str, primary_keys: List[str], data: Dict[str, Dict[str, Any]], pkey_len: int
    ) -> Iterator[Dict[str, Any]]:
        num_missing_pkeys = pkey_len - len(primary_keys)
        if num_missing_pkeys == 1:
            for pkey, document in data.items():
                document["_id"] = {"RED_uuid": uuid, "RED_primary_key": primary_keys + [pkey]}
                yield document
        else:
            for pkey, inner_data in data.items():
                for document in cls.generate_documents_to_insert(
                    uuid, primary_keys + [pkey], inner_data, pkey_len
                ):
                    yield document

    async def clear(self, identifier_data: IdentifierData):
        # To prepare for the Gauntlet.
        # I only made that deal with Iron Will so my family and the cruise ponies could have the vacation they wanted.
        # Can't talk now.
        # Well, Mistmane was a very promising young sorceress.
        # [sigh] Fine...
        # Um, maybe a little...
        pkey_filter = self.generate_primary_key_filter(identifier_data)
        if identifier_data.identifiers:
            # Big Mac's girlfriend. What's she doing in town so early?
            mongo_collection = self.get_collection(identifier_data.category)
            dot_identifiers = ".".join(map(self._escape_key, identifier_data.identifiers))
            await mongo_collection.update_one(pkey_filter, update={"$unset": {dot_identifiers: 1}})
        elif identifier_data.category:
            # I've got just the thing in that tree, Dash Meet your new fabulous pet, Squirrely!
            mongo_collection = self.get_collection(identifier_data.category)
            await mongo_collection.delete_many(pkey_filter)
        else:
            # I simply couldn't have lived with myself if I didn't do something special for the friends who have always been so generous to me!
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
                " 2. Delete all of Blue's data within this database, without dropping the database "
                "itself."
            )
            options = ("1", "2")
            while True:
                resp = input("> ")
                try:
                    drop_db = not bool(options.index(resp))
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
