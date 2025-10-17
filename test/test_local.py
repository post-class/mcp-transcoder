import os
from contextlib import asynccontextmanager

import anyio
import pytest

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


TEST_URL = os.environ.get("TEST_URL_LOCAL", "http://localhost:8931/mcp")


def _uv_env() -> dict[str, str]:
    env = dict(os.environ)
    # キャッシュ対策: 各テストでuvのキャッシュディレクトリを分ける
    env.setdefault("UV_CACHE_DIR", os.path.join(os.getcwd(), ".uv_cache"))
    return env


@asynccontextmanager
async def spawn_transcoder(url: str):
    # ローカルの実装を使うため uv run を使用
    server = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "-q",
            "mcp-transcoder",
            url,
        ],
        env=_uv_env(),
    )
    async with stdio_client(server):
        yield


@pytest.mark.anyio
async def test_list_tools_local():
    server = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "-q",
            "mcp-transcoder",
            TEST_URL,
        ],
        env=_uv_env(),
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            assert result.tools and len(result.tools) > 0


@pytest.mark.anyio
async def test_call_tool_browser_navigate_local():
    server = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "-q",
            "mcp-transcoder",
            TEST_URL,
        ],
        env=_uv_env(),
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # 存在すれば browser_navigate を呼び出す
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            if "browser_navigate" in names:
                res = await session.call_tool("browser_navigate", {"url": "https://example.com"})
                assert res.isError is False
            else:
                pytest.skip("browser_navigate ツールが提供されていません")


def test_cli_help_shows_options():
    # --help の出力に主要オプションが含まれること
    import subprocess

    env = _uv_env()
    proc = subprocess.run(
        ["uv", "run", "-q", "mcp-transcoder", "--help"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    assert "--headers" in out
    assert "--timeout" in out
    assert "--log-level" in out
    assert "--insecure" in out
    assert "--ssl-cert-file" in out

