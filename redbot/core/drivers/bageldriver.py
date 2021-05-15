import asyncio
import getpass
from typing import Any, Dict, Final, Optional, Union, AsyncIterator, Tuple

import aiohttp
from aiohttp import ClientTimeout, JsonPayload

from redbot import json
from redbot.core import errors
from redbot.core.drivers.log import log
from secrets import compare_digest


from .base import BaseDriver, IdentifierData, ConfigCategory

__all__ = ["BagelDriver"]


_GET_ENDPOINT: Final[str] = "{base}/config/get"
_AITER_COGS_ENDPOINT: Final[str] = "{base}/config/cogs"
_SET_ENDPOINT: Final[str] = "{base}/config/set"
_INCREMENT_ENDPOINT: Final[str] = "{base}/config/increment"
_TOGGLE_ENDPOINT: Final[str] = "{base}/config/toggle"
_CLEAR_ENDPOINT: Final[str] = "{base}/config/clear"
_CLEAR_ALL_ENDPOINT: Final[str] = "{base}/config/clear_all"


# noinspection PyProtectedMember
class BagelDriver(BaseDriver):
    __token: Optional[str] = None
    __base_url: Optional[str] = None
    __sockets: Optional[str] = None
    __timeout: Optional[ClientTimeout] = None
    __connector: Optional[aiohttp.UnixConnector] = None
    __connector_owner: bool = False
    __default_headers: Dict[str, Any] = {}
    __serializer: str = json.json_module

    @property
    def serializer(self):
        return self.__serializer

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        host = storage_details["host"]
        password = storage_details["password"]
        sockets = storage_details["unix_socket"]
        timeout = storage_details.get("timeout", 5)
        cls.__token = password
        cls.__base_url = host
        cls.__sockets = sockets
        cls.__timeout = ClientTimeout(total=timeout)
        cls.__connector = (
            aiohttp.UnixConnector(path=cls.__sockets, keepalive_timeout=15.0, limit=0)
            if cls.__sockets
            else None
        )
        cls.__connector_owner = False if cls.__connector else True
        cls.__default_headers = {"Authorization": cls.__token}

    @classmethod
    async def teardown(cls) -> None:
        if cls.__connector is not None:
            await cls.__connector.close()

    @staticmethod
    def get_config_details():
        host = (
            input(
                f"Enter the API server's base url. "
                f"If left blank, Red will try the following, in order:\n"
                f" - http://localhost:8005.\n"
                f"> "
            )
            or "http://localhost:8005"
        )
        if host.endswith("/"):
            host = host[:-1]
        password = getpass.getpass(
            f"Enter the API server password. The input will be hidden.\n"
            f"  NOTE: If the server requires no password, enter NONE (Case sensitive).\n"
            f"When NONE is entered, this will default to:\n"
            f" - No password.\n"
            f"> "
        )
        if compare_digest(password, "NONE"):
            password = None
        sockets = (
            input(
                f"Enter the path full to your UNIX socket file. "
                f"If left blank, Red will use a TCP connector:\n"
                f"> "
            )
            or None
        )
        print("Enter the connection timeout.\nIf left blank, this will default to 5:\n - 5.\n")
        while True:
            timeout = input("> ") or 5
            if timeout == 5:
                break

            try:
                timeout = int(timeout)
                if timeout < 1:
                    raise ValueError
            except ValueError:
                print("Timeout must be a number greater than 0")
            else:
                break
        return {"host": host, "password": password, "unix_socket": sockets, "timeout": timeout}

    async def get(self, identifier_data: IdentifierData):
        full_identifiers = identifier_data.to_dict()
        try:
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=self.__connector,
                timeout=self.__timeout,
                connector_owner=self.__connector_owner,
                headers=self.__default_headers,
            ) as session:
                async with session.post(
                    url=_GET_ENDPOINT.replace("{base}", self.__base_url),
                    data=JsonPayload({"identifier": full_identifiers}, dumps=json.dumps),
                ) as response:
                    if response.status == 200:
                        return await response.json(loads=json.loads)
                    else:
                        raise KeyError
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await self.get(identifier_data=identifier_data)

    async def set(self, identifier_data: IdentifierData, value=None):
        full_identifiers = identifier_data.to_dict()
        try:
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=self.__connector,
                timeout=self.__timeout,
                connector_owner=self.__connector_owner,
                headers=self.__default_headers,
            ) as session:
                async with session.put(
                    url=_SET_ENDPOINT.replace("{base}", self.__base_url),
                    data=JsonPayload(
                        {
                            "identifier": full_identifiers,
                            "config_data": json.dumps(value),
                        },
                        dumps=json.dumps,
                    ),
                ) as response:
                    response_output = await response.json(loads=json.loads)
                    if response.status == 200:
                        return response_output.get("value")
                    else:
                        raise errors.ConfigError(str(response_output))
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await self.set(identifier_data=identifier_data, value=value)

    async def clear(self, identifier_data: IdentifierData):
        full_identifiers = identifier_data.to_dict()
        try:
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=self.__connector,
                timeout=self.__timeout,
                connector_owner=self.__connector_owner,
                headers=self.__default_headers,
            ) as session:
                async with session.put(
                    url=_CLEAR_ENDPOINT.replace("{base}", self.__base_url),
                    data=JsonPayload({"identifier": full_identifiers}, dumps=json.dumps),
                ) as response:
                    response_output = await response.json(loads=json.loads)
                    if response.status == 200:
                        return response_output.get("value")
                    else:
                        raise errors.ConfigError(str(response_output))
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await self.clear(identifier_data=identifier_data)

    async def inc(
        self,
        identifier_data: IdentifierData,
        value: Union[int, float],
        default: Union[int, float] = 0,
    ) -> Union[int, float]:
        try:
            full_identifiers = identifier_data.to_dict()
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=self.__connector,
                timeout=self.__timeout,
                connector_owner=self.__connector_owner,
                headers=self.__default_headers,
            ) as session:
                async with session.put(
                    url=_INCREMENT_ENDPOINT.replace("{base}", self.__base_url),
                    data=JsonPayload(
                        {
                            "identifier": full_identifiers,
                            "config_data": json.dumps(value),
                            "default": json.dumps(default),
                        },
                        dumps=json.dumps,
                    ),
                ) as response:
                    response_output = await response.json(loads=json.loads)
                    if response.status == 200:
                        return response_output.get("value")
                    else:
                        raise errors.ConfigError(str(response_output))
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await self.inc(identifier_data=identifier_data, value=value, default=default)

    async def toggle(
        self, identifier_data: IdentifierData, value: bool = None, default: Optional[bool] = None
    ) -> bool:
        try:
            full_identifiers = identifier_data.to_dict()
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=self.__connector,
                timeout=self.__timeout,
                connector_owner=self.__connector_owner,
                headers=self.__default_headers,
            ) as session:
                async with session.put(
                    url=_TOGGLE_ENDPOINT.replace("{base}", self.__base_url),
                    data=JsonPayload(
                        {
                            "identifier": full_identifiers,
                            "config_data": json.dumps(value),
                            "default": json.dumps(default),
                        },
                        dumps=json.dumps,
                    ),
                ) as response:
                    response_output = await response.json(loads=json.loads)
                    if response.status == 200:
                        return response_output.get("value")
                    else:
                        raise errors.ConfigError(str(response_output))
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await self.toggle(identifier_data=identifier_data, value=value, default=default)

    @classmethod
    async def delete_all_data(cls, **kwargs) -> None:
        """Delete all data being stored by this driver."""
        try:
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=cls.__connector,
                timeout=cls.__timeout,
                connector_owner=cls.__connector_owner,
                headers=cls.__default_headers,
            ) as session:
                async with session.put(
                    url=_CLEAR_ALL_ENDPOINT.replace("{base}", cls.__base_url),
                    param={"i_want_to_do_this": True},
                ) as response:
                    response_output = await response.json(loads=json.loads)
                    if response.status == 200:
                        return response_output.get("value")
                    else:
                        raise errors.ConfigError(str(response_output))
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await cls.delete_all_data(**kwargs)

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        try:
            async with aiohttp.ClientSession(
                json_serialize=json.dumps,
                connector=cls.__connector,
                timeout=cls.__timeout,
                connector_owner=cls.__connector_owner,
                headers=cls.__default_headers,
            ) as session:
                async with session.post(
                    url=_AITER_COGS_ENDPOINT.replace("{base}", cls.__base_url),
                ) as response:
                    return await response.json(loads=json.loads)
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return await cls.aiter_cogs()

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
