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
    from .client_interface import Client, create_redis_pool, str_path
except ImportError:
    aioredis = None
    Client = None

try:
    # pylint: disable=import-error
    import ujson as json
except ImportError:
    import json

from ..base import BaseDriver, IdentifierData, ConfigCategory
from ...errors import StoredTypeError

__all__ = ["RedisDriver"]


# noinspection PyProtectedMember
class RedisDriver(BaseDriver):
    _pool: Optional["Client"] = None
    _pool_set: Optional["Client"] = None
    _pool_get: Optional["Client"] = None
    _pool_pre_flight: Optional["Client"] = None
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
        cls._pool = await create_redis_pool(
            address=address, db=database, password=password, encoding="utf-8", maxsize=50,
        )
        cls._pool_set = await create_redis_pool(
            address=address, db=database, password=password, encoding="utf-8", maxsize=50,
        )
        cls._pool_get = await create_redis_pool(
            address=address, db=database, password=password, encoding="utf-8", maxsize=50,
        )
        cls._pool_pre_flight = await create_redis_pool(
            address=address, db=database, password=password, encoding="utf-8", maxsize=50,
        )
        cls._lock = asyncio.Lock()

    @classmethod
    async def teardown(cls) -> None:
        if cls._pool is not None:
            cls._pool.close()
            await cls._pool.wait_closed()
        if cls._pool_get is not None:
            cls._pool_get.close()
            await cls._pool_get.wait_closed()
        if cls._pool_set is not None:
            cls._pool_set.close()
            await cls._pool_set.wait_closed()
        if cls._pool_pre_flight is not None:
            cls._pool_pre_flight.close()
            await cls._pool_pre_flight.wait_closed()

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
        cog_name, full_identifiers = self._escape_key(_full_identifiers[0]), _full_identifiers[1:]
        full_identifiers_test = list(map(self._escape_key, full_identifiers))

        try:
            string = "."
            string += ".".join([str_path(p) for p in full_identifiers_test])
            result = await self._pool_pre_flight.jsonset(cog_name, path=string, obj={}, nx=True)
        except aioredis.errors.ReplyError:
            async with self._lock:
                _cur_path = "."
                await self._pool_pre_flight.jsonset(cog_name, path=_cur_path, obj={}, nx=True)
                for i in full_identifiers:
                    if _cur_path.endswith("."):
                        _cur_path += self._escape_key(i)
                    else:
                        _cur_path += f".{self._escape_key(i)}"
                    await self._pool_pre_flight.jsonset(cog_name, path=_cur_path, obj={}, nx=True)

    @classmethod
    async def _execute(cls, query: str, *args, method: Optional[Callable] = None, **kwargs) -> Any:
        if method is None:
            method = cls._pool.execute
        log.invisible("Query: %s", query)
        if args:
            log.invisible("Args: %s", args)
        output = await method(query, *args, **kwargs)
        return output

    async def get(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = self._escape_key(_full_identifiers[0]), _full_identifiers[1:]
        full_identifiers = list(map(self._escape_key, full_identifiers))
        if not await self._pool.exists(cog_name):
            raise KeyError
        try:
            result = await self._execute(
                cog_name, *full_identifiers, method=self._pool_get.jsonget, no_escape=True
            )
        except aioredis.errors.ReplyError:
            raise KeyError
        if isinstance(result, str):
            result = json.loads(result)
        if isinstance(result, dict):
            if result == {}:
                raise KeyError
            result = self._unescape_dict_keys(result)
        return result

    async def set(self, identifier_data: IdentifierData, value=None):
        try:
            _full_identifiers = identifier_data.to_tuple()
            cog_name, full_identifiers = (
                self._escape_key(_full_identifiers[0]),
                _full_identifiers[1:],
            )
            identifier_string = "."
            identifier_string += ".".join(map(self._escape_key, full_identifiers))
            value_copy = json.loads(json.dumps(value))
            if isinstance(value_copy, dict):
                value_copy = self._escape_dict_keys(value_copy)
            await self._pre_flight(identifier_data)
            async with self._lock:
                await self._execute(
                    cog_name,
                    path=identifier_string,
                    obj=value_copy,
                    method=self._pool_set.jsonset,
                )
        except Exception:
            log.exception(f"Error saving data for {self.cog_name}")
            raise

    async def clear(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = self._escape_key(_full_identifiers[0]), _full_identifiers[1:]
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
        cog_name, full_identifiers = self._escape_key(_full_identifiers[0]), _full_identifiers[1:]
        identifier_string = "."
        identifier_string += ".".join(map(self._escape_key, full_identifiers))
        await self._pre_flight(identifier_data)

        async with self._lock:
            _type = await self._pool.jsontype(name=cog_name, path=identifier_string)

            if _type not in [None, "integer", "number", "object"]:
                raise StoredTypeError("The value is not a Integer or Float")
            elif _type in [None, "null"] or (
                _type == "object"
                and not await self._pool.jsonobjlen(name=cog_name, path=identifier_string)
            ):
                await self._execute(
                    cog_name,
                    path=identifier_string,
                    obj=default + 1,
                    method=self._pool_set.jsonset,
                )
                return default + 1
            elif _type == "object":
                raise StoredTypeError("The value is not a Integer or Float")
            else:
                applying = await self._execute(
                    cog_name,
                    path=identifier_string,
                    number=value,
                    method=self._pool.jsonnumincrby,
                )
                return json.loads(applying)

    async def toggle(
        self, identifier_data: IdentifierData, value: bool = None, default: Optional[bool] = None
    ) -> bool:
        _full_identifiers = identifier_data.to_tuple()
        cog_name, full_identifiers = self._escape_key(_full_identifiers[0]), _full_identifiers[1:]
        identifier_string = "."
        identifier_string += ".".join(map(self._escape_key, full_identifiers))
        await self._pre_flight(identifier_data)
        value = value if value is not None else default
        async with self._lock:
            _type = await self._pool.jsontype(name=cog_name, path=identifier_string)
            if _type not in [None, "null", "boolean", "object"]:
                raise StoredTypeError("The value is not a Boolean or Null")
            elif _type in [None, "null"] or (
                _type == "object"
                and not await self._pool.jsonobjlen(name=cog_name, path=identifier_string)
            ):
                await self._execute(
                    cog_name, path=identifier_string, obj=not value, method=self._pool_set.jsonset,
                )
                return not value
            elif _type == "object":
                raise StoredTypeError("The value is not a Boolean or Null")
            else:
                result = await self._execute(
                    cog_name, path=identifier_string, method=self._pool_get.jsonget, no_escape=True
                )
                result = not json.loads(result)
                await self._execute(
                    cog_name, path=identifier_string, obj=result, method=self._pool_set.jsonset,
                )
                return result

    @classmethod
    async def delete_all_data(cls, **kwargs) -> None:
        """Delete all data being stored by this driver."""
        await cls._pool.flushdb(async_op=True)
        await cls._pool.bgsave()

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        cogs = await cls._pool.keys("*", encoding="utf-8")
        for cog in cogs:
            cog = cls._unescape_key(cog)
            cog_ids = await cls._pool.jsonobjkeys(cog, ".")
            for cog_id in cog_ids:
                cog_id = cls._unescape_key(cog_id)
                yield cog, cog_id

    async def import_data(self, cog_data, custom_group_data):
        log.info(f"Converting Cog: {self.cog_name}")
        for category, all_data in cog_data:
            log.info(f"Converting cog category: {category}")
            ident_data = IdentifierData(
                self.cog_name,
                self.unique_cog_identifier,
                category,
                (),
                (),
                *ConfigCategory.get_pkey_info(category, custom_group_data),
            )
            try:
                await self.set(ident_data, all_data)
            except Exception:
                await self._individual_migrate(category, custom_group_data, all_data)

    async def _individual_migrate(self, category, custom_group_data, all_data):
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
            try:
                await self.set(ident_data, data)
            except Exception as err:
                log.critical(f"Error saving: {ident_data.__repr__()}: {data}", exc_info=err)

    @staticmethod
    def _escape_key(key: str) -> str:
        string = f"${base64.b16encode(key.encode()).decode()}"
        return string

    @staticmethod
    def _unescape_key(key: str) -> str:
        string = key[1:].encode()
        return base64.b16decode(string).decode()

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
