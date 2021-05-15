import asyncio
import warnings

from aiohttp.abc import AbstractCookieJar
from aiohttp.web_response import Response

from redbot import json

from aiohttp import __version__ as __version__, http
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type, Union  # noqa
from aiohttp import hdrs as hdrs
from aiohttp.client import BaseConnector as BaseConnector
from aiohttp.client import ClientConnectionError as ClientConnectionError
from aiohttp.client import (
    ClientConnectorCertificateError as ClientConnectorCertificateError,
)
from aiohttp.client import ClientConnectorError as ClientConnectorError
from aiohttp.client import ClientConnectorSSLError as ClientConnectorSSLError
from aiohttp.client import ClientError as ClientError
from aiohttp.client import ClientHttpProxyError as ClientHttpProxyError
from aiohttp.client import ClientOSError as ClientOSError
from aiohttp.client import ClientPayloadError as ClientPayloadError
from aiohttp.client import ClientProxyConnectionError as ClientProxyConnectionError
from aiohttp.client import ClientRequest as ClientRequest
from aiohttp.client import ClientResponse as ClientResponse
from aiohttp.client import ClientResponseError as ClientResponseError
from aiohttp.client import ClientSession as ClientSession
from aiohttp.client import ClientSSLError as ClientSSLError
from aiohttp.client import ClientTimeout as ClientTimeout
from aiohttp.client import ClientWebSocketResponse as ClientWebSocketResponse
from aiohttp.client import ContentTypeError as ContentTypeError
from aiohttp.client import Fingerprint as Fingerprint
from aiohttp.client import InvalidURL as InvalidURL
from aiohttp.client import NamedPipeConnector as NamedPipeConnector
from aiohttp.client import RequestInfo as RequestInfo
from aiohttp.client import ServerConnectionError as ServerConnectionError
from aiohttp.client import ServerDisconnectedError as ServerDisconnectedError
from aiohttp.client import ServerFingerprintMismatch as ServerFingerprintMismatch
from aiohttp.client import ServerTimeoutError as ServerTimeoutError
from aiohttp.client import TCPConnector as TCPConnector
from aiohttp.client import TooManyRedirects as TooManyRedirects
from aiohttp.client import UnixConnector as UnixConnector
from aiohttp.client import WSServerHandshakeError as WSServerHandshakeError
from aiohttp.client import request as request
from aiohttp.cookiejar import CookieJar as CookieJar
from aiohttp.cookiejar import DummyCookieJar as DummyCookieJar
from aiohttp.formdata import FormData as FormData
from aiohttp.helpers import BasicAuth as BasicAuth, sentinel
from aiohttp.helpers import ChainMapProxy as ChainMapProxy
from aiohttp.http import HttpVersion as HttpVersion
from aiohttp.http import HttpVersion10 as HttpVersion10
from aiohttp.http import HttpVersion11 as HttpVersion11
from aiohttp.http import WebSocketError as WebSocketError
from aiohttp.http import WSCloseCode as WSCloseCode
from aiohttp.http import WSMessage as WSMessage
from aiohttp.http import WSMsgType as WSMsgType
from aiohttp.multipart import (
    BadContentDispositionHeader as BadContentDispositionHeader,
)
from aiohttp.multipart import BadContentDispositionParam as BadContentDispositionParam
from aiohttp.multipart import BodyPartReader as BodyPartReader
from aiohttp.multipart import MultipartReader as MultipartReader
from aiohttp.multipart import MultipartWriter as MultipartWriter
from aiohttp.multipart import (
    content_disposition_filename as content_disposition_filename,
)
from aiohttp.multipart import parse_content_disposition as parse_content_disposition
from aiohttp.payload import PAYLOAD_REGISTRY as PAYLOAD_REGISTRY
from aiohttp.payload import AsyncIterablePayload as AsyncIterablePayload
from aiohttp.payload import BufferedReaderPayload as BufferedReaderPayload
from aiohttp.payload import BytesIOPayload as BytesIOPayload
from aiohttp.payload import BytesPayload as BytesPayload
from aiohttp.payload import IOBasePayload as IOBasePayload
from aiohttp.payload import JsonPayload as JsonPayload
from aiohttp.payload import Payload as Payload
from aiohttp.payload import StringIOPayload as StringIOPayload
from aiohttp.payload import StringPayload as StringPayload
from aiohttp.payload import TextIOPayload as TextIOPayload
from aiohttp.payload import get_payload as get_payload
from aiohttp.payload import payload_type as payload_type
from aiohttp.payload_streamer import streamer as streamer
from aiohttp.resolver import AsyncResolver as AsyncResolver
from aiohttp.resolver import DefaultResolver as DefaultResolver
from aiohttp.resolver import ThreadedResolver as ThreadedResolver
from aiohttp.signals import Signal as Signal
from aiohttp.streams import EMPTY_PAYLOAD as EMPTY_PAYLOAD
from aiohttp.streams import DataQueue as DataQueue
from aiohttp.streams import EofStream as EofStream
from aiohttp.streams import FlowControlDataQueue as FlowControlDataQueue
from aiohttp.streams import StreamReader as StreamReader
from aiohttp.tracing import TraceConfig as TraceConfig
from aiohttp.tracing import (
    TraceConnectionCreateEndParams as TraceConnectionCreateEndParams,
)
from aiohttp.tracing import (
    TraceConnectionCreateStartParams as TraceConnectionCreateStartParams,
)
from aiohttp.tracing import (
    TraceConnectionQueuedEndParams as TraceConnectionQueuedEndParams,
)
from aiohttp.tracing import (
    TraceConnectionQueuedStartParams as TraceConnectionQueuedStartParams,
)
from aiohttp.tracing import (
    TraceConnectionReuseconnParams as TraceConnectionReuseconnParams,
)
from aiohttp.tracing import TraceDnsCacheHitParams as TraceDnsCacheHitParams
from aiohttp.tracing import TraceDnsCacheMissParams as TraceDnsCacheMissParams
from aiohttp.tracing import (
    TraceDnsResolveHostEndParams as TraceDnsResolveHostEndParams,
)
from aiohttp.tracing import (
    TraceDnsResolveHostStartParams as TraceDnsResolveHostStartParams,
)
from aiohttp.tracing import TraceRequestChunkSentParams as TraceRequestChunkSentParams
from aiohttp.tracing import TraceRequestEndParams as TraceRequestEndParams
from aiohttp.tracing import TraceRequestExceptionParams as TraceRequestExceptionParams
from aiohttp.tracing import TraceRequestRedirectParams as TraceRequestRedirectParams
from aiohttp.tracing import TraceRequestStartParams as TraceRequestStartParams
from aiohttp.tracing import (
    TraceResponseChunkReceivedParams as TraceResponseChunkReceivedParams,
)

