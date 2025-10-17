import argparse
import asyncio
import json
import logging
import os
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, Dict, Optional

import anyio
import httpx
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions


def _get_version() -> str:
    try:
        return version("mcp-transcoder")
    except PackageNotFoundError:
        return "0.0.0"


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-transcoder",
        description="STDIOクライアントとStreamableHTTP MCPサーバ間を仲介するアダプタ",
    )

    parser.add_argument(
        "url",
        help="接続先の StreamableHTTP MCP エンドポイント (例: https://example/mcp)",
    )

    parser.add_argument(
        "-H",
        "--headers",
        metavar=("KEY", "VALUE"),
        action="append",
        nargs=2,
        help="追加HTTPヘッダー (複数指定可)",
    )

    parser.add_argument(
        "--insecure",
        dest="insecure",
        action="store_true",
        help="TLS証明書検証を無効化",
    )
    parser.add_argument(
        "--no-insecure",
        dest="insecure",
        action="store_false",
        help="TLS証明書検証を有効化",
    )
    parser.set_defaults(insecure=False)

    # Timeout priority: CLI > MCP_PROXY_TIMEOUT env > default 120
    default_timeout_env = os.getenv("MCP_PROXY_TIMEOUT")
    default_timeout = int(default_timeout_env) if default_timeout_env else 120
    parser.add_argument(
        "--timeout",
        type=int,
        default=default_timeout,
        help="各リクエストの全体タイムアウト秒 (initialize/list_tools/call_tool等)",
    )

    parser.add_argument(
        "--ssl-cert-file",
        type=str,
        default=None,
        help="MCP接続時のみ使用するCAバンドルのパス",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="ログ出力の詳細度",
    )

    return parser.parse_args(argv)


def _build_headers(header_items: Optional[list[list[str]]]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if header_items:
        for key, value in header_items:
            headers[str(key)] = str(value)
    return headers


def _httpx_client_factory_builder(verify: Any) -> Callable[[Dict[str, str] | None, httpx.Timeout | None, httpx.Auth | None], httpx.AsyncClient]:
    def factory(headers: Dict[str, str] | None = None, timeout: httpx.Timeout | None = None, auth: httpx.Auth | None = None) -> httpx.AsyncClient:  # noqa: E501
        kwargs: Dict[str, Any] = {
            "follow_redirects": True,
            "verify": verify,
        }
        if headers is not None:
            kwargs["headers"] = headers
        if timeout is not None:
            kwargs["timeout"] = timeout
        if auth is not None:
            kwargs["auth"] = auth
        return httpx.AsyncClient(**kwargs)

    return factory


async def _forward_server_requests(
    server_session: ServerSession,
    client_session: ClientSession,
    request_timeout: timedelta,
) -> None:
    async for incoming in server_session.incoming_messages:
        # Exception from parsing incoming message
        if isinstance(incoming, Exception):
            logging.getLogger(__name__).exception("Error from client stream:", exc_info=incoming)
            continue

        # Notifications from client are not expected here for our proxy; ignore.
        if isinstance(incoming, types.ClientNotification):
            continue

        responder = incoming
        match responder.request.root:
            case types.ListToolsRequest():
                with responder:
                    result = await client_session.list_tools()
                    await responder.respond(types.ServerResult(result))

            case types.CallToolRequest(params=params):
                meta = responder.request_meta
                progress_token = meta.progressToken if meta else None

                async def progress_cb(progress: float, total: float | None, message: str | None) -> None:
                    if progress_token is not None:
                        await server_session.send_progress_notification(
                            progress_token=progress_token,
                            progress=progress,
                            total=total,
                            message=message,
                            related_request_id=responder.request_id,
                        )

                with responder:
                    result = await client_session.call_tool(
                        params.name,
                        params.arguments,
                        read_timeout_seconds=request_timeout,
                        progress_callback=progress_cb,
                    )
                    await responder.respond(types.ServerResult(result))

            case _:
                # Not implemented/pass-through for this proxy
                with responder:
                    await responder.respond(
                        types.ErrorData(
                            code=httpx.codes.NOT_IMPLEMENTED,
                            message="Not implemented in mcp-transcoder",
                            data={"method": responder.request.root.method},
                        )
                    )


async def async_main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level), format="[%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("mcp-transcoder")

    headers = _build_headers(args.headers)

    # Build verify argument for httpx
    verify: Any
    if args.insecure:
        verify = False
    elif args.ssl_cert_file:
        verify = args.ssl_cert_file
    else:
        # Respect system defaults / SSL_CERT_FILE env
        verify = True

    httpx_factory = _httpx_client_factory_builder(verify)

    # Stream timeouts
    timeout_seconds = float(args.timeout)
    request_timeout = timedelta(seconds=timeout_seconds)

    # Create STDIO server side
    async with stdio_server() as (srv_read, srv_write):
        # Initialize MCP ServerSession (acts as server towards STDIO client)
        init_options = InitializationOptions(
            server_name="mcp-transcoder",
            server_version=_get_version(),
            capabilities=types.ServerCapabilities(
                tools=types.ToolsCapability(listChanged=True),
            ),
            instructions=f"Proxy to {args.url}",
        )
        server_session = ServerSession(
            read_stream=srv_read,
            write_stream=srv_write,
            init_options=init_options,
            stateless=False,
        )
        # Start server-session receive loop immediately so downstream client can initialize
        await server_session.__aenter__()

        # Connect to remote StreamableHTTP MCP as client
        async with streamablehttp_client(
            url=args.url,
            headers=headers,
            timeout=timeout_seconds,
            sse_read_timeout=timeout_seconds,
            terminate_on_close=True,
            httpx_client_factory=httpx_factory,
        ) as (
            remote_read,
            remote_write,
            _get_session_id,
        ):
            # Handler for remote notifications -> forward to downstream client
            async def _remote_message_handler(message: Any) -> None:
                if isinstance(message, Exception):
                    logging.getLogger(__name__).exception("Error from remote stream:", exc_info=message)
                    return
                if isinstance(message, types.ServerNotification):
                    match message.root:
                        case types.ToolListChangedNotification():
                            await server_session.send_tool_list_changed()
                        case types.ResourceListChangedNotification():
                            await server_session.send_resource_list_changed()
                        case types.PromptListChangedNotification():
                            await server_session.send_prompt_list_changed()
                        case types.LoggingMessageNotification(params=params):
                            logging.getLogger("remote").log(
                                getattr(logging, str(params.level), logging.INFO),
                                "%s",
                                params.data,
                            )
                        case _:
                            pass

            client_session = ClientSession(
                read_stream=remote_read,
                write_stream=remote_write,
                read_timeout_seconds=request_timeout,
                message_handler=_remote_message_handler,
            )

            async with client_session:
                # Initialize remote session
                try:
                    init_res = await client_session.initialize()
                    logger.debug("Remote initialized: protocol=%s", init_res.protocolVersion)
                except Exception as e:
                    logger.exception("Failed to initialize remote MCP: %s", e)
                    raise

                # Start bridging: forward downstream requests to remote until closed
                await _forward_server_requests(server_session, client_session, request_timeout)
        # Ensure server_session is closed when remote connection exits
        await server_session.__aexit__(None, None, None)

    return 0


def main() -> None:
    try:
        anyio.run(async_main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
