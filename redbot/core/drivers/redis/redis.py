import asyncio
import base64
import getpass
import re
from typing import Optional, Callable, Any, Union, AsyncIterator, Tuple, Pattern

from redbot.core import errors
from redbot.core.drivers.log import log
from secrets import compare_digest

try:
    # pylint: disable=import-error
    import aioredis
    import aioredis_lock
    import ujson
    from .client_interface import Client
except ModuleNotFoundError:
    aioredis = None
    Client = None
    import json as ujson


from ..base import BaseDriver, IdentifierData, ConfigCategory
from ...errors import StoredTypeError

__all__ = ["RedisDriver"]


# noinspection PyProtectedMember
class RedisDriver(BaseDriver):
    _pool: Optional["Client"] = None
    _lock: Optional["asyncio.Lock"] = None

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        if aioredis is None:
            raise errors.MissingExtraRequirements(
                "Red must be installed with the [redis] extra to use the Redis driver"
            )
        host = storage_details["host"]
        port = storage_details["port"]
        password = storage_details["password"]
        database = storage_details.get("database", 0)
        address = f"redis://{host}:{port}"
        client = await aioredis.create_redis_pool(
            address=address, db=database, password=password, encoding="utf-8", maxsize=50
        )
        cls._pool = Client(client._pool_or_conn)
        cls._lock = asyncio.Lock()

    @classmethod
    async def teardown(cls) -> None:
        if cls._pool is not None:
            cls._pool.close()
            await cls._pool.wait_closed()

    @staticmethod
    def get_config_details():
        host = (
            input(
                f"Enter the Redis server's address "
                f"(This server needs the RedisJSON extension: "
                f"https://hub.docker.com/r/redislabs/rejson/).\n"
                f"If left blank, Red will try the following, in order:\n"
                f" - localhost.\n"
                f"> "
            )
            or "localhost"
        )

        print(
            "Enter the Redis server port.\n"
            "If left blank, this will default to either:\n"
            " - 6379."
        )
        while True:
            port = input("> ") or 6379
            if port == 6379:
                break

            try:
                port = int(port)
            except ValueError:
                print("Port must be a number")
            else:
                break
        password = getpass.getpass(
            f"Enter the Redis server password. The input will be hidden.\n"
            f"  NOTE: If the server requires no password, enter NONE (Case sensitive).\n"
            f"When NONE is entered, this will default to:\n"
            f" - No password.\n"
            f"> "
        )
        if compare_digest(password, "NONE"):
            password = None
        print(
            "Enter the Redis database's number.\n"
            "If left blank, this will default to either:\n"
            " - 0.\n"
        )
        while True:
            database = input("> ") or 0
            if database == 0:
                break

            try:
                database = int(database)
            except ValueError:
                print("Database must be a number")
            else:
                break

        return {
            "host": host,
            "port": port,
            "password": password,
            "database": database,
        }

    async def _pre_flight(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = _full_identifiers[0], _full_identifiers[1:]
        async with self._lock:
            _cur_path = "."
            await self._pool.jsonset(cog_name, path=_cur_path, obj={}, nx=True)
            for i in full_identifiers:
                if _cur_path.endswith("."):
                    _cur_path += self._escape_key(i)
                else:
                    _cur_path += f".{self._escape_key(i)}"
                await self._pool.jsonset(cog_name, path=_cur_path, obj={}, nx=True)
        # if await self._pool.jsonget(cog_name, path=_cur_path) == {}:
        #     await self._pool.jsondel(cog_name, path=_cur_path)

    @classmethod
    async def _execute(cls, query: str, *args, method: Optional[Callable] = None, **kwargs) -> Any:
        if method is None:
            method = cls._pool.execute
        log.invisible("Query: %s", query)
        if args:
            log.invisible("Args: %s", args)
        return await method(query, *args, **kwargs)

    async def get(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = _full_identifiers[0], _full_identifiers[1:]
        full_identifiers = list(map(self._escape_key, full_identifiers))
        await self._pre_flight(identifier_data)
        try:
            result = await self._execute(cog_name, *full_identifiers, method=self._pool.jsonget,)
        except aioredis.errors.ReplyError:
            raise KeyError
        if isinstance(result, str):
            result = ujson.loads(result)
        if isinstance(result, dict):
            if result == {}:
                raise KeyError
            result = self._unescape_dict_keys(result)
        return result

    async def set(self, identifier_data: IdentifierData, value=None):
        try:
            _full_identifiers = identifier_data.to_tuple()
            cog_name, full_identifiers = _full_identifiers[0], _full_identifiers[1:]
            identifier_string = "."
            identifier_string += ".".join(map(self._escape_key, full_identifiers))
            value_copy = ujson.loads(ujson.dumps(value))
            if isinstance(value_copy, dict):
                value_copy = self._escape_dict_keys(value_copy)
            await self._pre_flight(identifier_data)
            async with self._lock:
                await self._execute(
                    cog_name, path=identifier_string, obj=value_copy, method=self._pool.jsonset,
                )
        except Exception as exc:
            log.exception(exc, exc_info=exc)

    async def clear(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = _full_identifiers[0], _full_identifiers[1:]
        identifier_string = "."
        identifier_string += ".".join(map(self._escape_key, full_identifiers))
        await self._pre_flight(identifier_data)
        async with self._lock:
            await self._execute(
                cog_name, path=identifier_string, method=self._pool.jsondel,
            )

    async def inc(
        self,
        identifier_data: IdentifierData,
        value: Union[int, float],
        default: Union[int, float] = 0,
    ) -> Union[int, float]:
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = _full_identifiers[0], _full_identifiers[1:]
        identifier_string = "."
        identifier_string += ".".join(map(self._escape_key, full_identifiers))
        await self._pre_flight(identifier_data)

        async with self._lock:
            _type = await self._pool.jsontype(name=cog_name, path=identifier_string)
            if _type is None:
                await self._execute(
                    cog_name, path=identifier_string, obj=default, method=self._pool.jsonset,
                )
            elif _type not in [
                "integer",
                "number",
            ]:
                raise StoredTypeError("The value is not a Integer or Float")
            applying = await self._execute(
                cog_name, path=identifier_string, number=value, method=self._pool.jsonnumincrby,
            )
            return ujson.loads(applying)

    async def toggle(
        self, identifier_data: IdentifierData, value: bool = None, default: Optional[bool] = None
    ) -> bool:
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = _full_identifiers[0], _full_identifiers[1:]
        identifier_string = "."
        identifier_string += ".".join(map(self._escape_key, full_identifiers))
        await self._pre_flight(identifier_data)
        value = value if value is not None else default
        async with self._lock:
            _type = await self._pool.jsontype(name=cog_name, path=identifier_string)
            if _type not in [None, "null", "boolean"]:
                raise StoredTypeError("The value is not a Boolean or Null")
            elif _type in [None, "null"]:
                await self._execute(
                    cog_name, path=identifier_string, obj=not value, method=self._pool.jsonset,
                )
                return not value
            else:
                result = await self._execute(
                    cog_name, path=identifier_string, method=self._pool.jsonget,
                )
                result = not ujson.loads(result)
                await self._execute(
                    cog_name, path=identifier_string, obj=result, method=self._pool.jsonset,
                )
                return result

    @classmethod
    async def delete_all_data(cls, **kwargs) -> None:
        """Delete all data being stored by this driver."""
        await cls._pool.flushdb(async_op=True)

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        cogs = await cls._pool.keys("*", encoding="utf-8")
        for cog in cogs:
            cog_ids = await cls._pool.jsonobjkeys(cog, ".")
            for cog_id in cog_ids:
                yield cog, cog_id

    async def import_data(self, cog_data, custom_group_data):
        for category, all_data in cog_data:
            splitted_pkey = self._split_primary_key(category, custom_group_data, all_data)
            for pkey, data in splitted_pkey:
                ident_data = IdentifierData(
                    self.cog_name,
                    self.unique_cog_identifier,
                    category,
                    pkey,
                    (),
                    *ConfigCategory.get_pkey_info(category, custom_group_data),
                )
                await self.set(ident_data, data)

    @staticmethod
    def _escape_key(key: str) -> str:
        string = key
        return string

    @staticmethod
    def _unescape_key(key: str) -> str:
        return key

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


_CHAR_ESCAPE_PATTERN: Pattern[str] = re.compile(r"^(\$)")