__all__ = (
    "hdrs",
    # client
    "BaseConnector",
    "ClientConnectionError",
    "ClientConnectorCertificateError",
    "ClientConnectorError",
    "ClientConnectorSSLError",
    "ClientError",
    "ClientHttpProxyError",
    "ClientOSError",
    "ClientPayloadError",
    "ClientProxyConnectionError",
    "ClientResponse",
    "ClientRequest",
    "ClientResponseError",
    "ClientSSLError",
    "ClientSession",
    "ClientTimeout",
    "ClientWebSocketResponse",
    "ContentTypeError",
    "Fingerprint",
    "InvalidURL",
    "RequestInfo",
    "ServerConnectionError",
    "ServerDisconnectedError",
    "ServerFingerprintMismatch",
    "ServerTimeoutError",
    "TCPConnector",
    "TooManyRedirects",
    "UnixConnector",
    "NamedPipeConnector",
    "WSServerHandshakeError",
    "request",
    # cookiejar
    "CookieJar",
    "DummyCookieJar",
    # formdata
    "FormData",
    # helpers
    "BasicAuth",
    "ChainMapProxy",
    # http
    "HttpVersion",
    "HttpVersion10",
    "HttpVersion11",
    "WSMsgType",
    "WSCloseCode",
    "WSMessage",
    "WebSocketError",
    # multipart
    "BadContentDispositionHeader",
    "BadContentDispositionParam",
    "BodyPartReader",
    "MultipartReader",
    "MultipartWriter",
    "content_disposition_filename",
    "parse_content_disposition",
    # payload
    "AsyncIterablePayload",
    "BufferedReaderPayload",
    "BytesIOPayload",
    "BytesPayload",
    "IOBasePayload",
    "JsonPayload",
    "PAYLOAD_REGISTRY",
    "Payload",
    "StringIOPayload",
    "StringPayload",
    "TextIOPayload",
    "get_payload",
    "payload_type",
    # payload_streamer
    "streamer",
    # resolver
    "AsyncResolver",
    "DefaultResolver",
    "ThreadedResolver",
    # signals
    "Signal",
    "DataQueue",
    "EMPTY_PAYLOAD",
    "EofStream",
    "FlowControlDataQueue",
    "StreamReader",
    # tracing
    "TraceConfig",
    "TraceConnectionCreateEndParams",
    "TraceConnectionCreateStartParams",
    "TraceConnectionQueuedEndParams",
    "TraceConnectionQueuedStartParams",
    "TraceConnectionReuseconnParams",
    "TraceDnsCacheHitParams",
    "TraceDnsCacheMissParams",
    "TraceDnsResolveHostEndParams",
    "TraceDnsResolveHostStartParams",
    "TraceRequestChunkSentParams",
    "TraceRequestEndParams",
    "TraceRequestExceptionParams",
    "TraceRequestRedirectParams",
    "TraceRequestStartParams",
    "TraceResponseChunkReceivedParams",
    "DEFAULT_JSON_ENCODER",
    "DEFAULT_JSON_DECODER",
)  # type: Tuple[str, ...]

from aiohttp.typedefs import JSONDecoder, JSONEncoder, LooseCookies, LooseHeaders
import aiohttp.web_ws
import aiohttp

try:
    from aiohttp.worker import GunicornWebWorker, GunicornUVLoopWebWorker  # noqa

    __all__ += ("GunicornWebWorker", "GunicornUVLoopWebWorker")
except ImportError:  # pragma: no cover
    pass


class ClientSession(ClientSession):
    def __init__(
        self,
        *,
        connector: Optional[BaseConnector] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        cookies: Optional[LooseCookies] = None,
        headers: Optional[LooseHeaders] = None,
        skip_auto_headers: Optional[Iterable[str]] = None,
        auth: Optional[BasicAuth] = None,
        json_serialize: JSONEncoder = json.dumps,
        request_class: Type[ClientRequest] = ClientRequest,
        response_class: Type[ClientResponse] = ClientResponse,
        ws_response_class: Type[ClientWebSocketResponse] = ClientWebSocketResponse,  # noqa
        version: HttpVersion = http.HttpVersion11,
        cookie_jar: Optional[AbstractCookieJar] = None,
        connector_owner: bool = True,
        raise_for_status: bool = False,
        read_timeout: Union[float, object] = sentinel,
        conn_timeout: Optional[float] = None,
        timeout: Union[object, ClientTimeout] = sentinel,
        auto_decompress: bool = True,
        trust_env: bool = False,
        requote_redirect_url: bool = True,
        trace_configs: Optional[List[TraceConfig]] = None,
    ) -> None:
        super().__init__(
            connector=connector,
            loop=loop,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            json_serialize=json_serialize,
            request_class=request_class,
            response_class=response_class,
            ws_response_class=ws_response_class,
            version=version,
            cookie_jar=cookie_jar,
            connector_owner=connector_owner,
            raise_for_status=raise_for_status,
            read_timeout=read_timeout,
            conn_timeout=conn_timeout,
            timeout=timeout,
            auto_decompress=auto_decompress,
            trust_env=trust_env,
            requote_redirect_url=requote_redirect_url,
            trace_configs=trace_configs,
        )


class WSMessage(WSMessage):
    def json(self, *, loads: Callable[[Any], Any] = json.loads) -> Any:
        """Return parsed JSON data.

        .. versionadded:: 0.22
        """
        return loads(self.data)


def json_response(
    data: Any = sentinel,
    *,
    text: str = None,
    body: bytes = None,
    status: int = 200,
    reason: Optional[str] = None,
    headers: LooseHeaders = None,
    content_type: str = "application/json",
    dumps: JSONEncoder = json.dumps,
) -> Response:
    if data is not sentinel:
        if text or body:
            raise ValueError("only one of data, text, or body should be specified")
        else:
            text = dumps(data)
    return Response(
        text=text,
        body=body,
        status=status,
        reason=reason,
        headers=headers,
        content_type=content_type,
    )


class WebSocketResponse(aiohttp.web_ws.WebSocketResponse):
    async def send_json(
        self, data: Any, compress: Optional[bool] = None, *, dumps: JSONEncoder = json.dumps
    ) -> None:
        await self.send_str(dumps(data), compress=compress)

    async def receive_json(
        self, *, loads: JSONDecoder = json.loads, timeout: Optional[float] = None
    ) -> Any:
        data = await self.receive_str(timeout=timeout)
        return loads(data)


class JsonPayload(BytesPayload):
    def __init__(
        self,
        value: Any,
        encoding: str = "utf-8",
        content_type: str = "application/json",
        dumps: JSONEncoder = json.dumps,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            dumps(value).encode(encoding),
            content_type=content_type,
            encoding=encoding,
            *args,
            **kwargs,
        )


DEFAULT_JSON_ENCODER = aiohttp.typedefs.DEFAULT_JSON_ENCODER = json.dumps
DEFAULT_JSON_DECODER = aiohttp.typedefs.DEFAULT_JSON_DECODER = json.loads
aiohttp.JsonPayload = JsonPayload
aiohttp.WSMessage = WSMessage
aiohttp.web_response.json_response = json_response
aiohttp.web_ws.WebSocketResponse = WebSocketResponse
